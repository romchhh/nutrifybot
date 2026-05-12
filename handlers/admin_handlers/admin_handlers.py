from aiogram import F, Router, types
from aiogram.types import FSInputFile
from main import bot
from utils.filters import IsAdmin
from aiogram.fsm.context import FSMContext
from keyboards.client_keyboards import get_start_keyboard
from keyboards.admin_keyboards import admin_keyboard, get_export_database_keyboard
from Content.texts import get_greeting_message
from utils.admin_functions import generate_database_export, format_statistics_message
from datetime import datetime
import os


router = Router()


@router.message(IsAdmin(), F.text.in_(["👨‍💻 Адмін панель", "Адмін панель 💻", "/admin"]))
async def admin_panel(message: types.Message):
    await message.answer("Вітаю в адмін панелі. Ось ваші доступні опції.", reply_markup=admin_keyboard())
    
    
@router.message(IsAdmin(), F.text.in_(["Головне меню"]))
async def my_parcel(message: types.Message, state: FSMContext):
    user = message.from_user
    user_id = message.from_user.id
    keyboard = get_start_keyboard(user_id)
    greeting_message = get_greeting_message()
    await message.answer(greeting_message, reply_markup=keyboard, parse_mode="HTML")
    
    
@router.message(IsAdmin(), F.text.in_(["Статистика"]))
async def statistic_handler(message: types.Message):
    response_message = format_statistics_message()
    await message.answer(response_message, parse_mode="HTML", reply_markup=get_export_database_keyboard())
  
        
@router.callback_query(IsAdmin(), F.data == "export_database")
async def export_database(callback: types.CallbackQuery):
    response_message = (
            "<b>ВИГРУЗКА БАЗИ ДАНИХ</b>\n\n"
            f"Зачекайте поки ми сформуємо ексель файл з базою даних"
        )
    await callback.message.answer(response_message, parse_mode="HTML")
    
    filename, users_count, links_count = generate_database_export()
    
    file = FSInputFile(filename)
    await bot.send_document(
        callback.message.chat.id, 
        document=file, 
        caption=f"📊 База даних експортована\n\n"
                f"👥 Користувачів: {users_count}\n"
                f"🔗 Посилань: {links_count}\n"
                f"📅 Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    )
    
    if os.path.exists(filename):
        os.remove(filename)