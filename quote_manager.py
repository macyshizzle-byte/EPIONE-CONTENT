"""Quote manager — create, store, and retrieve quotes."""

import json
import os
import uuid
from datetime import datetime, timedelta

QUOTES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "quotes")
os.makedirs(QUOTES_DIR, exist_ok=True)

MAX_DISCOUNT_PERCENT = 8  # Technicians can discount up to 8%
QUOTE_VALIDITY_DAYS = 7


def create_quote(data):
    """Create a new quote and save to disk.

    data = {
        "customer_name": str,
        "customer_company": str (optional),
        "customer_phone": str (optional),
        "customer_email": str (optional),
        "items": [
            {"product_name": str, "variant_name": str, "sku": str,
             "unit_price": int, "quantity": int}
        ],
        "discount_percent": float (0-8),
        "note": str (optional),
        "created_by": str (technician name, optional),
    }
    """
    quote_id = uuid.uuid4().hex[:8].upper()
    now = datetime.now()

    # Validate discount
    discount_pct = min(float(data.get("discount_percent", 0)), MAX_DISCOUNT_PERCENT)
    discount_pct = max(discount_pct, 0)

    # Calculate totals
    items = data.get("items", [])
    for item in items:
        item["subtotal"] = item["unit_price"] * item["quantity"]

    subtotal = sum(i["subtotal"] for i in items)
    discount_amount = int(subtotal * discount_pct / 100)
    after_discount = subtotal - discount_amount
    total = after_discount  # Giá bán lẻ đã bao gồm VAT

    quote = {
        "id": quote_id,
        "created_at": now.isoformat(timespec="minutes"),
        "valid_until": (now + timedelta(days=QUOTE_VALIDITY_DAYS)).strftime("%d/%m/%Y"),
        "customer": {
            "name": data.get("customer_name", ""),
            "company": data.get("customer_company", ""),
            "phone": data.get("customer_phone", ""),
            "email": data.get("customer_email", ""),
        },
        "items": items,
        "subtotal": subtotal,
        "discount_percent": discount_pct,
        "discount_amount": discount_amount,
        "total": total,
        "note": data.get("note", ""),
        "created_by": data.get("created_by", ""),
        "status": "draft",
    }

    # Save to disk
    filepath = os.path.join(QUOTES_DIR, f"{quote_id}.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(quote, f, ensure_ascii=False, indent=2)

    return quote


def get_quote(quote_id):
    """Retrieve a quote by ID."""
    filepath = os.path.join(QUOTES_DIR, f"{quote_id}.json")
    if not os.path.exists(filepath):
        return None
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def list_quotes(limit=20):
    """List recent quotes."""
    quotes = []
    for filename in sorted(os.listdir(QUOTES_DIR), reverse=True)[:limit]:
        if filename.endswith(".json"):
            filepath = os.path.join(QUOTES_DIR, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                quotes.append(json.load(f))
    return quotes
