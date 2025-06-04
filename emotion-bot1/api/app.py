# app.py - FastAPI сервис для определения эмоций в тексте
from fastapi import FastAPI
from pydantic import BaseModel
from transformers import pipeline
import re
from typing import Dict
import os

app = FastAPI()

# Загрузка моделей для обработки текста
# Русская модель для определения эмоций
ru_model = pipeline(
    "text-classification",
    model="blanchefort/rubert-base-cased-sentiment"  
)
# Английская модель для определения эмоций
en_model = pipeline(
    "text-classification",
    model="SamLowe/roberta-base-go_emotions"
)
# Модель запроса - ожидает текст для анализа
class TextRequest(BaseModel):
    text: str
# Словарь соответствий эмоций на русском и английском
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
    # Обработка русского текста
    if lang == "ru":
        result = ru_model(text)[0]
        print(f"Raw RU model output: {result}")  # Логирование
        emotion = result["label"]
    else: # Обработка английского текста
        result = en_model(text)[0]
        print(f"Raw EN model output: {result}")  # Логирование
        emotion_map = { # Маппинг эмоций английской модели к нашим категориям
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
    
    print(f"Final emotion: {emotion}")  #Логирование итоговой эмоции
    localized_label = EMOTIONS.get(emotion, {}).get(lang, emotion)
    
    return {
        "emotion": emotion,  # Ключ эмоции
        "label": localized_label, # Локализованное название
        "confidence": result["score"], # Уверенность модели (0-1)
        "language": lang # Язык текста ("ru" или "en")
    }

if __name__ == "__main__":
    import uvicorn # Запуск сервера FastAPI
    uvicorn.run(app, host="0.0.0.0", port=8001)
