"""
Property-based testing for RRF fusion algorithm in HybridSearch.
"""
from hypothesis import given
from hypothesis import strategies as st

from cortex.models import EpisodicHit, MemoryEntry, SemanticDocument
from cortex.retrieval.hybrid_search import HybridSearch

# Strategy for generating MemoryEntry
memory_entry_strategy = st.builds(
    MemoryEntry,
    id=st.uuids().map(lambda u: f"mem_{u.hex[:8]}"),
    content=st.text(min_size=1, max_size=100),
    memory_type=st.sampled_from(["general", "bug", "feature"]),
    tags=st.lists(st.text(min_size=1, max_size=10), max_size=3),
    files=st.lists(st.text(min_size=1, max_size=20), max_size=2),
)

# Strategy for EpisodicHit
episodic_hit_strategy = st.builds(
    EpisodicHit,
    entry=memory_entry_strategy,
    score=st.floats(min_value=0.0, max_value=1.0),
)

# Strategy for SemanticDocument
semantic_document_strategy = st.builds(
    SemanticDocument,
    path=st.text(min_size=1, max_size=20).map(lambda p: f"vault/{p}.md"),
    title=st.text(min_size=1, max_size=50),
    content=st.text(min_size=1, max_size=100),
    score=st.floats(min_value=0.0, max_value=1.0),
)



@given(
    episodic_hits=st.lists(episodic_hit_strategy, max_size=10),
    semantic_hits=st.lists(semantic_document_strategy, max_size=10),
    top_k=st.integers(min_value=1, max_value=20),
)
def test_rrf_fusion_properties(episodic_hits, semantic_hits, top_k):
    # Ensure distinct IDs/paths for the generated hits
    # Hypothesis can generate duplicates, but the algorithm expects unique keys 
    # per source, so we'll just let it run. If there are duplicates, 
    # RRF combines their scores correctly or overwrites map, which is fine to test.
    
    hybrid_search = HybridSearch(
        episodic=None,  # type: ignore
        semantic=None,  # type: ignore
        top_k=5,
        episodic_weight=1.0,
        semantic_weight=1.0,
        adaptive_weights=False,
    )
    
    unified = hybrid_search._rrf_fuse(
        episodic_hits=episodic_hits,
        semantic_hits=semantic_hits,
        top_k=top_k,
    )
    
    # 1. Length constraint
    assert len(unified) <= top_k
    
    # Total unique items expected
    unique_ep = len({h.entry.id for h in episodic_hits})
    unique_sem = len({h.path for h in semantic_hits})
    total_unique = unique_ep + unique_sem
    assert len(unified) <= total_unique
    
    if total_unique == 0:
        assert len(unified) == 0
        return
        
    # 2. Ranking should be sorted by fused score descending
    scores = [hit.score for hit in unified]
    assert scores == sorted(scores, reverse=True)
    
    # 3. Score bounds
    for hit in unified:
        assert hit.score > 0.0
        # The max score for an item is weight / (RRF_K + 1) -> 1.0 / 61
        # If it appeared multiple times (hypothesis duplicates), could be higher, 
        # but always > 0
    
    # 4. Source mapping correctness
    for hit in unified:
        if hit.source == "episodic":
            assert hit.entry is not None
            assert hit.doc is None
            # Must exist in input
            assert any(e.entry.id == hit.entry.id for e in episodic_hits)
        else:
            assert hit.doc is not None
            assert hit.entry is None
            # Must exist in input
            assert any(s.path == hit.doc.path for s in semantic_hits)

