from flask import Flask, render_template, request, redirect, url_for, flash
from flask_scss import Scss
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user, logout_user
from sqlalchemy import text
from APIs import get_nearby_coffee_shops, filter_valid_places_with_route, geocode_location
from data.data_pipeline import create_coffee_dataframe
import folium
from ML.predictor import predict_coffee_spot
import re
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()
login_manager = LoginManager()

saved_spots = []
coffee_spot_df = []
map_html = None
top_three_spots = []
compare_spots = []
compare_initialized = False


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(125), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), unique=False)

    def __repr__(self):
        return f"<User {self.username}>"


def CreateApp():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'dev-secret-key'
    app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///coffee_spot.db"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "login"


    @app.route('/health/db')
    def health_db():
        try:
            db.session.execute(text("SELECT 1"))
            return {"db": "ok"}, 200
        except Exception as e:
            return {"db": "error", "detail": str(e)}, 500

    with app.app_context():
        db.create_all()

    @app.route('/register', methods=["GET", "POST"])
    def register():
        errors = []
        
        if request.method == "POST":
            username = (request.form.get("username") or "").strip()
            email = (request.form.get("email") or "").strip()
            password = (request.form.get("password") or "")
            confirm_password = (request.form.get("confirm_password")  or "")

            if not (3 <= len(username) <= 80):
                errors.append("Username must be between 3-80 characters")
            if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
                errors.append("Please enter a valid email")
            if len(password) < 5:
                errors.append("Password needs to be at least 5 characters")
            if password != confirm_password:
                errors.append("Passwords do not match")

            if not errors:
                try:
                    pw_hash = generate_password_hash(password)
                    user = User(username=username, email=email, password_hash=pw_hash)
                    db.session.add(user)
                    db.session.commit()

                    return redirect(url_for('login'))
                
                except IntegrityError:
                    db.session.rollback()
                    errors.append("Username or email is already registered")
        
        return render_template('register.html', errors=errors)

    @app.route('/login', methods=["GET", "POST"])
    def login():
        errors = []

        if request.method == "POST":
            email = (request.form.get("email") or "").strip()
            password = (request.form.get("password") or "")

            if not email:
                errors.append("Email is required")
            if not password:
                errors.append("Password is required")
            if not errors:
                user = User.query.filter_by(email=email).first()
            if not user or not check_password_hash(user.password_hash, password):
                errors.append("Invalid email or password")
            else:
                login_user(user)
                return redirect(url_for("discover_screen"))

        return render_template('login.html', errors=errors)

    @app.route("/logout")
    def logout():
        logout_user()
        flash("You have been logged out") 
        return redirect(url_for('discover_screen'))

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(user_id)

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

        return render_template("compare.html", compare_spots=compare_spots)

    @app.route('/saved')
    @login_required
    def saved_screen():
        global saved_spots
        return render_template('saved.html', saved_spots=saved_spots)

    @app.route('/details', methods=["GET", "POST"])
    def details_screen():
        global coffee_spot_df
        global saved_spots
        coffee_spot = None
        saved_page = False
        compare_page = False
        home_page = False

        if request.method == "POST":

            place_id = request.form.get("place_id")
            page = request.form.get("page")
            button_pressed = request.form.get("button")

            if page == "saved":
                saved_page = True

            elif page == "home":
                home_page = True

            elif page == "compare":
                compare_page = True

            for place in coffee_spot_df:
                if place["id"] == place_id:
                    coffee_spot = place
                    break

            if coffee_spot is None:
                for place in saved_spots:

                    if place["id"] == place_id:
                        coffee_spot = place
                        break

            if button_pressed == "saved":
                add_to_saved(coffee_spot)
                return redirect(url_for("saved_screen"))

            elif button_pressed == "compare":
                add_to_compare(coffee_spot)
                return redirect(url_for("compare_screen"))

            elif button_pressed == "chosen":
                add_to_saved(coffee_spot)
                return redirect(url_for("saved_screen"))

        return render_template(
            "details.html",
            spot=coffee_spot,
            saved_page=saved_page,
            home_page=home_page,
            compare_page=compare_page
        )

    @app.route('/about')
    def about_screen():
        return render_template("about.html")

    def add_to_compare(coffee_spot):
        global compare_spots
        if coffee_spot is None:
            return
        
        if len(compare_spots) >= 3:
            return
        
        already_added = any(place["id"] == coffee_spot["id"] for place in compare_spots)

        if not already_added:
            compare_spots.append(coffee_spot)


    def add_to_saved(coffee_spot):
        global saved_spots

        if coffee_spot is None: return

        already_saved = any(place["id"] == coffee_spot["id"] for place in saved_spots)

        if not already_saved:
            saved_spots.append(coffee_spot)

    return app