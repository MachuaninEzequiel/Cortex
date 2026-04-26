const modeSelect = document.getElementById("mode");
const projectFilter = document.getElementById("project-filter");
const typeFilter = document.getElementById("type-filter");
const timeFilter = document.getElementById("time-filter");
const depthSelect = document.getElementById("depth");
const searchInput = document.getElementById("search");
const searchButton = document.getElementById("search-button");
const reloadButton = document.getElementById("reload");
const resetButton = document.getElementById("reset-view");
const openNodeButton = document.getElementById("open-node");
const loadSubgraphButton = document.getElementById("load-subgraph");

const detailTitle = document.getElementById("detail-title");
const detailSummary = document.getElementById("detail-summary");
const detailMeta = document.getElementById("detail-meta");
const relationList = document.getElementById("relation-list");
const neighborList = document.getElementById("neighbor-list");

const statusScope = document.getElementById("status-scope");
const statusMode = document.getElementById("status-mode");
const statusNodes = document.getElementById("status-nodes");
const statusEdges = document.getElementById("status-edges");
const statusFingerprint = document.getElementById("status-fingerprint");

const networkContainer = document.getElementById("network");

let network = null;
let rootSnapshot = null;
let currentBaseSnapshot = null;
let currentSnapshot = null;
let selectedNode = null;

const nodePalette = {
  semantic_spec: { color: "#ff9f43", shape: "hexagon" },
  semantic_session: { color: "#10ac84", shape: "box" },
  semantic_doc: { color: "#2e86de", shape: "dot" },
  episodic_spec: { color: "#ee5253", shape: "diamond" },
  episodic_session: { color: "#5f27cd", shape: "star" },
  episodic_general: { color: "#576574", shape: "triangle" },
};

const edgePalette = {
  wikilink: "#1f78b4",
  same_spec_reference: "#d97706",
  same_file_reference: "#16a34a",
  shared_entity: "#9333ea",
  shared_tag: "#0f766e",
  semantic_neighbor: "#64748b",
};

function toast(message) {
  const node = document.createElement("div");
  node.className = "toast";
  node.textContent = message;
  document.body.appendChild(node);
  setTimeout(() => node.remove(), 2800);
}

function labelForNode(node) {
  return node.label || node.memory_id || node.rel_path || node.id;
}

function formatSource(node) {
  return `${node.source}:${node.node_type}`;
}

function makeMetaPill(label, value) {
  const pill = document.createElement("span");
  pill.className = "meta-pill";
  pill.innerHTML = `<strong>${label}</strong> ${value}`;
  return pill;
}

function updateStatus(snapshot, baseSnapshot) {
  statusScope.textContent = baseSnapshot && snapshot.fingerprint === baseSnapshot.fingerprint &&
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
  if (!relations.length) {
    relationList.innerHTML = '<li class="detail-empty">No explicit relationships for this node in the current view.</li>';
    return;
  }
  relations.forEach((relation) => {
    const item = document.createElement("li");
    const evidence = relation.evidence?.length ? relation.evidence.join(", ") : "No evidence";
    item.innerHTML = `
      <span class="relation-type">${relation.edge_type}</span>
      <div>${relation.source} -> ${relation.target}</div>
      <div class="neighbor-meta">${evidence}</div>
    `;
    relationList.appendChild(item);
  });
}

function renderNeighbors(neighbors) {
  neighborList.innerHTML = "";
  if (!neighbors.length) {
    neighborList.innerHTML = '<li class="detail-empty">No neighbors in the current graph slice.</li>';
    return;
  }
  neighbors.forEach((neighbor) => {
    const item = document.createElement("li");
    const button = document.createElement("button");
    button.type = "button";
    button.innerHTML = `
      <div class="neighbor-label">${labelForNode(neighbor)}</div>
      <div class="neighbor-meta">${formatSource(neighbor)}</div>
    `;
    button.addEventListener("click", () => focusNode(neighbor.id));
    item.appendChild(button);
    neighborList.appendChild(item);
  });
}

function renderDetail(detail) {
  selectedNode = detail.node;
  detailTitle.textContent = labelForNode(detail.node);
  detailSummary.textContent = detail.node.summary || "No summary available for this node.";
  detailMeta.innerHTML = "";
  detailMeta.appendChild(makeMetaPill("Type", detail.node.node_type));
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
    detailMeta.appendChild(makeMetaPill("Memory", detail.node.memory_id));
  }
  if (detail.node.tags?.length) {
    detailMeta.appendChild(makeMetaPill("Tags", detail.node.tags.join(", ")));
  }
  if (detail.node.timestamp) {
    detailMeta.appendChild(makeMetaPill("Time", new Date(detail.node.timestamp).toLocaleString()));
  }

  openNodeButton.disabled = !detail.node.rel_path;
  loadSubgraphButton.disabled = false;
  renderRelations(detail.relations || []);
  renderNeighbors(detail.neighbors || []);
}

function resetDetail() {
  selectedNode = null;
  detailTitle.textContent = "No node selected";
  detailSummary.textContent = "Click a node to inspect its memory details, related artifacts, and available actions.";
  detailMeta.innerHTML = "";
  relationList.innerHTML = '<li class="detail-empty">No relationships yet.</li>';
  neighborList.innerHTML = '<li class="detail-empty">Select a node to inspect its local neighborhood.</li>';
  openNodeButton.disabled = true;
  loadSubgraphButton.disabled = true;
}

function networkOptions(snapshot) {
  const largerGraph = snapshot.stats.node_count > 120;
  return {
    autoResize: true,
    physics: largerGraph
      ? { enabled: false }
      : {
          enabled: true,
          stabilization: { iterations: 160, fit: true },
          barnesHut: { springLength: 140, gravitationalConstant: -3800 },
        },
    interaction: {
      hover: true,
      navigationButtons: true,
      keyboard: true,
      tooltipDelay: 120,
    },
    nodes: {
      borderWidth: 2,
      font: {
        color: "#163246",
        face: "Segoe UI",
        size: 14,
      },
      shadow: {
        enabled: true,
        color: "rgba(24, 48, 69, 0.12)",
        size: 10,
      },
    },
    edges: {
      smooth: { type: "dynamic" },
      width: 2,
      color: { inherit: false, opacity: 0.72 },
    },
  };
}

function normalizeNodes(nodes) {
  return nodes.map((node) => {
    const palette = nodePalette[node.node_type] || { color: "#3c6382", shape: "dot" };
    const projectId = node.metadata?.project_id ? `Project: ${node.metadata.project_id}` : "";
    const title = [
      `<strong>${labelForNode(node)}</strong>`,
      `${formatSource(node)}`,
      projectId,
      node.summary || "",
    ]
      .filter(Boolean)
      .join("<br>");

    return {
      id: node.id,
      label: labelForNode(node),
      title,
      shape: palette.shape,
      color: {
        background: palette.color,
        border: "#173144",
        highlight: { background: palette.color, border: "#0b1520" },
      },
      size: Math.max(18, 18 + Math.min(node.degree || 0, 10) * 1.8),
      font: { color: "#132839" },
    };
  });
}

function normalizeEdges(edges) {
  return edges.map((edge) => ({
    id: edge.id,
    from: edge.source,
    to: edge.target,
    label: edge.edge_type === "semantic_neighbor" ? "" : edge.edge_type,
    title: edge.evidence?.length ? edge.evidence.join(", ") : edge.edge_type,
    color: { color: edgePalette[edge.edge_type] || "#718096" },
    dashes: edge.edge_type === "semantic_neighbor",
    width: Math.max(1.5, edge.weight || 1.0),
  }));
}

function buildNetwork(snapshot) {
  const data = {
    nodes: new vis.DataSet(normalizeNodes(snapshot.nodes)),
    edges: new vis.DataSet(normalizeEdges(snapshot.edges)),
  };

  if (network) {
    network.destroy();
  }

  network = new vis.Network(networkContainer, data, networkOptions(snapshot));

  network.on("click", async (params) => {
    if (!params.nodes.length) {
      resetDetail();
      return;
    }
    const nodeId = params.nodes[0];
    await selectNode(nodeId);
  });

  network.on("doubleClick", async (params) => {
    if (!params.nodes.length) {
      return;
    }
    const nodeId = params.nodes[0];
    await openNode(nodeId);
  });
}

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

  syncFilterOptions(projectFilter, projects, (value) => value);
  syncFilterOptions(typeFilter, nodeTypes, (value) => value.replaceAll("_", " "));
}

function timeWindowToMs(value) {
  if (value === "7d") {
    return 7 * 24 * 60 * 60 * 1000;
  }
  if (value === "30d") {
    return 30 * 24 * 60 * 60 * 1000;
  }
  if (value === "90d") {
    return 90 * 24 * 60 * 60 * 1000;
  }
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

function filteredSnapshot(snapshot) {
  const visibleNodes = snapshot.nodes.filter((node) => nodeMatchesFilters(node));
  const visibleNodeIds = new Set(visibleNodes.map((node) => node.id));
  const visibleEdges = snapshot.edges.filter(
    (edge) => visibleNodeIds.has(edge.source) && visibleNodeIds.has(edge.target)
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
  if (!currentBaseSnapshot) {
    return;
  }

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

async function loadSnapshot(mode = modeSelect.value) {
  const response = await fetch(`/api/snapshot?mode=${encodeURIComponent(mode)}`, {
    headers: { "X-Cortex-WebGraph": "1" },
  });
  if (!response.ok) {
    throw new Error(`Snapshot request failed with ${response.status}`);
  }
  const snapshot = await response.json();
  rootSnapshot = snapshot;
  currentBaseSnapshot = snapshot;
  populateFilterOptions(snapshot);
  refreshView({ preserveSelection: false });
}

async function selectNode(nodeId) {
  const response = await fetch(`/api/node/${encodeURIComponent(nodeId)}?mode=${encodeURIComponent(modeSelect.value)}`, {
    headers: { "X-Cortex-WebGraph": "1" },
  });
  if (!response.ok) {
    throw new Error(`Node detail request failed with ${response.status}`);
  }
  const detail = await response.json();
  renderDetail(detail);
}

function focusNode(nodeId) {
  if (!network) {
    return;
  }
  network.selectNodes([nodeId]);
  network.focus(nodeId, {
    scale: 1.12,
    animation: { duration: 500, easingFunction: "easeInOutQuad" },
  });
  selectNode(nodeId).catch((error) => toast(`Failed to load node detail: ${error.message}`));
}

async function openNode(nodeId = selectedNode?.id) {
  if (!nodeId) {
    return;
  }
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
  toast("Document opened from Cortex WebGraph");
}

async function loadSubgraph(nodeId = selectedNode?.id) {
  if (!nodeId) {
    return;
  }
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

function findNode() {
  const term = searchInput.value.trim().toLowerCase();
  if (!term || !currentSnapshot?.nodes?.length) {
    return;
  }
  const match = currentSnapshot.nodes.find((node) => labelForNode(node).toLowerCase().includes(term));
  if (!match) {
    toast(`No node found for "${searchInput.value}"`);
    return;
  }
  focusNode(match.id);
}

reloadButton.addEventListener("click", () => {
  loadSnapshot().catch((error) => toast(`Failed to reload graph: ${error.message}`));
});

modeSelect.addEventListener("change", () => {
  loadSnapshot(modeSelect.value).catch((error) => toast(`Failed to switch mode: ${error.message}`));
});

[projectFilter, typeFilter, timeFilter].forEach((element) => {
  element.addEventListener("change", () => refreshView());
});

searchButton.addEventListener("click", findNode);
searchInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    findNode();
  }
});

openNodeButton.addEventListener("click", () => {
  openNode().catch((error) => toast(`Failed to open node: ${error.message}`));
});

loadSubgraphButton.addEventListener("click", () => {
  loadSubgraph().catch((error) => toast(`Failed to load subgraph: ${error.message}`));
});

resetButton.addEventListener("click", () => {
  if (!rootSnapshot) {
    return;
  }
  currentBaseSnapshot = rootSnapshot;
  refreshView();
});

loadSnapshot().catch((error) => {
  toast(`Failed to load snapshot: ${error.message}`);
  networkContainer.innerHTML = `<p style="padding:16px;color:#7a1f1f;">Failed to load Cortex graph: ${error.message}</p>`;
});
