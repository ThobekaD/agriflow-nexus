/*─────────────────────────────────────────────────────────────────────────────
  Build road_network_sadc  – SADC-only road lines with ISO tag
──────────────────────────────────────────────────────────────────────────────*/

CREATE OR REPLACE TABLE `ag_flow.road_network_sadc` AS
WITH
  -- dissolve GADM-L2 polygons → one polygon per country
  countries AS (
    SELECT
      GID_0              AS country_iso,      -- ISO-3
      ST_UNION_AGG(geom) AS geom              -- GEOGRAPHY
    FROM  `ag_flow.gadm_lvl2`
    WHERE GID_0 IN (
      'AGO','BWA','COM','COD','SWZ','LSO','MDG','MWI',
      'MUS','MOZ','NAM','SYC','ZAF','TZA','ZMB','ZWE'
    )
    GROUP BY country_iso
  )

SELECT
  c.country_iso,
  r.geometry                     AS geom,          -- GEOGRAPHY linestring
  ST_ASTEXT(r.geometry)          AS wkt            -- WKT text for convenience
FROM  `ag_flow.africa_roads` AS r                   -- roads table
JOIN  countries              AS c
  ON  ST_WITHIN(r.geometry, c.geom);                -- spatial filter
