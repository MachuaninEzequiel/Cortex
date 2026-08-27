#!/usr/bin/env python3
"""Oráculo P12A-5 — SpecService + NoteService.

S01 spec básica (writer/index/episodic)
S02 proposal modes/errores exactos
S03 hooks + tasks-required (contenido completo)
S04 orden index→sync→session→episodic + session failure best-effort
S05 duplicate/invalid hooks
S06 note básica (contenido/index/episodic)
S07 note handoff con campos completos
S08 rollback por semantic
S09 rollback por episodic
S10 remember=False + sync

Normalizaciones: {{ROOT}}, {{DATE}}, {{TS}}, {{SID}}, {{FP}}. El contrato de
filenames/contenido se conserva salvo valores aleatorios/reloj/fingerprint.
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))


class Semantic:
    def __init__(self, events=None, fail=False):
        self.events = events if events is not None else []
        self.fail = fail
        self.indexed = []
        self.synced = 0
    def index_file(self, rel):
        self.events.append("index")
        if self.fail: raise RuntimeError("semantic indexing failed")
        self.indexed.append(rel); return True
    def sync(self):
        self.events.append("sync"); self.synced += 1; return 0


class Episodic:
    def __init__(self, events=None, fail=False):
        self.events = events if events is not None else []
        self.fail = fail
        self.added = []
    def add(self, **kwargs):
        self.events.append("episodic")
        if self.fail: raise RuntimeError("episodic add failed")
        self.added.append(kwargs); return kwargs


class Sessions:
    def __init__(self, events, fail=False): self.events=events; self.fail=fail; self.calls=[]
    def open(self, **kwargs):
        self.events.append("session"); self.calls.append(kwargs)
        if self.fail: raise RuntimeError("session open failed")
        return SimpleNamespace(session_id=kwargs["spec_id"], is_gitless=False)


def pylist(xs): return repr(list(xs))
def req_report(req):
    if not req: return "episodic=[]"
    r=req[0]
    return "\n".join([
        "episodic_content="+json.dumps(r["content"], ensure_ascii=False),
        f"episodic_type={r['memory_type']}", f"episodic_tags={pylist(r['tags'])}",
        f"episodic_files={pylist(r['files'])}",
        "episodic_meta="+json.dumps(r.get("extra_metadata",{}), ensure_ascii=False, sort_keys=True, separators=(",",":")),
    ])


def run(work: Path) -> str:
    from cortex.services.note_service import NoteService
    from cortex.services.spec_service import SpecService
    from cortex.session import VerificationHook
    blocks=[]
    def emit(name, fn):
        try: blocks.append(f"### {name}\nrc=0\n{fn()}")
        except Exception as e: blocks.append(f"### {name}\nrc=1\n{type(e).__name__}: {e}")
    def vault(name):
        p=work/name; p.mkdir(parents=True, exist_ok=True); return p

    def s01():
        v=vault("s01"); sem=Semantic(); ep=Episodic()
        svc=SpecService(v,sem,ep,context_metadata={"workspace":"obra07"})
        r=svc.create(title="Auth JWT",goal="Refresh tokens",requirements=["rotar","revocar"],files_in_scope=["src/auth.py"],tags=["backend"])
        return f"path={r.path}\nsession={r.session}\nindexed={pylist(sem.indexed)}\n"+req_report(ep.added)+"\n---\n"+r.path.read_text()
    def s02():
        v=vault("s02")
        out=[]
        for mode,conf in [("required",False),("invalid-mode",False)]:
            try: SpecService(v,Semantic(),Episodic()).create(title="X",goal="Y",proposal_mode=mode,proposal_confirmed=conf)
            except Exception as e: out.append(f"{mode}={type(e).__name__}: {e}")
        ok=SpecService(v,Semantic(),Episodic()).create(title="Req OK",goal="Y",proposal_mode="required",proposal_confirmed=True,remember=False)
        out.append(f"confirmed_exists={ok.path.exists()}")
        return "\n".join(out)
    def s03():
        v=vault("s03"); sem=Semantic(); ep=Episodic()
        hooks=[VerificationHook(name="tests",command="pytest"),{"name":"lint","command":"ruff check .","required":False}]
        r=SpecService(v,sem,ep).create(title="Hooks",goal="Probar",verification_hooks=hooks,with_tasks=True,remember=False)
        return f"path={r.path}\nindexed={pylist(sem.indexed)}\n---\n"+r.path.read_text()
    def s04():
        ev=[]; v=vault("s04"); ss=Sessions(ev)
        svc=SpecService(v,Semantic(ev),Episodic(ev),session_service=ss)
        r=svc.create(title="Ordered",goal="Goal",sync_vault=True)
        call=ss.calls[0]
        ev2=[]; ss2=Sessions(ev2,fail=True); v2=vault("s04fail")
        r2=SpecService(v2,Semantic(ev2),Episodic(ev2),session_service=ss2).create(title="Resilient",goal="")
        return "\n".join([f"events={pylist(ev)}",f"session_id={r.session.session_id}",f"open_summary={call['spec_summary']}",f"fail_events={pylist(ev2)}",f"fail_session={r2.session}",f"fail_exists={r2.path.exists()}"])
    def s05():
        v=vault("s05"); svc=SpecService(v,Semantic(),Episodic()); out=[]
        try: svc.create(title="Dup",goal="x",verification_hooks=[{"name":"tests","command":"a"},{"name":"tests","command":"b"}])
        except Exception as e: out.append(f"dup={type(e).__name__}: {e}")
        try: svc.create(title="Bad",goal="x",verification_hooks=[{"name":"tests"}])
        except Exception as e: out.append(f"invalid={type(e).__name__}: {{{{HOOK_ERR}}}}")
        return "\n".join(out)
    def s06():
        v=vault("n06"); sem=Semantic(); ep=Episodic()
        svc=NoteService(v,sem,ep,context_metadata={"workspace":"obra07"})
        p=svc.create(title="Happy",spec_summary="Survive",changes_made=["uno","dos"],files_touched=["src/a.py"],key_decisions=["usar Rust"],tags=["backend"])
        return f"path={p}\nindexed={pylist(sem.indexed)}\n"+req_report(ep.added)+"\n---\n"+p.read_text()
    def s07():
        v=vault("n07"); sem=Semantic(); ep=Episodic(); svc=NoteService(v,sem,ep)
        p=svc.create(title="Handoff",spec_summary="seguir",handoff=True,blockers=["B1"],verified_state=["tests"],unverified_claims=["perf"],suggested_skills=["rust"],tags=["x"],remember=False,gitless=True,task_type="bugfix",tasks=[{"id":"T1","status":"done"}],tasks_total=1,tasks_done=1)
        return f"path={p}\nindexed={pylist(sem.indexed)}\n---\n"+p.read_text()
    def s08():
        v=vault("n08"); svc=NoteService(v,Semantic(fail=True),Episodic()); out=[]
        try: svc.create(title="Rollback semantic",spec_summary="x")
        except Exception as e: out.append(f"error={type(e).__name__}: {e}")
        out.append(f"files={pylist((v/'sessions').glob('*.md'))}")
        return "\n".join(out)
    def s09():
        v=vault("n09"); svc=NoteService(v,Semantic(),Episodic(fail=True)); out=[]
        try: svc.create(title="Rollback episodic",spec_summary="x")
        except Exception as e: out.append(f"error={type(e).__name__}: {e}")
        out.append(f"files={pylist((v/'sessions').glob('*.md'))}")
        return "\n".join(out)
    def s10():
        ev=[]; v=vault("n10"); sem=Semantic(ev); ep=Episodic(ev)
        p=NoteService(v,sem,ep).create(title="No remember",spec_summary="x",remember=False,sync_vault=True)
        return f"events={pylist(ev)}\nepisodic={pylist(ep.added)}\nexists={p.exists()}"
    for n,fn in [("S01 spec básica",s01),("S02 proposal",s02),("S03 hooks tasks",s03),("S04 session order",s04),("S05 hooks errors",s05),("S06 note básica",s06),("S07 note handoff",s07),("S08 rollback semantic",s08),("S09 rollback episodic",s09),("S10 note no-remember sync",s10)]: emit(n,fn)
    return "".join(blocks)


def normalize(s: str, work: Path) -> str:
    s=s.replace(str(work),"{{ROOT}}")
    s=re.sub(r"(created_at|updated_at): '[^']+'",r"\1: '{{TS}}'",s)
    s=re.sub(r"fingerprint: [0-9a-f]{64}","fingerprint: {{FP}}",s)
    s=re.sub(r"[0-9a-f]{12}","{{SID}}",s)
    s=re.sub(r"\d{4}-\d{2}-\d{2}","{{DATE}}",s)
    return s if s.endswith("\n") else s+"\n"


def main():
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest="cmd",required=True)
    for n in ("build","verify"):
        p=sub.add_parser(n); p.add_argument("--out",type=Path,default=ROOT/"bench/parity/golden_p12a5")
    ns=ap.parse_args(); dest=ns.out/"golden_p12a5.txt"
    with tempfile.TemporaryDirectory() as t:
        content=normalize(run(Path(t)),Path(t))
        if ns.cmd=="build": ns.out.mkdir(parents=True,exist_ok=True); dest.write_text(content); print(f"[capturado] {dest}"); return 0
        old=dest.read_text()
        if old==content: print("[PASS] golden_p12a5.txt\n\n✅ ORÁCULO DETERMINISTA"); return 0
        print("[FAIL]"); print("\n".join(list(difflib.unified_diff(old.splitlines(),content.splitlines(),lineterm=""))[:80])); return 1
if __name__=="__main__": raise SystemExit(main())
