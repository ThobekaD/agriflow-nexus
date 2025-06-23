# aagriflow-nexus/models.py
from dataclasses import dataclass
from datetime import datetime, date
from typing import Optional, List

# --- Core Data Models from BigQuery Schema ---

@dataclass
class PrecipDaily:
    country_iso: str
    date: date
    lat: float
    lon: float
    pr_mm: float
    created_at: Optional[datetime] = None

@dataclass
class SoilMoistureDaily:
    country_iso: str
    date: date
    lat: float
    lon: float
    sm_percent: float
    created_at: Optional[datetime] = None

@dataclass
class TmaxDaily:
    country_iso: str
    date: date
    lat: float
    lon: float
    tasmax_c: float
    created_at: Optional[datetime] = None

@dataclass
class CommodityPrice:
    year: int
    commodity: str
    price: float
    unit: str
    series_type: str
    created_at: Optional[datetime] = None

@dataclass
class ProductionStat:
    country_iso: str
    variable: str
    year: int
    value: float
    created_at: Optional[datetime] = None

@dataclass
class InvestmentStat:
    country_iso: str
    year: int
    variable: str
    value: float
    created_at: Optional[datetime] = None

@dataclass
class MarketPrice:
    country_iso: str
    commodity: str
    year: int
    price: float
    unit: str
    created_at: Optional[datetime] = None
    
@dataclass
class AcledEvent:
    country_iso: str
    date: date
    lat: float
    lon: float
    event: str
    sub_event: str
    fatalities: int

@dataclass
class CrudeOilPrice:
    year: int
    usd_per_bbl: float
    source: str

# --- Agent-Specific Data Models ---

@dataclass
class WeatherData:
    location_id: str
    timestamp: datetime
    temperature: float
    humidity: float
    rainfall: float
    wind_speed: float
    forecast_type: str

@dataclass
class MarketData:
    commodity_type: str
    price: float
    currency: str
    market_location: str
    timestamp: datetime
    data_source: str

@dataclass
class FarmData:
    farmer_id: str
    location_lat: float
    location_lng: float
    farm_size: float
    primary_crop: str
    livestock_count: int
    last_updated: datetime

@dataclass
class LogisticsData:
    route_id: str
    origin_location: str
    destination_location: str
    distance_km: float
    estimated_cost: float
    transport_type: str

# --- System Messaging ---

@dataclass
class AgentMessage:
    sender_agent: str
    receiver_agent: str
    message_type: str
    message_content: str
    timestamp: datetime
    status: str = "pending"