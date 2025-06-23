-- agriflow-nexus/config/database_schema.sql
-- This file defines the database schema for the agricultural supply chain optimization system.
-- Weather Data Table
CREATE TABLE weather_data (
    id STRING,
    location_id STRING,
    timestamp TIMESTAMP,
    temperature FLOAT64,
    humidity FLOAT64,
    rainfall FLOAT64,
    wind_speed FLOAT64,
    forecast_type STRING,
    created_at TIMESTAMP
);

-- Market Data Table
CREATE TABLE market_data (
    id STRING,
    commodity_type STRING,
    price FLOAT64,
    currency STRING,
    market_location STRING,
    timestamp TIMESTAMP,
    data_source STRING,
    created_at TIMESTAMP
);

-- Farm Data Table
CREATE TABLE farm_data (
    id STRING,
    farmer_id STRING,
    location_lat FLOAT64,
    location_lng FLOAT64,
    farm_size FLOAT64,
    primary_crop STRING,
    livestock_count INT64,
    last_updated TIMESTAMP,
    created_at TIMESTAMP
);

-- Logistics Data Table
CREATE TABLE logistics_data (
    id STRING,
    route_id STRING,
    origin_location STRING,
    destination_location STRING,
    distance_km FLOAT64,
    estimated_cost FLOAT64,
    transport_type STRING,
    created_at TIMESTAMP
);

-- 1.  DAILY PRECIPITATION  (≈ 2003-2023)
CREATE TABLE IF NOT EXISTS precip_daily (
    country_iso STRING,
    date DATE,
    lat FLOAT64,
    lon FLOAT64,
    pr_mm FLOAT64,
    created_at TIMESTAMP
)
PARTITION BY DATE(date)
CLUSTER BY country_iso, lat, lon;

-- 2.  DAILY SOIL-MOISTURE
CREATE TABLE IF NOT EXISTS soil_moisture_daily (
    country_iso STRING,
    date DATE,
    lat FLOAT64,
    lon FLOAT64,
    sm_percent FLOAT64,
    created_at TIMESTAMP
)
PARTITION BY DATE(date)
CLUSTER BY country_iso, lat, lon;

-- 3.  DAILY MAX-TEMP
CREATE TABLE IF NOT EXISTS tmax_daily (
    country_iso STRING,
    date DATE,
    lat FLOAT64,
    lon FLOAT64,
    tasmax_c FLOAT64,
    created_at TIMESTAMP
)
PARTITION BY DATE(date)
CLUSTER BY country_iso, lat, lon;

-- 4.  ANNUAL COMMODITY PRICES
CREATE TABLE IF NOT EXISTS commodity_prices (
    year INT64,
    commodity STRING,
    price FLOAT64,
    unit STRING,
    series_type STRING,
    created_at TIMESTAMP
);

-- 5.  CROPS & LIVESTOCK PRODUCTION
CREATE TABLE IF NOT EXISTS production_stats (
    country_iso STRING,
    variable STRING,
    year INT64,
    value FLOAT64,
    created_at TIMESTAMP
);

-- 6.  INVESTMENT & MACRO STATS
CREATE TABLE IF NOT EXISTS investment_stats (
    country_iso STRING,
    year INT64,
    variable STRING,
    value FLOAT64,
    created_at TIMESTAMP
);
-- 7.  MARKET PRICES
CREATE TABLE IF NOT EXISTS market_prices (
    country_iso STRING,
    commodity STRING,
    year INT64,
    price FLOAT64,
    unit STRING,
    created_at TIMESTAMP
)
PARTITION BY DATE(year)
CLUSTER BY country_iso, commodity;      

-- Agent Communications Table
CREATE TABLE agent_communications (
    id STRING,
    sender_agent STRING,
    receiver_agent STRING,
    message_type STRING,
    message_content STRING,
    timestamp TIMESTAMP,
    status STRING
);