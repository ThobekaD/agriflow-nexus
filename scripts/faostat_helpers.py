# scripts/faostat_helpers.py
import pandas as pd, re, pycountry

AF_ISO = {  # 54 African ISO-3 codes
 'DZA','AGO','BEN','BWA','BFA','BDI','CMR','CPV','CAF','TCD','COM','COG','CIV','COD','DJI',
 'EGY','GNQ','ERI','SWZ','ETH','GAB','GMB','GHA','GIN','GNB','KEN','LSO','LBR','LBY','MDG',
 'MWI','MLI','MRT','MUS','MAR','MOZ','NAM','NER','NGA','RWA','STP','SEN','SYC','SLE','SOM',
 'ZAF','SSD','SDN','TZA','TGO','TUN','UGA','ZMB','ZWE'}

def area_to_iso(name: str) -> str|None:
    """Convert full country name to ISO-3 if it is in Africa."""
    try:
        iso = pycountry.countries.lookup(name).alpha_3
        return iso if iso in AF_ISO else None
    except LookupError:
        return None

def read_any(src: str) -> pd.DataFrame:
    """Read CSV or Excel transparently."""
    if src.lower().endswith((".xls", ".xlsx")):
        return pd.read_excel(src)
    return pd.read_csv(src)

def detect_year_cols(df: pd.DataFrame):
    """Return list of columns that look like year numbers or 'Y2003' etc."""
    return [c for c in df.columns if re.fullmatch(r"Y?\d{4}", str(c))]
