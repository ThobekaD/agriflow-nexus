from typing import Dict, Any, List

def get_dynamic_negotiation_parties(forecasts: Dict[str, List[Dict]]) -> List[Dict[str, Any]]:
    """
    Generates negotiation party constraints based on the latest forecast price
    for the primary commodity.
    """
    if not forecasts:
        # Fallback to default static values if no forecast is available
        return [
            {"type": "farmer", "id": "FARM_GRP_A", "constraints": {"min_price": 280}},
            {"type": "buyer",  "id": "BUYER_XYZ",  "constraints": {"max_price": 350, "quality": "premium"}},
        ]

    # Use the first commodity's forecast as the basis for negotiation
    primary_commodity_name = next(iter(forecasts))
    primary_forecast = forecasts[primary_commodity_name]

    if not primary_forecast:
        # Fallback if the primary forecast is empty
        return get_dynamic_negotiation_parties({})

    # Get the first year's forecasted price
    latest_price = primary_forecast[0].get('price', 315) # Default to 315 if price is missing

    # Create dynamic constraints based on the forecast price
    # Farmer wants at least 90% of the forecast price
    # Buyer is willing to pay up to 110% of the forecast price
    min_price = round(latest_price * 0.90, 2)
    max_price = round(latest_price * 1.10, 2)

    return [
        {
            "type": "farmer",
            "id": "FARM_GRP_A",
            "constraints": {"min_price": min_price}
        },
        {
            "type": "buyer",
            "id": "BUYER_XYZ",
            "constraints": {"max_price": max_price, "quality": "premium"}
        }
    ]