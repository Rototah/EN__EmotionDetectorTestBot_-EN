from fastapi import FastAPI
from pydantic import BaseModel
from transformers import pipeline
import re
from typing import Dict
import os

app = FastAPI()

# Загрузка моделей
ru_model = pipeline(
    "text-classification",
    model="blanchefort/rubert-base-cased-sentiment"  
)
en_model = pipeline(
    "text-classification",
    model="SamLowe/roberta-base-go_emotions"
)

class TextRequest(BaseModel):
    text: str

EMOTIONS = {
    "joy": {"ru": "радость", "en": "joy"},
    "sadness": {"ru": "грусть", "en": "sadness"},
    "anger": {"ru": "гнев", "en": "anger"},
    "fear": {"ru": "страх", "en": "fear"},
    "surprise": {"ru": "удивление", "en": "surprise"},
    "neutral": {"ru": "нейтрально", "en": "neutral"},
    "gratitude": {"ru": "благодарность", "en": "gratitude"},
    "excitement": {"ru": "волнение", "en": "excitement"},
    "love": {"ru": "любовь", "en": "love"},
    "loneliness": {"ru": "одиночество", "en": "loneliness"},
    "anticipation": {"ru": "ожидание", "en": "anticipation"},
    "disgust": {"ru": "отвращение", "en": "disgust"},
    "jealousy": {"ru": "ревность", "en": "jealousy"},
    "embarrassment": {"ru": "смущение", "en": "embarrassment"},
    "serenity": {"ru": "спокойствие", "en": "serenity"},
    "shame": {"ru": "стыд", "en": "shame"},
    "confusion": {"ru": "замешательство", "en": "confusion"}
}

def detect_language(text: str) -> str:
    return "ru" if re.search(r'[а-яё]', text.lower()) else "en"

@app.post("/predict")
def predict(request: TextRequest):
    text = request.text
    lang = detect_language(text)
    
    if lang == "ru":
        result = ru_model(text)[0]
        print(f"Raw RU model output: {result}")  # Логирование
        emotion = result["label"]
    else:
        result = en_model(text)[0]
        print(f"Raw EN model output: {result}")  # Логирование
        emotion_map = {
            "admiration": "gratitude",
            "amusement": "joy",
            "anger": "anger",
            "annoyance": "anger",
            "approval": "gratitude",
            "caring": "love",
            "confusion": "confusion",
            "curiosity": "excitement",
            "desire": "love",
	    "disappointment": "sadness",
            "disapproval": "anger",
            "disgust": "disgust",
            "embarrassment": "embarrassment",
            "excitement": "excitement",
            "fear": "fear",
            "gratitude": "gratitude",
            "grief": "sadness",
            "joy": "joy",
            "love": "love",
            "nervousness": "fear",
            "optimism": "joy",
            "pride": "joy",
            "realization": "surprise",
            "relief": "serenity",
            "remorse": "shame",
            "sadness": "sadness",
            "surprise": "surprise",
            "neutral": "neutral"
        }
        emotion = emotion_map.get(result['label'], "neutral")
    
    print(f"Final emotion: {emotion}")  # Логирование
    localized_label = EMOTIONS.get(emotion, {}).get(lang, emotion)
    
    return {
        "emotion": emotion,
        "label": localized_label,
        "confidence": result["score"],
        "language": lang
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)