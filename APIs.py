import os
import requests
from dotenv import load_dotenv
from pathlib import Path
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

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
            "places.generativeSummary,"
            "places.editorialSummary,"
            "places.reviewSummary,"
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


# def get_place_image(place_name):

#     # 1. Try Google
#     google_photo = get_google_photo(place_name)

#     if google_photo:
#         return google_photo

#     # 2. Try Unsplash
#     unsplash_photo = get_unsplash_photo(place_name)

#     if unsplash_photo:
#         return unsplash_photo

#     # 3. Guaranteed fallback
#     return "/static/images/coffee-default.jpg"



   
  