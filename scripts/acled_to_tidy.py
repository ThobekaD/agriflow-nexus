#!/usr/bin/env python3
# ag-optimizer/scripts/acled_to_tidy.py
import argparse
import csv
import sys
from pathlib import Path

import pandas as pd

# --------------------------------------------------------------------------- #
# 1. CLI -------------------------------------------------------------------- #
# --------------------------------------------------------------------------- #
parser = argparse.ArgumentParser(
    description="Tidy ACLED download → thin CSV",
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
)
parser.add_argument("infile", type=Path, help="Raw ACLED *.csv")
parser.add_argument("outfile", type=Path, help="Destination tidy CSV")
parser.add_argument(
    "--africa-only",
    action="store_true",
    help="Keep just events whose ISO-numeric code is an African state "
         "(otherwise no ISO filtering is applied).",
)

args = parser.parse_args()

# --------------------------------------------------------------------------- #
# 2. Column config ---------------------------------------------------------- #
# --------------------------------------------------------------------------- #
RAW_COLS = {
    "iso",            # country ISO-numeric (e.g. 180 for DRC)
    "event_date",     # yyyy-mm-dd
    "latitude",
    "longitude",
    "event_type",
    "sub_event_type",
    "fatalities",
}

RENAMER = {
    "iso": "country_iso",
    "event_date": "date",
    "latitude": "lat",
    "longitude": "lon",
    "event_type": "event",
    "sub_event_type": "sub_event",
    # fatalities keeps its name
}

AFRICA_ISO_NUMERIC = {
     12,  24,  72,  108, 120, 148, 174, 175, 178, 180, 204, 226, 231,
    232, 233, 262, 266, 270, 288, 324, 384, 404, 426, 430, 434, 450,
    454, 466, 478, 480, 504, 508, 516, 562, 566, 624, 646, 678, 686,
    706, 710, 716, 728, 729, 748, 800, 818, 834, 854, 894,
}

# --------------------------------------------------------------------------- #
# 3. Utility: sniff delimiter ---------------------------------------------- #
# --------------------------------------------------------------------------- #
def sniff_delimiter(csv_path: Path, sample_bytes: int = 65536) -> str:
    with csv_path.open("rb") as fh:
        sample = fh.read(sample_bytes)
    dialect = csv.Sniffer().sniff(sample.decode("utf-8", "ignore"))
    return dialect.delimiter


delimiter = sniff_delimiter(args.infile)

# --------------------------------------------------------------------------- #
# 4. Stream-process in chunks ---------------------------------------------- #
# --------------------------------------------------------------------------- #
rows_written = 0
CHUNK = 250_000  # adjust if you have plenty of RAM

# prepare writer (append mode so we can stream multiple chunks)
args.outfile.parent.mkdir(parents=True, exist_ok=True)
first_chunk = True

reader_kw = dict(
    sep=delimiter,
    usecols=lambda c: c in RAW_COLS,
    parse_dates=["event_date"],
    dtype={"iso": "Int64", "fatalities": "Int64"},
    chunksize=CHUNK,
    low_memory=False,
)

for chunk in pd.read_csv(args.infile, **reader_kw):
    # optional Africa filter
    if args.africa_only:
        chunk = chunk[chunk["iso"].isin(AFRICA_ISO_NUMERIC)]

    # rename & reorder
    chunk = (
        chunk.rename(columns=RENAMER)
             .loc[:, ["country_iso", "date", "lat", "lon",
                      "event", "sub_event", "fatalities"]]
    )

    # write out
    chunk.to_csv(
        args.outfile,
        mode="w" if first_chunk else "a",
        header=first_chunk,
        index=False,
        encoding="utf-8",  # no BOM by default
    )
    rows_written += len(chunk)
    first_chunk = False

# --------------------------------------------------------------------------- #
# 5. Final report ----------------------------------------------------------- #
# --------------------------------------------------------------------------- #
print(f"✅  Saved {args.outfile}  rows={rows_written:,}", file=sys.stderr)
