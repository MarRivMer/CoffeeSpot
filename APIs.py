import os
import requests
from dotenv import load_dotenv
from pathlib import Path
import requests
# from data.data_pipeline import create_coffee_dataframe


load_dotenv()
PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")
PLACES_URL = "https://places.googleapis.com/v1/places:searchNearby"

ORS_API_KEY = os.getenv("OPENROUTESERVICE_API_KEY")
ORS_MATRIX_URL = ("https://api.openrouteservice.org/v2/matrix/driving-car")


def get_nearby_coffee_shops(latitude, longitude, radius=5000):
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": PLACES_API_KEY,
        "X-Goog-FieldMask": (
            "places.id,"
            "places.displayName,"
            "places.formattedAddress,"
            "places.location,"
            "places.rating,"
            "places.userRatingCount,"
            "places.editorialSummary,"
            "places.priceLevel,"
            "places.currentOpeningHours,"
            "places.regularOpeningHours,"
            "places.outdoorSeating,"
            "places.websiteUri,"
            "places.nationalPhoneNumber,"
            "places.photos,"
            "places.restroom,"
            "places.parkingOptions,"
            "places.curbsidePickup,"
            "places.reservable,"
            "places.delivery,"
            "places.servesBreakfast,"
            "places.regularSecondaryOpeningHours,"
            "places.currentSecondaryOpeningHours"
        )
    }

    data = {
        "includedPrimaryTypes": ['cafe'],
        "maxResultCount": 10,
        "locationRestriction": {
            "circle": {
                "center": {
                    "latitude": latitude,
                    "longitude": longitude
                },
                "radius": radius
            }
        }
    }

    response = requests.post(PLACES_URL, headers=headers, json=data)
    response.raise_for_status()

    return response.json().get("places", [])

def filter_valid_places_with_route(origin_lat, origin_lon, coffee_shops):
    locations = []

    valid_places = []

    locations.append([origin_lon, origin_lat])

    for place in coffee_shops:
        location = place.get("location", {})

        latitude = location.get("latitude")
        longitude = location.get("longitude")

        if latitude is None or longitude is None:
            continue

        locations.append([longitude, latitude])

        valid_places.append(place)

    if not valid_places:
        return [], {}


    destination_indexes = list(range(1, len(locations)))

    data = {
        "locations": locations,

        "sources": [0],

        "destinations": destination_indexes,

        "metrics": [
            "duration",
            "distance"
        ],

        "units": "km"
    }

    headers = {
        "Authorization": ORS_API_KEY,
        "Content-Type": "application/json"
    }

    route_data = requests.post(ORS_MATRIX_URL, headers=headers, json=data)
    route_data.raise_for_status()

    return valid_places, route_data.json()

def geocode_location(location):

    url = "https://nominatim.openstreetmap.org/search"

    params = {
        "q": location,
        "format": "json",
        "limit": 1
    }

    headers = {
        "User-Agent": "CoffeeSpot/1.0"
    }

    response = requests.get(url, params=params, headers=headers)
    response.raise_for_status()

    data = response.json()

    if not data:
        raise ValueError("Location could not be found.")

    latitude = float(data[0]["lat"])
    longitude = float(data[0]["lon"])

    return latitude, longitude


# New York Coordinates = 40.7128, -74.0060
# Orlando Coordinates = 28.5383, -81.3792
# Testing get_nearby_coffee_shops(Orlando FL)
# if __name__ == '__main__':
#     results_test = get_nearby_coffee_shops(28.5383, -81.3792)
#     for place in results_test:
#         name = place.get("displayName", {}).get("text", "Unknown")
#         address = place.get("formattedAddress", "No address")
#         rating = place.get("rating", "No Rating")
#         reviews = place.get("userRatingCount", 0)

#         print(f"{name}")
#         print(f"Address: {address}")
#         print(f"Rating: {rating}")
#         print(f"Reviews: {reviews}")
#         print("----------------------")


# Testing get_travel_time()
# if __name__ == "__main__":

#     latitude = 28.5383
#     longitude = -81.3792

#     shops = get_nearby_coffee_shops(latitude, longitude)
#     valid_shops, route_data = get_travel_times(latitude, longitude, shops)

    # durations = route_data.get("durations", [[]])[0]
    # distances = route_data.get("distances", [[]])[0]


    # for index, place in enumerate(valid_shops):

    #     name = place.get("displayName", {}).get("text", "Unknown")
    #     duration_seconds = durations[index]
    #     distance_km = distances[index]

    #     if duration_seconds is not None:
    #         duration_minutes = duration_seconds / 60
    #     else:
    #         duration_minutes = None

    #     print(name)

    #     if duration_minutes is not None:
    #         print(
    #             f"Travel time: "
    #             f"{duration_minutes:.1f} minutes"
    #         )
    #     else:
    #         print("Travel time: unavailable")

    #     print(f"Distance: {distance_km} km")

    #     print("----------------------")

    # coffee_df = create_coffee_dataframe(valid_shops, route_data, "Study")
    # print(coffee_df)