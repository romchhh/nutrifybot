from __future__ import annotations

import io
import logging
import re
from datetime import date, timedelta

from aiogram import F, Router, types
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# Твої локальні імпорти — підлаштуй під свій проєкт
from utils.calories_analyzer import CalorieAnalyzer, NutritionResult
from utils.nutrition_kb import NutritionKnowledgeBase
from database_functions.client_db import get_user_profile, is_registration_complete
from database_functions.ration_db import (
    add_ration_entry,
    get_ration_day_totals,
)
from keyboards.client_keyboards import (
    calorie_add_to_ration_keyboard,
    calorie_custom_date_keyboard,
    calorie_pick_day_keyboard,
    ration_date_keyboard,
)
from Content.texts import (
    calories_ai_notes_block,
    calories_analysis_result,
    calories_confidence_block,
    calories_confidence_explanation_plain,
    calories_section_entry,
    msg_bad_date_format,
    msg_bad_date_value,
    msg_cancelled,
    msg_enter_date_calories,
    msg_need_registration,
    ration_section_entry,
    ration_entry_added,
)
from states.client_states import CalorieCount
from config import OPENAI_API_KEY

logger = logging.getLogger(__name__)
router = Router()

_kb = NutritionKnowledgeBase(api_key=OPENAI_API_KEY)
_analyzer = CalorieAnalyzer(api_key=OPENAI_API_KEY, kb=_kb)



@router.message(F.text == "📸 Порахувати калорії", StateFilter(None))
async def calories_open(message: types.Message, state: FSMContext):
    if not is_registration_complete(message.from_user.id):
        await message.answer(msg_need_registration(), parse_mode="HTML")
        return

    await state.set_state(CalorieCount.waiting_input)
    await message.answer(
        calories_section_entry(),
        parse_mode="HTML",
    )


@router.message(CalorieCount.waiting_input, F.photo)
async def calories_got_photo(message: types.Message, state: FSMContext):
    progress_message = await message.answer("⏳ Аналізую фото...")

    photo = message.photo[-1]
    file = await message.bot.get_file(photo.file_id)
    buf = io.BytesIO()
    await message.bot.download_file(file.file_path, destination=buf)
    photo_bytes = buf.getvalue()

    caption = message.caption or ""

    try:
        result = await _analyzer.analyze_photo(photo_bytes, caption=caption)
    except Exception as exc:
        logger.error("Photo analysis failed: %s", exc)
        await message.answer(
            "❌ Не вдалося проаналізувати фото. Спробуй описати страву текстом."
        )
        return

    await _show_result(message, state, result, progress_message)


@router.message(CalorieCount.waiting_input, F.text)
async def calories_got_text(message: types.Message, state: FSMContext):
    text = (message.text or "").strip()

    if await _handle_non_analysis_text(message, state, text):
        return

    if text.startswith("/") or text in ("❌ Скасувати",):
        return

    progress_message = await message.answer("⏳ Аналізую...")

    try:
        result = await _analyzer.analyze_text(text)
    except Exception as exc:
        logger.error("Text analysis failed: %s", exc)
        await message.answer(
            "❌ Не вдалося проаналізувати. Спробуй описати точніше, наприклад: "
            "<b>гречка з куркою 300г</b>",
            parse_mode="HTML",
        )
        return

    await _show_result(message, state, result, progress_message)


def _print_analysis_console(result: NutritionResult) -> None:
    """Дублює зміст результату аналізу в stdout (без HTML), як у Telegram."""
    conf_icon = {"high": "✅", "medium": "🟡", "low": "🔴"}.get(result.confidence, "🟡")
    conf_plain = calories_confidence_explanation_plain(result.confidence)
    notes_body = (result.notes or "").strip() or "(немає приміток від моделі)"
    block = [
        "",
        "=" * 44,
        "Результат аналізу",
        "",
        f"{result.name}",
        f"Калорії: ~{result.calories:.1f} ккал",
        f"Білки: ~{result.protein:.1f} г",
        f"Жири: ~{result.fat:.1f} г",
        f"Вуглеводи: ~{result.carbs:.1f} г",
        "",
        "Додати до раціону?",
        "",
        f"confidence: {result.confidence} {conf_icon}",
        conf_plain,
        "",
        f"Порція: {result.portion_g:.0f} г",
        "",
        "Примітки від моделі (AI):",
        notes_body,
        "=" * 44,
    ]
    print("\n".join(block), flush=True)


async def _show_result(
    message: types.Message,
    state: FSMContext,
    result: NutritionResult,
    target_message: types.Message | None = None,
):
    """Показати результат аналізу в одному інтерактивному повідомленні."""
    _print_analysis_console(result)
    dish = result.as_dict()
    await state.update_data(pending_dish=dish)
    text = _render_result_text(
        result.name,
        result.calories,
        result.protein,
        result.fat,
        result.carbs,
        result.confidence,
        result.portion_g,
        result.notes,
    )
    if target_message is not None:
        await target_message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=calorie_add_to_ration_keyboard(),
        )
        await state.update_data(interactive_message_id=target_message.message_id)
        return
    sent = await message.answer(
        text, parse_mode="HTML", reply_markup=calorie_add_to_ration_keyboard()
    )
    await state.update_data(interactive_message_id=sent.message_id)


@router.message(
    StateFilter(
        CalorieCount.waiting_input,
        CalorieCount.pick_day_add,
        CalorieCount.custom_day_date,
    ),
    F.text == "❌ Скасувати",
)
async def calories_cancel_text(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(msg_cancelled(), parse_mode="HTML")


@router.callback_query(
    StateFilter(
        CalorieCount.waiting_input,
        CalorieCount.pick_day_add,
        CalorieCount.custom_day_date,
    ),
    F.data == "cal_cancel",
)
async def calories_cancel_cb(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(msg_cancelled(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "cal_add_ration")
async def calories_add_prompt(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if "pending_dish" not in data:
        await callback.answer("Немає страви для додавання", show_alert=True)
        return

    await state.set_state(CalorieCount.pick_day_add)
    await callback.message.edit_text(
        "📅 <b>До якого дня додати?</b>",
        parse_mode="HTML",
        reply_markup=calorie_pick_day_keyboard(),
    )
    await state.update_data(interactive_message_id=callback.message.message_id)
    await callback.answer()


@router.callback_query(CalorieCount.pick_day_add, F.data.startswith("cal_day:"))
async def calories_day_pick(callback: types.CallbackQuery, state: FSMContext):
    part = callback.data.split(":")[1]
    today = date.today()

    day_map = {
        "today": today,
        "yesterday": today - timedelta(days=1),
        "tomorrow": today + timedelta(days=1),
    }

    if part in day_map:
        await _calories_commit(callback, state, day_map[part].isoformat())
    else:
        await state.set_state(CalorieCount.custom_day_date)
        await callback.message.edit_text(
            msg_enter_date_calories(),
            parse_mode="HTML",
            reply_markup=calorie_custom_date_keyboard(),
        )
        await state.update_data(interactive_message_id=callback.message.message_id)
        await callback.answer()


@router.callback_query(
    StateFilter(CalorieCount.pick_day_add, CalorieCount.custom_day_date),
    F.data == "cal_back_result",
)
async def calories_back_to_result(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    dish = data.get("pending_dish")
    if not dish:
        await state.clear()
        await callback.message.edit_text(msg_cancelled(), parse_mode="HTML")
        await callback.answer()
        return
    await state.set_state(CalorieCount.waiting_input)
    await callback.message.edit_text(
        _render_result_text(
            dish.get("name", "Страва"),
            float(dish.get("calories", 0)),
            float(dish.get("protein", 0)),
            float(dish.get("fat", 0)),
            float(dish.get("carbs", 0)),
            dish.get("confidence", "medium"),
            float(dish.get("portion_g", 300)),
            dish.get("notes", ""),
        ),
        parse_mode="HTML",
        reply_markup=calorie_add_to_ration_keyboard(),
    )
    await state.update_data(interactive_message_id=callback.message.message_id)
    await callback.answer()


@router.callback_query(CalorieCount.custom_day_date, F.data == "cal_back_day_picker")
async def calories_back_to_day_picker(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(CalorieCount.pick_day_add)
    await callback.message.edit_text(
        "📅 <b>До якого дня додати?</b>",
        parse_mode="HTML",
        reply_markup=calorie_pick_day_keyboard(),
    )
    await state.update_data(interactive_message_id=callback.message.message_id)
    await callback.answer()


@router.message(CalorieCount.custom_day_date)
async def calories_other_date(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if "pending_dish" not in data:
        await state.clear()
        return

    raw = (message.text or "").strip()
    m = re.fullmatch(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", raw)
    if not m:
        await message.answer(msg_bad_date_format(), parse_mode="HTML")
        return

    d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
    try:
        iso = date(y, mo, d).isoformat()
    except ValueError:
        await message.answer(msg_bad_date_value(), parse_mode="HTML")
        return

    dish = data["pending_dish"]
    user_id = message.from_user.id
    add_ration_entry(
        user_id,
        iso,
        dish["name"],
        float(dish["calories"]),
        float(dish["protein"]),
        float(dish["fat"]),
        float(dish["carbs"]),
    )
    await state.clear()
    profile = get_user_profile(user_id)
    norm = int(profile["daily_calories"]) if profile and profile.get("daily_calories") else 2000
    kcal_t, *_ = get_ration_day_totals(user_id, iso)
    interactive_message_id = data.get("interactive_message_id")
    if interactive_message_id:
        await message.bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=interactive_message_id,
            text=ration_entry_added(_label_iso(iso), kcal_t, norm),
            parse_mode="HTML",
        )
        return
    await message.answer(ration_entry_added(_label_iso(iso), kcal_t, norm), parse_mode="HTML")


async def _calories_commit(
    callback: types.CallbackQuery, state: FSMContext, iso: str
):
    data = await state.get_data()
    dish = data["pending_dish"]
    user_id = callback.from_user.id

    add_ration_entry(
        user_id,
        iso,
        dish["name"],
        float(dish["calories"]),
        float(dish["protein"]),
        float(dish["fat"]),
        float(dish["carbs"]),
    )
    await state.clear()

    profile = get_user_profile(user_id)
    norm = int(profile["daily_calories"]) if profile and profile.get("daily_calories") else 2000
    kcal_t, *_ = get_ration_day_totals(user_id, iso)

    await callback.message.edit_text(
        ration_entry_added(_label_iso(iso), kcal_t, norm),
        parse_mode="HTML",
    )
    await callback.answer()


def _label_iso(iso: str) -> str:
    today = date.today()
    d = date.fromisoformat(iso)
    if d == today:
        return "сьогодні"
    if d == today - timedelta(days=1):
        return "вчора"
    if d == today + timedelta(days=1):
        return "завтра"
    return d.strftime("%d.%m.%Y")


def _render_result_text(
    name: str,
    calories: float,
    protein: float,
    fat: float,
    carbs: float,
    confidence: str,
    portion_g: float,
    notes: str,
) -> str:
    confidence_icon = {"high": "✅", "medium": "🟡", "low": "🔴"}.get(
        (confidence or "medium").lower(), "🟡"
    )
    text = calories_analysis_result(name, calories, protein, fat, carbs)
    text += "\n\n"
    text += calories_confidence_block(confidence, confidence_icon)
    text += f"\n\n⚖️ <b>Порція:</b> <code>{portion_g:.0f}</code> г"
    text += "\n\n"
    text += calories_ai_notes_block(notes)
    text += "\n\n<b>Додати до раціону?</b>"
    return text


async def _handle_non_analysis_text(
    message: types.Message,
    state: FSMContext,
    text: str,
) -> bool:
    if text == "📅 Мій раціон":
        await state.clear()
        if not is_registration_complete(message.from_user.id):
            await message.answer(msg_need_registration(), parse_mode="HTML")
            return True

        await message.answer(
            ration_section_entry(),
            parse_mode="HTML",
            reply_markup=ration_date_keyboard(message.from_user.id),
        )
        return True

    if text in {"👤 Профіль", "📸 Порахувати калорії", "📸 Аналіз страви"}:
        await message.answer(
            "Надішли <b>фото</b> або <b>опис страви</b> для аналізу.",
            parse_mode="HTML",
        )
        return True

    return False