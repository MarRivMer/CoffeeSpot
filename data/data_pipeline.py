from datetime import datetime, timezone
import pandas as pd


def get_hours_until_close(opening_hours):
    if not opening_hours:
        return 0.0

    if not opening_hours.get("openNow", False):
        return 0.0

    next_close_time = opening_hours.get("nextCloseTime")

    if not next_close_time:
        return 0.0

    close_time = datetime.fromisoformat(next_close_time.replace("Z", "+00:00"))
    current_time = datetime.now(timezone.utc)
    difference = close_time - current_time
    hours_remaining = difference.total_seconds() / 3600

    return max(hours_remaining, 0.0)

def create_coffee_dataframe(valid_shops, route_data, purpose):
    rows = []

    durations = route_data.get("durations", [[]])[0]
    distances = route_data.get("distances", [[]])[0]

    for index, place in enumerate(valid_shops):

        duration_seconds = (
            durations[index]
            if index < len(durations)
            else None
        )
        distance_km = (
            distances[index]
            if index < len(distances)
            else None
        )

        if duration_seconds is not None:
            travel_time_minutes = duration_seconds / 60
        else:
            travel_time_minutes = None

        opening_hours = place.get("currentOpeningHours", {})

        open_now = int(opening_hours.get("openNow", False))

        hours_until_close = get_hours_until_close(opening_hours)

        row = {
            "id": place.get("id"),

            "name": place.get("displayName", {}).get("text", "Unknown"),

            "address": place.get("formattedAddress", "No address"),

            "rating": place.get("rating"),

            "review_count": place.get("userRatingCount"),

            "price_level": place.get("priceLevel"),

            "open_now": open_now,

            "hours_until_close": round(hours_until_close, 2),

            "travel_time_minutes": round(travel_time_minutes, 2) 
            if travel_time_minutes is not None else None,

            "distance_km": distance_km,

            "purpose": purpose
        }

        rows.append(row)

    return pd.DataFrame(rows)