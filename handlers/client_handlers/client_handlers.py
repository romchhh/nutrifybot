from aiogram import Router, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardRemove

from Content.texts import get_greeting_message, profile_ask_name, registration_intro_welcome
from database_functions.client_db import (
    add_user,
    check_user,
    is_registration_complete,
    update_user_activity,
)
from database_functions.create_dbs import create_dbs
from database_functions.links_db import increment_link_count
from keyboards.client_keyboards import get_start_keyboard
from main import bot
from states.client_states import Registration
from utils.nutrition_kb import init_knowledge_base

router = Router()


@router.message(CommandStart()) 
async def start_command(message: types.Message, state: FSMContext):
    user = message.from_user
    user_id = user.id
    username = user.username
    args = message.text.split()

    user_exists = check_user(user_id)

    ref_link = None
    if len(args) > 1 and args[1].startswith("linktowatch_"):
        try:
            ref_link = int(args[1].split("_")[1])
            if not user_exists:
                increment_link_count(ref_link)
        except (ValueError, IndexError):
            pass

    if not user_exists:
        add_user(user_id, username, user.first_name, user.last_name, user.language_code, ref_link)

    update_user_activity(user_id)

    if not is_registration_complete(user_id):
        await state.set_state(Registration.name)
        await message.answer(
            registration_intro_welcome(),
            parse_mode="HTML",
            reply_markup=ReplyKeyboardRemove(),
        )
        await message.answer(profile_ask_name(), parse_mode="HTML")
        return

    start_keyboard = get_start_keyboard(user_id)
    await message.answer(
        get_greeting_message(),
        parse_mode="HTML",
        reply_markup=start_keyboard,
    )


async def on_startup(router):
    me = await bot.get_me()
    create_dbs()
    init_knowledge_base()

    print(f"Bot: @{me.username} запущений!")


async def on_shutdown(router):
    me = await bot.get_me()
    print(f"Bot: @{me.username} зупинений!")
