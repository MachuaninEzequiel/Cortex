import React, { useState, useMemo, useEffect } from "react";
import { GraphNode, ProjectGraphPayload, Lang, PinnedContextNode } from "../types";
import { getT } from "../i18n";

interface WebGraphModalProps {
  isOpen: boolean;
  onClose: () => void;
  graphData: ProjectGraphPayload | null;
  isLoading: boolean;
  highlightedNodeIds: string[];
  onPinNode: (node: PinnedContextNode) => void;
  onLaunchExternalServer?: () => void;
  lang: Lang;
}

export const WebGraphModal: React.FC<WebGraphModalProps> = ({
  isOpen,
  onClose,
  graphData,
  isLoading,
  highlightedNodeIds,
  onPinNode,
  onLaunchExternalServer,
  lang,
}) => {
  const t = getT(lang);
  const [filterKind, setFilterKind] = useState<string>("all");
  const [searchTerm, setSearchTerm] = useState<string>("");
  const [zoom, setZoom] = useState<number>(1);
  const [pan, setPan] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [dragStart, setDragStart] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  // Keyboard escape
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  // Filtrado de nodos
  const filteredNodes = useMemo(() => {
    if (!graphData || !graphData.nodes) return [];
    return graphData.nodes.filter((node) => {
      const matchesKind = filterKind === "all" || node.kind === filterKind;
      const matchesSearch =
        searchTerm.trim() === "" ||
        node.label.toLowerCase().includes(searchTerm.toLowerCase()) ||
        node.path.toLowerCase().includes(searchTerm.toLowerCase());
      return matchesKind && matchesSearch;
    });
  }, [graphData, filterKind, searchTerm]);

  // Layout determinístico: Nodo raíz en el centro, otros orbitando simétricamente
  const nodePositions = useMemo(() => {
    const positions: Record<string, { x: number; y: number }> = {};
    const count = filteredNodes.length;
    if (count === 0) return positions;

    const centerX = 380;
    const centerY = 260;
    const radius = Math.min(200, Math.max(130, count * 30));

    const rootIndex = filteredNodes.findIndex((n) => n.kind === "module" || n.id === "root");
    const hasCenter = rootIndex >= 0 && count > 1;

    let orbitIdx = 0;
    const orbitCount = hasCenter ? count - 1 : count;

    filteredNodes.forEach((node, idx) => {
      if (hasCenter && idx === rootIndex) {
        positions[node.id] = { x: centerX, y: centerY };
      } else {
        const angle = (orbitIdx / orbitCount) * 2 * Math.PI - Math.PI / 2;
        positions[node.id] = {
          x: centerX + radius * Math.cos(angle),
          y: centerY + radius * Math.sin(angle),
        };
        orbitIdx++;
      }
    });

    return positions;
  }, [filteredNodes]);

  // Filtrado de aristas visibles
  const visibleEdges = useMemo(() => {
    if (!graphData || !graphData.edges) return [];
    const visibleIds = new Set(filteredNodes.map((n) => n.id));
    return graphData.edges.filter((e) => visibleIds.has(e.source) && visibleIds.has(e.target));
  }, [graphData, filteredNodes]);

  // Manejo de drag & pan del canvas
  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.button === 0) {
      setIsDragging(true);
      setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
    }
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isDragging) {
      setPan({ x: e.clientX - dragStart.x, y: e.clientY - dragStart.y });
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const handleNodeClick = (node: GraphNode, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    setSelectedNodeId(node.id);
    onPinNode({
      id: node.id,
      label: node.label,
      kind: node.kind,
      path: node.path,
    });
  };

  const getNodeColor = (kind: string, isHighlighted: boolean, isSelected: boolean) => {
    if (isSelected) return "#f5c2e7"; // Pink
    if (isHighlighted) return "#a6e3a1"; // Green
    switch (kind) {
      case "module":
        return "#cba6f7"; // Mauve
      case "spec":
        return "#a6e3a1"; // Mint
      case "adr":
        return "#fab387"; // Peach
      case "file":
      default:
        return "#89b4fa"; // Blue
    }
  };

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center select-none"
      style={{ backgroundColor: "rgba(0, 0, 0, 0.75)" }}
    >
      <div
        className="flex flex-col rounded-xl border border-[#313244] shadow-2xl overflow-hidden font-sans"
        style={{
          width: "960px",
          maxWidth: "94vw",
          height: "620px",
          maxHeight: "90vh",
          backgroundColor: "#1e1e2e",
          color: "#cdd6f4",
        }}
      >
        {/* Header */}
        <div
          className="flex h-14 items-center justify-between px-5 border-b border-[#313244]"
          style={{ backgroundColor: "#181825" }}
        >
          <div className="flex items-center gap-3">
            <span className="text-xl">🕸️</span>
            <div>
              <h3 className="font-bold text-sm font-mono text-[#cdd6f4]">
                {t.webgraph.title}
              </h3>
              <p className="text-[11px] text-[#a6adc8]">
                {t.webgraph.subtitle}
              </p>
            </div>
          </div>

          {/* Search, Server trigger & Close */}
          <div className="flex items-center gap-3">
            <div className="relative">
              <input
                type="text"
                placeholder={t.webgraph.searchPlaceholder}
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-48 rounded-lg border border-[#313244] bg-[#313244]/60 px-3 py-1 font-mono text-xs text-[#cdd6f4] focus:outline-none focus:border-[#cba6f7]"
              />
              {searchTerm && (
                <button
                  onClick={() => setSearchTerm("")}
                  className="absolute right-2 top-1 text-xs text-[#a6adc8] hover:text-[#cdd6f4]"
                >
                  ✕
                </button>
              )}
            </div>

            {onLaunchExternalServer && (
              <button
                onClick={onLaunchExternalServer}
                className="flex items-center gap-1.5 rounded-lg border border-[#313244] bg-[#313244]/40 px-3 py-1 font-mono text-xs text-[#8FDCB0] hover:bg-[#03522E]/40 transition active:scale-95"
                title="Levanta el visualizador WebGraph nativo de Cortex en un puerto local"
              >
                <span>🌐</span>
                <span className="hidden sm:inline">Servidor Web</span>
              </button>
            )}

            <button
              onClick={onClose}
              className="rounded-lg bg-[#313244] px-3 py-1 font-mono text-xs text-[#cdd6f4] hover:bg-[#cba6f7] hover:text-[#181825] transition"
            >
              ✕ {t.webgraph.close}
            </button>
          </div>
        </div>

        {/* Filter Bar */}
        <div
          className="flex items-center justify-between px-5 py-2 border-b border-[#313244]"
          style={{ backgroundColor: "#1e1e2e" }}
        >
          <div className="flex items-center gap-2 font-mono text-xs">
            <span className="text-[#a6adc8]">Filtrar:</span>
            {["all", "module", "file", "spec", "adr"].map((kind) => (
              <button
                key={kind}
                onClick={() => setFilterKind(kind)}
                className={`rounded px-2.5 py-0.5 transition ${
                  filterKind === kind
                    ? "bg-[#cba6f7] text-[#181825] font-bold"
                    : "bg-[#313244]/50 text-[#a6adc8] hover:text-[#cdd6f4] hover:bg-[#313244]"
                }`}
              >
                {kind === "all"
                  ? t.webgraph.allNodes
                  : kind === "module"
                  ? t.webgraph.modules
                  : kind === "file"
                  ? t.webgraph.files
                  : kind === "spec"
                  ? t.webgraph.specs
                  : t.webgraph.adrs}
              </button>
            ))}
          </div>

          <div className="text-xs font-mono text-[#a6adc8]">
            {filteredNodes.length} nodos / {visibleEdges.length} relaciones
          </div>
        </div>

        {/* Content Body: Sidebar List + SVG Canvas */}
        <div className="flex flex-1 min-h-0 min-w-0 overflow-hidden">
          {/* Left: Interactive Node Directory List */}
          <div
            className="w-64 border-r border-[#313244] p-3 overflow-y-auto flex flex-col gap-1.5 font-mono text-xs flex-shrink-0"
            style={{ backgroundColor: "#181825" }}
          >
            <div className="text-[10px] font-bold text-[#a6adc8] uppercase tracking-wider mb-1 px-1">
              Directorio de Nodos ({filteredNodes.length})
            </div>
            {filteredNodes.length === 0 ? (
              <div className="text-xs text-[#585b70] p-2">Sin nodos disponibles</div>
            ) : (
              filteredNodes.map((node) => {
                const isSelected = selectedNodeId === node.id;
                const isHighlighted = highlightedNodeIds.includes(node.id);
                const color = getNodeColor(node.kind, isHighlighted, isSelected);

                return (
                  <div
                    key={node.id}
                    onClick={() => handleNodeClick(node)}
                    className={`flex items-center justify-between rounded-lg p-2 cursor-pointer transition ${
                      isSelected
                        ? "bg-[#cba6f7]/20 border border-[#cba6f7] text-[#cdd6f4]"
                        : "bg-[#313244]/30 border border-[#313244]/50 text-[#a6adc8] hover:bg-[#313244] hover:text-[#cdd6f4]"
                    }`}
                  >
                    <div className="flex items-center gap-2 truncate">
                      <span
                        className="h-2.5 w-2.5 rounded-full flex-shrink-0"
                        style={{ backgroundColor: color }}
                      />
                      <span className="truncate font-semibold">{node.label}</span>
                    </div>
                    <span className="text-[10px] rounded bg-[#313244] px-1 py-0.5 text-[#a6adc8]">
                      {node.kind}
                    </span>
                  </div>
                );
              })
            )}
          </div>

          {/* Right: Interactive SVG Canvas */}
          <div
            className="relative flex-1 min-h-0 min-w-0 overflow-hidden cursor-grab active:cursor-grabbing"
            style={{ backgroundColor: "#11111b" }}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
          >
            {isLoading ? (
              <div className="flex h-full w-full items-center justify-center">
                <div className="flex items-center gap-3 rounded-xl border border-[#313244] bg-[#181825] px-6 py-4 font-mono text-xs text-[#cba6f7] animate-pulse">
                  <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-[#cba6f7] border-t-transparent" />
                  <span>Extrayendo grafo de dependencias y specs...</span>
                </div>
              </div>
            ) : filteredNodes.length === 0 ? (
              <div className="flex h-full w-full items-center justify-center font-mono text-xs text-[#585b70]">
                No se encontraron nodos que coincidan con la búsqueda.
              </div>
            ) : (
              <svg
                width="100%"
                height="100%"
                viewBox="0 0 760 520"
                style={{
                  transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
                  transformOrigin: "center center",
                  transition: isDragging ? "none" : "transform 0.15s ease-out",
                  display: "block",
                }}
              >
                {/* Aristas / Conexiones */}
                <g className="edges">
                  {visibleEdges.map((edge, idx) => {
                    const src = nodePositions[edge.source];
                    const tgt = nodePositions[edge.target];
                    if (!src || !tgt) return null;
                    const isHighlighted =
                      highlightedNodeIds.includes(edge.source) || highlightedNodeIds.includes(edge.target);
                    return (
                      <line
                        key={`${edge.source}-${edge.target}-${idx}`}
                        x1={src.x}
                        y1={src.y}
                        x2={tgt.x}
                        y2={tgt.y}
                        stroke={isHighlighted ? "#a6e3a1" : "#45475a"}
                        strokeWidth={isHighlighted ? 3 : 1.8}
                        strokeDasharray={edge.relation === "tests" ? "4 4" : undefined}
                      />
                    );
                  })}
                </g>

                {/* Nodos */}
                <g className="nodes">
                  {filteredNodes.map((node) => {
                    const pos = nodePositions[node.id];
                    if (!pos) return null;
                    const isHighlighted = highlightedNodeIds.includes(node.id);
                    const isSelected = selectedNodeId === node.id;
                    const color = getNodeColor(node.kind, isHighlighted, isSelected);

                    const pillWidth = Math.max(70, node.label.length * 7.5 + 16);

                    return (
                      <g
                        key={node.id}
                        transform={`translate(${pos.x}, ${pos.y})`}
                        onClick={(e) => handleNodeClick(node, e)}
                        className="cursor-pointer"
                      >
                        {/* Círculo Principal */}
                        <circle
                          r={isHighlighted || isSelected ? 22 : 18}
                          fill="#1e1e2e"
                          stroke={color}
                          strokeWidth={isHighlighted || isSelected ? 4 : 2.5}
                        />

                        {/* Icono / Inicial */}
                        <text
                          textAnchor="middle"
                          dy=".35em"
                          fill={color}
                          fontSize={isHighlighted || isSelected ? "13" : "11"}
                          fontWeight="bold"
                          fontFamily="monospace"
                          style={{ pointerEvents: "none" }}
                        >
                          {node.kind === "module"
                            ? "📦"
                            : node.kind === "spec"
                            ? "📄"
                            : node.kind === "adr"
                            ? "🏛️"
                            : "📄"}
                        </text>

                        {/* Pill de fondo para el texto */}
                        <rect
                          x={-pillWidth / 2}
                          y={isHighlighted || isSelected ? 28 : 24}
                          width={pillWidth}
                          height="18"
                          rx="4"
                          fill="#181825"
                          stroke={isSelected ? color : "#313244"}
                          strokeWidth="1"
                          style={{ pointerEvents: "none" }}
                        />

                        {/* Etiqueta / Nombre */}
                        <text
                          textAnchor="middle"
                          y={isHighlighted || isSelected ? 41 : 37}
                          fill={isHighlighted || isSelected ? "#cdd6f4" : "#a6adc8"}
                          fontSize="11"
                          fontWeight={isHighlighted || isSelected ? "bold" : "normal"}
                          fontFamily="monospace"
                          style={{ pointerEvents: "none" }}
                        >
                          {node.label}
                        </text>
                      </g>
                    );
                  })}
                </g>
              </svg>
            )}

            {/* Floating Controls: Zoom */}
            <div
              className="absolute bottom-3 right-3 flex items-center gap-1.5 rounded-lg border border-[#313244] p-1.5 shadow-lg"
              style={{ backgroundColor: "#181825" }}
            >
              <button
                onClick={() => setZoom((z) => Math.min(2.5, z + 0.2))}
                className="h-6 w-6 rounded bg-[#313244] font-mono text-xs text-[#cdd6f4] hover:bg-[#cba6f7] hover:text-[#181825] transition"
                title="Zoom In"
              >
                +
              </button>
              <button
                onClick={() => setZoom((z) => Math.max(0.4, z - 0.2))}
                className="h-6 w-6 rounded bg-[#313244] font-mono text-xs text-[#cdd6f4] hover:bg-[#cba6f7] hover:text-[#181825] transition"
                title="Zoom Out"
              >
                -
              </button>
              <button
                onClick={() => {
                  setZoom(1);
                  setPan({ x: 0, y: 0 });
                }}
                className="rounded bg-[#313244] px-2 py-0.5 font-mono text-[10px] text-[#cdd6f4] hover:bg-[#cba6f7] hover:text-[#181825] transition"
                title="Reset View"
              >
                Reset
              </button>
            </div>

            {/* Legend Banner */}
            <div
              className="absolute bottom-3 left-3 flex items-center gap-3 rounded-lg border border-[#313244] px-3 py-1.5 text-[10px] font-mono text-[#a6adc8] shadow-lg"
              style={{ backgroundColor: "#181825" }}
            >
              <div className="flex items-center gap-1">
                <span className="h-2 w-2 rounded-full bg-[#cba6f7]" />
                <span>Módulos</span>
              </div>
              <div className="flex items-center gap-1">
                <span className="h-2 w-2 rounded-full bg-[#89b4fa]" />
                <span>Archivos</span>
              </div>
              <div className="flex items-center gap-1">
                <span className="h-2 w-2 rounded-full bg-[#a6e3a1]" />
                <span>Specs</span>
              </div>
              <div className="flex items-center gap-1">
                <span className="h-2 w-2 rounded-full bg-[#fab387]" />
                <span>ADRs</span>
              </div>
            </div>
          </div>
        </div>

        {/* Footer Hint */}
        <div
          className="flex h-8 items-center justify-between px-5 border-t border-[#313244] font-mono text-[10px] text-[#a6adc8]"
          style={{ backgroundColor: "#181825" }}
        >
          <span>💡 {t.webgraph.clickHint}</span>
          <span className="text-[#cba6f7] font-semibold">Cortex WebGraph Engine</span>
        </div>
      </div>
    </div>
  );
};
