# cortex/webgraph/templates/index.html

## Qué tiene adentro

Plantilla Jinja2/Flask de la UI WebGraph. Carga `vis-network` desde unpkg. CSS via `url_for('static', filename='style.css')`.

Controles en toolbar: `mode` (hybrid/semantic/episodic, `default_mode` del servidor), filtro proyecto, filtro tipo de nodo. El resto del HTML (canvas `#network`, panel de detalle, status) lo consume `static/app.js`.

## Para qué sirve

Página única que pinta el grafo memoria semántica + episódica.

## Relaciones

### Recibe de

- `cortex.webgraph.server` (Flask `render_template`).
- Variables de plantilla (`default_mode`).

### Envía a

- Navegador. JS llama endpoints JSON del mismo server.

---
Fuente: lectura de `cortex/webgraph/templates/index.html`. No se usó documentación previa.
