# ag-agents/utils/farm_locations.py
"""
Canonical demo farm coordinates for each supported country.
Lat/Lon are approximate but inside major farming corridors.
"""

FARMS_BY_COUNTRY: dict[str, dict[str, tuple[float, float]]] = {
    # Botswana
    "BWA": {
        "F01": (-24.2, 26.1),   # Kweneng
        "F02": (-24.9, 26.4),   # Southern District
        "F03": (-25.1, 25.6),   # Kgatleng
    },

    # South Africa
    "ZAF": {
        "F01": (-28.5, 26.8),   # Free State
        "F02": (-25.7, 28.1),   # Mpumalanga
        "F03": (-33.2, 18.9),   # Western Cape
    },

    # Zambia
    "ZMB": {
        "F01": (-15.4, 28.3),   # Central
        "F02": (-13.0, 27.0),   # Copperbelt
        "F03": (-17.3, 24.3),   # Southern
    },

    # Namibia
    "NAM": {
        "F01": (-22.6, 17.1),   # Khomas
        "F02": (-19.8, 15.9),   # Otjozondjupa
        "F03": (-25.0, 17.4),   # Hardap
    },

    # Mozambique
    "MOZ": {
        "F01": (-19.1, 34.8),   # Sofala
        "F02": (-25.0, 33.6),   # Gaza
        "F03": (-16.8, 33.2),   # Zambezia
    },

    # Zimbabwe
    "ZWE": {
        "F01": (-18.9, 29.8),   # Midlands
        "F02": (-20.0, 28.6),   # Matabeleland S.
        "F03": (-17.3, 31.5),   # Mashonaland E.
    },

    # Tanzania
    "TZA": {
        "F01": (-6.2, 35.8),    # Dodoma
        "F02": (-3.3, 36.0),    # Arusha
        "F03": (-8.6, 33.4),    # Mbeya
    },

    # Angola
    "AGO": {
        "F01": (-8.8, 13.2),    # Cuanza Sul
        "F02": (-11.7, 15.0),   # Huambo
        "F03": (-14.9, 13.5),   # Huila
    },

    # Malawi
    "MWI": {
        "F01": (-13.1, 34.2),   # Lilongwe
        "F02": (-14.0, 33.8),   # Dedza
        "F03": (-9.7, 33.0),    # Karonga
    },

    # Kenya
    "KEN": {
        "F01": (0.3, 37.5),     # Meru
        "F02": (-1.1, 36.9),    # Kiambu
        "F03": (0.1, 34.8),     # Kakamega
    },
}
