# agriflow-nexus/config/config.py
import os
from dataclasses import dataclass
import os, datetime as _dt
from decouple import config

@dataclass
class Config:
    # Google Cloud Configuration
    PROJECT_ID:       str = os.getenv("GOOGLE_CLOUD_PROJECT", "fieldsense-optimizer")
    BIGQUERY_DATASET: str = os.getenv("BQ_DATASET", "ag_flow")      # ⬅️ new
    CLOUD_REGION:     str = "africa-south1"
    # misc
    NOW:              _dt.datetime = _dt.datetime.utcnow()
    
    # Agent Configuration
    MAX_RETRIES: int = 3
    AGENT_TIMEOUT: int = 30
    MESSAGE_QUEUE_SIZE: int = 100
    
    # Database Configuration
    BATCH_SIZE: int = 1000
    MAX_CONNECTIONS: int = 10

# Create environment template
def create_env_template():
    env_content = """
# Google Cloud Configuration
GOOGLE_CLOUD_PROJECT=fieldsense-optimizer
GOOGLE_APPLICATION_CREDENTIALS= config('GOOGLE_APPLICATION_CREDENTIALS')

# API Keys
WEATHER_API_KEY=your-weather-api-key-here

# Development Settings
DEBUG=True
LOG_LEVEL=INFO
"""
    with open('.env.template', 'w') as f:
        f.write(env_content)

if __name__ == "__main__":
    create_env_template()
    print("Environment template created at .env.template")