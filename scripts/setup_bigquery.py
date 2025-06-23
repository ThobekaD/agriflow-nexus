from google.cloud import bigquery
import os

# Set up client
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'service-account-key.json'
client = bigquery.Client()

# Create dataset
dataset_id = "agricultural_supply_chain"
dataset = bigquery.Dataset(f"{client.project}.{dataset_id}")
dataset.location = "US"  # or your preferred location
dataset.description = "Agricultural Supply Chain Optimization Data"

try:
    dataset = client.create_dataset(dataset, timeout=30)
    print(f"Created dataset {client.project}.{dataset_id}")
except Exception as e:
    print(f"Dataset creation failed: {e}")

# Create tables
def create_table(table_id, schema):
    table_ref = client.dataset(dataset_id).table(table_id)
    table = bigquery.Table(table_ref, schema=schema)
    table = client.create_table(table)
    print(f"Created table {table.project}.{table.dataset_id}.{table.table_id}")

# Weather data schema
weather_schema = [
    bigquery.SchemaField("id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("location_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("timestamp", "TIMESTAMP", mode="REQUIRED"),
    bigquery.SchemaField("temperature", "FLOAT64"),
    bigquery.SchemaField("humidity", "FLOAT64"),
    bigquery.SchemaField("rainfall", "FLOAT64"),
    bigquery.SchemaField("wind_speed", "FLOAT64"),
    bigquery.SchemaField("forecast_type", "STRING"),
    bigquery.SchemaField("created_at", "TIMESTAMP", mode="REQUIRED"),
]

create_table("weather_data", weather_schema)

# Add similar schema creation for other tables...