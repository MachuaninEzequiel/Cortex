from __future__ import annotations

from pathlib import Path
from typing import Any

from cortex.webgraph.config import WebGraphConfig
from cortex.webgraph.federation import FederatedWebGraphService
from cortex.webgraph.openers import open_path, resolve_safe_vault_path
from cortex.webgraph.service import WebGraphService


def create_app(project_root: Path | None = None, *, workspace_file: Path | None = None):
    try:
        from flask import Flask, jsonify, render_template, request
    except ImportError as exc:  # pragma: no cover - exercised manually
        raise ImportError(
            "Flask is required for `cortex webgraph serve`. Install cortex-memory[webgraph]."
        ) from exc

    try:
        from flask_compress import Compress
    except ImportError:  # pragma: no cover - exercised manually
        Compress = None  # type: ignore[misc, assignment]

    root = project_root or Path.cwd()
    service: WebGraphService | FederatedWebGraphService
    if workspace_file is not None:
        service = FederatedWebGraphService(workspace_file)
        config = WebGraphConfig()
    else:
        service = WebGraphService(root)
        config = WebGraphConfig.load(root)

    app = Flask(__name__, template_folder="templates", static_folder="static")
    if Compress is not None:
        Compress(app)

    @app.before_request
    def require_cortex_header():
        if request.path.startswith("/api/") and request.headers.get("X-Cortex-WebGraph") != "1":
                from flask import abort
                abort(403, "Missing or invalid Cortex WebGraph security header.")

    @app.get("/")
    def index():
        return render_template("index.html", default_mode=config.default_mode)

    @app.get("/api/snapshot")
    def snapshot():
        mode = request.args.get("mode", config.default_mode)
        return jsonify(service.build_snapshot(mode=mode).model_dump())

    @app.get("/api/node/<path:node_id>")
    def node_detail(node_id: str):
        from typing import cast
        mode = cast(Any, request.args.get("mode", config.default_mode))
        return jsonify(service.get_node_detail(node_id, mode=mode).model_dump())

    @app.get("/api/subgraph")
    def subgraph():
        node_id = request.args["node_id"]
        depth = int(request.args.get("depth", 1))
        raw_types = request.args.get("edge_types", "")
        edge_types = {value for value in raw_types.split(",") if value} or None
        mode = request.args.get("mode", config.default_mode)
        return jsonify(
            service.get_subgraph(node_id, depth=depth, mode=mode, edge_types=edge_types).model_dump()
        )

    @app.post("/api/open")
    def open_node():
        payload: dict[str, Any] = request.get_json(force=True) or {}
        node_id = payload.get("node_id")
        if not node_id:
            return jsonify({"error": "Missing node_id"}), 400
        detail = service.get_node_detail(node_id, mode="hybrid")
        resolved_path = service.resolve_node_path(node_id, mode="hybrid")
        if resolved_path is None:
            return jsonify({"error": "Selected node has no local document"}), 400
        if workspace_file is None:
            rel_path = detail.node.rel_path
            if not rel_path:
                return jsonify({"error": "Selected node has no local document"}), 400
            path = resolve_safe_vault_path(service.semantic_source.vault_path, rel_path)
        else:
            path = resolved_path
        open_path(path)
        return jsonify({"status": "ok", "path": str(path)})

    return app


def run_server(
    project_root: Path | None = None,
    *,
    host: str | None = None,
    port: int | None = None,
    open_browser: bool | None = None,
    workspace_file: Path | None = None,
) -> None:
    import webbrowser

    root = project_root or Path.cwd()
    config = WebGraphConfig.load(root)
    app = create_app(root, workspace_file=workspace_file)
    final_host = host or config.server_host
    final_port = port or config.server_port
    should_open = config.auto_open_browser if open_browser is None else open_browser
    if should_open:
        webbrowser.open(f"http://{final_host}:{final_port}")
    app.run(host=final_host, port=final_port, debug=False)

