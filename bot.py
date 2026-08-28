import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from aiogram.enums import ParseMode

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_GROUP_ID = int(os.getenv("ADMIN_GROUP_ID", "-1004342969244"))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def main_keyboard():
    kb = [[KeyboardButton(text="Найти вещь")]]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def request_keyboard():
    kb = [
        [
            InlineKeyboardButton(text="Взял в работу", callback_data="taken"),
            InlineKeyboardButton(text="Закрыл", callback_data="closed")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "Привет! Я помогу найти нужную вещь.\n\nНажми кнопку ниже и пришли фото или название:",
        reply_markup=main_keyboard()
    )

@dp.message(F.text == "Найти вещь")
async def find_item(message: Message):
    await message.answer(
        "Пришли фото вещи или просто напиши название/описание.\nЯ передам запрос, и тебе ответят в личные сообщения.",
        reply_markup=ReplyKeyboardRemove()
    )

@dp.message(F.photo | F.text)
async def handle_request(message: Message):
    user = message.from_user
    username = f"@{user.username}" if user.username else "нет юзернейма"
    user_link = f"<a href='tg://user?id={user.id}'>{user.full_name}</a>"

    caption = (
        f"<b>Новая заявка</b>\n\n"
        f"От: {user_link}\n"
        f"Юзернейм: {username}\n"
        f"ID: <code>{user.id}</code>\n\n"
    )

    if message.text and message.text != "Найти вещь":
        caption += f"Текст: {message.text}"
    else:
        caption += "Прислал фото"

    try:
        if message.photo:
            await bot.send_photo(
                chat_id=ADMIN_GROUP_ID,
                photo=message.photo[-1].file_id,
                caption=caption,
                parse_mode=ParseMode.HTML,
                reply_markup=request_keyboard()
            )
        else:
            await bot.send_message(
                chat_id=ADMIN_GROUP_ID,
                text=caption,
                parse_mode=ParseMode.HTML,
                reply_markup=request_keyboard()
            )

        await message.answer("Принял, ищем.\nОтвет придёт тебе в личные сообщения в ближайшее время.")

    except Exception as e:
        await message.answer("Произошла ошибка, попробуй позже.")
        logging.error(f"Ошибка: {e}")

@dp.callback_query(F.data == "taken")
async def process_taken(callback: CallbackQuery):
    await callback.answer("Заявка взята в работу")
    new_text = (callback.message.caption or callback.message.text) + "\n\n🟡 <b>Статус: В работе</b>"
    
    if callback.message.photo:
        await callback.message.edit_caption(caption=new_text, parse_mode=ParseMode.HTML, reply_markup=request_keyboard())
    else:
        await callback.message.edit_text(text=new_text, parse_mode=ParseMode.HTML, reply_markup=request_keyboard())

@dp.callback_query(F.data == "closed")
async def process_closed(callback: CallbackQuery):
    await callback.answer("Заявка закрыта")
    new_text = (callback.message.caption or callback.message.text) + "\n\n✅ <b>Статус: Закрыта</b>"
    
    if callback.message.photo:
        await callback.message.edit_caption(caption=new_text, parse_mode=ParseMode.HTML, reply_markup=None)
    else:
        await callback.message.edit_text(text=new_text, parse_mode=ParseMode.HTML, reply_markup=None)

async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
