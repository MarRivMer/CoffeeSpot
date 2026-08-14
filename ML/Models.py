import numpy as np
import pandas as pd
import random
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import joblib
import torch
import torch.nn as nn


class CoffeeSpotMLP(nn.Module):
    """
    CoffeeSpotMLP: Basline Multi Layer model

    """
    def __init__(self, input_dim, hidden_dim=32, depth=2, output_dim=1, dropout=0.0):
        super().__init__()
        layers = []

        # input layer
        layers.append(nn.Linear(input_dim, hidden_dim))
        layers.append(nn.ReLU())

        # hidden layers
        for _ in range(depth - 1):
            layers.append(nn.Linear(hidden_dim, hidden_dim))
            layers.append(nn.ReLU())
            
            if dropout > 0:
                layers.append(nn.Dropout(dropout))

        # output layer
        layers.append(nn.Linear(hidden_dim, output_dim))

        self.net = nn.Sequential(*layers)

    def forward(self, x):
        return self.net(x)


def train_model(configs, n_epochs = 100):
    """
        Trains an MLP model, ensure that the traing/validate/split is already set before calling the func.

        Args:
            configs, n_epochs = 100

        Returns:
            Model, Training Loss, Val Loss
    """

    model = CoffeeSpotMLP(X_train.shape[1], configs['width'], configs['depth'], dropout=configs['dropout'])
    
    loss_fn = torch.nn.BCEWithLogitsLoss()
    if configs['optimizer'] == "sgd":
        optimizer = torch.optim.SGD(model.parameters(), configs['lr'])
    elif configs['optimizer'] == "adam":
        optimizer = torch.optim.Adam(model.parameters(), configs['lr'])
    else: 
        raise ValueError(f"Unknown optimizer: {configs['optimizer']}")

    for _ in range(n_epochs):
        model.train()
        optimizer.zero_grad()
        outputs = model(X_train)
        loss = loss_fn(outputs, y_train)
        loss.backward()
        optimizer.step()

    model.eval()
    with torch.no_grad():
        val_outputs = model(X_val)
        val_loss = loss_fn(val_outputs, y_val)

    return model, loss.item(), val_loss.item()

def predict(sample, model):
    """
    Inference Pipeline. Takes in a sample and the model to perform a prediction using the model.
    
    Args:
        sample, model
    
    Returns:
        int (prediction 0 or 1)
        probability: value between 0 and 1

    """

    sample = np.array(sample).reshape(1, -1)
    sample = torch.tensor(sample, dtype=torch.float32)

    model.eval()
    with torch.no_grad():
        output = model(sample)
        probability = torch.sigmoid(output)
        prediction = (probability >= 0.5).float()

    return (int(prediction.item()), float(probability.item()))


# ----- Supervised ML Training -----
if __name__ == '__main__':

    out_dir = 'ML/model_outputs/'

    configs = pd.DataFrame([
            {"depth": 2, "width": 16, "optimizer": "sgd", "lr":0.001, "dropout": 0.0},
            {"depth": 4, "width": 32, "optimizer": "sgd", "lr":0.01, "dropout": 0.2},
            {"depth": 4, "width": 64, "optimizer": "adam", "lr":0.001, "dropout": 0.0},
            {"depth": 6, "width": 128, "optimizer": "adam", "lr":0.01, "dropout": 0.5},
    ])

    # EDA 
    df = pd.read_csv('data/CoffeeShopDummyTrainingData.csv')
    print(df.head(10))
    df.info()
    print(df.describe())

    df = pd.get_dummies(df, columns=["price_level", "purpose"], dtype=int)


    # Setup Train/Test/Split for Model
    SEED = 1122
    torch.manual_seed(SEED)
    np.random.seed(SEED)
    random.seed(SEED)

    X = df.drop(columns=["chosen"])
    y = df["chosen"]
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=SEED)
    X_train, X_val, y_train, y_val = train_test_split(X_train, y_train, test_size=0.2, random_state=SEED)
    
    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_val = scaler.transform(X_val)
    X_test = scaler.transform(X_test)
    
    X_train = torch.from_numpy(X_train).float()
    X_val = torch.from_numpy(X_val).float()
    X_test = torch.from_numpy(X_test).float()
    
    y_train = torch.tensor(y_train.values).float().view(-1,1)
    y_val = torch.tensor(y_val.values).float().view(-1,1)
    y_test = torch.tensor(y_test.values).float().view(-1,1)

    # ----- Training -----
    results = []
    best_loss = float("inf")
    best_model = None
    loss_fn = nn.BCEWithLogitsLoss()
    
    for _, row in configs.iterrows():
        config = row.to_dict()
        model, train_loss, val_loss = train_model(config)

        model.eval()
        with torch.no_grad():
            outputs = model(X_test)
            predictions = (torch.sigmoid(outputs) >= 0.5).float()
            accuracy = (predictions == y_test).float().mean()

        config["train_loss"] = train_loss
        config["val_loss"] = val_loss
        config["test_accuracy"] = accuracy.item() * 100

        if val_loss < best_loss:
            best_loss = val_loss
            best_model = model

        results.append(config)

    # Save Results & Model
    results_df = pd.DataFrame(results).sort_values("val_loss")
    best_config = results_df.iloc[0]
    model_metadata = {
        "input_dim": X_train.shape[1],
        "hidden_dim": int(best_config["width"]),
        "depth": int(best_config["depth"]),
        "dropout": float(best_config["dropout"]),
        "test_accuracy": float(best_config['test_accuracy'])
    }

    torch.save(best_model.state_dict(), out_dir + "coffee_spot_model.pth")
    joblib.dump(scaler, out_dir + "scaler.pkl")
    joblib.dump(X.columns.tolist(), out_dir + "feature_columns.pkl")
    joblib.dump(model_metadata, out_dir + "model_metadata.pkl")

    print("Model and preprocessing files saved.")
    # print(results_df)
