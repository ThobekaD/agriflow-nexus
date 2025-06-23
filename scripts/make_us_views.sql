-- scripts/make_us_views.sql
DECLARE src_proj  STRING DEFAULT 'fieldsense-optimizer';
DECLARE src_ds    STRING DEFAULT 'asco_core';
DECLARE trg_ds    STRING DEFAULT 'asco_ml';

-- tuple array <source_table , target_view >
DECLARE pairs ARRAY<STRUCT<src STRING, trg STRING>> DEFAULT [
  ('commodity_prices_all', 'commodity_prices_all_v'),
  ('crude_oil_prices'    , 'crude_oil_prices_v'    )
];

FOR rec IN (SELECT * FROM UNNEST(pairs)) DO
  EXECUTE IMMEDIATE FORMAT("""
    CREATE OR REPLACE VIEW `%s.%s.%s`
    AS SELECT * FROM `%s.%s.%s`""",
    src_proj, trg_ds, rec.trg,
    src_proj, src_ds, rec.src);
END FOR;
