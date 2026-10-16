import asyncio
import logging
import os
import time
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton, ReplyKeyboardMarkup
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

BOT_TOKEN = "8768803904:AAHBB7IypN65IXC4SpWgTMK0tWHYXvlw58E"
ADMIN_GROUP_ID = int(os.getenv("ADMIN_GROUP_ID", "-1004342969244"))

# Включаем HTML по умолчанию для всех сообщений бота
bot = Bot(
    token=BOT_TOKEN, 
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

# Защита от спама (30 секунд)
spam_protection = {}

class SearchState(StatesGroup):
    waiting_for_brand = State()
    waiting_for_custom_brand = State()
    waiting_for_budget = State()
    waiting_for_photo_desc = State()

def main_keyboard():
    kb = [[KeyboardButton(text="🔍 Найти вещь")]]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def cancel_keyboard():
    kb = [[InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_search")]]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def request_keyboard(user_id: int):
    kb = [
        [
            InlineKeyboardButton(text="🟡 Взял в работу", callback_data=f"taken_{user_id}"),
            InlineKeyboardButton(text="✅ Закрыл", callback_data=f"closed_{user_id}")
        ],
        [
            InlineKeyboardButton(text="💬 Написать клиенту", url=f"tg://user?id={user_id}")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def brand_keyboard():
    kb = [
        [InlineKeyboardButton(text="Derschutze", callback_data="brand_derschutze")],
        [InlineKeyboardButton(text="Vescartes", callback_data="brand_vescartes")],
        [InlineKeyboardButton(text="Alpha Industries", callback_data="brand_alpha")],
        [InlineKeyboardButton(text="✏️ Другой бренд (вписать)", callback_data="brand_other")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_search")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def budget_keyboard():
    kb = [
        [InlineKeyboardButton(text="До 5 000 ₽", callback_data="budget_low")],
        [InlineKeyboardButton(text="5 000 – 15 000 ₽", callback_data="budget_mid")],
        [InlineKeyboardButton(text="Более 15 000 ₽", callback_data="budget_high")],
        [InlineKeyboardButton(text="Любой / Не важно", callback_data="budget_any")],
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_brand"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_search")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def photo_desc_keyboard():
    kb = [
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_budget"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_search")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

@dp.callback_query(F.data == "cancel_search")
async def cancel_handler(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Поиск отменен. Если захотите найти вещь — нажмите кнопку внизу.")
    await callback.answer()

@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Привет! Я помогу найти нужную вещь.\n\nНажми кнопку ниже, чтобы начать подбор:",
        reply_markup=main_keyboard()
    )

@dp.message(F.text == "🔍 Найти вещь")
async def find_item(message: Message, state: FSMContext):
    user_id = message.from_user.id
    current_time = time.time()
    
    if user_id in spam_protection and current_time - spam_protection[user_id] < 30:
        left_time = int(30 - (current_time - spam_protection[user_id]))
        await message.answer(f"⏳ Пожалуйста, подождите еще {left_time} сек. перед отправкой нового запроса.")
        return

    spam_protection[user_id] = current_time
    
    await state.set_state(SearchState.waiting_for_brand)
    await message.answer(
        "🏷 <b>Шаг 1 из 3:</b> Выберите бренд или нажмите «✏️ Другой бренд»:",
        reply_markup=brand_keyboard()
    )

@dp.callback_query(F.data == "back_to_brand")
async def back_to_brand(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SearchState.waiting_for_brand)
    await callback.message.edit_text(
        "🏷 <b>Шаг 1 из 3:</b> Выберите бренд или нажмите «✏️ Другой бренд»:",
        reply_markup=brand_keyboard()
    )
    await callback.answer()

@dp.callback_query(SearchState.waiting_for_brand, F.data.startswith("brand_"))
async def process_brand(callback: CallbackQuery, state: FSMContext):
    if callback.data == "brand_other":
        await state.set_state(SearchState.waiting_for_custom_brand)
        await callback.message.edit_text(
            "✏️ Напишите название бренда вручную ответным сообщением:",
            reply_markup=cancel_keyboard()
        )
        await callback.answer()
        return

    brand_map = {
        "brand_derschutze": "Derschutze",
        "brand_vescartes": "Vescartes",
        "brand_alpha": "Alpha Industries"
    }
    selected_brand = brand_map.get(callback.data, "Не указан")
    await state.update_data(brand=selected_brand)
    
    await state.set_state(SearchState.waiting_for_budget)
    await callback.message.edit_text(
        f"🏷 Бренд: <b>{selected_brand}</b>\n\n"
        "💰 <b>Шаг 2 из 3:</b> Укажите ваш бюджет:",
        reply_markup=budget_keyboard()
    )
    await callback.answer()

@dp.message(SearchState.waiting_for_custom_brand, F.text)
async def process_custom_brand(message: Message, state: FSMContext):
    selected_brand = message.text.strip()
    await state.update_data(brand=selected_brand)
    
    await state.set_state(SearchState.waiting_for_budget)
    await message.answer(
        f"🏷 Бренд: <b>{selected_brand}</b>\n\n"
        "💰 <b>Шаг 2 из 3:</b> Укажите ваш бюджет:",
        reply_markup=budget_keyboard()
    )

@dp.callback_query(F.data == "back_to_budget")
async def back_to_budget(callback: CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    brand = user_data.get("brand", "Не указан")
    
    await state.set_state(SearchState.waiting_for_budget)
    await callback.message.edit_text(
        f"🏷 Бренд: <b>{brand}</b>\n\n"
        "💰 <b>Шаг 2 из 3:</b> Укажите ваш бюджет:",
        reply_markup=budget_keyboard()
    )
    await callback.answer()

@dp.callback_query(SearchState.waiting_for_budget, F.data.startswith("budget_"))
async def process_budget(callback: CallbackQuery, state: FSMContext):
    budget_map = {
        "budget_low": "До 5 000 ₽",
        "budget_mid": "5 000 – 15 000 ₽",
        "budget_high": "Более 15 000 ₽",
        "budget_any": "Любой / Не важно"
    }
    selected_budget = budget_map.get(callback.data, "Не указан")
    await state.update_data(budget=selected_budget)
    
    await state.set_state(SearchState.waiting_for_photo_desc)
    await callback.message.edit_text(
        f"💰 Бюджет: <b>{selected_budget}</b>\n\n"
        "📸 <b>Шаг 3 из 3:</b> Пришлите фото вещи или напишите её название, размер и описание:",
        reply_markup=photo_desc_keyboard()
    )
    await callback.answer()

@dp.message(SearchState.waiting_for_photo_desc, F.photo | F.text)
async def handle_request(message: Message, state: FSMContext):
    user_data = await state.get_data()
    brand = user_data.get("brand", "Не указан")
    budget = user_data.get("budget", "Не указан")
    
    user = message.from_user
    username = f"@{user.username}" if user.username else "нет юзернейма"
    user_link = f"<a href='tg://user?id={user.id}'>{user.full_name}</a>"
    
    caption = (
        f"🔥 <b>Новая заявка на поиск!</b>\n\n"
        f"👤 <b>Клиент:</b> {user_link}\n"
        f"🔗 <b>Юзернейм:</b> {username}\n"
        f"🆔 <b>ID:</b> <code>{user.id}</code>\n\n"
        f"🏷 <b>Бренд:</b> {brand}\n"
        f"💰 <b>Бюджет:</b> {budget}\n"
    )
    
    if message.text:
        caption += f"📝 <b>Описание/Размер:</b> {message.text}"
    else:
        caption += f"📝 <b>Описание:</b> Прислал фото (без текста)"

    try:
        if message.photo:
            await bot.send_photo(
                chat_id=ADMIN_GROUP_ID,
                photo=message.photo[-1].file_id,
                caption=caption,
                reply_markup=request_keyboard(user.id)
            )
        else:
            await bot.send_message(
                chat_id=ADMIN_GROUP_ID,
                text=caption,
                reply_markup=request_keyboard(user.id)
            )
        
        await message.answer(
            "✅ <b>Заявка принята!</b>\nМы уже ищем ваш вариант и скоро ответим вам в личные сообщения.",
            reply_markup=main_keyboard()
        )
    except Exception as e:
        await message.answer("Произошла ошибка при отправке заявки, попробуйте позже.", reply_markup=main_keyboard())
        logging.error(f"Ошибка отправки в группу: {e}")
    
    await state.clear()

@dp.callback_query(F.data.startswith("taken_"))
async def process_taken(callback: CallbackQuery):
    user_id = int(callback.data.split("_")[1])
    new_text = (callback.message.caption or callback.message.text) + "\n\n🟡 <b>Статус: В работе</b>"
    
    if callback.message.photo:
        await callback.message.edit_caption(caption=new_text, reply_markup=request_keyboard(user_id))
    else:
        await callback.message.edit_text(text=new_text, reply_markup=request_keyboard(user_id))
    
    await callback.answer("Заявка взята в работу")

    try:
        await bot.send_message(
            chat_id=user_id,
            text="🟡 <b>Обновление по вашей заявке:</b>\nМенеджер взял ваш запрос в работу! Скоро свяжемся с вами."
        )
    except Exception as e:
        logging.error(f"Не удалось отправить ЛС пользователю {user_id}: {e}")

@dp.callback_query(F.data.startswith("closed_"))
async def process_closed(callback: CallbackQuery):
    user_id = int(callback.data.split("_")[1])
    new_text = (callback.message.caption or callback.message.text) + "\n\n✅ <b>Статус: Закрыта</b>"
    
    if callback.message.photo:
        await callback.message.edit_caption(caption=new_text, reply_markup=None)
    else:
        await callback.message.edit_text(text=new_text, reply_markup=None)
    
    await callback.answer("Заявка закрыта")

    try:
        await bot.send_message(
            chat_id=user_id,
            text="✅ <b>Ваша заявка обработана и закрыта.</b>\nСпасибо за обращение!"
        )
    except Exception as e:
        logging.error(f"Не удалось отправить ЛС пользователю {user_id}: {e}")

async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
