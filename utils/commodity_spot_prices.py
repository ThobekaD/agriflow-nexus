# ag-agents/utils/commodity_spot_prices.py
"""
Static spot prices per kg (USD) – mid-points taken from the user-supplied
table dated 21 Jun 2025.  None == data unavailable.
"""
PRICES: dict[str, dict[str, float | None]] = {
    "BWA": {"Barley": .27,  "Beef": 3.59, "Maize": .425, "Sorghum": .30,  "Wheat": .30},
    "ZAF": {"Barley": .955, "Beef": 2.90, "Maize": .235, "Sorghum": .25,  "Wheat": .35},
    "ZMB": {"Barley": .295, "Beef": 3.00, "Maize": .35,  "Sorghum": 2.155,"Wheat": .30},
    "NAM": {"Barley": .48,  "Beef": 3.78, "Maize": .22,  "Sorghum": 2.20, "Wheat": .30},
    "MOZ": {"Barley": .72,  "Beef": .705, "Maize": .425, "Sorghum": 4.47, "Wheat": .30},
    "ZWE": {"Barley": .27,  "Beef": 7.50, "Maize": None, "Sorghum": None,"Wheat": None},
    "TZA": {"Barley": .185, "Beef": 1.685,"Maize": .285, "Sorghum": .385,"Wheat": .30},
    "AGO": {"Barley": 1.73, "Beef": 3.415,"Maize": .57,  "Sorghum": .22, "Wheat": .30},
    "MWI": {"Barley": 5.00, "Beef": None, "Maize": .175, "Sorghum": None,"Wheat": .30},
    "KEN": {"Barley": .24,  "Beef": 3.15, "Maize": .375, "Sorghum": .37, "Wheat": .46},
}
