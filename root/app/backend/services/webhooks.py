from collections import defaultdict
from typing import Any

import httpx

from ..database import Purchase, StoreWebhook

MAX_RESPONSE_BYTES = 64 * 1024
WEBHOOK_TIMEOUT = 5.0


def _response_details(response: httpx.Response) -> dict[str, Any]:
    body = response.content[:MAX_RESPONSE_BYTES].decode("utf-8", errors="replace")
    return {
        "status_code": response.status_code,
        "headers": dict(response.headers),
        "body": body,
        "body_truncated": len(response.content) > MAX_RESPONSE_BYTES,
    }


def test_webhook_url(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Send a test request. URL validation is intentionally not performed here."""
    try:
        with httpx.Client(timeout=WEBHOOK_TIMEOUT, follow_redirects=False) as client:
            response = client.post(url, json=payload, headers={"User-Agent": "TokTok-Webhook/1.0"})
        return _response_details(response)
    except httpx.RequestError as exc:
        return {"status_code": None, "headers": {}, "body": str(exc), "error": "Webhook request failed"}


def dispatch_order_created(webhooks: list[StoreWebhook], purchases: list[Purchase], customer_id: int) -> None:
    by_webhook: dict[int, list[Purchase]] = defaultdict(list)
    for purchase in purchases:
        for webhook in webhooks:
            if webhook.active and webhook.store_id == purchase.product.store_id:
                by_webhook[webhook.id].append(purchase)

    for webhook in webhooks:
        rows = by_webhook.get(webhook.id, [])
        if not rows:
            continue
        payload = {
            "content": f"New order received by {rows[0].product.store.name if rows[0].product.store else 'TokTok'}",
            "username": "TokTok",
            "embeds": [{
                "title": "New order",
                "color": 0x007C0C,
                "fields": [
                    {"name": "Order IDs", "value": ", ".join(str(row.id) for row in rows), "inline": True},
                    {"name": "Customer ID", "value": str(customer_id), "inline": True},
                    {"name": "Total", "value": f"IDR {sum(row.total for row in rows):,.0f}", "inline": True},
                ],
            }],
        }
        try:
            with httpx.Client(timeout=WEBHOOK_TIMEOUT, follow_redirects=False) as client:
                client.post(webhook.url, json=payload, headers={"User-Agent": "TokTok-Webhook/1.0"})
        except httpx.RequestError:
            # Webhook delivery must not roll back a completed checkout.
            continue
