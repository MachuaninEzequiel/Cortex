// ============================================================================
// Cortex WebGraph — Modern Interactive Experience & Visual Engine
// ============================================================================

// DOM Elements
const modeSelect = document.getElementById("mode");
const modeTabs = document.querySelectorAll(".mode-tab");
const projectFilter = document.getElementById("project-filter");
const typeFilter = document.getElementById("type-filter");
const timeFilter = document.getElementById("time-filter");
const edgeFilter = document.getElementById("edge-filter");
const labelModeSelect = document.getElementById("label-mode");
const layoutSpacingSelect = document.getElementById("layout-spacing");
const depthSelect = document.getElementById("depth");

const searchInput = document.getElementById("search");
const searchButton = document.getElementById("search-button");
const searchCounter = document.getElementById("search-counter");
const reloadButton = document.getElementById("reload");
const resetButton = document.getElementById("reset-view");
const fitButton = document.getElementById("fit-view");
const togglePhysicsButton = document.getElementById("toggle-physics");
const physicsIndicator = document.getElementById("physics-indicator");
const physicsLabel = document.getElementById("physics-label");

const openNodeButton = document.getElementById("open-node");
const loadSubgraphButton = document.getElementById("load-subgraph");
const detailTitle = document.getElementById("detail-title");
const detailSummary = document.getElementById("detail-summary");
const detailMeta = document.getElementById("detail-meta");
const detailTypeBadge = document.getElementById("detail-type-badge");
const relationList = document.getElementById("relation-list");
const relationCount = document.getElementById("relation-count");
const neighborList = document.getElementById("neighbor-list");
const neighborCount = document.getElementById("neighbor-count");

const statusScope = document.getElementById("status-scope");
const statusMode = document.getElementById("status-mode");
const statusNodes = document.getElementById("status-nodes");
const statusEdges = document.getElementById("status-edges");
const statusFingerprint = document.getElementById("status-fingerprint");
const statusSim = document.getElementById("status-sim");

const networkContainer = document.getElementById("network");
const zoomInBtn = document.getElementById("zoom-in");
const zoomOutBtn = document.getElementById("zoom-out");
const zoomFitBtn = document.getElementById("zoom-fit");
const toggleLegendBtn = document.getElementById("toggle-legend");
const legendDrawer = document.getElementById("legend-drawer");
const closeLegendBtn = document.getElementById("close-legend");
const legendNodesContainer = document.getElementById("legend-nodes");
const legendEdgesContainer = document.getElementById("legend-edges");

const hoverCard = document.getElementById("node-hover-card");
const hoverBadge = document.getElementById("hover-badge");
const hoverSource = document.getElementById("hover-source");
const hoverDegree = document.getElementById("hover-degree");
const hoverTitle = document.getElementById("hover-title");
const hoverPath = document.getElementById("hover-path");
const hoverSummary = document.getElementById("hover-summary");

// Runtime State
let network = null;
let nodesDataSet = null;
let edgesDataSet = null;
let rootSnapshot = null;
let currentBaseSnapshot = null;
let currentSnapshot = null;
let selectedNode = null;
let physicsEnabled = true;
let searchMatches = [];
let searchMatchIndex = 0;
let hoveredNodeId = null;

// Palette configurations with high contrast modern accents
const defaultNodePalette = {
  semantic_spec: { color: "#f59e0b", shape: "hexagon", label: "Spec" },
  semantic_session: { color: "#10b981", shape: "box", label: "Session" },
  semantic_doc: { color: "#38bdf8", shape: "dot", label: "Document" },
  episodic_spec: { color: "#f43f5e", shape: "diamond", label: "Episodic Spec" },
  episodic_session: { color: "#8b5cf6", shape: "star", label: "Episodic Session" },
  episodic_general: { color: "#64748b", shape: "triangle", label: "Memory" },
  architecture: { color: "#ec4899", shape: "hexagon", label: "Architecture" },
  decisions: { color: "#06b6d4", shape: "dot", label: "Decision (ADR)" },
  changelog: { color: "#a855f7", shape: "box", label: "Changelog" },
  runbooks: { color: "#14b8a6", shape: "diamond", label: "Runbook" },
  incidents: { color: "#ef4444", shape: "star", label: "Incident" },
};

const defaultEdgePalette = {
  wikilink: { color: "#38bdf8", label: "Wiki Link" },
  same_spec_reference: { color: "#f59e0b", label: "Spec Reference" },
  same_file_reference: { color: "#10b981", label: "File Reference" },
  shared_entity: { color: "#8b5cf6", label: "Shared Entity" },
  shared_tag: { color: "#14b8a6", label: "Shared Tag" },
  semantic_neighbor: { color: "#64748b", label: "Semantic Neighbor" },
  supersedes: { color: "#ef4444", label: "Supersedes" },
  tested_by: { color: "#22c55e", label: "Tested By" },
  imports: { color: "#60a5fa", label: "Imports" },
};

// ============================================================================
// Utility Helpers
// ============================================================================

function toast(message) {
  const node = document.createElement("div");
  node.className = "toast";
  node.textContent = message;
  document.body.appendChild(node);
  setTimeout(() => {
    node.style.opacity = "0";
    node.style.transform = "translateY(8px)";
    setTimeout(() => node.remove(), 250);
  }, 2800);
}

/**
 * Strips long file path prefixes to return a clean, readable name.
 * e.g. "docs/canonical-documentation/fase-09-webgraph/tutor.md" -> "tutor.md"
 */
function cleanNodeName(raw) {
  if (!raw) return "Untitled";
  let str = String(raw).trim();
  if (str.includes("/") || str.includes("\\")) {
    const parts = str.split(/[/\\]+/).filter(Boolean);
    str = parts[parts.length - 1];
  }
  return str;
}

function truncate(text, maxLen = 22) {
  if (!text) return "";
  const s = String(text).trim();
  if (s.length <= maxLen) return s;
  return s.slice(0, maxLen - 1) + "…";
}

function labelForNode(node) {
  return node.label || node.memory_id || cleanNodeName(node.rel_path) || node.id;
}

function formatSource(node) {
  return `${node.source}:${node.node_type || "node"}`;
}

function makeMetaPill(label, value) {
  const pill = document.createElement("span");
  pill.className = "meta-pill";
  pill.innerHTML = `<strong>${label}</strong> ${value}`;
  return pill;
}

// ============================================================================
// Legend Builder
// ============================================================================

function renderLegend(snapshot) {
  legendNodesContainer.innerHTML = "";
  legendEdgesContainer.innerHTML = "";

  const legendData = snapshot.legend || {};
  const docTypes = legendData.doc_types || [];
  const edgeTypes = legendData.edge_types || [];

  if (docTypes.length > 0) {
    docTypes.forEach((dt) => {
      const item = document.createElement("div");
      item.className = "legend-item";
      item.innerHTML = `<span class="legend-indicator" style="background-color:${dt.color};"></span><span>${dt.type.replace(/_/g, " ")}</span>`;
      legendNodesContainer.appendChild(item);
    });
  } else {
    Object.entries(defaultNodePalette).forEach(([key, val]) => {
      const item = document.createElement("div");
      item.className = "legend-item";
      item.innerHTML = `<span class="legend-indicator" style="background-color:${val.color};"></span><span>${val.label || key.replace(/_/g, " ")}</span>`;
      legendNodesContainer.appendChild(item);
    });
  }

  if (edgeTypes.length > 0) {
    edgeTypes.forEach((et) => {
      const item = document.createElement("div");
      item.className = "legend-item";
      item.innerHTML = `<span class="legend-indicator" style="background-color:${et.color};"></span><span>${et.label || et.type.replace(/_/g, " ")}</span>`;
      legendEdgesContainer.appendChild(item);
    });
  } else {
    Object.entries(defaultEdgePalette).forEach(([key, val]) => {
      const item = document.createElement("div");
      item.className = "legend-item";
      item.innerHTML = `<span class="legend-indicator" style="background-color:${val.color};"></span><span>${val.label}</span>`;
      legendEdgesContainer.appendChild(item);
    });
  }
}

// ============================================================================
// Node Classification: Principal Hubs vs Secondary Nodes
// ============================================================================

/**
 * Determines which nodes are "nodos principales" (high degree hubs, specs, roots).
 * For non-principal nodes, their default label is empty to avoid visual overlap
 * and cluttered canvases, revealing labels on hover.
 */
function classifyPrincipalNodes(nodes) {
  if (nodes.length <= 12) {
    // Small graphs: all nodes can show labels
    return new Set(nodes.map((n) => n.id));
  }

  const degrees = nodes.map((n) => n.degree || 0).sort((a, b) => b - a);
  // Cutoff at top 20% highest degree or degree >= 4
  const cutoffIndex = Math.max(3, Math.floor(nodes.length * 0.2));
  const degreeThreshold = Math.max(4, degrees[cutoffIndex] || 4);

  const principalIds = new Set();
  nodes.forEach((node) => {
    const deg = node.degree || 0;
    const isMajorType = node.node_type === "semantic_spec" || node.node_type === "architecture";
    if (deg >= degreeThreshold || isMajorType) {
      principalIds.add(node.id);
    }
  });

  return principalIds;
}

// ============================================================================
// Vis Network Node & Edge Normalization
// ============================================================================

function normalizeNodes(nodes, principalIds, labelMode = "hubs") {
  return nodes.map((node) => {
    const palette = defaultNodePalette[node.node_type] || { color: "#38bdf8", shape: "dot" };
    const isPrincipal = principalIds.has(node.id);
    const cleanName = cleanNodeName(labelForNode(node));
    const degree = node.degree || 0;

    // Determine label display according to user preference & principal classification
    let displayLabel = "";
    if (labelMode === "all") {
      displayLabel = truncate(cleanName, 22);
    } else if (labelMode === "hubs") {
      if (isPrincipal) {
        displayLabel = truncate(cleanName, 20);
      } else {
        displayLabel = ""; // Clean view: no label initially
      }
    } else if (labelMode === "hover") {
      displayLabel = "";
    }

    // Dynamic sizing based on degree to create clear visual hierarchy
    const baseSize = isPrincipal ? 22 : 14;
    const size = Math.min(36, baseSize + Math.min(degree, 20) * 1.2);

    return {
      id: node.id,
      label: displayLabel,
      _cleanName: cleanName,
      _fullLabel: labelForNode(node),
      _isPrincipal: isPrincipal,
      _rawNode: node,
      shape: palette.shape,
      size: size,
      color: {
        background: palette.color,
        border: isPrincipal ? "#ffffff" : "rgba(255, 255, 255, 0.45)",
        highlight: {
          background: palette.color,
          border: "#38bdf8",
        },
        hover: {
          background: palette.color,
          border: "#ffffff",
        },
      },
      borderWidth: isPrincipal ? 2.5 : 1.5,
      borderWidthSelected: 3.5,
      font: {
        color: "#f1f5f9",
        face: "Inter, Segoe UI, sans-serif",
        size: isPrincipal ? 13 : 11,
        strokeWidth: 3,
        strokeColor: "rgba(11, 15, 25, 0.92)",
        vadjust: 2,
      },
      shadow: {
        enabled: true,
        color: "rgba(0, 0, 0, 0.5)",
        size: isPrincipal ? 12 : 6,
        x: 0,
        y: 3,
      },
    };
  });
}

function normalizeEdges(edges, density, spacingMultiplier = 1.0) {
  const baseSpring = Math.max(160, Math.min(300, 140 + density * 7)) * spacingMultiplier;

  return edges.map((edge) => {
    const isNeighbor = edge.edge_type === "semantic_neighbor";
    const palette = defaultEdgePalette[edge.edge_type] || { color: "#64748b" };

    // Adaptive edge resting length:
    // Soft similarity edges have longer, looser springs so they do NOT pull nodes into a hairball.
    // Explicit structural links have tighter springs to group related nodes naturally.
    const edgeLength = isNeighbor ? baseSpring * 1.45 : baseSpring * 0.9;

    const baseColor = isNeighbor ? "rgba(100, 116, 139, 0.2)" : palette.color;
    const opacity = isNeighbor ? 0.25 : 0.65;

    return {
      id: edge.id,
      from: edge.source,
      to: edge.target,
      _edgeType: edge.edge_type,
      _isNeighbor: isNeighbor,
      length: edgeLength,
      color: {
        color: baseColor,
        opacity: opacity,
        highlight: "#38bdf8",
        hover: "#a5b4fc",
      },
      width: isNeighbor ? 0.9 : Math.max(1.6, Math.min(3.5, edge.weight || 1.6)),
      selectionWidth: 3.5,
      hoverWidth: 2.5,
      dashes: isNeighbor ? [4, 6] : false,
      smooth: {
        type: isNeighbor ? "continuous" : "dynamic",
        roundness: 0.2,
      },
    };
  });
}

// ============================================================================
// Adaptive Physics Configuration
// ============================================================================

function networkOptions(snapshot, spacingPreset = "spacious") {
  const nodeCount = snapshot.stats.node_count;
  const edgeCount = snapshot.stats.edge_count;
  const density = edgeCount / Math.max(1, nodeCount);

  let spacingMultiplier = 1.0;
  if (spacingPreset === "wide") spacingMultiplier = 1.4;
  else if (spacingPreset === "compact") spacingMultiplier = 0.75;

  // Adaptive ForceAtlas2 settings:
  // - High damping (0.65) absorbs oscillation energy, stopping the constant collision & shaking!
  // - avoidOverlap: 1.0 ensures node boundaries never collide or sit on top of each other.
  // - Gentle centralGravity (0.006) prevents tight clumping.
  // - Repulsion scales with graph density so dense clusters push apart with breathing room.
  const repulsion = (-110 - Math.min(140, density * 8)) * spacingMultiplier;
  const springLength = Math.max(170, Math.min(320, 140 + density * 8)) * spacingMultiplier;
  const springConstant = Math.max(0.018, Math.min(0.045, 0.35 / Math.sqrt(Math.max(1, density))));

  return {
    autoResize: true,
    physics: {
      enabled: physicsEnabled,
      solver: "forceAtlas2Based",
      forceAtlas2Based: {
        gravitationalConstant: repulsion,
        centralGravity: 0.006,
        springLength: springLength,
        springConstant: springConstant,
        damping: 0.65,
        avoidOverlap: 1.0,
      },
      stabilization: {
        enabled: true,
        iterations: Math.min(320, 140 + nodeCount * 2),
        updateInterval: 25,
        fit: true,
      },
    },
    interaction: {
      hover: true,
      hoverConnectedEdges: true,
      selectConnectedEdges: true,
      navigationButtons: false,
      keyboard: {
        enabled: true,
        bindTo: "window",
      },
      tooltipDelay: 100,
      zoomView: true,
      dragView: true,
    },
  };
}

// ============================================================================
// Build & Render Vis.js Network
// ============================================================================

function buildNetwork(snapshot) {
  const nodeCount = snapshot.stats.node_count;
  const edgeCount = snapshot.stats.edge_count;
  const density = edgeCount / Math.max(1, nodeCount);
  const spacingPreset = layoutSpacingSelect.value || "spacious";
  let spacingMultiplier = spacingPreset === "wide" ? 1.4 : spacingPreset === "compact" ? 0.75 : 1.0;

  const principalIds = classifyPrincipalNodes(snapshot.nodes);
  const labelMode = labelModeSelect.value || "hubs";

  const rawNodes = normalizeNodes(snapshot.nodes, principalIds, labelMode);
  const rawEdges = normalizeEdges(snapshot.edges, density, spacingMultiplier);

  nodesDataSet = new vis.DataSet(rawNodes);
  edgesDataSet = new vis.DataSet(rawEdges);

  const data = {
    nodes: nodesDataSet,
    edges: edgesDataSet,
  };

  if (network) {
    network.destroy();
    network = null;
  }

  statusSim.textContent = "Stabilizing...";
  statusSim.style.color = "var(--accent-amber)";

  network = new vis.Network(networkContainer, data, networkOptions(snapshot, spacingPreset));

  // Network Simulation Lifecycle Events
  network.on("stabilizationProgress", (params) => {
    const pct = Math.round((params.iterations / params.total) * 100);
    statusSim.textContent = `Stabilizing ${pct}%`;
  });

  network.once("stabilizationIterationsDone", () => {
    statusSim.textContent = "Stabilized";
    statusSim.style.color = "var(--accent-emerald)";
    // Optional gentle freeze after stabilization so nodes remain static and completely clickable!
    if (snapshot.stats.node_count > 15) {
      freezePhysics(true);
    }
  });

  network.on("stabilized", () => {
    statusSim.textContent = "Settled";
    statusSim.style.color = "var(--accent-emerald)";
  });

  // Hover Events for Clean Label Display & Rich HUD Popover
  network.on("hoverNode", (params) => {
    const nodeId = params.node;
    hoveredNodeId = nodeId;
    const nodeItem = nodesDataSet.get(nodeId);
    if (!nodeItem) return;

    // Dynamically show the clean name on the hovered node if it was hidden
    if (!nodeItem.label || nodeItem.label.length < nodeItem._cleanName.length) {
      nodesDataSet.update({
        id: nodeId,
        label: truncate(nodeItem._cleanName, 32),
        font: {
          color: "#ffffff",
          background: "rgba(15, 23, 42, 0.95)",
          strokeWidth: 0,
          size: 13,
        },
      });
    }

    // Dim unconnected edges and highlight direct edges
    highlightNodeConnections(nodeId);

    // Show floating HUD popover
    showHoverCard(nodeItem, params.event);
  });

  network.on("blurNode", (params) => {
    const nodeId = params.node;
    hoveredNodeId = null;
    hideHoverCard();
    restoreNodeConnections();

    // Restore original label state
    const nodeItem = nodesDataSet.get(nodeId);
    if (!nodeItem) return;

    const labelMode = labelModeSelect.value;
    let originalLabel = "";
    if (labelMode === "all") {
      originalLabel = truncate(nodeItem._cleanName, 22);
    } else if (labelMode === "hubs") {
      originalLabel = nodeItem._isPrincipal ? truncate(nodeItem._cleanName, 20) : "";
    }

    nodesDataSet.update({
      id: nodeId,
      label: originalLabel,
      font: {
        color: "#f1f5f9",
        face: "Inter, Segoe UI, sans-serif",
        size: nodeItem._isPrincipal ? 13 : 11,
        strokeWidth: 3,
        strokeColor: "rgba(11, 15, 25, 0.92)",
        vadjust: 2,
      },
    });
  });

  // Click & Selection
  network.on("click", async (params) => {
    if (!params.nodes.length) {
      resetDetail();
      restoreNodeConnections();
      return;
    }
    const nodeId = params.nodes[0];
    await selectNode(nodeId);
  });

  // Double click opens file
  network.on("doubleClick", async (params) => {
    if (!params.nodes.length) return;
    const nodeId = params.nodes[0];
    await openNode(nodeId);
  });

  // Dragging interaction: allow drag without jitter
  network.on("dragStart", (params) => {
    if (params.nodes.length && !physicsEnabled) {
      // Allow moving the individual node smoothly
    }
  });

  renderLegend(snapshot);
}

// ============================================================================
// Visual Connection Highlighting (Focus effect on Hover/Select)
// ============================================================================

function highlightNodeConnections(nodeId) {
  if (!network || !edgesDataSet) return;

  const connectedEdgeIds = new Set(network.getConnectedEdges(nodeId));
  const updates = [];

  edgesDataSet.forEach((edge) => {
    if (connectedEdgeIds.has(edge.id)) {
      updates.push({
        id: edge.id,
        color: { color: "#38bdf8", opacity: 0.95 },
        width: Math.max(2.5, (edge.width || 1.5) * 1.5),
      });
    } else {
      updates.push({
        id: edge.id,
        color: { color: "rgba(100, 116, 139, 0.08)", opacity: 0.08 },
      });
    }
  });

  if (updates.length) {
    edgesDataSet.update(updates);
  }
}

function restoreNodeConnections() {
  if (!network || !edgesDataSet || !currentSnapshot) return;

  const nodeCount = currentSnapshot.stats.node_count;
  const edgeCount = currentSnapshot.stats.edge_count;
  const density = edgeCount / Math.max(1, nodeCount);
  const spacingPreset = layoutSpacingSelect.value || "spacious";
  const spacingMultiplier = spacingPreset === "wide" ? 1.4 : spacingPreset === "compact" ? 0.75 : 1.0;

  const restored = normalizeEdges(currentSnapshot.edges, density, spacingMultiplier);
  edgesDataSet.update(restored);
}

// ============================================================================
// Floating Hover HUD Popover
// ============================================================================

function showHoverCard(nodeItem, event) {
  const raw = nodeItem._rawNode || {};
  hoverTitle.textContent = nodeItem._cleanName || labelForNode(raw);
  hoverPath.textContent = raw.rel_path || raw.memory_id || "";
  hoverSummary.textContent = raw.summary || "No summary description available.";

  hoverBadge.textContent = (raw.node_type || "node").replace(/_/g, " ");
  const palette = defaultNodePalette[raw.node_type] || { color: "#38bdf8" };
  hoverBadge.style.backgroundColor = `${palette.color}25`;
  hoverBadge.style.color = palette.color;
  hoverBadge.style.borderColor = `${palette.color}60`;

  hoverSource.textContent = raw.source || "source";
  hoverDegree.textContent = `${raw.degree || 0} links`;

  // Position the card near the cursor within the network wrapper
  const wrapperRect = networkContainer.getBoundingClientRect();
  const mouseX = event ? event.clientX - wrapperRect.left : 40;
  const mouseY = event ? event.clientY - wrapperRect.top : 40;

  const cardWidth = 300;
  const cardHeight = 140;

  let left = mouseX + 16;
  let top = mouseY + 16;

  if (left + cardWidth > wrapperRect.width - 20) {
    left = mouseX - cardWidth - 16;
  }
  if (top + cardHeight > wrapperRect.height - 20) {
    top = mouseY - cardHeight - 16;
  }

  hoverCard.style.left = `${Math.max(10, left)}px`;
  hoverCard.style.top = `${Math.max(10, top)}px`;
  hoverCard.style.display = "block";
  hoverCard.style.opacity = "1";
}

function hideHoverCard() {
  hoverCard.style.display = "none";
  hoverCard.style.opacity = "0";
}

// ============================================================================
// Physics Freeze / Toggle Controls
// ============================================================================

function freezePhysics(freeze) {
  physicsEnabled = !freeze;
  if (!network) return;

  network.setOptions({ physics: { enabled: physicsEnabled } });

  if (freeze) {
    physicsIndicator.className = "btn-indicator frozen";
    physicsLabel.textContent = "Physics Frozen";
    statusSim.textContent = "Static (Frozen)";
    statusSim.style.color = "var(--accent-amber)";
  } else {
    physicsIndicator.className = "btn-indicator active";
    physicsLabel.textContent = "Physics Active";
    statusSim.textContent = "Active";
    statusSim.style.color = "var(--accent-emerald)";
    network.startSimulation();
  }
}

togglePhysicsButton.addEventListener("click", () => {
  freezePhysics(physicsEnabled);
  toast(physicsEnabled ? "Simulation physics un-frozen" : "Simulation physics frozen");
});

// ============================================================================
// Detail Sidebar Rendering
// ============================================================================

function updateStatus(snapshot, baseSnapshot) {
  statusScope.textContent =
    baseSnapshot &&
    snapshot.fingerprint === baseSnapshot.fingerprint &&
    snapshot.stats.node_count === baseSnapshot.stats.node_count &&
    snapshot.stats.edge_count === baseSnapshot.stats.edge_count
      ? "full"
      : "filtered";

  statusMode.textContent = snapshot.mode;
  statusNodes.textContent = snapshot.stats.node_count;
  statusEdges.textContent = snapshot.stats.edge_count;
  statusFingerprint.textContent = snapshot.fingerprint.slice(0, 12);
}

function renderRelations(relations) {
  relationList.innerHTML = "";
  relationCount.textContent = relations.length;

  if (!relations.length) {
    relationList.innerHTML = '<li class="detail-empty">No explicit relationships for this node in the current view.</li>';
    return;
  }

  relations.forEach((relation) => {
    const item = document.createElement("li");
    item.className = "relation-item";
    const evidence = relation.evidence?.length ? relation.evidence.join(", ") : "Direct reference";
    const palette = defaultEdgePalette[relation.edge_type] || { color: "#8b5cf6" };

    item.innerHTML = `
      <div class="relation-header">
        <span class="relation-type" style="color:${palette.color}">${relation.edge_type.replace(/_/g, " ")}</span>
        <span class="badge-count">${relation.weight ? relation.weight.toFixed(1) : "1.0"}</span>
      </div>
      <div class="relation-endpoints">${cleanNodeName(relation.source)} &rarr; ${cleanNodeName(relation.target)}</div>
      <div class="relation-evidence">${evidence}</div>
    `;
    relationList.appendChild(item);
  });
}

function renderNeighbors(neighbors) {
  neighborList.innerHTML = "";
  neighborCount.textContent = neighbors.length;

  if (!neighbors.length) {
    neighborList.innerHTML = '<li class="detail-empty">No neighbors in the current graph slice.</li>';
    return;
  }

  neighbors.forEach((neighbor) => {
    const item = document.createElement("li");
    const button = document.createElement("button");
    button.type = "button";
    button.className = "neighbor-button";

    const palette = defaultNodePalette[neighbor.node_type] || { color: "#38bdf8" };

    button.innerHTML = `
      <div class="neighbor-label">
        <span class="legend-indicator" style="display:inline-block;margin-right:6px;background-color:${palette.color};"></span>
        ${cleanNodeName(labelForNode(neighbor))}
      </div>
      <div class="neighbor-meta">
        <span>${neighbor.node_type.replace(/_/g, " ")}</span> &bull;
        <span>${neighbor.degree || 0} links</span>
      </div>
    `;

    button.addEventListener("click", () => focusNode(neighbor.id));
    item.appendChild(button);
    neighborList.appendChild(item);
  });
}

function renderDetail(detail) {
  selectedNode = detail.node;
  const cleanTitle = cleanNodeName(labelForNode(detail.node));
  detailTitle.textContent = cleanTitle;
  detailSummary.textContent = detail.node.summary || "No summary available for this node.";

  const palette = defaultNodePalette[detail.node.node_type] || { color: "#38bdf8" };
  detailTypeBadge.textContent = (detail.node.node_type || "node").replace(/_/g, " ");
  detailTypeBadge.style.display = "inline-flex";
  detailTypeBadge.style.backgroundColor = `${palette.color}25`;
  detailTypeBadge.style.color = palette.color;
  detailTypeBadge.style.borderColor = `${palette.color}60`;

  detailMeta.innerHTML = "";
  detailMeta.appendChild(makeMetaPill("Source", detail.node.source));
  detailMeta.appendChild(makeMetaPill("Degree", String(detail.node.degree ?? 0)));

  const projectId = detail.node.metadata?.project_id;
  if (projectId) {
    detailMeta.appendChild(makeMetaPill("Project", projectId));
  }
  if (detail.node.rel_path) {
    detailMeta.appendChild(makeMetaPill("Path", detail.node.rel_path));
  }
  if (detail.node.memory_id) {
    detailMeta.appendChild(makeMetaPill("Memory ID", detail.node.memory_id));
  }
  if (detail.node.tags?.length) {
    detailMeta.appendChild(makeMetaPill("Tags", detail.node.tags.join(", ")));
  }
  if (detail.node.timestamp) {
    detailMeta.appendChild(makeMetaPill("Time", new Date(detail.node.timestamp).toLocaleDateString()));
  }

  openNodeButton.disabled = !detail.node.rel_path;
  loadSubgraphButton.disabled = false;
  renderRelations(detail.relations || []);
  renderNeighbors(detail.neighbors || []);
}

function resetDetail() {
  selectedNode = null;
  detailTitle.textContent = "No node selected";
  detailSummary.textContent = "Click on any node in the graph to inspect memory details, explainable connections, and available source actions.";
  detailTypeBadge.style.display = "none";
  detailMeta.innerHTML = "";
  relationList.innerHTML = '<li class="detail-empty">No relationships yet.</li>';
  relationCount.textContent = "0";
  neighborList.innerHTML = '<li class="detail-empty">Select a node to inspect its local neighborhood.</li>';
  neighborCount.textContent = "0";
  openNodeButton.disabled = true;
  loadSubgraphButton.disabled = true;
}

// ============================================================================
// Filter Synchronization & Filtering Engine
// ============================================================================

function syncFilterOptions(select, values, labelFactory) {
  const previous = select.value;
  const existing = Array.from(select.options)
    .slice(1)
    .map((option) => option.value);

  if (JSON.stringify(existing) === JSON.stringify(values)) {
    if (values.includes(previous) || previous === "all") {
      select.value = previous;
    }
    return;
  }

  while (select.options.length > 1) {
    select.remove(1);
  }

  values.forEach((value) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = labelFactory(value);
    select.appendChild(option);
  });

  select.value = values.includes(previous) ? previous : "all";
}

function populateFilterOptions(snapshot) {
  const projects = Array.from(
    new Set(
      snapshot.nodes
        .map((node) => node.metadata?.project_id)
        .filter(Boolean)
    )
  ).sort();
  const nodeTypes = Array.from(new Set(snapshot.nodes.map((node) => node.node_type))).sort();

  syncFilterOptions(projectFilter, projects, (v) => v);
  syncFilterOptions(typeFilter, nodeTypes, (v) => v.replace(/_/g, " "));
}

function timeWindowToMs(value) {
  if (value === "7d") return 7 * 24 * 60 * 60 * 1000;
  if (value === "30d") return 30 * 24 * 60 * 60 * 1000;
  if (value === "90d") return 90 * 24 * 60 * 60 * 1000;
  return null;
}

function nodeMatchesFilters(node) {
  if (projectFilter.value !== "all" && node.metadata?.project_id !== projectFilter.value) {
    return false;
  }
  if (typeFilter.value !== "all" && node.node_type !== typeFilter.value) {
    return false;
  }

  const timeWindowMs = timeWindowToMs(timeFilter.value);
  if (timeWindowMs !== null && node.timestamp) {
    const age = Date.now() - new Date(node.timestamp).getTime();
    if (Number.isFinite(age) && age > timeWindowMs) {
      return false;
    }
  }

  return true;
}

function edgeMatchesFilters(edge) {
  const edgeFilterVal = edgeFilter.value;
  if (edgeFilterVal === "structural") {
    // Hide soft embedding similarity neighbors to eliminate hairballs!
    return edge.edge_type !== "semantic_neighbor";
  }
  if (edgeFilterVal === "semantic_only") {
    return edge.edge_type === "semantic_neighbor";
  }
  return true;
}

function filteredSnapshot(snapshot) {
  const visibleNodes = snapshot.nodes.filter((node) => nodeMatchesFilters(node));
  const visibleNodeIds = new Set(visibleNodes.map((node) => node.id));

  const visibleEdges = snapshot.edges.filter(
    (edge) =>
      visibleNodeIds.has(edge.source) &&
      visibleNodeIds.has(edge.target) &&
      edgeMatchesFilters(edge)
  );

  return {
    ...snapshot,
    nodes: visibleNodes,
    edges: visibleEdges,
    stats: {
      ...snapshot.stats,
      node_count: visibleNodes.length,
      edge_count: visibleEdges.length,
    },
  };
}

function refreshView({ preserveSelection = true } = {}) {
  if (!currentBaseSnapshot) return;

  currentSnapshot = filteredSnapshot(currentBaseSnapshot);
  buildNetwork(currentSnapshot);
  updateStatus(currentSnapshot, currentBaseSnapshot);
  resetButton.disabled = currentBaseSnapshot === rootSnapshot;

  if (preserveSelection && selectedNode) {
    const exists = currentSnapshot.nodes.some((node) => node.id === selectedNode.id);
    if (exists) {
      focusNode(selectedNode.id);
      return;
    }
  }
  resetDetail();
}

// ============================================================================
// Snapshot & Node Loading (Backend API)
// ============================================================================

async function loadSnapshot(mode = modeSelect.value) {
  statusSim.textContent = "Loading snapshot...";
  const response = await fetch(`/api/snapshot?mode=${encodeURIComponent(mode)}`, {
    headers: { "X-Cortex-WebGraph": "1" },
  });
  if (!response.ok) {
    throw new Error(`Snapshot request failed with HTTP ${response.status}`);
  }
  const snapshot = await response.json();
  rootSnapshot = snapshot;
  currentBaseSnapshot = snapshot;

  // Sync mode tab UI
  modeTabs.forEach((tab) => {
    tab.classList.toggle("active", tab.dataset.mode === mode);
  });
  modeSelect.value = mode;

  populateFilterOptions(snapshot);
  refreshView({ preserveSelection: false });
}

async function selectNode(nodeId) {
  try {
    const response = await fetch(
      `/api/node/${encodeURIComponent(nodeId)}?mode=${encodeURIComponent(modeSelect.value)}`,
      {
        headers: { "X-Cortex-WebGraph": "1" },
      }
    );
    if (!response.ok) {
      throw new Error(`Node detail request failed with ${response.status}`);
    }
    const detail = await response.json();
    renderDetail(detail);
    highlightNodeConnections(nodeId);
  } catch (error) {
    toast(`Failed to load node: ${error.message}`);
  }
}

function focusNode(nodeId) {
  if (!network) return;
  network.selectNodes([nodeId]);
  network.focus(nodeId, {
    scale: 1.2,
    animation: { duration: 450, easingFunction: "easeInOutQuad" },
  });
  selectNode(nodeId);
}

async function openNode(nodeId = selectedNode?.id) {
  if (!nodeId) return;
  const response = await fetch("/api/open", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Cortex-WebGraph": "1",
    },
    body: JSON.stringify({ node_id: nodeId }),
  });
  const payload = await response.json();
  if (!response.ok) {
    toast(payload.error || "Unable to open this node");
    return;
  }
  toast(`Opened: ${cleanNodeName(payload.path || "document")}`);
}

async function loadSubgraph(nodeId = selectedNode?.id) {
  if (!nodeId) return;
  const params = new URLSearchParams({
    node_id: nodeId,
    depth: depthSelect.value,
    mode: modeSelect.value,
  });
  const response = await fetch(`/api/subgraph?${params.toString()}`, {
    headers: { "X-Cortex-WebGraph": "1" },
  });
  if (!response.ok) {
    throw new Error(`Subgraph request failed with ${response.status}`);
  }
  currentBaseSnapshot = await response.json();
  refreshView();
  await selectNode(nodeId);
}

// ============================================================================
// Search & Quick Jump
// ============================================================================

function runSearch() {
  const term = searchInput.value.trim().toLowerCase();
  if (!term || !currentSnapshot?.nodes?.length) {
    searchCounter.style.display = "none";
    searchMatches = [];
    return;
  }

  searchMatches = currentSnapshot.nodes.filter((node) => {
    const label = (node.label || "").toLowerCase();
    const relPath = (node.rel_path || "").toLowerCase();
    const summary = (node.summary || "").toLowerCase();
    const tags = (node.tags || []).join(" ").toLowerCase();
    return label.includes(term) || relPath.includes(term) || summary.includes(term) || tags.includes(term);
  });

  if (!searchMatches.length) {
    searchCounter.style.display = "inline-block";
    searchCounter.textContent = "0 matches";
    toast(`No nodes matching "${searchInput.value}"`);
    return;
  }

  searchMatchIndex = (searchMatchIndex + 1) % searchMatches.length;
  searchCounter.style.display = "inline-block";
  searchCounter.textContent = `${searchMatchIndex + 1}/${searchMatches.length}`;

  const match = searchMatches[searchMatchIndex];
  focusNode(match.id);
}

// ============================================================================
// Event Listeners & Bindings
// ============================================================================

// Mode Tabs
modeTabs.forEach((tab) => {
  tab.addEventListener("click", () => {
    const mode = tab.dataset.mode;
    modeTabs.forEach((t) => t.classList.toggle("active", t === tab));
    modeSelect.value = mode;
    loadSnapshot(mode).catch((err) => toast(`Failed to switch mode: ${err.message}`));
  });
});

modeSelect.addEventListener("change", () => {
  loadSnapshot(modeSelect.value).catch((err) => toast(`Failed to switch mode: ${err.message}`));
});

// Filter triggers
[projectFilter, typeFilter, timeFilter, edgeFilter].forEach((element) => {
  element.addEventListener("change", () => refreshView());
});

labelModeSelect.addEventListener("change", () => {
  refreshView();
  toast(`Labels: ${labelModeSelect.options[labelModeSelect.selectedIndex].text}`);
});

layoutSpacingSelect.addEventListener("change", () => {
  refreshView();
});

// Search
searchButton.addEventListener("click", runSearch);
searchInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    runSearch();
  }
});

// Global Toolbar buttons
reloadButton.addEventListener("click", () => {
  loadSnapshot().catch((error) => toast(`Failed to reload graph: ${error.message}`));
});

resetButton.addEventListener("click", () => {
  if (!rootSnapshot) return;
  currentBaseSnapshot = rootSnapshot;
  refreshView();
  toast("View reset to root snapshot");
});

fitButton.addEventListener("click", () => {
  if (network) {
    network.fit({ animation: { duration: 500, easingFunction: "easeInOutQuad" } });
  }
});

zoomFitBtn.addEventListener("click", () => {
  if (network) {
    network.fit({ animation: { duration: 500, easingFunction: "easeInOutQuad" } });
  }
});

zoomInBtn.addEventListener("click", () => {
  if (!network) return;
  const currentScale = network.getScale();
  network.moveTo({ scale: currentScale * 1.35, animation: { duration: 250 } });
});

zoomOutBtn.addEventListener("click", () => {
  if (!network) return;
  const currentScale = network.getScale();
  network.moveTo({ scale: currentScale * 0.75, animation: { duration: 250 } });
});

// Legend Drawer Toggle
toggleLegendBtn.addEventListener("click", () => {
  const isHidden = legendDrawer.style.display === "none";
  legendDrawer.style.display = isHidden ? "block" : "none";
});

closeLegendBtn.addEventListener("click", () => {
  legendDrawer.style.display = "none";
});

// Node Details actions
openNodeButton.addEventListener("click", () => {
  openNode().catch((error) => toast(`Failed to open node: ${error.message}`));
});

loadSubgraphButton.addEventListener("click", () => {
  loadSubgraph().catch((error) => toast(`Failed to load subgraph: ${error.message}`));
});

// Initialize
loadSnapshot().catch((error) => {
  toast(`Failed to initialize graph: ${error.message}`);
  networkContainer.innerHTML = `
    <div style="display:flex;align-items:center;justify-content:center;height:100%;color:#ef4444;font-family:sans-serif;padding:24px;text-align:center;">
      <div>
        <h3 style="margin-top:0;">Failed to load Cortex WebGraph</h3>
        <p style="color:#94a3b8;font-size:0.875rem;">${error.message}</p>
        <button onclick="location.reload()" style="background:#4f46e5;color:#fff;border:none;padding:8px 16px;border-radius:8px;cursor:pointer;">Retry</button>
      </div>
    </div>
  `;
});
