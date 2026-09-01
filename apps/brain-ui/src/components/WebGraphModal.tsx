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

  // Layout determinístico: Nodo raíz en el centro, otros orbitando simétricamente
  const nodePositions = useMemo(() => {
    const positions: Record<string, { x: number; y: number }> = {};
    const count = filteredNodes.length;
    if (count === 0) return positions;

    const centerX = 400;
    const centerY = 280;
    const radius = Math.min(220, Math.max(140, count * 35));

    // Si el primer nodo es root/module, ponerlo al centro
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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-6 select-none animate-fade-in font-sans">
      <div className="flex h-[88vh] w-[92vw] max-w-6xl flex-col rounded-2xl border border-mocha-surface bg-mocha-base shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex h-14 items-center justify-between border-b border-mocha-surface bg-mocha-mantle px-6">
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

          {/* Search, Server trigger & Close */}
          <div className="flex items-center gap-3">
            <div className="relative">
              <input
                type="text"
                placeholder={t.webgraph.searchPlaceholder}
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-52 rounded-lg border border-mocha-surface bg-mocha-surface/50 px-3 py-1.5 font-mono text-xs text-mocha-text focus:border-mocha-mauve focus:outline-none"
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

            {onLaunchExternalServer && (
              <button
                onClick={onLaunchExternalServer}
                className="flex items-center gap-1.5 rounded-lg border border-mocha-surface bg-mocha-surface/40 px-3 py-1.5 font-mono text-xs text-cortex-mint hover:bg-cortex-forest/40 transition active:scale-95"
                title="Levanta el visualizador WebGraph nativo de Cortex en un puerto local"
              >
                <span>🌐</span>
                <span>Servidor Web</span>
              </button>
            )}

            <button
              onClick={onClose}
              className="rounded-lg bg-mocha-surface px-3 py-1.5 font-mono text-xs text-mocha-text hover:bg-mocha-mauve hover:text-mocha-base transition"
            >
              ✕ {t.webgraph.close}
            </button>
          </div>
        </div>

        {/* Filter Bar */}
        <div className="flex items-center justify-between border-b border-mocha-surface/60 bg-mocha-surface/20 px-6 py-2">
          <div className="flex items-center gap-2 font-mono text-xs">
            <span className="text-mocha-subtext0">Filtrar:</span>
            {["all", "module", "file", "spec", "adr"].map((kind) => (
              <button
                key={kind}
                onClick={() => setFilterKind(kind)}
                className={`rounded px-2.5 py-1 transition ${
                  filterKind === kind
                    ? "bg-mocha-mauve text-mocha-base font-bold shadow-sm"
                    : "bg-mocha-surface/30 text-mocha-subtext0 hover:text-mocha-text hover:bg-mocha-surface/60"
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

          <div className="text-xs font-mono text-mocha-subtext0">
            {filteredNodes.length} nodos / {visibleEdges.length} relaciones
          </div>
        </div>

        {/* Content Body: Sidebar List + SVG Canvas */}
        <div className="flex flex-1 overflow-hidden">
          {/* Left: Interactive Node Directory List */}
          <div className="w-72 border-r border-mocha-surface bg-mocha-mantle/60 p-3 overflow-y-auto flex flex-col gap-1.5 font-mono text-xs">
            <div className="text-[11px] font-bold text-mocha-subtext0 uppercase tracking-wider mb-1 px-1">
              Directorio de Nodos ({filteredNodes.length})
            </div>
            {filteredNodes.map((node) => {
              const isSelected = selectedNodeId === node.id;
              const isHighlighted = highlightedNodeIds.includes(node.id);
              const color = getNodeColor(node.kind, isHighlighted, isSelected);

              return (
                <div
                  key={node.id}
                  onClick={() => handleNodeClick(node)}
                  className={`flex items-center justify-between rounded-lg p-2 cursor-pointer transition ${
                    isSelected
                      ? "bg-mocha-mauve/20 border border-mocha-mauve text-mocha-text"
                      : "bg-mocha-surface/20 border border-mocha-surface/40 text-mocha-subtext0 hover:bg-mocha-surface/50 hover:text-mocha-text"
                  }`}
                >
                  <div className="flex items-center gap-2 truncate">
                    <span
                      className="h-2.5 w-2.5 rounded-full flex-shrink-0"
                      style={{ backgroundColor: color }}
                    />
                    <span className="truncate font-semibold">{node.label}</span>
                  </div>
                  <span className="text-[10px] rounded bg-mocha-surface px-1 py-0.5 text-mocha-surface2">
                    {node.kind}
                  </span>
                </div>
              );
            })}
          </div>

          {/* Right: Interactive SVG Canvas */}
          <div
            className="relative flex-1 bg-mocha-base/90 overflow-hidden cursor-grab active:cursor-grabbing"
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
                viewBox="0 0 800 560"
                style={{
                  transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
                  transformOrigin: "center center",
                  transition: isDragging ? "none" : "transform 0.15s ease-out",
                }}
              >
                <defs>
                  <filter id="glow" x="-30%" y="-30%" width="160%" height="160%">
                    <feGaussianBlur stdDeviation="8" result="blur" />
                    <feComposite in="SourceGraphic" in2="blur" operator="over" />
                  </filter>
                </defs>

                {/* Aristas / Conexiones */}
                <g className="edges opacity-60">
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
                        strokeWidth={isHighlighted ? 3 : 1.5}
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

                    return (
                      <g
                        key={node.id}
                        transform={`translate(${pos.x}, ${pos.y})`}
                        onClick={(e) => handleNodeClick(node, e)}
                        className="cursor-pointer group"
                      >
                        {/* Glow si está resaltado o seleccionado */}
                        {(isHighlighted || isSelected) && (
                          <circle
                            r="32"
                            fill={color}
                            opacity="0.35"
                            filter="url(#glow)"
                            className="animate-pulse"
                          />
                        )}

                        {/* Círculo Principal */}
                        <circle
                          r={isHighlighted || isSelected ? 22 : 18}
                          fill="#181825"
                          stroke={color}
                          strokeWidth={isHighlighted || isSelected ? 4 : 2.5}
                          className="transition-all duration-200 group-hover:scale-110 shadow-lg"
                        />

                        {/* Icono / Inicial */}
                        <text
                          textAnchor="middle"
                          dy=".35em"
                          fill={color}
                          fontSize={isHighlighted || isSelected ? "13" : "11"}
                          fontWeight="bold"
                          fontFamily="monospace"
                          className="pointer-events-none select-none"
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
                          x={-(node.label.length * 3.8 + 8)}
                          y={isHighlighted || isSelected ? 30 : 26}
                          width={node.label.length * 7.6 + 16}
                          height="18"
                          rx="4"
                          fill="#11111b"
                          stroke={isSelected ? color : "#313244"}
                          strokeWidth="1"
                          opacity="0.95"
                          className="pointer-events-none"
                        />

                        {/* Etiqueta / Nombre */}
                        <text
                          textAnchor="middle"
                          y={isHighlighted || isSelected ? 43 : 39}
                          fill={isHighlighted || isSelected ? "#cdd6f4" : "#a6adc8"}
                          fontSize="11"
                          fontWeight={isHighlighted || isSelected ? "bold" : "normal"}
                          fontFamily="monospace"
                          className="pointer-events-none select-none"
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
            <div className="absolute bottom-4 right-4 flex items-center gap-2 rounded-xl border border-mocha-surface bg-mocha-mantle/90 p-2 shadow-lg backdrop-blur">
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
                title="Reset View"
              >
                Reset
              </button>
            </div>

            {/* Legend Banner */}
            <div className="absolute bottom-4 left-4 flex items-center gap-4 rounded-xl border border-mocha-surface bg-mocha-mantle/90 px-4 py-2 text-[11px] font-mono text-mocha-subtext0 shadow-lg backdrop-blur">
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
        </div>

        {/* Footer Hint */}
        <div className="flex h-9 items-center justify-between border-t border-mocha-surface bg-mocha-mantle px-6 font-mono text-[11px] text-mocha-subtext0">
          <span>💡 {t.webgraph.clickHint}</span>
          <span className="text-mocha-mauve font-semibold">Cortex Brain 2.0 WebGraph Engine</span>
        </div>
      </div>
    </div>
  );
};
