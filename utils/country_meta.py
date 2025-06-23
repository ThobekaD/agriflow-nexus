# ag-agents/utils/country_meta.py
"""
Country metadata + pump prices snapshot (16 Jun 2025, USD / Litre).
"""

# ─── Human-readable names ──────────────────────────────────────────────
COUNTRIES: dict[str, str] = {
    "BWA": "Botswana",
    "ZAF": "South Africa",
    "ZMB": "Zambia",
    "NAM": "Namibia",
    "MOZ": "Mozambique",
    "ZWE": "Zimbabwe",
    "TZA": "Tanzania",
    "AGO": "Angola",
    "MWI": "Malawi",
    "KEN": "Kenya",
}

# ─── Current retail pump prices ───────────────────────────────────────
PETROL_USD_L: dict[str, float] = {
    "BWA": 1.104, "ZAF": 1.162, "ZMB": 1.289, "NAM": 1.159, "MOZ": 1.342,
    "ZWE": 1.540, "TZA": 1.111, "AGO": 0.328, "MWI": 1.460, "KEN": 1.359,
}

DIESEL_USD_L: dict[str, float] = {
    "BWA": 1.118, "ZAF": 1.171, "ZMB": 1.032, "NAM": 1.157, "MOZ": 1.357,
    "ZWE": 1.500, "TZA": 1.088, "AGO": 0.328, "MWI": 1.577, "KEN": 1.248,
}

# ─── Supported commodities ────────────────────────────────────────────
COMMODITIES = ["Barley", "Maize", "Sorghum", "Wheat", "Beef"]
