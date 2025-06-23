```bash
$ python main.py
FieldSentinel → weather_oracle: normal
WeatherOracle → price_predictor: 7-day forecast ready
PricePredictor → logistics_master: forecast for Barley using rolling_mean_with_oil_factor
LogisticsMaster final plan → None

=== FINAL OUTPUT ===
{
  "routes": [
    {"truck": "T1", "stops": ["F02", "F01"], "distance_km": 312.4, "eta_hours": 5.21},
    {"truck": "T2", "stops": ["F03"],        "distance_km": 172.0, "eta_hours": 2.87}
  ],
  "generated_at": "2025-06-16T19:55:00Z"
}
