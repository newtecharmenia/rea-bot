import os
import json
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.client.default import DefaultBotProperties
from google_sheets import add_lead
from config import BOT_TOKEN, ADMIN_ID

# --- Загрузка Google credentials из переменной окружения ---
creds_json = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
if creds_json:
    creds = json.loads(creds_json)
else:
    creds = None
    logging.warning("⚠️ GOOGLE_APPLICATION_CREDENTIALS_JSON не найден. Проверь настройки окружения!")

logging.basicConfig(level=logging.INFO)

# --- Создание бота ---
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()


# Загружаем сценарии
with open("scenarios.json", "r", encoding="utf-8") as f:
    SCENES = json.load(f)

# Словарь для хранения состояния пользователя
user_state = {}
user_lang = {}

# Функция клавиатуры
def make_keyboard(options):
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=o)] for o in options],
        resize_keyboard=True
    )

# /start
@dp.message(CommandStart())
async def start(message: types.Message):
    kb = make_keyboard(["🇷🇺 Русский", "🇦🇲 Հայերեն"])
    await message.answer(SCENES["welcome"]["ru"], reply_markup=kb)

@dp.message(F.text.in_(["🇷🇺 Русский", "🇦🇲 Հայերեն"]))
async def set_language(message: types.Message):
    lang = "ru" if "Русский" in message.text else "hy"
    user_lang[message.from_user.id] = lang
    menu = SCENES["menu"][lang]["main"]
    await message.answer("Главное меню:" if lang == "ru" else "Գլխավոր մենյու․", reply_markup=make_keyboard(menu))

# Меню выбора
@dp.message(F.text)
async def menu_handler(message: types.Message):
    lang = user_lang.get(message.from_user.id, "ru")
    text = message.text

    # Курсы
    if "Курс" in text or "դասընթաց" in text:
        opts = SCENES["courses"][lang]["options"]
        await message.answer(SCENES["courses"][lang]["intro"], reply_markup=make_keyboard(opts))

    # Для новичков
    elif "новичков" in text or "Սկսնակ" in text:
        user_state[message.from_user.id] = "course_beginner"
        await message.answer(SCENES["courses"][lang]["beginner"], reply_markup=make_keyboard(["✅ Записаться" if lang=="ru" else "✅ Գրանցվել", "🔙 Назад" if lang=="ru" else "🔙 Վերադառնալ"]))

    # Для агентов
    elif "агентов" in text or "գործակալ" in text:
        user_state[message.from_user.id] = "course_agent"
        await message.answer(SCENES["courses"][lang]["agent"], reply_markup=make_keyboard(["✅ Записаться" if lang=="ru" else "✅ Գրանցվել", "🔙 Назад" if lang=="ru" else "🔙 Վերադառնալ"]))

    # Для инвесторов
    elif "инвесторов" in text or "ներդրող" in text:
        user_state[message.from_user.id] = "course_investor"
        await message.answer(SCENES["courses"][lang]["investor"], reply_markup=make_keyboard(["✅ Записаться" if lang=="ru" else "✅ Գրանցվել", "🔙 Назад" if lang=="ru" else "🔙 Վերադառնալ"]))

    # Записаться
    elif "Записаться" in text or "Գրանցվել" in text:
        user_state[message.from_user.id] = "collect_name"
        await message.answer(SCENES["courses"][lang]["signup"])

    elif user_state.get(message.from_user.id) == "collect_name":
        user_state[message.from_user.id] = {"name": message.text}
        await message.answer("Ваш город:" if lang=="ru" else "Ձեր քաղաքը:")

    elif isinstance(user_state.get(message.from_user.id), dict) and "name" in user_state[message.from_user.id] and "city" not in user_state[message.from_user.id]:
        user_state[message.from_user.id]["city"] = message.text
        await message.answer("Ваш номер телефона:" if lang=="ru" else "Ձեր հեռախոսահամարը:")

    elif isinstance(user_state.get(message.from_user.id), dict) and "city" in user_state[message.from_user.id] and "phone" not in user_state[message.from_user.id]:
        user_state[message.from_user.id]["phone"] = message.text
        state = user_state[message.from_user.id]
        course = "Beginner" if "course_beginner" in state.get("course", "course_beginner") else "Custom"
        add_lead(state["name"], state["city"], state["phone"], course)
        await message.answer(SCENES["courses"][lang]["thanks"])
        menu = SCENES["menu"][lang]["main"]
        await message.answer("Главное меню:" if lang=="ru" else "Գլխավոր մենյու․", reply_markup=make_keyboard(menu))
        user_state.pop(message.from_user.id, None)

    elif "менеджер" in text or "մենեջեր" in text:
        user_state[message.from_user.id] = "contact_manager"
        await message.answer(SCENES["manager"][lang])

    elif user_state.get(message.from_user.id) == "contact_manager":
        # Переслать админу
        await bot.send_message(ADMIN_ID, f"🆕 Новый запрос от @{message.from_user.username}:\n{text}")
        await message.answer(SCENES["manager"][f"thanks_{lang}"])
        user_state.pop(message.from_user.id, None)

    elif "FAQ" in text or "հարց" in text:
        q_list = list(SCENES["faq"][lang]["questions"].keys())
        await message.answer(SCENES["faq"][lang]["intro"], reply_markup=make_keyboard(q_list + ["🔙 Назад" if lang=="ru" else "🔙 Վերադառնալ"]))

    elif text in SCENES["faq"][lang]["questions"]:
        await message.answer(SCENES["faq"][lang]["questions"][text])

    elif "Назад" in text or "Վերադառնալ" in text:
        menu = SCENES["menu"][lang]["main"]
        await message.answer("Главное меню:" if lang=="ru" else "Գլխավոր մենյու․", reply_markup=make_keyboard(menu))

    else:
        await message.answer("Пожалуйста, выберите пункт меню ⬆️" if lang=="ru" else "Խնդրում ենք ընտրել մենյուի կետը ⬆️")

if __name__ == "__main__":
    import asyncio
    asyncio.run(dp.start_polling(bot))
