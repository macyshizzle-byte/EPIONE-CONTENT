"""Order manager — convert quotes to orders, track status, generate VietQR payment."""

import json
import os
import uuid
from datetime import datetime
from urllib.parse import quote as url_quote

if os.environ.get("VERCEL"):
    ORDERS_DIR = "/tmp/orders"
else:
    ORDERS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "orders")
os.makedirs(ORDERS_DIR, exist_ok=True)

# Bank config for VietQR — set via environment variables
BANK_ID = os.environ.get("BANK_ID", "MB")
BANK_ACCOUNT_NO = os.environ.get("BANK_ACCOUNT_NO", "")
BANK_ACCOUNT_NAME = os.environ.get("BANK_ACCOUNT_NAME", "EPIONE")

ORDER_STATUSES = [
    "confirmed",
    "pending_payment",
    "paid",
    "processing",
    "shipping",
    "delivered",
    "cancelled",
]

STATUS_LABELS = {
    "confirmed": "Da xac nhan",
    "pending_payment": "Cho thanh toan",
    "paid": "Da thanh toan",
    "processing": "Dang xu ly",
    "shipping": "Dang giao hang",
    "delivered": "Da giao",
    "cancelled": "Da huy",
}


def create_order_from_quote(quote, payment_option="full"):
    """Convert a quote to an order.

    payment_option: 'full', 'deposit_30', 'deposit_50'
    """
    order_id = "ORD-" + uuid.uuid4().hex[:6].upper()
    now = datetime.now()

    total = quote["total"]
    if payment_option == "deposit_30":
        payment_amount = int(total * 0.3)
        payment_label = "Dat coc 30%"
    elif payment_option == "deposit_50":
        payment_amount = int(total * 0.5)
        payment_label = "Dat coc 50%"
    else:
        payment_amount = total
        payment_label = "Thanh toan toan bo"

    order = {
        "id": order_id,
        "quote_id": quote["id"],
        "created_at": now.isoformat(timespec="minutes"),
        "customer": quote["customer"],
        "items": quote["items"],
        "subtotal": quote["subtotal"],
        "discount_percent": quote.get("discount_percent", 0),
        "discount_amount": quote.get("discount_amount", 0),
        "total": total,
        "payment_option": payment_option,
        "payment_label": payment_label,
        "payment_amount": payment_amount,
        "payment_remaining": total - payment_amount,
        "status": "pending_payment",
        "status_history": [
            {"status": "confirmed", "at": now.isoformat(timespec="minutes"),
             "by": quote.get("created_by", "")},
            {"status": "pending_payment", "at": now.isoformat(timespec="minutes"),
             "by": "system"},
        ],
        "created_by": quote.get("created_by", ""),
        "note": quote.get("note", ""),
    }

    filepath = os.path.join(ORDERS_DIR, f"{order_id}.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(order, f, ensure_ascii=False, indent=2)

    return order


def get_order(order_id):
    """Retrieve an order by ID."""
    filepath = os.path.join(ORDERS_DIR, f"{order_id}.json")
    if not os.path.exists(filepath):
        return None
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def update_order_status(order_id, new_status, updated_by=""):
    """Advance order to a new status."""
    order = get_order(order_id)
    if not order:
        return None
    if new_status not in ORDER_STATUSES:
        return None

    order["status"] = new_status
    order["status_history"].append({
        "status": new_status,
        "at": datetime.now().isoformat(timespec="minutes"),
        "by": updated_by,
    })

    filepath = os.path.join(ORDERS_DIR, f"{order_id}.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(order, f, ensure_ascii=False, indent=2)

    return order


def list_orders(limit=50):
    """List recent orders, newest first."""
    orders = []
    if not os.path.exists(ORDERS_DIR):
        return orders
    for filename in sorted(os.listdir(ORDERS_DIR), reverse=True)[:limit]:
        if filename.endswith(".json"):
            filepath = os.path.join(ORDERS_DIR, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                orders.append(json.load(f))
    return orders


def generate_qr_url(order):
    """Generate VietQR image URL for payment."""
    if not BANK_ACCOUNT_NO:
        return None

    amount = order["payment_amount"]
    description = url_quote(f"EPIONE {order['id']}")
    account_name = url_quote(BANK_ACCOUNT_NAME)

    return (
        f"https://img.vietqr.io/image/{BANK_ID}-{BANK_ACCOUNT_NO}-compact2.png"
        f"?amount={amount}&addInfo={description}&accountName={account_name}"
    )


def get_bank_info():
    """Return bank info for display."""
    if not BANK_ACCOUNT_NO:
        return None
    return {
        "bank_id": BANK_ID,
        "account_no": BANK_ACCOUNT_NO,
        "account_name": BANK_ACCOUNT_NAME,
    }
