import re
from datetime import date, datetime, timedelta

from aiogram import Router, F, types
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from Content.texts import (
    msg_bad_date_format,
    msg_bad_date_value,
    msg_enter_dish_name,
    msg_need_registration,
    parse_macros_help,
    ration_day_view,
    ration_entry_added,
    ration_manual_add_hint,
    ration_section_entry,
)
from database_functions.client_db import (
    get_user_profile,
    is_registration_complete,
)
from database_functions.ration_db import (
    add_ration_entry,
    get_ration_day_totals,
    get_ration_entries_for_day,
    get_ration_entry,
    update_ration_entry,
)
from keyboards.client_keyboards import create_calendar, ration_after_day_keyboard, ration_date_keyboard
from states.client_states import Ration

router = Router()


@router.message(F.text == "📅 Мій раціон", StateFilter(None))
async def ration_menu(message: types.Message):
    if not is_registration_complete(message.from_user.id):
        await message.answer(msg_need_registration(), parse_mode="HTML")
        return
    await message.answer(
        ration_section_entry(),
        parse_mode="HTML",
        reply_markup=ration_date_keyboard(message.from_user.id),
    )


@router.callback_query(F.data.startswith("ration_day:"))
async def ration_pick_day(callback: types.CallbackQuery, state: FSMContext):
    if not is_registration_complete(callback.from_user.id):
        await callback.answer("Спочатку реєстрація", show_alert=True)
        return
    part = callback.data.split(":")[1]
    today = date.today()
    if part == "today":
        iso = today.isoformat()
        await _show_ration_day(callback.from_user.id, iso, callback.message)
    elif part == "yesterday":
        iso = (today - timedelta(days=1)).isoformat()
        await _show_ration_day(callback.from_user.id, iso, callback.message)
    else:
        await state.set_state(Ration.pick_custom_date)
        await callback.message.answer(
            "📅 <b>Обери дату в календарі</b>",
            parse_mode="HTML",
            reply_markup=create_calendar(callback.from_user.id),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("ration_cal:"))
async def ration_pick_calendar_day(callback: types.CallbackQuery):
    if not is_registration_complete(callback.from_user.id):
        await callback.answer("Спочатку реєстрація", show_alert=True)
        return
    iso = callback.data.split(":", 1)[1]
    await _show_ration_day(callback.from_user.id, iso, callback.message)
    await callback.answer()


@router.callback_query(F.data.startswith("ration_add_dish:"))
async def ration_add_start(callback: types.CallbackQuery, state: FSMContext):
    if not is_registration_complete(callback.from_user.id):
        await callback.answer("Спочатку реєстрація", show_alert=True)
        return
    entry_date_iso = callback.data.split(":", 1)[1]
    await state.update_data(ration_date=entry_date_iso)
    await state.set_state(Ration.add_dish_name)
    await callback.message.answer(ration_manual_add_hint(), parse_mode="HTML")
    await callback.answer()


@router.message(Ration.add_dish_name)
async def ration_dish_name(message: types.Message, state: FSMContext):
    name = (message.text or "").strip()
    if not name:
        await message.answer(msg_enter_dish_name(), parse_mode="HTML")
        return
    await state.update_data(dish_name=name)
    await state.set_state(Ration.add_dish_macros)
    await message.answer(parse_macros_help(), parse_mode="HTML")


@router.message(Ration.add_dish_macros)
async def ration_dish_macros(message: types.Message, state: FSMContext):
    parsed = _parse_macros((message.text or ""))
    if not parsed:
        await message.answer(parse_macros_help(), parse_mode="HTML")
        return
    kcal, p, f, c = parsed
    data = await state.get_data()
    entry_date_iso = data["ration_date"]
    dish_name = data["dish_name"]
    user_id = message.from_user.id
    add_ration_entry(user_id, entry_date_iso, dish_name, kcal, p, f, c)
    await state.clear()
    profile = get_user_profile(user_id)
    norm = int(profile["daily_calories"]) if profile and profile.get("daily_calories") else 2000
    kcal_t, _, _, _, _ = get_ration_day_totals(user_id, entry_date_iso)
    await message.answer(
        ration_entry_added(_label_for_iso(entry_date_iso), kcal_t, norm),
        parse_mode="HTML",
        reply_markup=ration_after_day_keyboard(entry_date_iso),
    )


@router.callback_query(F.data == "ration_back_dates")
async def ration_back_dates(callback: types.CallbackQuery):
    if not is_registration_complete(callback.from_user.id):
        await callback.answer("Спочатку реєстрація", show_alert=True)
        return
    await callback.message.answer(
        "📅 <b>Обери дату в календарі</b>",
        parse_mode="HTML",
        reply_markup=create_calendar(callback.from_user.id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("ration_edit_list:"))
async def ration_edit_list(callback: types.CallbackQuery):
    if not is_registration_complete(callback.from_user.id):
        await callback.answer("Спочатку реєстрація", show_alert=True)
        return
    entry_date_iso = callback.data.split(":", 1)[1]
    entries = get_ration_entries_for_day(callback.from_user.id, entry_date_iso)
    if not entries:
        await callback.answer("За цей день немає записів", show_alert=True)
        return
    await callback.message.answer(
        "✏️ <b>Що редагуємо?</b>",
        parse_mode="HTML",
        reply_markup=_ration_edit_entries_keyboard(entry_date_iso, entries),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("ration_edit:"))
async def ration_edit_start(callback: types.CallbackQuery, state: FSMContext):
    if not is_registration_complete(callback.from_user.id):
        await callback.answer("Спочатку реєстрація", show_alert=True)
        return
    entry_id = int(callback.data.split(":", 1)[1])
    entry = get_ration_entry(entry_id, callback.from_user.id)
    if not entry:
        await callback.answer("Запис не знайдено", show_alert=True)
        return
    _, entry_date_iso, dish_name, kcal, p, f, c = entry
    await state.update_data(
        edit_entry_id=entry_id,
        ration_date=entry_date_iso,
    )
    await state.set_state(Ration.edit_dish_name)
    await callback.message.answer(
        "✏️ <b>Редагування страви</b>\n\n"
        f"Поточна назва: <code>{dish_name}</code>\n"
        f"Поточне КБЖУ: <code>{kcal:.0f} {p:.1f} {f:.1f} {c:.1f}</code>\n\n"
        "Надішли нову назву страви.",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(Ration.edit_dish_name)
async def ration_edit_name(message: types.Message, state: FSMContext):
    name = (message.text or "").strip()
    if not name:
        await message.answer(msg_enter_dish_name(), parse_mode="HTML")
        return
    await state.update_data(dish_name=name)
    await state.set_state(Ration.edit_dish_macros)
    await message.answer(parse_macros_help(), parse_mode="HTML")


@router.message(Ration.edit_dish_macros)
async def ration_edit_macros(message: types.Message, state: FSMContext):
    parsed = _parse_macros((message.text or ""))
    if not parsed:
        await message.answer(parse_macros_help(), parse_mode="HTML")
        return
    kcal, p, f, c = parsed
    data = await state.get_data()
    user_id = message.from_user.id
    entry_id = data["edit_entry_id"]
    dish_name = data["dish_name"]
    entry_date_iso = data["ration_date"]
    update_ration_entry(entry_id, user_id, dish_name, kcal, p, f, c)
    await state.clear()
    await _show_ration_day(user_id, entry_date_iso, message)


@router.message(Ration.pick_custom_date)
async def ration_pick_custom_date(message: types.Message):
    raw = (message.text or "").strip()
    iso = _parse_ukr_date_to_iso(raw)
    if not iso:
        if re.fullmatch(r"\d{1,2}\.\d{1,2}\.\d{4}", raw):
            await message.answer(msg_bad_date_value(), parse_mode="HTML")
        else:
            await message.answer(msg_bad_date_format(), parse_mode="HTML")
        return
    await _show_ration_day(message.from_user.id, iso, message)


@router.callback_query(F.data.startswith("prev:"))
async def handle_prev_month(callback_query: types.CallbackQuery):
    year, month = map(int, callback_query.data.split(":")[1].split("-"))
    user_id = callback_query.from_user.id
    await callback_query.message.edit_reply_markup(
        reply_markup=create_calendar(user_id, year, month)
    )
    await callback_query.answer()


@router.callback_query(F.data.startswith("next:"))
async def handle_next_month(callback_query: types.CallbackQuery):
    year, month = map(int, callback_query.data.split(":")[1].split("-"))
    user_id = callback_query.from_user.id
    await callback_query.message.edit_reply_markup(
        reply_markup=create_calendar(user_id, year, month)
    )
    await callback_query.answer()


@router.callback_query(F.data == "ignore")
async def handle_ignore(callback_query: types.CallbackQuery):
    await callback_query.answer()


async def _show_ration_day(user_id: int, entry_date_iso: str, target: types.Message):
    profile = get_user_profile(user_id)
    norm_kcal = int(profile["daily_calories"]) if profile and profile.get("daily_calories") else 2000
    norm_p = float(profile["daily_protein"]) if profile and profile.get("daily_protein") else 120.0
    norm_f = float(profile["daily_fat"]) if profile and profile.get("daily_fat") else 70.0
    norm_c = float(profile["daily_carbs"]) if profile and profile.get("daily_carbs") else 250.0
    kcal_t, p_t, f_t, c_t, items = get_ration_day_totals(user_id, entry_date_iso)
    lines = [f"• {name} — {int(round(kcal))} ккал" for name, kcal in items]
    await target.answer(
        ration_day_view(
            _label_for_iso(entry_date_iso),
            kcal_t,
            norm_kcal,
            p_t,
            norm_p,
            f_t,
            norm_f,
            c_t,
            norm_c,
            lines,
        ),
        parse_mode="HTML",
        reply_markup=ration_after_day_keyboard(entry_date_iso),
    )


def _ration_edit_entries_keyboard(
    entry_date_iso: str, entries: list[tuple[int, str, float, float, float, float]]
) -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = []
    for entry_id, dish_name, kcal, _, _, _ in entries:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"{dish_name} ({int(round(kcal))} ккал)",
                    callback_data=f"ration_edit:{entry_id}",
                )
            ]
        )
    buttons.append(
        [InlineKeyboardButton(text="◀️ До дня", callback_data=f"ration_cal:{entry_date_iso}")]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _parse_macros(raw: str) -> tuple[float, float, float, float] | None:
    parts = raw.replace(",", ".").split()
    if len(parts) < 4:
        return None
    try:
        return float(parts[0]), float(parts[1]), float(parts[2]), float(parts[3])
    except ValueError:
        return None


def _parse_ukr_date_to_iso(raw: str) -> str | None:
    m = re.fullmatch(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", raw)
    if not m:
        return None
    day_v, month_v, year_v = int(m.group(1)), int(m.group(2)), int(m.group(3))
    try:
        return date(year_v, month_v, day_v).isoformat()
    except ValueError:
        return None


def _label_for_iso(entry_date_iso: str) -> str:
    dt = datetime.strptime(entry_date_iso, "%Y-%m-%d")
    return dt.strftime("%d.%m.%Y")