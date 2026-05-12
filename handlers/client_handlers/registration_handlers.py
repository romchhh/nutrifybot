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
    profile_ask_age,
    profile_ask_goal,
    profile_ask_height,
    profile_ask_sex_prompt,
    profile_ask_weight,
    profile_saved,
)
from database_functions.client_db import save_profile_and_norm
from keyboards.client_keyboards import get_start_keyboard, goal_keyboard, sex_keyboard
from states.client_states import Registration
from utils.nutrition_calculator import calculate_daily_norm

router = Router()


@router.message(Registration.name)
async def registration_name(message: types.Message, state: FSMContext):
    name = (message.text or "").strip()
    if not name:
        await message.answer(msg_enter_name_plain(), parse_mode="HTML")
        return
    await state.update_data(display_name=name)
    await state.set_state(Registration.age)
    await message.answer(profile_ask_age(), parse_mode="HTML")


@router.message(Registration.age)
async def registration_age(message: types.Message, state: FSMContext):
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
    await state.set_state(Registration.sex)
    await message.answer(
        profile_ask_sex_prompt(),
        parse_mode="HTML",
        reply_markup=sex_keyboard("reg"),
    )


@router.callback_query(Registration.sex, F.data.startswith("reg_sex:"))
async def registration_sex(callback: types.CallbackQuery, state: FSMContext):
    sex = callback.data.split(":")[1]
    await state.update_data(sex=sex)
    await state.set_state(Registration.weight)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(profile_ask_weight(), parse_mode="HTML")
    await callback.answer()


@router.message(Registration.weight)
async def registration_weight(message: types.Message, state: FSMContext):
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
    await state.set_state(Registration.height)
    await message.answer(profile_ask_height(), parse_mode="HTML")


@router.message(Registration.height)
async def registration_height(message: types.Message, state: FSMContext):
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
    await state.set_state(Registration.goal)
    await message.answer(profile_ask_goal(), parse_mode="HTML", reply_markup=goal_keyboard("reg"))


@router.callback_query(Registration.goal, F.data.startswith("reg_goal:"))
async def registration_goal(callback: types.CallbackQuery, state: FSMContext):
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
