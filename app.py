from flask import Flask, render_template, request, redirect, url_for
from flask_scss import Scss
from APIs import get_nearby_coffee_shops, filter_valid_places_with_route, geocode_location
from data.data_pipeline import create_coffee_dataframe
import folium
from ML.predictor import predict_coffee_spot

app = Flask(__name__)

saved_spots = []

coffee_spot_df = []
map_html = None
top_three_spots = []

compare_spots = []
compare_initialized = False

@app.route('/', methods=["GET", "POST"])
def discover_screen():

    global coffee_spot_df
    global map_html
    global top_three_spots
    global compare_spots
    global compare_initialized
    coffee_shops = []

    if request.method == "POST":
        location = request.form['location']
        latitude, longitude = geocode_location(location)
        purpose = request.form["purpose"]

        # ------ Coffee Spots Logic -----
        coffee_shops = get_nearby_coffee_shops(latitude=latitude, longitude=longitude)
        valid_shops, route_data = filter_valid_places_with_route(latitude, longitude, coffee_shops)
        coffee_spot_df = create_coffee_dataframe(valid_shops, route_data, purpose)

        # ----- Map Logic -----
        coffee_map = folium.Map(location=[latitude, longitude], zoom_start=13)
        folium.Marker([latitude, longitude], popup="Search Location", tooltip="Search Location").add_to(coffee_map)

        for place in coffee_shops:
            location = place.get("location", {})
            shop_lat = location.get("latitude")
            shop_lon = location.get("longitude")

            if shop_lat is None or shop_lon is None:
                continue

            name = place.get("displayName", {}).get("text", "Unknown Coffee Shop")
            rating = place.get("rating", "No rating")
            popup_text = f"""
            <strong>{name}</strong><br>
            Rating: {rating}
            """

            folium.Marker([shop_lat, shop_lon], popup=popup_text, tooltip=name).add_to(coffee_map)

        map_html = coffee_map._repr_html_()

        # ----- AI MLP Model Recommendation Logic -----
        predictions = []
        match_scores = []

        for _, row in coffee_spot_df.iterrows():

            sample = {
                "rating": row["rating"],
                "review_count": row["review_count"],
                "price_level": row["price_level"],
                "open_now": row["open_now"],
                "hours_until_close": row["hours_until_close"],
                "travel_time_minutes": row["travel_time_minutes"],
                "purpose": row["purpose"]
            }

            prediction, match_score = predict_coffee_spot(sample)

            predictions.append(prediction)
            match_scores.append(match_score)

        coffee_spot_df["prediction"] = predictions
        coffee_spot_df["match_score"] = match_scores
        coffee_spot_df["match_score"] = coffee_spot_df["match_score"].fillna(0)
        coffee_spot_df['rating'] = coffee_spot_df['rating'].fillna('No Rating Found')
        coffee_spot_df = coffee_spot_df.sort_values(by="match_score", ascending=False)
        top_three_spots = coffee_spot_df.head(3)

        coffee_spot_df = coffee_spot_df.to_dict(orient="records")
        top_three_spots = top_three_spots.to_dict(orient="records")

        compare_spots = top_three_spots.copy()
        compare_initialized = True
        
        
    return render_template('home.html', coffee_shops=coffee_spot_df, map_html=map_html, top_three_spots=top_three_spots)

@app.route('/compare', methods=["GET", "POST"])
def compare_screen():
    global saved_spots
    global compare_spots
    global compare_initialized
    global coffee_spot_df
    global top_three_spots

    if not compare_initialized:

        compare_spots = top_three_spots.copy()
        compare_initialized = True

    if request.method == "POST":

        action = request.form.get("action")
        place_id = request.form.get("place_id")
       
        if action == "remove":

            compare_spots = [
                place
                for place in compare_spots
                if place["id"] != place_id
            ]

        elif action == "choose":

            chosenID = request.form.get("chosenID")

            spot_already_saved = any(
                spot["id"] == chosenID
                for spot in saved_spots
            )

            if not spot_already_saved:

                for place in compare_spots:

                    if place["id"] == chosenID:

                        saved_spots.append(place)
                        break

            return redirect(url_for("saved_screen"))

        return redirect(url_for("compare_screen"))

    return render_template(
        "compare.html",
        compare_spots=compare_spots)

@app.route('/saved')
def saved_screen():
    global saved_spots
    return render_template('saved.html', saved_spots=saved_spots)

@app.route('/details', methods=["GET", "POST"])
def details_screen():
    global coffee_spot_df, saved_spots
    coffee_spot = None

    if request.method == "POST":
        place_id = request.form.get("place_id")
        page = request.form.get("page")

        saved_page = False
        compare_page = False
        home_page = False

        if page == "saved":
            saved_page = True
        elif page == "home":
            home_page = True

        print(f'page: {page}')
        print(f"Home page: {home_page} ")
        print(f"Saved page: {saved_page}")

        # Check current coffee shop results
        for place in coffee_spot_df:
            if place['id'] == place_id:
                coffee_spot = place
                break

        # If not found, check saved spots
        if coffee_spot is None:
            for place in saved_spots:
                if place['id'] == place_id:
                    coffee_spot = place
                    break    
        

    return render_template('details.html', spot=coffee_spot, saved_page=saved_page, home_page=home_page)


def add_to_compare(place_id):
    global compare_spots, coffee_spot_df

    if len(compare_spots) < 3:
    
        already_added = any(
            place["id"] == place_id
            for place in compare_spots
        )
    
        if not already_added:
    
            for place in coffee_spot_df:
    
                if place["id"] == place_id:
                    compare_spots.append(place)
                    break




if __name__ == "__main__":
    app.run(debug=True)


