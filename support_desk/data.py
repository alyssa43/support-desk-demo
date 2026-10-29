"""Fake shop data. Every tool reads from these dicts; nothing is real."""

ORDERS = {
    "1001": {"item": "T-shirt", "size": "M", "status": "not_shipped",
             "days_since_delivery": None, "damaged": False, "eta_days": None},
    "1002": {"item": "Hoodie", "size": "L", "status": "in_transit",
             "days_since_delivery": None, "damaged": False, "eta_days": 3},
    "1003": {"item": "T-shirt", "size": "S", "status": "delivered",
             "days_since_delivery": 5, "damaged": True, "eta_days": None},
    "1004": {"item": "Mug", "size": None, "status": "delivered",
             "days_since_delivery": 10, "damaged": False, "eta_days": None},
    "1005": {"item": "T-shirt", "size": "XL", "status": "delivered",
             "days_since_delivery": 45, "damaged": True, "eta_days": None},
    "1006": {"item": "Hoodie", "size": "M", "status": "delivered",
             "days_since_delivery": 30, "damaged": False, "eta_days": None},
    # Damaged orders right at the 30-day refund boundary.
    "1007": {"item": "T-shirt", "size": "L", "status": "delivered",
             "days_since_delivery": 29, "damaged": True, "eta_days": None},
    "1008": {"item": "T-shirt", "size": "M", "status": "delivered",
             "days_since_delivery": 30, "damaged": True, "eta_days": None},
    "1009": {"item": "Hoodie", "size": "S", "status": "delivered",
             "days_since_delivery": 31, "damaged": True, "eta_days": None},
}

# Everything is in stock except Hoodie L.
OUT_OF_STOCK = {("Hoodie", "L")}
