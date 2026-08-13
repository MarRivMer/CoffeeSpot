from flask import Flask, render_template, request
from flask_scss import Scss
from APIs import get_nearby_coffee_shops, get_travel_times # create_coffee_dataframe
import folium
# from ML.predictor import predict_coffee_spot

app = Flask(__name__)

@app.route('/', methods=["GET", "POST"])
def discover_screen():
    coffee_shops = []
    map_html = None
    top_three_spots = []

    # coffee_shops = get_nearby_coffee_shops(28.5383, -81.3792)


    if request.method == "POST":
        location = request.form['location']
        latitude = 28.5383
        longitude = -81.3792
        purpose = request.form["purpose"]
        print(location)
        print(purpose)

        # ------ Coffee Spots Logic -----
        coffee_shops = get_nearby_coffee_shops(latitude=latitude, longitude=longitude)


        # # ----- Map Logic -----
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

        # # ----- AI MLP Model Recommendation Logic -----
        # valid_shops, route_data = get_travel_times(latitude, longitude, coffee_shops)
        # coffee_df = create_coffee_dataframe(valid_shops, route_data, purpose)

        # predictions = []
        # match_scores = []

        # for _, row in coffee_df.iterrows():

        #     sample = {
        #         "rating": row["rating"],
        #         "review_count": row["review_count"],
        #         "price_level": row["price_level"],
        #         "open_now": row["open_now"],
        #         "hours_until_close": row["hours_until_close"],
        #         "travel_time_minutes": row["travel_time_minutes"],
        #         "purpose": row["purpose"]
        #     }

        #     prediction, match_score = predict_coffee_spot(sample)

        #     predictions.append(prediction)
        #     match_scores.append(match_score)

        # coffee_df["prediction"] = predictions
        # coffee_df["match_score"] = match_scores
        # coffee_df = coffee_df.sort_values(by="match_score", ascending=False)
        # top_three_spots = coffee_df.head(3)
        # top_three_spots = top_three_spots.to_dict(orient="records")
        
    return render_template('home.html', coffee_shops=coffee_shops, map_html=map_html, top_three_spots=top_three_spots)



@app.route('/Compare')
def compare_screen():
    return None

@app.route('/Saved')
def saved_screen():
    return None

@app.route('/Details')
def details_screen():
    return None







if __name__ == "__main__":
    app.run(debug=True)


