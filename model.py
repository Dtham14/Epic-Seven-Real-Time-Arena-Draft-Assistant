import pandas as pd
import numpy as np
import pickle
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

# Try to load pre-trained model
_model_data = None

def load_model():
    global _model_data
    if _model_data is None:
        try:
            with open('e7_data/trained_model.pkl', 'rb') as f:
                _model_data = pickle.load(f)
            print("Loaded pre-trained model")
        except FileNotFoundError:
            print("Pre-trained model not found, will train on demand")
            _model_data = None
    return _model_data

def getModel(draft):
    """
    Predict win probability for a draft.
    draft: list of 16 hero names in order:
        enemy1, main1, enemy2, main2, enemy3, main3, enemy4, main4,
        enemy5, main5, main_pre_b1, enemy_pre_b1, main_pre_b2, enemy_pre_b2,
        main_post_b, enemy_post_b
    """
    model_data = load_model()

    if model_data is not None:
        # Use pre-trained model
        model = model_data['model']
        label_encoders = model_data['label_encoders']
        scaler = model_data['scaler']
        columns = model_data['columns']

        # Prepare input
        draft_with_first = draft + ["0"]  # is_first = 0
        col_names = ['enemy1', 'main1', 'enemy2', 'main2', 'enemy3', 'main3',
                     'enemy4', 'main4', 'enemy5', 'main5', 'main_pre_b1', 'enemy_pre_b1',
                     'main_pre_b2', 'enemy_pre_b2', 'main_post_b', 'enemy_post_b', 'is_first']

        draft_df = pd.DataFrame([draft_with_first], columns=col_names)

        # Encode using the saved label encoders
        for column in draft_df.columns:
            if column in label_encoders:
                draft_df[column] = draft_df[column].astype(str)
                # Handle unseen labels
                le = label_encoders[column]
                draft_df[column] = draft_df[column].apply(
                    lambda x: le.transform([x])[0] if x in le.classes_ else 0
                )
            elif draft_df[column].dtype == 'object':
                draft_df[column] = 0

        # Ensure columns match training order
        draft_df = draft_df[columns]

        # Scale
        X_sample = scaler.transform(draft_df)

        # Predict
        prediction = model.predict(X_sample)
        return prediction
    else:
        # Fallback: train on the fly (slower)
        return train_and_predict(draft)

def train_and_predict(draft):
    """Fallback: train model on the fly if pre-trained model not available"""
    file_path = "e7_data/drafts_dataset.csv"
    df = pd.read_csv(file_path)

    # Fill missing values
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].fillna('None')

    draft.append("0")
    col_names = ['enemy1', 'main1', 'enemy2', 'main2', 'enemy3', 'main3',
                 'enemy4', 'main4', 'enemy5', 'main5', 'main_pre_b1', 'enemy_pre_b1',
                 'main_pre_b2', 'enemy_pre_b2', 'main_post_b', 'enemy_post_b', 'is_first']
    draft_df = pd.DataFrame(np.array(draft).reshape(1, 17), columns=col_names)

    y = df.iloc[:, -1]
    X = df.iloc[:, :-1]

    label_encoders = {}
    X_draft = draft_df
    X = pd.concat([X_draft, X], ignore_index=True)

    for column in X.select_dtypes(include=['object']).columns:
        label_encoders[column] = LabelEncoder()
        X[column] = X[column].astype(str)
        X[column] = label_encoders[column].fit_transform(X[column]) + 1

    first_row = X.iloc[0]
    X = X[1:]

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, y, test_size=0.3, random_state=42)

    model = LogisticRegression(max_iter=1000)
    model.fit(X_train, y_train)

    X_sample = np.array(first_row).reshape(1, -1)
    win_prob = model.predict(X_sample)

    return win_prob
