import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.multiclass import OneVsRestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline, FeatureUnion
from sklearn.metrics import classification_report, confusion_matrix

from backend.config import TRAINING_DATA_PATH, CLASSIFIER_PATH, ML_RANDOM_SEED

def main():
    print(f"Loading data from {TRAINING_DATA_PATH}...")
    try:
        df = pd.read_csv(TRAINING_DATA_PATH)
    except FileNotFoundError:
        print("Training data not found. Please ensure it exists.")
        return
        
    X = df['text']
    y = df['label']

    print("Splitting data into train/test (80/20)...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=ML_RANDOM_SEED
    )

    print("Building TF-IDF features and model pipeline...")
    pipeline = Pipeline([
        ('features', FeatureUnion([
            ('word_tfidf', TfidfVectorizer(analyzer='word', ngram_range=(1, 2))),
            ('char_tfidf', TfidfVectorizer(analyzer='char', ngram_range=(3, 5)))
        ])),
        ('clf', OneVsRestClassifier(LogisticRegression(
            random_state=ML_RANDOM_SEED,
            class_weight='balanced'
        )))
    ])

    print("Training model...")
    pipeline.fit(X_train, y_train)

    print("Evaluating model...")
    y_pred = pipeline.predict(X_test)
    
    print("\n=== Classification Report ===")
    print(classification_report(y_test, y_pred))
    
    print("\n=== Confusion Matrix ===")
    print(confusion_matrix(y_test, y_pred))

    print(f"\nSaving model to {CLASSIFIER_PATH}...")
    CLASSIFIER_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, CLASSIFIER_PATH)
    print("Done!")

if __name__ == "__main__":
    main()
