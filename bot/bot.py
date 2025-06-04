import os
import re
import json
import asyncio
import logging
import aiohttp
from datetime import datetime
from collections import Counter, defaultdict
import time

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# Настройки
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE = os.path.join(BASE_DIR, "bot/data/user_data.json")
#VOTE_THRESHOLD = 2  # Минимальное количество голосов для подтверждения эмоции

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
    "confusion": {"ru": "замешательство", "en": "confusion"},
    "no_emotion": {"ru": "нет эмоции", "en": "no emotion"},
}

STICKER_PATHS = {
    "joy": {
        "ru": os.path.join(BASE_DIR, "bot/assets/ru/радость.gif"),
        "en": os.path.join(BASE_DIR, "bot/assets/en/joy.gif")
    },
    "sadness": {
        "ru": os.path.join(BASE_DIR, "bot/assets/ru/грусть.gif"),
        "en": os.path.join(BASE_DIR, "bot/assets/en/sadness.gif")
    },
    "anger": {
        "ru": os.path.join(BASE_DIR, "bot/assets/ru/гнев.gif"),
        "en": os.path.join(BASE_DIR, "bot/assets/en/anger.gif")
    },
    "fear": {
        "ru": os.path.join(BASE_DIR, "bot/assets/ru/страх.gif"),
        "en": os.path.join(BASE_DIR, "bot/assets/en/fear.gif")
    },
    "surprise": {
        "ru": os.path.join(BASE_DIR, "bot/assets/ru/удивление.gif"),
        "en": os.path.join(BASE_DIR, "bot/assets/en/surprise.gif")
    },
    "neutral": {
        "ru": os.path.join(BASE_DIR, "bot/assets/ru/нейтрально.gif"),
        "en": os.path.join(BASE_DIR, "bot/assets/en/neutral.gif")
    },
    "gratitude": {
        "ru": os.path.join(BASE_DIR, "bot/assets/ru/благодарность.gif"),
        "en": os.path.join(BASE_DIR, "bot/assets/en/gratitude.gif")
    },
    "excitement": {
        "ru": os.path.join(BASE_DIR, "bot/assets/ru/волнение.gif"),
        "en": os.path.join(BASE_DIR, "bot/assets/en/excitement.gif")
    },
    "love": {
        "ru": os.path.join(BASE_DIR, "bot/assets/ru/любовь.gif"),
        "en": os.path.join(BASE_DIR, "bot/assets/en/love.gif")
    },
    "loneliness": {
        "ru": os.path.join(BASE_DIR, "bot/assets/ru/одиночество.gif"),
        "en": os.path.join(BASE_DIR, "bot/assets/en/loneliness.gif")
    },
    "anticipation": {
        "ru": os.path.join(BASE_DIR, "bot/assets/ru/ожидание.gif"),
        "en": os.path.join(BASE_DIR, "bot/assets/en/anticipation.gif")
    },
    "disgust": {
        "ru": os.path.join(BASE_DIR, "bot/assets/ru/отвращение.gif"),
        "en": os.path.join(BASE_DIR, "bot/assets/en/disgust.gif")
    },
    "jealousy": {
        "ru": os.path.join(BASE_DIR, "bot/assets/ru/ревность.gif"),
        "en": os.path.join(BASE_DIR, "bot/assets/en/jealousy.gif")
    },
    "embarrassment": {
        "ru": os.path.join(BASE_DIR, "bot/assets/ru/смущение.gif"),
        "en": os.path.join(BASE_DIR, "bot/assets/en/embarrassment.gif")
    },
    "serenity": {
        "ru": os.path.join(BASE_DIR, "bot/assets/ru/спокойствие.gif"),
        "en": os.path.join(BASE_DIR, "bot/assets/en/serenity.gif")
    },
    "shame": {
        "ru": os.path.join(BASE_DIR, "bot/assets/ru/стыд.gif"),
        "en": os.path.join(BASE_DIR, "bot/assets/en/shame.gif")
    },
    "confusion": {
        "ru": os.path.join(BASE_DIR, "bot/assets/ru/замешательство.gif"),
        "en": os.path.join(BASE_DIR, "bot/assets/en/confusion.gif")
    },
    "no_emotion": {
        "ru": os.path.join(BASE_DIR, "bot/assets/ru/нет_эмоции.gif"),
        "en": os.path.join(BASE_DIR, "bot/assets/en/no_emotion.gif")}
    
}

class FeedbackStates(StatesGroup):
    waiting_for_feedback = State()
    waiting_for_emotion = State()

storage = MemoryStorage()
bot = Bot(token="8085305653:AAF9PT4PrItuach8YtY7DC-EL135qrQ3xwM", default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=storage)

# Глобальные переменные
user_history = {}
emotion_stats = {}
message_to_emotion = {}
user_votes = {}
user_last_request = defaultdict(float)

async def detect_emotion_api(text: str) -> dict:
    """Определяет эмоцию через API"""
    lang = detect_language(text)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "http://localhost:8001/predict",
                json={"text": text},
                timeout=3
            ) as response:
                data = await response.json()
                return {
                    "emotion": data["emotion"],
                    "confidence": data["confidence"],
                    "language": data["language"],
                    "label": data["label"]
                }
    except Exception as e:
        logger.error(f"API error: {e}")
        return {
            "emotion": "neutral",
            "confidence": 0.5,
            "language": lang,
            "label": EMOTIONS["neutral"][lang]
        }

def detect_language(text: str) -> str:
    return "ru" if re.search(r'[а-яё]', text.lower()) else "en"

def get_feedback_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👍 Подходит", callback_data="feedback_yes"),
         InlineKeyboardButton(text="👎 Не подходит", callback_data="feedback_no")]
    ])

def get_emotions_kb():
    buttons = []
    row = []
    for i, emotion in enumerate(EMOTIONS.keys()):
        row.append(InlineKeyboardButton(text=EMOTIONS[emotion]["ru"], callback_data=f"emotion_{emotion}"))
        if (i + 1) % 3 == 0:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def save_data():
    data = {
        "message_to_emotion": message_to_emotion,
        "user_history": user_history,
        "emotion_stats": {k: dict(v) for k, v in emotion_stats.items()},
        "user_votes": {k: dict(v) for k, v in user_votes.items()}
    }
    try:
        with open(DATA_FILE, "w", encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка сохранения данных: {e}")

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding='utf-8') as f:
                data = json.load(f)
                globals().update(data)
                emotion_stats.update({k: Counter(v) for k, v in data.get("emotion_stats", {}).items()})
                user_votes.update({k: Counter(v) for k, v in data.get("user_votes", {}).items()})
        except Exception as e:
            logger.error(f"Ошибка загрузки данных: {e}")

# Обработчики команд
@dp.message(Command("start"))
async def start(message: types.Message):
    """Обработчик команды /start"""
    await message.answer(
        "Hello! I'm an emotion detection bot.\n"
        "Привет! Я бот для определения эмоций.\n\n"
        "Currently, I am only good at defining emotions in English. The Russian language is under development.\n"
        "В настоящее время я хорошо определяю эмоции только на английском языке. Русский язык находится в разработке.\n\n"
        "If you have trouble with English, here's a very accurate translator:\n"
        "Если у вас проблемы с английским, вот очень точный переводчик:\n"
        "https://www.deepl.com/translator\n\n"
        "Send me a message in English and I'll detect the emotion in it!\n"
        "Отправьте мне сообщение на английском, и я определю эмоцию!"
    )

@dp.message(Command("help"))
async def help_command(message: types.Message):
    await message.answer(
        "Доступные команды:\n"
        "/start - Начало работы\n"
        "/help - Справка\n"
        "/stats - Ваша статистика стикеров\n"
	"/how_i_work - Как я работаю\n"
	"/history - Ваша история(последние 5 сообщений)\n"
        "Просто напишите сообщение для анализа!"
    )


@dp.message(Command("stats"))
async def show_stats(message: types.Message):
    user_id = str(message.from_user.id)
    
    if user_id not in user_history or not user_history[user_id]:
        await message.answer("У вас пока нет истории эмоций.")
        return
    
    # Собираем полную статистику по всем эмоциям
    emotion_counter = Counter()
    for entry in user_history[user_id]:
        emotion = entry["emotion"]
        emotion_counter[emotion] += 1
    
    total = sum(emotion_counter.values())
    lang = detect_language(message.text) if message.text else "ru"
    
    # Формируем сообщение с полной статистикой
    stats_text = "📊 <b>Полная статистика ваших эмоций:</b>\n\n"
    
    # Сортируем по убыванию частоты
    sorted_emotions = sorted(emotion_counter.items(), key=lambda x: x[1], reverse=True)
    
    for emotion, count in sorted_emotions:
        percentage = (count / total) * 100
        emotion_name = EMOTIONS.get(emotion, {}).get(lang, emotion)
        stats_text += f"• {emotion_name}: {count} ({percentage:.1f}%)\n"
    
    # Добавляем топ-3
    top_emotions = sorted_emotions[:3]
    if top_emotions:
        stats_text += "\n🏆 <b>Топ-3 эмоции:</b>\n"
        for i, (emotion, count) in enumerate(top_emotions, 1):
            emotion_name = EMOTIONS.get(emotion, {}).get(lang, emotion)
            stats_text += f"{i}. {emotion_name} - {count} раз\n"
    
    stats_text += f"\n<b>Всего анализов:</b> {total}"
    
    await message.answer(stats_text, parse_mode=ParseMode.HTML)

@dp.message(Command("history"))
async def show_history(message: types.Message):
    user_id = str(message.from_user.id)
    
    if user_id not in user_history or not user_history[user_id]:
        await message.answer("У вас пока нет истории запросов.")
        return
    
    lang = "ru"  # Или можно определить язык пользователя
    history_text = "🕒 <b>Последние 5 запросов:</b>\n\n"
    
    # Берем последние 5 записей
    last_entries = user_history[user_id][-5:][::-1]  # Новые сверху
    
    for i, entry in enumerate(last_entries, 1):
        emotion = entry["emotion"]
        text_preview = (
            entry["text"][:20] + "..." 
            if len(entry["text"]) > 20 
            else entry["text"]
        )
        timestamp = datetime.fromisoformat(entry["timestamp"]).strftime("%d.%m %H:%M")
        
        history_text += (
            f"{i}. <i>{text_preview}</i>\n"
            f"→ {EMOTIONS.get(emotion, {}).get(lang, emotion)}\n"
            f"<code>{timestamp}</code>\n\n"
        )
    
    await message.answer(history_text, parse_mode=ParseMode.HTML)


@dp.message(Command("how_i_work"))
async def how_i_work(message: types.Message):
    await message.answer(
        "🤖 <b>Как я работаю:</b>\n\n"
        "Я - бот для определения эмоций в тексте. Вот мои возможности:\n\n"
        "🔹 <b>Доступные команды:</b>\n"
        "/start - начать общение\n"
        "/help - краткая справка\n"
        "/stats - ваша персональная статистика эмоций\n"
        "/how_i_work - подробное описание моей работы\n\n"
        "🔹 <b>Как использовать:</b>\n"
        "Просто напишите мне сообщение, и я определю эмоцию.\n"
        "Вы можете подтвердить мой выбор или указать правильную эмоцию - это поможет мне стать точнее!\n\n"
        "🔹 <b>Система обратной связи:</b>\n"
        "Если я ошибся, нажмите 'Не подходит' и выберите верный вариант.\n"
        "Я запомню ваш выбор для этого текста на будущее.",
        parse_mode=ParseMode.HTML
    )


# Основной обработчик
@dp.message(F.text)
async def analyze(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    current_time = time.time()
    
    if current_time - user_last_request.get(user_id, 0) < 10:
        await message.answer("Пожалуйста, подождите 10 секунд перед следующим запросом.")
        return
    
    user_last_request[user_id] = current_time
    user_text = message.text.lower()
    
    # Проверяем, есть ли голосованные эмоции для этого текста
    if user_text in user_votes:
        votes = user_votes[user_text]
        
        # Если есть голоса, выбираем эмоцию с максимальным количеством
        if votes:
            max_emotion = max(votes, key=votes.get)
            lang = detect_language(user_text)
            sticker_path = STICKER_PATHS.get(max_emotion, {}).get(lang, "")
            
            if sticker_path and os.path.exists(sticker_path):
                with open(sticker_path, "rb") as f:
                    await message.answer_animation(
                        BufferedInputFile(f.read(), "sticker.gif"),
                        caption=f"На основе голосования: {EMOTIONS[max_emotion][lang]} (голосов: {votes[max_emotion]})"
                    )
            else:
                await message.answer(f"На основе голосования: {EMOTIONS[max_emotion][lang]} (голосов: {votes[max_emotion]})")
            return
    
    # Если нет подтвержденной эмоции, определяем через API
    emotion_data = await detect_emotion_api(message.text)
    
    # Сохраняем историю
    if user_id not in user_history:
        user_history[user_id] = []
    user_history[user_id].append({
        "text": message.text,
        "emotion": emotion_data["emotion"],
        "timestamp": datetime.now().isoformat()
    })
    
    # Отправляем результат с возможностью обратной связи
    sticker_path = STICKER_PATHS.get(emotion_data["emotion"], {}).get(emotion_data["language"], "")
    if sticker_path and os.path.exists(sticker_path):
        with open(sticker_path, "rb") as f:
            sent_message = await message.answer_animation(
                BufferedInputFile(f.read(), "sticker.gif"),
                caption=f"Я думаю, это {emotion_data['label']}...",
                reply_markup=get_feedback_kb()
            )
    else:
        sent_message = await message.answer(
            f"{emotion_data['label']} (уверенность: {emotion_data['confidence']:.0%})",
            reply_markup=get_feedback_kb()
        )
    
    await state.set_state(FeedbackStates.waiting_for_feedback)
    await state.set_data({
        "user_text": message.text.lower(),
        "original_emotion": emotion_data["emotion"],
        "message_id": sent_message.message_id
    })
    
    save_data()

# Обработчики обратной связи
@dp.callback_query(F.data.startswith("feedback_"))
async def handle_feedback(callback: types.CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    user_text = user_data.get("user_text", "")
    original_emotion = user_data.get("original_emotion", "")
    
    if callback.data == "feedback_yes":
        if user_text not in user_votes:
            user_votes[user_text] = Counter()
        user_votes[user_text][original_emotion] += 1
        
        votes = user_votes[user_text]
        max_emotion = max(votes, key=votes.get)
        lang = detect_language(user_text)
        
        # Только редактируем подпись, не удаляем сообщение
        await callback.message.edit_caption(
            caption=f"✅ Ваш голос учтён: {EMOTIONS[max_emotion][lang]} (голосов: {votes[max_emotion]})",
            reply_markup=None  # Убираем кнопки
        )
        await state.clear()

    elif callback.data == "feedback_no":
        await callback.message.edit_caption(
            "Какая эмоция подходит лучше?",
            reply_markup=get_emotions_kb()
        )
        await state.set_state(FeedbackStates.waiting_for_emotion)
    
    save_data()
    await callback.answer()

@dp.callback_query(F.data.startswith("emotion_"), FeedbackStates.waiting_for_emotion)
async def handle_emotion_choice(callback: types.CallbackQuery, state: FSMContext):
    selected_emotion = callback.data.split("_")[1]
    user_data = await state.get_data()
    user_text = user_data.get("user_text", "")
    original_emotion = user_data.get("original_emotion", "")
    message_id = user_data.get("message_id", "")
    
    if user_text not in user_votes:
        user_votes[user_text] = Counter()
    user_votes[user_text][selected_emotion] += 1
    
    votes = user_votes[user_text]
    lang = detect_language(user_text)
    
    # Удаляем предыдущий стикер только при изменении эмоции
    if selected_emotion != original_emotion:
        try:
            await bot.delete_message(chat_id=callback.message.chat.id, message_id=message_id)
        except Exception as e:
            logger.error(f"Ошибка при удалении сообщения: {e}")
        
        sticker_path = STICKER_PATHS.get(selected_emotion, {}).get(lang, "")
        if sticker_path and os.path.exists(sticker_path):
            with open(sticker_path, "rb") as f:
                await callback.message.answer_animation(
                    BufferedInputFile(f.read(), "sticker.gif"),
                    caption=f"✅ Спасибо за помощь! Благодаря вам, я стал умнее!\n"
                           f"Выбрано: {EMOTIONS[selected_emotion][lang]} (голосов: {votes[selected_emotion]})"
                )
        else:
            await callback.message.answer(
                f"✅ Спасибо за помощь! Благодаря вам, я стал умнее!\n"
                f"Выбрано: {EMOTIONS[selected_emotion][lang]} (голосов: {votes[selected_emotion]})"
            )
    else:
        # Если эмоция не изменилась, просто обновляем подпись
        await callback.message.edit_caption(
            caption=f"✅ Ваш голос учтён: {EMOTIONS[selected_emotion][lang]} (голосов: {votes[selected_emotion]})",
            reply_markup=None
        )
    
    await state.clear()
    save_data()
    await callback.answer()

# Запуск
async def on_startup():
    load_data()
    logger.info("Bot started")

async def on_shutdown():
    save_data()
    logger.info("Bot stopped")

if __name__ == "__main__":
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    asyncio.run(dp.start_polling(bot))