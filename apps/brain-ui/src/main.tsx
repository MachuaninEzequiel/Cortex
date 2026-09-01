import React from "react";
import ReactDOM from "react-dom/client";
import { App } from "./App";
import "./index.css";
import { invoke, isTauri } from "@tauri-apps/api/core";

// Puente global de logs de JavaScript hacia la terminal de Rust
if (isTauri()) {
  const origLog = console.log;
  const origWarn = console.warn;
  const origError = console.error;

  console.log = (...args: unknown[]) => {
    origLog(...args);
    const msg = args.map((a) => (typeof a === "object" ? JSON.stringify(a) : String(a))).join(" ");
    invoke("log_to_terminal", { level: "info", msg }).catch(() => {});
  };

  console.warn = (...args: unknown[]) => {
    origWarn(...args);
    const msg = args.map((a) => (typeof a === "object" ? JSON.stringify(a) : String(a))).join(" ");
    invoke("log_to_terminal", { level: "warn", msg }).catch(() => {});
  };

  console.error = (...args: unknown[]) => {
    origError(...args);
    const msg = args.map((a) => (typeof a === "object" ? JSON.stringify(a) : String(a))).join(" ");
    invoke("log_to_terminal", { level: "error", msg }).catch(() => {});
  };

  window.addEventListener("error", (e) => {
    invoke("log_to_terminal", {
      level: "FATAL_ERROR",
      msg: `${e.message} at ${e.filename}:${e.lineno}:${e.colno} stack: ${e.error?.stack || "no stack"}`,
    }).catch(() => {});
  });

  window.addEventListener("unhandledrejection", (e) => {
    invoke("log_to_terminal", {
      level: "FATAL_PROMISE",
      msg: `Unhandled Promise Rejection: ${String(e.reason?.stack || e.reason)}`,
    }).catch(() => {});
  });
}

class RootErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { hasError: boolean; error: string }
> {
  constructor(props: { children: React.ReactNode }) {
    super(props);
    this.state = { hasError: false, error: "" };
  }
  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error: error.message + "\n" + (error.stack || "") };
  }
  componentDidCatch(error: Error, info: React.ErrorInfo) {
    if (isTauri()) {
      invoke("log_to_terminal", {
        level: "REACT_CRASH",
        msg: `React Crashed: ${error.message}\nComponentStack: ${info.componentStack}`,
      }).catch(() => {});
    }
  }
  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: 24, backgroundColor: "#181825", color: "#f38ba8", fontFamily: "monospace", height: "100vh" }}>
          <h2 style={{ color: "#f38ba8", marginBottom: 12 }}>⚠️ Error en el Renderizado de la Interfaz</h2>
          <pre style={{ whiteSpace: "pre-wrap", background: "#11111b", padding: 12, borderRadius: 8, color: "#cdd6f4", maxHeight: "60vh", overflow: "auto" }}>
            {this.state.error}
          </pre>
          <button
            onClick={() => this.setState({ hasError: false, error: "" })}
            style={{ marginTop: 16, padding: "8px 18px", background: "#313244", color: "#cdd6f4", border: "1px solid #cba6f7", borderRadius: 6, cursor: "pointer" }}
          >
            Reintentar Render
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

const root = document.getElementById("root");
if (!root) {
  throw new Error("#root no encontrado en index.html");
}

ReactDOM.createRoot(root).render(
  <React.StrictMode>
    <RootErrorBoundary>
      <App />
    </RootErrorBoundary>
  </React.StrictMode>,
);
