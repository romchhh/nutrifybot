from datetime import date, timedelta

from aiogram import Router, F, types
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from Content.texts import (
    msg_enter_age_invalid,
    msg_enter_age_number,
    msg_enter_height_number,
    msg_enter_height_range,
    msg_enter_name_plain,
    msg_enter_weight_number,
    msg_enter_weight_range,
    msg_need_registration,
    msg_profile_missing,
    profile_ask_age,
    profile_ask_goal,
    profile_ask_height,
    profile_ask_name,
    profile_ask_sex_prompt,
    profile_ask_weight,
    profile_saved,
    profile_view,
)
from database_functions.client_db import get_user_profile, is_registration_complete, save_profile_and_norm
from keyboards.client_keyboards import get_start_keyboard, goal_keyboard, profile_edit_keyboard, sex_keyboard
from states.client_states import ProfileEdit
from utils.nutrition_calculator import calculate_daily_norm

router = Router()


def _sex_label(sex: str | None) -> str:
    if sex == "male":
        return "чол"
    return "жін"


def _goal_label(goal: str) -> str:
    return {"lose": "Схуднення", "maintain": "Підтримка ваги", "gain": "Набір маси"}.get(goal, goal)


@router.message(F.text == "👤 Профіль", StateFilter(None))
async def profile_open(message: types.Message):
    if not is_registration_complete(message.from_user.id):
        await message.answer(msg_need_registration(), parse_mode="HTML")
        return
    row = get_user_profile(message.from_user.id)
    if not row or not row.get("display_name"):
        await message.answer(msg_profile_missing(), parse_mode="HTML")
        return
    await message.answer(
        profile_view(
            row["display_name"],
            row["age"],
            _sex_label(row["sex"]),
            row["weight"],
            row["height"],
            _goal_label(row["goal"]),
            row["daily_calories"],
            row["daily_protein"],
            row["daily_fat"],
            row["daily_carbs"],
        ),
        parse_mode="HTML",
        reply_markup=profile_edit_keyboard(),
    )


@router.callback_query(StateFilter(None), F.data == "profile_edit_start")
async def profile_edit_start(callback: types.CallbackQuery, state: FSMContext):
    if not is_registration_complete(callback.from_user.id):
        await callback.answer("Спочатку реєстрація", show_alert=True)
        return
    await state.set_state(ProfileEdit.name)
    await callback.message.answer(profile_ask_name(), parse_mode="HTML")
    await callback.answer()


@router.message(ProfileEdit.name)
async def profile_name(message: types.Message, state: FSMContext):
    name = (message.text or "").strip()
    if not name:
        await message.answer(msg_enter_name_plain(), parse_mode="HTML")
        return
    await state.update_data(display_name=name)
    await state.set_state(ProfileEdit.age)
    await message.answer(profile_ask_age(), parse_mode="HTML")


@router.message(ProfileEdit.age)
async def profile_age(message: types.Message, state: FSMContext):
    raw = (message.text or "").strip()
    try:
        age = int(raw)
    except ValueError:
        await message.answer(msg_enter_age_number(), parse_mode="HTML")
        return
    if age < 10 or age > 120:
        await message.answer(msg_enter_age_invalid(), parse_mode="HTML")
        return
    await state.update_data(age=age)
    await state.set_state(ProfileEdit.sex)
    await message.answer(profile_ask_sex_prompt(), parse_mode="HTML", reply_markup=sex_keyboard("prof"))


@router.callback_query(ProfileEdit.sex, F.data.startswith("prof_sex:"))
async def profile_sex_cb(callback: types.CallbackQuery, state: FSMContext):
    sex = callback.data.split(":")[1]
    await state.update_data(sex=sex)
    await state.set_state(ProfileEdit.weight)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(profile_ask_weight(), parse_mode="HTML")
    await callback.answer()


@router.message(ProfileEdit.weight)
async def profile_weight(message: types.Message, state: FSMContext):
    raw = (message.text or "").replace(",", ".").strip()
    try:
        weight = float(raw)
    except ValueError:
        await message.answer(msg_enter_weight_number(), parse_mode="HTML")
        return
    if weight < 30 or weight > 300:
        await message.answer(msg_enter_weight_range(), parse_mode="HTML")
        return
    await state.update_data(weight=weight)
    await state.set_state(ProfileEdit.height)
    await message.answer(profile_ask_height(), parse_mode="HTML")


@router.message(ProfileEdit.height)
async def profile_height(message: types.Message, state: FSMContext):
    raw = (message.text or "").replace(",", ".").strip()
    try:
        height = float(raw)
    except ValueError:
        await message.answer(msg_enter_height_number(), parse_mode="HTML")
        return
    if height < 100 or height > 250:
        await message.answer(msg_enter_height_range(), parse_mode="HTML")
        return
    await state.update_data(height=height)
    await state.set_state(ProfileEdit.goal)
    await message.answer(profile_ask_goal(), parse_mode="HTML", reply_markup=goal_keyboard("prof"))


@router.callback_query(ProfileEdit.goal, F.data.startswith("prof_goal:"))
async def profile_goal_cb(callback: types.CallbackQuery, state: FSMContext):
    goal = callback.data.split(":")[1]
    data = await state.get_data()
    plan = calculate_daily_norm(
        weight_kg=data["weight"],
        height_cm=data["height"],
        age=data["age"],
        sex=data["sex"],
        goal=goal,
    )
    user_id = callback.from_user.id
    save_profile_and_norm(
        user_id,
        display_name=data["display_name"],
        age=data["age"],
        sex=data["sex"],
        weight=data["weight"],
        height=data["height"],
        goal=goal,
        daily_calories=plan["calories"],
        daily_protein=plan["protein"],
        daily_fat=plan["fat"],
        daily_carbs=plan["carbs"],
    )
    await state.clear()
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        profile_saved(plan["calories"], plan["protein"], plan["fat"], plan["carbs"]),
        parse_mode="HTML",
        reply_markup=get_start_keyboard(user_id),
    )
    await callback.answer()
