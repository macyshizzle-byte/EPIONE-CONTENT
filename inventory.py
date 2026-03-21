"""Inventory module — Supabase (Nhanh.vn sync) with mock fallback.

Data source: nhanh_products table on Supabase CRM.
Column `inventory_available` = số lượng khả dụng (đã trừ đang giao, holding, v.v.)
Synced from Nhanh.vn → Supabase automatically.
"""

import os
import random
import json
from datetime import datetime, timedelta
from urllib.request import Request, urlopen
from urllib.error import URLError

# ========== SKU MAPPING ==========
# Maps our catalog SKU → Nhanh.vn product code in Supabase
SKU_TO_NHANH = {
    # Chairs — ElysChair
    "ELYS-H-BK": "EPI-CEL-H1",   # Có kê đầu — All Black
    "ELYS-H-GR": "EPI-CEL-H2",   # Có kê đầu — Cool Gray
    "ELYS-Z-BK": "EPI-CEL-Z1",   # Không kê đầu — All Black
    "ELYS-Z-GR": "EPI-CEL-Z2",   # Không kê đầu — Cool Gray
    # Chairs — SynoChair
    "SYNO-BK": "EPI-CSY-Z1",     # Không kê chân — All Black
    # Chairs — FortisChair
    "FORT-Z-BK": "EPI-CFT-Z1",   # Không kê chân — All Black
    "FORT-B-BK": "EPI-CFT-B1",   # Có kê chân — All Black
    # Chairs — EasyChair 2.0
    "EASY-BK": "EPI-ESv2-Z1",    # All Black
    "EASY-GR": "EPI-ESv2-Z2",    # Cool Gray
    "EASY-FR": "EPI-ESv2-F1",    # Footrest accessory
    # Chairs — AliusChair
    "ALIUS-BK": "EPI-CAL-B1",    # Standard — All Black
    "ALIUS-GR": "EPI-CAL-C2",    # Standard — Cool Gray
    "ALIUS-6D-BK": "EPI-CAL6D-B1",  # 6D — All Black
    "ALIUS-6D-GR": "EPI-CAL6D-C2",  # 6D — Cool Gray
    # Desks — SmartDesk Pro frame
    "SDP-120": "EPI-D3-Z1",
    "SDP-140": "EPI-D3-Z1",
    # Desks — Delight tabletop
    "DD-140": "EPI-DDE-T51",
    "DD-160": "EPI-DDE-T71",
    # Kids — RingoChair (SIDIZ brand, code = SID-RIN-*)
    "RNG-PK": "SID-RIN-K3",      # Grayish Pink
    "RNG-BG": "SID-RIN-K2",      # Begie Gray
    "RNG-GR": "SID-RIN-K4",      # Grayish Green
    # Arms — Essentials Arm & Delight Arm
    "EA-S-BK": "EPI-AEA-A1v2",    # Essentials Arm Single — All Black
    "EA-D-BK": "EPI-AEA-A1Sv2",   # Essentials Arm Dual — All Black
    "EA-D-WH": "EPI-AEA-A2Sv2",   # Essentials Arm Dual — Pure White
    "DA-BK": "EPI-ADE-A1",        # Delight Arm — All Black
    # Kids — AlphaDesk & AlphaLight
    "ALD-STD": "EPI-DAL-Z1",
    "ALL-STD": "EPI-LAL-Z1",
}

# ========== SUPABASE CONFIG ==========

_SUPABASE_URL = "https://rfipscqzaafmqxkcyxig.supabase.co"
_SUPABASE_KEY = os.environ.get(
    "SUPABASE_SERVICE_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJmaXBzY3F6YWFmbXF4a2N5eGlnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM3NTg0NTcsImV4cCI6MjA4OTMzNDQ1N30.JYHfYopywvzD89yyhaDORSsbr72ll2TP8akG7Rn3RPI",
)

# Cache: {nhanh_code: {"available": int, "remain": int, "name": str, "fetched_at": datetime}}
_cache = {}
_CACHE_TTL = timedelta(minutes=5)


def _supabase_get(endpoint):
    """Make a GET request to Supabase REST API. Returns parsed JSON or None."""
    url = f"{_SUPABASE_URL}/rest/v1/{endpoint}"
    req = Request(url)
    req.add_header("apikey", _SUPABASE_KEY)
    req.add_header("Authorization", f"Bearer {_SUPABASE_KEY}")
    try:
        with urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except (URLError, json.JSONDecodeError, Exception):
        return None


def _query_stock(nhanh_code):
    """Query Supabase for a single Nhanh product code. Returns available qty or None."""
    cached = _cache.get(nhanh_code)
    if cached and (datetime.now() - cached["fetched_at"]) < _CACHE_TTL:
        return cached["available"]

    data = _supabase_get(
        f"nhanh_products?select=code,name,inventory_available,inventory_remain"
        f"&code=eq.{nhanh_code}&limit=1"
    )
    if data and len(data) > 0:
        row = data[0]
        avail = row.get("inventory_available") or 0
        remain = row.get("inventory_remain") or 0
        _cache[nhanh_code] = {
            "available": avail,
            "remain": remain,
            "name": row.get("name", ""),
            "fetched_at": datetime.now(),
        }
        return avail
    return None  # Not found — fall back to mock


# ========== MOCK FALLBACK ==========

_MOCK_STOCK = {
    # ElysChair
    "ELYS-H-BK": 5, "ELYS-H-GR": 1, "ELYS-Z-BK": 0, "ELYS-Z-GR": 6,
    # SynoChair
    "SYNO-BK": 49,
    # FortisChair
    "FORT-Z-BK": 9, "FORT-B-BK": 0,
    # EasyChair
    "EASY-BK": 0, "EASY-GR": 44, "EASY-FR": 94,
    # AliusChair
    "ALIUS-BK": 8, "ALIUS-GR": 8, "ALIUS-6D-BK": 0, "ALIUS-6D-GR": 0,
    # Desks
    "SDM-120": 22, "SDM-140": 10,
    "SDL-120": 14, "SDL-140": 7, "SDP-120": 0, "SDP-140": 0,
    "DD-140": 0, "DD-160": 0, "AND-120": 30, "AND-140": 20,
    # Kids
    "ALD-STD": 43, "ALD-COMBO": 5,
    "RNG-PK": 6, "RNG-BG": 0, "RNG-GR": 9, "ALL-STD": 39,
    # Booths
    "WPD-STD": 3, "WPD-PLUS": 2, "WPD-DUAL": 1, "PB-ONE": 3,
}


# ========== PUBLIC API ==========

def get_stock(sku=None):
    """Get stock for a SKU or all SKUs.

    Tries Supabase first (real Nhanh.vn data), falls back to mock.
    Returns: {"sku": str, "quantity": int, "status": str, "updated_at": str}
    """
    now = datetime.now().isoformat(timespec="minutes")

    def _stock_info(s, qty):
        if qty <= 0:
            status = "out_of_stock"
        elif qty < 5:
            status = "low_stock"
        else:
            status = "in_stock"
        return {"sku": s, "quantity": qty, "status": status, "updated_at": now}

    if sku:
        # Try Supabase
        nhanh_code = SKU_TO_NHANH.get(sku)
        if nhanh_code:
            qty = _query_stock(nhanh_code)
            if qty is not None:
                return _stock_info(sku, qty)
        # Fallback to mock
        qty = _MOCK_STOCK.get(sku, 0)
        return _stock_info(sku, qty)

    # All SKUs
    return {s: _stock_info(s, _MOCK_STOCK.get(s, 0)) for s in _MOCK_STOCK}


def estimate_delivery(sku, quantity):
    """Estimate delivery date based on stock."""
    stock = get_stock(sku)
    qty_available = stock["quantity"]

    if quantity <= qty_available:
        days = random.choice([3, 4, 5])
        note = "Có sẵn trong kho"
    elif qty_available > 0:
        days = random.choice([7, 10, 14])
        note = f"Có {qty_available} sẵn, còn lại chờ nhập"
    else:
        days = random.choice([14, 21])
        note = "Đặt hàng từ nhà máy"

    delivery_date = (datetime.now() + timedelta(days=days)).strftime("%d/%m/%Y")
    return {
        "sku": sku,
        "quantity_requested": quantity,
        "quantity_available": qty_available,
        "estimated_date": delivery_date,
        "estimated_days": days,
        "note": note,
    }
