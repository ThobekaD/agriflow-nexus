import pandas as pd, pathlib, re

SRC  = "data/raw/faostat/Commodity_Prices_History_n_Projections_time series.xlsx"
OUT  = pathlib.Path("data/sample/commodity_prices_2003_2023.csv")

def parse_header(h):
    """
    'Maize, nominal, $/mt – World (WB/commodity_prices/FMAIZE-1W)'
      → commodity='Maize', unit='$/mt', type='nominal'
    """
    m = re.match(r"([^,]+),\s*(nominal|real),\s*([^–]+)–", h)
    if not m:
        return None, None, None
    return m.group(1).strip(), m.group(3).strip(), m.group(2)

dfs = []
xls = pd.ExcelFile(SRC)
for sheet in xls.sheet_names:
    df = pd.read_excel(xls, sheet_name=sheet)
    df = df.rename(columns={df.columns[0]: "Year"})
    df = df[df["Year"].between(2003, 2023)]

    for col in df.columns[1:]:
        commodity, unit, series_type = parse_header(col)
        if commodity:
            tmp = df[["Year", col]].copy()
            tmp = tmp.rename(columns={col: "price"})
            tmp["commodity"]   = commodity
            tmp["unit"]        = unit
            tmp["series_type"] = series_type
            dfs.append(tmp)

tidy = pd.concat(dfs, ignore_index=True)
tidy.to_csv(OUT, index=False)
print(f"✅  Saved {OUT} with {len(tidy):,} rows and "
      f"{tidy['commodity'].nunique()} commodities")
