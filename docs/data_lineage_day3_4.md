# data_lineage_day3-4.md
# Data Lineage: Day 3-4 ETL Pipeline

## Objective

This document traces the data flow of the `day3_4.sh` script. The pipeline's goal is to take raw conflict event data, enrich it with geographical and economic information, and produce an aggregated KPI table for analysis.

## Source Tables

The pipeline reads from three raw source tables located in the `asco_core` dataset:

-   **`fieldsense-optimizer.asco_core.acled_events`**: Contains raw conflict event data from ACLED, including event date, location (lat/lon), and fatalities.
-   **`fieldsense-optimizer.asco_core.gadm_lvl2`**: Contains level-2 administrative boundary polygons from the GADM dataset.
-   **`fieldsense-optimizer.asco_core.crude_oil_prices`**: A small dimension table containing the annual average price of crude oil.

## Transformation Steps

The script executes the following sequence of transformations:

1.  **Filter & Geocode Events (`acled_events_geo`)**
    -   The raw `acled_events` table is filtered to a 2003-2023 time window.
    -   A new `GEOGRAPHY` column (`geom`) is created from the `lat` and `lon` columns.
    -   The resulting intermediate table is partitioned by month to improve performance.

2.  **Spatial Join (`acled_l2`)**
    -   A spatial join is performed between the geocoded events (`acled_events_geo`) and the administrative boundary polygons (`gadm_lvl2`).
    -   This adds country and regional names (`NAME_1`, `NAME_2`) and IDs to each conflict event based on its geographic location.

3.  **Economic Enrichment (`acled_enriched`)**
    -   The spatially joined data (`acled_l2`) is enriched with economic data by joining it with `crude_oil_prices` on the `year` column.
    -   This adds the `usd_per_bbl` for the year of each event.

4.  **Final Aggregation (`kpi_region_year`)**
    -   The fully enriched data is aggregated to produce the final KPI table.
    -   It calculates the total number of events (`events`) and the sum of fatalities (`deaths`) for each region (`NAME_1`) and `year`.

## Output Tables

The pipeline produces the following tables in the `asco_core` and `asco_derived` datasets:

-   **`fieldsense-optimizer.asco_core.acled_events_geo`**: Intermediate table with filtered and geocoded events.
-   **`fieldsense-optimizer.asco_derived.acled_l2`**: Intermediate table with events enriched with administrative boundaries.
-   **`fieldsense-optimizer.asco_derived.acled_enriched`**: The main, detailed fact table containing fully enriched event data.
-   **`fieldsense-optimizer.asco_derived.kpi_region_year`**: The final, aggregated table ready for business intelligence and dashboarding.

## Lineage Diagram

```mermaid
graph TD;
    subgraph Raw Sources (asco_core)
        A[acled_events];
        B[gadm_lvl2];
        C[crude_oil_prices];
    end

    subgraph Intermediate (asco_core)
        D[acled_events_geo];
    end

    subgraph Analytical Marts (asco_derived)
        E[acled_l2];
        F[acled_enriched];
        G[kpi_region_year];
    end

    A --> D;
    D --> E;
    B --> E;
    E --> F;
    C --> F;
    F --> G;