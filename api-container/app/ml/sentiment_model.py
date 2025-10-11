from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from typing import Optional

try:  # pragma: no cover - optional dependency
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
except ImportError:  # pragma: no cover
    TfidfVectorizer = None  # type: ignore
    LogisticRegression = None  # type: ignore


@dataclass
class SentimentResult:
    probability_positive: float
    label: str


class SentimentModel:
    _model: Optional["LogisticRegression"] = None
    _vectorizer: Optional["TfidfVectorizer"] = None
    _lock: Lock = Lock()

    @classmethod
    def _ensure_model(cls) -> None:
        if TfidfVectorizer is None or LogisticRegression is None:
            cls._model = None
            cls._vectorizer = None
            return

        if cls._model is not None and cls._vectorizer is not None:
            return

        with cls._lock:
            if cls._model is not None and cls._vectorizer is not None:
                return

            training_texts = [
                "I love spending time with you",
                "You make me so happy",
                "Today was wonderful",
                "Feeling grateful for our call",
                "Can't wait to see you",
                "That was amazing",
                "You are the best",
                "Feeling excited for tonight",
                "Thank you for being supportive",
                "Our date was perfect",
                "I'm really stressed right now",
                "Today was awful",
                "I'm upset about what happened",
                "Feeling sad and lonely",
                "This is frustrating",
                "I am worried about the future",
                "That hurt my feelings",
                "I'm really angry",
                "Nothing seems to go right",
                "Feeling tired and disappointed",
            ]
            training_labels = [1] * 10 + [0] * 10

            vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1)
            features = vectorizer.fit_transform(training_texts)

            model = LogisticRegression(max_iter=2000)
            model.fit(features, training_labels)

            cls._model = model
            cls._vectorizer = vectorizer

    @classmethod
    def predict(cls, text: str) -> SentimentResult:
        cls._ensure_model()

        if cls._model is None or cls._vectorizer is None:
            lowered = text.lower()
            positive_words = {
                "love",
                "happy",
                "great",
                "excited",
                "grateful",
                "proud",
                "amazing",
                "wonderful",
                "appreciate",
                "best",
            }
            negative_words = {
                "sad",
                "angry",
                "upset",
                "tired",
                "frustrated",
                "worried",
                "anxious",
                "awful",
                "depressed",
                "lonely",
            }
            positive_hits = sum(1 for w in positive_words if w in lowered)
            negative_hits = sum(1 for w in negative_words if w in lowered)
            score = positive_hits - negative_hits
            if score > 0:
                label = "positive"
                probability = 0.75
            elif score < 0:
                label = "negative"
                probability = 0.25
            else:
                label = "neutral"
                probability = 0.5
            return SentimentResult(probability_positive=probability, label=label)

        assert cls._vectorizer is not None

        features = cls._vectorizer.transform([text])
        probability_positive = float(cls._model.predict_proba(features)[0][1])

        if probability_positive >= 0.6:
            label = "positive"
        elif probability_positive <= 0.4:
            label = "negative"
        else:
            label = "neutral"

        return SentimentResult(probability_positive=probability_positive, label=label)
