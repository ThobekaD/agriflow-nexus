import random
from datetime import datetime, timedelta
from google.cloud import bigquery
import uuid
import os

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'service-account-key.json'
client = bigquery.Client()

def generate_sample_weather_data():
    """Generate sample weather data for Botswana locations"""
    locations = [
        "gaborone", "francistown", "molepolole", "selebi-phikwe", 
        "serowe", "maun", "lobatse", "kanye"
    ]
    
    data = []
    for _ in range(100):
        location = random.choice(locations)
        timestamp = datetime.now() - timedelta(days=random.randint(0, 30))
        
        # Simulate Botswana weather patterns
        base_temp = 25 if timestamp.month in [5,6,7,8] else 30  # Cooler in winter
        temperature = base_temp + random.uniform(-5, 10)
        humidity = random.uniform(20, 80)
        rainfall = random.uniform(0, 50) if timestamp.month in [11,12,1,2,3] else random.uniform(0, 5)
        wind_speed = random.uniform(5, 25)
        
        data.append({
            'id': str(uuid.uuid4()),
            'location_id': location,
            'timestamp': timestamp,
            'temperature': temperature,
            'humidity': humidity,
            'rainfall': rainfall,
            'wind_speed': wind_speed,
            'forecast_type': 'historical',
            'created_at': datetime.now()
        })
    
    return data

# Insert sample data
sample_data = generate_sample_weather_data()
table_id = "agricultural_supply_chain.weather_data"

job_config = bigquery.LoadJobConfig()
job = client.load_table_from_json(sample_data, table_id, job_config=job_config)
job.result()  # Wait for the job to complete

print(f"Loaded {len(sample_data)} rows into {table_id}")