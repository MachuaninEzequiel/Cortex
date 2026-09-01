#!/usr/bin/env python3
"""Generate the ES/EN evaluation dataset for retrieval quality testing.

Idempotent: re-running overwrites generated files deterministically.

Usage:
    python eval/retrieval/generate_dataset.py
"""

from __future__ import annotations

from pathlib import Path

DATASET_DIR = Path(__file__).resolve().parent / "dataset"

# ---------------------------------------------------------------------------
# Doc corpus: (relpath, title, tags, body). Realistic fictional e-commerce
# project "TiendaNube-Clone" so queries are semantically meaningful.
# ---------------------------------------------------------------------------

DOCS: dict[str, list[tuple[str, str, str]]] = {}

DOCS["es"] = [
    ("decisions/ADR-001-pasarela-pagos.md", "ADR-001: Elección de pasarela de pagos",
     """## Context
El checkout necesita procesar tarjetas y pagos en cuotas.
Mercado Pago y Stripe fueron evaluados para la pasarela de pagos.
## Decision
Elegimos Mercado Pago como pasarela de pagos por costos de comisión menores en LATAM.
## Consequences
El checkout depende del SDK de Mercado Pago; los webhooks de pago requieren idempotencia."""),
    ("decisions/ADR-002-cache-redis.md", "ADR-002: Cache de sesiones con Redis",
     """## Context
Las sesiones de usuario crecen y Postgres no soporta el volumen de lecturas.
## Decision
Usamos Redis como cache distribuido para sesiones con TTL de 24 horas.
## Consequences
La invalidación de cache requiere pub/sub; el failover de Redis debe ser supervisado."""),
    ("decisions/ADR-003-busquedas-postgres.md", "ADR-003: Búsqueda de productos sin Elasticsearch",
     """## Context
El buscador de productos debe soportar filtros por categoría y precio.
## Decision
Mantuvimos la búsqueda full-text en Postgres con índices GIN, descartando Elasticsearch.
## Consequences
Menos infraestructura operativa; límite práctico de ~1M de SKUs antes de revisitar la decisión."""),
    ("decisions/ADR-004-websockets-stock.md", "ADR-004: Stock en tiempo real con WebSockets",
     """## Context
Los usuarios ven stock desactualizado en la ficha de producto.
## Decision
Publicamos cambios de stock vía WebSockets desde el servicio de inventario.
## Consequences
Requiere conexiones persistentes y un balanceador compatible con sticky sessions."""),
    ("specs/spec-checkout.md", "Spec: Flujo de checkout en un paso",
     """## Goal
Reducir el abandono de carrito implementando checkout en una sola pantalla.
## Verification hooks
tests/checkout/test_one_page.py debe pasar.
## Scope
El flujo de checkout valida tarjeta, calcula envío y confirma el pedido sin recargas."""),
    ("specs/spec-notificaciones.md", "Spec: Notificaciones push de pedidos",
     """## Goal
Notificar estado del pedido (preparando, enviado, entregado) por push.
## Scope
Las notificaciones push usan Firebase Cloud Messaging; el usuario puede silenciarlas por tipo."""),
    ("specs/spec-cupones.md", "Spec: Sistema de cupones de descuento",
     """## Goal
cupones de descuento con caducidad, límite de uso y combinación con promociones.
## Scope
Un cupón aplica sobre el total del carrito; los cupones apilables quedan fuera de alcance."""),
    ("specs/spec-wishlist.md", "Spec: Lista de deseos compartible",
     """## Goal
wishlist pública con enlace compartible y vista solo lectura.
## Scope
La lista de deseos se guarda por usuario y genera URL corta para compartir."""),
    ("runbooks/runbook-caida-checkout.md", "Runbook: Caída del checkout",
     """## Síntomas
Checkout lento o errores 502 al confirmar pedido.
## Diagnóstico
Verificar latencia de la pasarela de pagos y pool de conexiones a Postgres.
## Mitigación
Si Mercado Pago está caído, activar el modo de cola diferida y avisar a soporte."""),
    ("runbooks/runbook-cache-invalido.md", "Runbook: Cache de sesión inválido",
     """## Síntomas
Usuarios deslogueados aleatoriamente o viendo datos de otros.
## Diagnóstico
Revisar evictions de Redis y desincronización de pub/sub.
## Mitigación
Flush selectivo por namespace de sesión y reinicio gradual de pods."""),
    ("runbooks/runbook-migracion-db.md", "Runbook: Migración de base de datos",
     """## Procedimiento
Correr migraciones de Postgres con pgroll en modo expand/contract.
## Rollback
Revertir el contract step; los datos agregados son compatibles hacia atrás."""),
]

DOCS["en"] = [
    ("decisions/ADR-001-payment-gateway.md", "ADR-001: Payment gateway selection",
     """## Context
The checkout must process cards and installment payments. Mercado Pago and Stripe were evaluated.
## Decision
We chose Stripe as the payment gateway for its developer experience and webhook reliability.
## Consequences
Checkout depends on Stripe SDK; payment webhooks require idempotency keys."""),
    ("decisions/ADR-002-session-cache.md", "ADR-002: Session caching with Redis",
     """## Context
User sessions grow and Postgres cannot sustain the read volume.
## Decision
We use Redis as the distributed session cache with a 24h TTL.
## Consequences
Cache invalidation requires pub/sub; Redis failover must be supervised."""),
    ("decisions/ADR-003-product-search.md", "ADR-003: Product search without Elasticsearch",
     """## Context
The product search must filter by category and price range.
## Decision
We kept full-text search in Postgres with GIN indexes and dropped Elasticsearch.
## Consequences
Less operational burden; practical ceiling around 1M SKUs before revisiting."""),
    ("decisions/ADR-004-realtime-inventory.md", "ADR-004: Real-time inventory with WebSockets",
     """## Context
Customers see stale stock levels on product pages.
## Decision
Inventory changes are broadcast via WebSockets from the inventory service.
## Consequences
Requires persistent connections and a load balancer with sticky sessions."""),
    ("specs/spec-one-page-checkout.md", "Spec: One-page checkout flow",
     """## Goal
Reduce cart abandonment by implementing a single-page checkout.
## Verification hooks
tests/checkout/test_one_page.py must pass.
## Scope
The checkout validates the card, computes shipping and confirms the order without page reloads."""),
    ("specs/spec-push-notifications.md", "Spec: Order status push notifications",
     """## Goal
Notify order status (packing, shipped, delivered) via push.
## Scope
Push notifications use Firebase Cloud Messaging; users can mute them per type."""),
    ("specs/spec-discount-coupons.md", "Spec: Discount coupon system",
     """## Goal
Discount coupons with expiry, usage limits and promotion combination rules.
## Scope
A coupon applies to the cart total; stackable coupons are out of scope."""),
    ("specs/spec-shared-wishlist.md", "Spec: Shareable wishlist",
     """## Goal
Public wishlist with a shareable link and read-only view.
## Scope
The wishlist is stored per user and generates a short URL for sharing."""),
    ("runbooks/runbook-checkout-outage.md", "Runbook: Checkout outage",
     """## Symptoms
Slow checkout or 502 errors when confirming an order.
## Diagnosis
Check payment gateway latency and the Postgres connection pool.
## Mitigation
If Stripe is down, enable deferred queue mode and notify support."""),
    ("runbooks/runbook-stale-session-cache.md", "Runbook: Stale session cache",
     """## Symptoms
Users randomly logged out or seeing other people's data.
## Diagnosis
Check Redis evictions and pub/sub desynchronization.
## Mitigation
Targeted flush of the session namespace and gradual pod restart."""),
    ("runbooks/runbook-db-migration.md", "Runbook: Database migration",
     """## Procedure
Run Postgres migrations with pgroll in expand/contract mode.
## Rollback
Revert the contract step; added data stays backward compatible."""),
]


def _extra_docs() -> None:
    """Add filler docs (per language) to reach realistic vault size."""
    fillers_es = [
        ("specs/spec-reviews.md", "Spec: Reseñas de productos con moderación",
         "reseñas de productos con moderación previa y verificación de compra."),
        ("specs/spec-multi-currency.md", "Spec: Precios en múltiples monedas",
         "precios multi-moneda con conversión diaria y redondeo psicológico."),
        ("specs/spec-email-recuperacion.md", "Spec: Email de carrito abandonado",
         "email automático de carrito abandonado a las 4 horas con cupón opcional."),
        ("runbooks/runbook-fraude.md", "Runbook: Pedidos sospechosos de fraude",
         "pedidos marcados por fraude requieren revisión manual antes del despacho."),
        ("decisions/ADR-005-imagenes-cdn.md", "ADR-005: Imágenes de producto en CDN",
         "imágenes de producto se sirven desde CDN con variantes WebP responsive."),
        ("decisions/ADR-006-feature-flags.md", "ADR-006: Feature flags con Unleash",
         "feature flags self-hosted con Unleash para releases progresivas."),
    ]
    fillers_en = [
        ("specs/spec-product-reviews.md", "Spec: Product reviews with moderation",
         "product reviews with pre-publication moderation and purchase verification."),
        ("specs/spec-multi-currency.md", "Spec: Multi-currency pricing",
         "multi-currency pricing with daily conversion rates and psychological rounding."),
        ("specs/spec-abandoned-cart-email.md", "Spec: Abandoned cart email",
         "automatic abandoned-cart email after 4 hours with an optional coupon."),
        ("runbooks/runbook-fraud-orders.md", "Runbook: Suspected fraud orders",
         "fraud-flagged orders require manual review before dispatch."),
        ("decisions/ADR-005-product-images-cdn.md", "ADR-005: Product images on CDN",
         "product images are served from a CDN with responsive WebP variants."),
        ("decisions/ADR-006-feature-flags.md", "ADR-006: Feature flags with Unleash",
         "self-hosted feature flags with Unleash for progressive rollouts."),
    ]
    DOCS["es"].extend(fillers_es)
    DOCS["en"].extend(fillers_en)


def _frontmatter(title: str, tags: str) -> str:
    nl = chr(10)
    return (
        "---" + nl
        + f"title: {title}" + nl
        + f"tags: [{tags}]" + nl
        + "---" + nl
    )


QUERIES: dict[str, list[dict]] = {
    "es": [
        {"q": "por qué eligieron Mercado Pago como pasarela de pagos", "relevant": ["decisions/ADR-001-pasarela-pagos.md"]},
        {"q": "costos de comisión del checkout", "relevant": ["decisions/ADR-001-pasarela-pagos.md"]},
        {"q": "cómo funciona el cache de sesiones", "relevant": ["decisions/ADR-002-cache-redis.md"]},
        {"q": "TTL de las sesiones de usuario", "relevant": ["decisions/ADR-002-cache-redis.md"]},
        {"q": "buscador de productos con filtros", "relevant": ["decisions/ADR-003-busquedas-postgres.md"]},
        {"q": "por qué no usan Elasticsearch", "relevant": ["decisions/ADR-003-busquedas-postgres.md"]},
        {"q": "stock en tiempo real", "relevant": ["decisions/ADR-004-websockets-stock.md", "specs/spec-checkout.md"]},
        {"q": "abandono de carrito checkout una pantalla", "relevant": ["specs/spec-checkout.md"]},
        {"q": "notificaciones push del pedido", "relevant": ["specs/spec-notificaciones.md"]},
        {"q": "cupones de descuento caducidad", "relevant": ["specs/spec-cupones.md"]},
        {"q": "lista de deseos compartible", "relevant": ["specs/spec-wishlist.md"]},
        {"q": "checkout caído errores 502", "relevant": ["runbooks/runbook-caida-checkout.md"]},
        {"q": "usuarios deslogueados aleatoriamente", "relevant": ["runbooks/runbook-cache-invalido.md"]},
        {"q": "migración de base de datos rollback", "relevant": ["runbooks/runbook-migracion-db.md"]},
        {"q": "reseñas de productos moderación", "relevant": ["specs/spec-reviews.md"]},
        {"q": "precios en varias monedas conversión", "relevant": ["specs/spec-multi-currency.md"]},
        {"q": "carrito abandonado email automático", "relevant": ["specs/spec-email-recuperacion.md"]},
        {"q": "pedidos sospechosos de fraude revisión", "relevant": ["runbooks/runbook-fraude.md"]},
        {"q": "dónde se sirven las imágenes de producto", "relevant": ["decisions/ADR-005-imagenes-cdn.md"]},
        {"q": "feature flags releases progresivas", "relevant": ["decisions/ADR-006-feature-flags.md"]},
        {"q": "webhooks de pago idempotencia", "relevant": ["decisions/ADR-001-pasarela-pagos.md"]},
        {"q": "invalidación de cache pub/sub", "relevant": ["decisions/ADR-002-cache-redis.md", "runbooks/runbook-cache-invalido.md"]},
        {"q": "límite de SKUs del buscador", "relevant": ["decisions/ADR-003-busquedas-postgres.md"]},
        {"q": "sticky sessions balanceador", "relevant": ["decisions/ADR-004-websockets-stock.md"]},
        {"q": "verificación de compra reseñas", "relevant": ["specs/spec-reviews.md"]},
        {"q": "cola diferida cuando la pasarela falla", "relevant": ["runbooks/caida-checkout.md"]},
    ],
    "en": [
        {"q": "why did they choose Stripe as the payment gateway", "relevant": ["decisions/ADR-001-payment-gateway.md"]},
        {"q": "checkout webhook reliability idempotency keys", "relevant": ["decisions/ADR-001-payment-gateway.md"]},
        {"q": "how does the session cache work", "relevant": ["decisions/ADR-002-session-cache.md"]},
        {"q": "session TTL hours redis", "relevant": ["decisions/ADR-002-session-cache.md"]},
        {"q": "product search filters category price", "relevant": ["decisions/ADR-003-product-search.md"]},
        {"q": "why not Elasticsearch", "relevant": ["decisions/ADR-003-product-search.md"]},
        {"q": "real time inventory updates", "relevant": ["decisions/ADR-004-realtime-inventory.md"]},
        {"q": "cart abandonment one-page checkout", "relevant": ["specs/spec-one-page-checkout.md"]},
        {"q": "order status push notifications firebase", "relevant": ["specs/spec-push-notifications.md"]},
        {"q": "discount coupons expiry usage limits", "relevant": ["specs/spec-discount-coupons.md"]},
        {"q": "shareable wishlist short url", "relevant": ["specs/spec-shared-wishlist.md"]},
        {"q": "checkout outage 502 errors", "relevant": ["runbooks/runbook-checkout-outage.md"]},
        {"q": "users randomly logged out seeing other data", "relevant": ["runbooks/runbook-stale-session-cache.md"]},
        {"q": "database migration rollback procedure", "relevant": ["runbooks/runbook-db-migration.md"]},
        {"q": "product reviews moderation verified purchase", "relevant": ["specs/spec-product-reviews.md"]},
        {"q": "multi currency pricing conversion", "relevant": ["specs/spec-multi-currency.md"]},
        {"q": "abandoned cart email automation", "relevant": ["specs/spec-abandoned-cart-email.md"]},
        {"q": "fraud flagged orders manual review", "relevant": ["runbooks/runbook-fraud-orders.md"]},
        {"q": "where are product images served from", "relevant": ["decisions/ADR-005-product-images-cdn.md"]},
        {"q": "feature flags progressive rollout unleash", "relevant": ["decisions/ADR-006-feature-flags.md"]},
        {"q": "payment webhooks retry dedupe", "relevant": ["decisions/ADR-001-payment-gateway.md"]},
        {"q": "cache invalidation pub/sub desync", "relevant": ["decisions/ADR-002-session-cache.md", "runbooks/runbook-stale-session-cache.md"]},
        {"q": "SKU ceiling full text search postgres", "relevant": ["decisions/ADR-003-product-search.md"]},
        {"q": "sticky sessions websocket connections", "relevant": ["decisions/ADR-004-realtime-inventory.md"]},
        {"q": "deferred queue mode gateway down", "relevant": ["runbooks/runbook-checkout-outage.md"]},
    ],
}


def generate() -> None:
    _extra_docs()
    tag_map = {
        "decisiones": "decision", "pagos": "payments", "redis": "redis",
        "postgres": "postgres", "websockets": "realtime", "checkout": "checkout",
        "notificaciones": "notifications", "cupones": "coupons",
        "wishlist": "wishlist", "runbook": "ops", "migración": "db",
        "reseñas": "reviews", "monedas": "currency", "fraude": "fraud",
        "cdn": "cdn", "flags": "flags", "email": "email",
    }
    n_docs = 0
    for lang in ("es", "en"):
        base = DATASET_DIR / lang
        if base.exists():
            for p in base.rglob("*.md"):
                p.unlink()
        for rel, title, body in DOCS[lang]:
            path = base / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            tag = next((v for k, v in tag_map.items() if k in rel), "doc")
            path.write_text(_frontmatter(title, tag) + "\n" + body + "\n", encoding="utf-8")
            n_docs += 1
        qname = f"queries.{lang}.yaml"
        import yaml  # local import: only needed at generation time

        out = DATASET_DIR / qname
        # stable dump, ordered
        lines = []
        for item in QUERIES[lang]:
            rel_str = "\n".join(f"      - {r}" for r in item["relevant"])
            lines.append(f"  - query: {item['q']}\n    relevant:\n{rel_str}")
        header = (
            "# Generated by eval/retrieval/generate_dataset.py — do not edit manually.\n"
            f"language: {lang}\n"
            "queries:\n"
        )
        out.write_text(header + "\n".join(lines) + "\n", encoding="utf-8")
        print(f"wrote {out} ({len(QUERIES[lang])} queries)")
    print(f"wrote {n_docs} docs under {DATASET_DIR}")


if __name__ == "__main__":
    generate()
