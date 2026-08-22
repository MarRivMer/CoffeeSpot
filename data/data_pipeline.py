from datetime import datetime, timezone
import pandas as pd
from APIs import get_nearby_coffee_shops, filter_valid_places_with_route


def get_hours_until_close(opening_hours):
    if not opening_hours:
        return None, 0.0

    if not opening_hours.get("openNow", False):
        return None, 0.0

    next_close_time = opening_hours.get("nextCloseTime")

    if not next_close_time:
        return None, 0.0

    close_time = datetime.fromisoformat(next_close_time.replace("Z", "+00:00"))

    current_time = datetime.now(timezone.utc)
    difference = close_time - current_time
    hours_remaining = difference.total_seconds() / 3600

    return close_time, max(hours_remaining, 0.0)

def get_parking_type(parking_options):
    if not parking_options:
        return "No Parking"

    free_parking = (
        parking_options.get("freeParkingLot", False)
        or parking_options.get("freeStreetParking", False)
    )

    paid_parking = (
        parking_options.get("paidParkingLot", False)
        or parking_options.get("paidStreetParking", False)
    )

    if free_parking:
        return "Free"
    
    if paid_parking:
        return "Paid"

    return "No Parking"

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
        close_time, hours_until_close = get_hours_until_close(opening_hours)
        parking_option = get_parking_type(place.get("parkingOptions"))
        review_summary = place.get("reviewSummary", {}).get("text", {}).get("text", "No summary")
        ai_summary = place.get("generativeSummary", {}).get("overview", {}).get("text", "No summary")

        # - Get the real wifi status from API in future -
        wifi = "Excellent"

        row = {
            "id": place.get("id"),
            "name": place.get("displayName", {}).get("text", "Unknown"),
            "photos": place.get("photos", []),
            "website_url": place.get("websiteUri", "Unknown"),
            "phone_number": place.get("nationalPhoneNumber", "Unkown"),
            "address": place.get("formattedAddress", "No address"),
            "rating": place.get("rating"),
            "review_count": place.get("userRatingCount"),
            "ai_summary": ai_summary,
            "review_summary": review_summary,
            "price_level": place.get("priceLevel"),
            "wifi": wifi,
            "open_now": open_now,

            "close_time": close_time.strftime("%I:%M %p")
            if close_time else None,

            "hours_until_close": round(hours_until_close, 2),

            "travel_time_minutes": round(travel_time_minutes, 2) 
            if travel_time_minutes is not None else None,

            "distance_km": distance_km,
            "outdoor_seating": place.get("outdoorSeating", "Unkown"),
            "restrooms": place.get("restroom", "Unkown"),
            "parking_options": parking_option,
            "reservable": place.get("reservable", "Unkown"),
            "delivery": place.get("delivery", "Unkown"),
            "serves_breakfast": place.get("servesBreakfast", "Unkown"),
            "purpose": purpose
        }

        rows.append(row)

    return pd.DataFrame(rows)


if __name__ == '__main__':
    latitude = 28.5383
    longitude = -81.3792
    purpose = 'STUDY'

    coffee_shops = get_nearby_coffee_shops(latitude=latitude, longitude=longitude)
    valid_shops, route_data = filter_valid_places_with_route(latitude, longitude, coffee_shops)
    coffee_spot_df = create_coffee_dataframe(valid_shops, route_data, purpose)

    coffee_spot_df.to_csv("data/coffee_df_test.csv")

    print(coffee_spot_df)