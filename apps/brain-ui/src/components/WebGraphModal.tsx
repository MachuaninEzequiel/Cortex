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
  lang: Lang;
}

export const WebGraphModal: React.FC<WebGraphModalProps> = ({
  isOpen,
  onClose,
  graphData,
  isLoading,
  highlightedNodeIds,
  onPinNode,
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

  if (!isOpen) return null;

  // Filtrado de nodos
  const filteredNodes = useMemo(() => {
    if (!graphData) return [];
    return graphData.nodes.filter((node) => {
      const matchesKind = filterKind === "all" || node.kind === filterKind;
      const matchesSearch =
        searchTerm.trim() === "" ||
        node.label.toLowerCase().includes(searchTerm.toLowerCase()) ||
        node.path.toLowerCase().includes(searchTerm.toLowerCase());
      return matchesKind && matchesSearch;
    });
  }, [graphData, filterKind, searchTerm]);

  // Layout posicional circular/orbital determinístico para los nodos
  const nodePositions = useMemo(() => {
    const positions: Record<string, { x: number; y: number }> = {};
    const count = filteredNodes.length;
    if (count === 0) return positions;

    const centerX = 400;
    const centerY = 300;
    const radius = Math.min(260, Math.max(120, count * 18));

    filteredNodes.forEach((node, idx) => {
      const angle = (idx / count) * 2 * Math.PI;
      // Posición orbital con variación según el tipo
      const dist = node.kind === "module" ? radius * 0.5 : node.kind === "spec" ? radius * 0.8 : radius;
      positions[node.id] = {
        x: centerX + dist * Math.cos(angle),
        y: centerY + dist * Math.sin(angle),
      };
    });

    return positions;
  }, [filteredNodes]);

  // Filtrado de aristas visibles
  const visibleEdges = useMemo(() => {
    if (!graphData) return [];
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

  const handleNodeClick = (node: GraphNode, e: React.MouseEvent) => {
    e.stopPropagation();
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
    if (isHighlighted) return "#a6e3a1"; // Green glow
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

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-mocha-crust/85 backdrop-blur-md p-6 select-none animate-fade-in">
      <div className="flex h-[85vh] w-[90vw] max-w-6xl flex-col rounded-2xl border border-mocha-surface bg-mocha-base shadow-2xl overflow-hidden font-sans">
        {/* Header */}
        <div className="flex h-14 items-center justify-between border-b border-mocha-surface bg-mocha-surface/20 px-6">
          <div className="flex items-center gap-3">
            <span className="text-xl">🕸️</span>
            <div>
              <h3 className="font-bold text-mocha-text font-mono text-sm">
                {t.webgraph.title}
              </h3>
              <p className="text-[11px] text-mocha-subtext0">
                {t.webgraph.subtitle}
              </p>
            </div>
          </div>

          {/* Search & Filter bar */}
          <div className="flex items-center gap-3">
            <div className="relative">
              <input
                type="text"
                placeholder={t.webgraph.searchPlaceholder}
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-56 rounded-lg border border-mocha-surface bg-mocha-surface/50 px-3 py-1.5 font-mono text-xs text-mocha-text focus:border-mocha-mauve focus:outline-none"
              />
              {searchTerm && (
                <button
                  onClick={() => setSearchTerm("")}
                  className="absolute right-2 top-1.5 text-xs text-mocha-subtext0 hover:text-mocha-text"
                >
                  ✕
                </button>
              )}
            </div>

            <div className="flex rounded-lg border border-mocha-surface bg-mocha-surface/30 p-0.5 font-mono text-[11px]">
              {["all", "module", "file", "spec", "adr"].map((kind) => (
                <button
                  key={kind}
                  onClick={() => setFilterKind(kind)}
                  className={`rounded px-2.5 py-1 transition ${
                    filterKind === kind
                      ? "bg-mocha-mauve text-mocha-base font-bold"
                      : "text-mocha-subtext0 hover:text-mocha-text"
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

            <button
              onClick={onClose}
              className="rounded-lg bg-mocha-surface px-3 py-1.5 font-mono text-xs text-mocha-text hover:bg-mocha-mauve hover:text-mocha-base transition"
            >
              {t.webgraph.close}
            </button>
          </div>
        </div>

        {/* Main Canvas Area */}
        <div
          className="relative flex-1 bg-mocha-base/80 overflow-hidden cursor-grab active:cursor-grabbing"
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
        >
          {isLoading ? (
            <div className="flex h-full w-full items-center justify-center">
              <div className="flex items-center gap-3 rounded-xl border border-mocha-surface bg-mocha-surface/30 px-6 py-4 font-mono text-xs text-mocha-mauve animate-pulse">
                <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-mocha-mauve border-t-transparent" />
                <span>Extrayendo grafo de dependencias y specs...</span>
              </div>
            </div>
          ) : filteredNodes.length === 0 ? (
            <div className="flex h-full w-full items-center justify-center font-mono text-xs text-mocha-surface2">
              No se encontraron nodos que coincidan con la búsqueda.
            </div>
          ) : (
            <svg
              className="h-full w-full"
              viewBox="0 0 800 600"
              style={{
                transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
                transformOrigin: "center center",
                transition: isDragging ? "none" : "transform 0.15s ease-out",
              }}
            >
              <defs>
                <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
                  <feGaussianBlur stdDeviation="6" result="blur" />
                  <feComposite in="SourceGraphic" in2="blur" operator="over" />
                </filter>
              </defs>

              {/* Aristas / Conexiones */}
              <g className="edges opacity-40">
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
                      stroke={isHighlighted ? "#a6e3a1" : "#585b70"}
                      strokeWidth={isHighlighted ? 2.5 : 1.2}
                      strokeDasharray={edge.relation === "tests" ? "4 4" : undefined}
                      className="transition-all duration-300"
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

                  return (
                    <g
                      key={node.id}
                      transform={`translate(${pos.x}, ${pos.y})`}
                      onClick={(e) => handleNodeClick(node, e)}
                      className="cursor-pointer group"
                    >
                      {/* Aura de Glow si está resaltado */}
                      {isHighlighted && (
                        <circle
                          r="26"
                          fill="#a6e3a1"
                          opacity="0.3"
                          filter="url(#glow)"
                          className="animate-pulse"
                        />
                      )}

                      {/* Círculo Principal */}
                      <circle
                        r={isHighlighted || isSelected ? 18 : 14}
                        fill="#181825"
                        stroke={color}
                        strokeWidth={isHighlighted || isSelected ? 3.5 : 2}
                        className="transition-all duration-200 group-hover:scale-125"
                      />

                      {/* Icono / Inicial según kind */}
                      <text
                        textAnchor="middle"
                        dy=".3em"
                        fill={color}
                        fontSize="10"
                        fontWeight="bold"
                        fontFamily="monospace"
                        className="pointer-events-none"
                      >
                        {node.kind === "module"
                          ? "M"
                          : node.kind === "spec"
                          ? "S"
                          : node.kind === "adr"
                          ? "A"
                          : "F"}
                      </text>

                      {/* Etiqueta / Nombre */}
                      <text
                        textAnchor="middle"
                        y={isHighlighted || isSelected ? 32 : 26}
                        fill={isHighlighted || isSelected ? "#cdd6f4" : "#a6adc8"}
                        fontSize="11"
                        fontWeight={isHighlighted || isSelected ? "bold" : "normal"}
                        fontFamily="monospace"
                        className="pointer-events-none select-none drop-shadow-md"
                      >
                        {node.label}
                      </text>
                    </g>
                  );
                })}
              </g>
            </svg>
          )}

          {/* Floating Controls: Zoom & Legend */}
          <div className="absolute bottom-4 right-4 flex items-center gap-2 rounded-xl border border-mocha-surface bg-mocha-base/90 p-2 shadow-lg backdrop-blur">
            <button
              onClick={() => setZoom((z) => Math.min(2.5, z + 0.2))}
              className="h-7 w-7 rounded bg-mocha-surface font-mono text-xs text-mocha-text hover:bg-mocha-mauve hover:text-mocha-base transition"
              title="Zoom In"
            >
              +
            </button>
            <button
              onClick={() => setZoom((z) => Math.max(0.4, z - 0.2))}
              className="h-7 w-7 rounded bg-mocha-surface font-mono text-xs text-mocha-text hover:bg-mocha-mauve hover:text-mocha-base transition"
              title="Zoom Out"
            >
              -
            </button>
            <button
              onClick={() => {
                setZoom(1);
                setPan({ x: 0, y: 0 });
              }}
              className="rounded bg-mocha-surface px-2.5 py-1 font-mono text-[11px] text-mocha-text hover:bg-mocha-mauve hover:text-mocha-base transition"
              title="Reset"
            >
              Reset
            </button>
          </div>

          {/* Legend Banner */}
          <div className="absolute bottom-4 left-4 flex items-center gap-4 rounded-xl border border-mocha-surface bg-mocha-base/90 px-4 py-2 text-[11px] font-mono text-mocha-subtext0 shadow-lg backdrop-blur">
            <div className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-full bg-[#cba6f7]" />
              <span>{t.webgraph.legendModules}</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-full bg-[#89b4fa]" />
              <span>{t.webgraph.legendFiles}</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-full bg-[#a6e3a1]" />
              <span>{t.webgraph.legendSpecs}</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-full bg-[#fab387]" />
              <span>{t.webgraph.legendAdrs}</span>
            </div>
          </div>
        </div>

        {/* Footer Hint */}
        <div className="flex h-9 items-center justify-between border-t border-mocha-surface bg-mocha-surface/10 px-6 font-mono text-[11px] text-mocha-surface2">
          <span>💡 {t.webgraph.clickHint}</span>
          <span>{filteredNodes.length} nodos / {visibleEdges.length} conexiones</span>
        </div>
      </div>
    </div>
  );
};
