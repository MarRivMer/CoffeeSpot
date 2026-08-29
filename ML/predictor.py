import joblib
import pandas as pd
import torch

from ML.Models import CoffeeSpotMLP, predict

# ----- Load Model -----
model_outputs_dir = 'ML/model_outputs/'
scaler = joblib.load(model_outputs_dir + "scaler.pkl")
feature_columns = joblib.load(model_outputs_dir + "feature_columns.pkl")
metadata = joblib.load(model_outputs_dir + "model_metadata.pkl")
model = CoffeeSpotMLP(
    input_dim=metadata["input_dim"],
    hidden_dim=metadata["hidden_dim"],
    depth=metadata["depth"],
    dropout=metadata["dropout"]
)
model.load_state_dict(torch.load(model_outputs_dir + "coffee_spot_model.pth", weights_only=True))

model.eval()

NUMERIC_COLUMNS = [
    "rating",
    "review_count",
    "hours_until_close",
    "travel_time_minutes"
]

def predict_coffee_spot(coffee_spot_search_sample):
    # ----- EDA Sample Data -----
    df = pd.DataFrame([coffee_spot_search_sample])
    df["price_level"] = (df["price_level"].fillna("MODERATE").str.replace("PRICE_LEVEL_","", regex=False))
    df = pd.get_dummies(df, columns=["price_level", "purpose"], dtype=int)
    for column in feature_columns:
        if column not in df.columns:
            df[column] = 0

    df = df[feature_columns]
    df_scaled = scaler.transform(df)
    prepared_sample = df_scaled[0]

    
    # ----- Predict -----
    prediction, probability = predict(prepared_sample, model)
    match_score = probability * 100

    return prediction, match_score

