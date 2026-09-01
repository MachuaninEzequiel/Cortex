import React from "react";
import { MarkRamState } from "../types";

interface MarkRamProps {
  state: MarkRamState;
  size?: "sm" | "md" | "lg";
  showLabel?: boolean;
  className?: string;
}

export const MarkRam: React.FC<MarkRamProps> = ({
  state,
  size = "md",
  showLabel = false,
  className = "",
}) => {
  const sizeMap = {
    sm: { box: "w-4 h-4", text: "text-xs" },
    md: { box: "w-6 h-6", text: "text-sm" },
    lg: { box: "w-8 h-8", text: "text-base" },
  };

  // Colores y animaciones según estado
  const stateConfig = {
    idle: {
      top: "#585b70",
      face: "#45475a",
      shadow: "#313244",
      dot: "bg-mocha-surface2",
      label: "Idle (0 MB RAM)",
      pulse: "",
    },
    weak_awake: {
      top: "#C8F0DC",
      face: "#AEE8C6",
      shadow: "#03522E",
      dot: "bg-cortex-mint opacity-80",
      label: "En espera (en RAM)",
      pulse: "animate-pulse",
    },
    awake: {
      top: "#E4EDE7",
      face: "#8FDCB0",
      shadow: "#06331C",
      dot: "bg-cortex-mint shadow-[0_0_8px_#8FDCB0]",
      label: "Activo (LFM2.5 en RAM)",
      pulse: "animate-pulse shadow-sm",
    },
  };

  const current = stateConfig[state];

  return (
    <div className={`inline-flex items-center gap-2 ${className}`} title={current.label}>
      <svg
        viewBox="0 0 24 24"
        className={`${sizeMap[size].box} ${current.pulse} transition-all duration-300`}
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        {/* Isotipo Voxel Cortex 3D */}
        {/* Cara superior (Top / Highlight) */}
        <path
          d="M12 2L20 6.5L12 11L4 6.5L12 2Z"
          fill={current.top}
          className="transition-colors duration-300"
        />
        {/* Cara frontal izquierda (Face / Mint) */}
        <path
          d="M4 6.5L12 11V21L4 16.5V6.5Z"
          fill={current.face}
          className="transition-colors duration-300"
        />
        {/* Cara frontal derecha (Shadow / Forest) */}
        <path
          d="M12 11L20 6.5V16.5L12 21V11Z"
          fill={current.shadow}
          className="transition-colors duration-300"
        />
        {/* Voxel central incrustado */}
        <path
          d="M12 7L16 9.25L12 11.5L8 9.25L12 7Z"
          fill={state === "awake" ? "#C8F0DC" : state === "weak_awake" ? "#8FDCB0" : "#313244"}
          opacity="0.8"
        />
      </svg>

      {showLabel && (
        <span
          className={`${sizeMap[size].text} font-mono font-medium ${
            state === "awake"
              ? "text-cortex-mint font-semibold"
              : state === "weak_awake"
              ? "text-mocha-lavender"
              : "text-mocha-surface2"
          }`}
        >
          {state.toUpperCase()}
        </span>
      )}
    </div>
  );
};
