import calendar
from datetime import datetime

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from database_functions.admin_db import get_all_administrators
from database_functions.ration_db import get_ration_days_with_entries


def get_start_keyboard(user_id: int) -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(text="📅 Мій раціон")],
        [KeyboardButton(text="📸 Порахувати калорії"), KeyboardButton(text="👤 Профіль")],
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def ration_date_keyboard(user_id: int, year: int | None = None, month: int | None = None) -> InlineKeyboardMarkup:
    return create_calendar(user_id, year, month)


def ration_after_day_keyboard(entry_date_iso: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Додати страву", callback_data=f"ration_add_dish:{entry_date_iso}")],
            [InlineKeyboardButton(text="✏️ Змінити записи", callback_data=f"ration_edit_list:{entry_date_iso}")],
            [InlineKeyboardButton(text="◀️ До вибору дати", callback_data="ration_back_dates")],
        ]
    )


def calorie_method_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📷 Фото", callback_data="cal_method:photo")],
            [InlineKeyboardButton(text="✍️ Опис", callback_data="cal_method:text")],
        ]
    )


def calorie_add_to_ration_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Додати до раціону", callback_data="cal_add_ration")],
            [InlineKeyboardButton(text="❌ Не додавати", callback_data="cal_cancel")],
        ]
    )


def calorie_pick_day_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Сьогодні", callback_data="cal_day:today"),
                InlineKeyboardButton(text="Вчора", callback_data="cal_day:yesterday"),
            ],
            [
                InlineKeyboardButton(text="Завтра", callback_data="cal_day:tomorrow"),
                InlineKeyboardButton(text="Інший день", callback_data="cal_day:other"),
            ],
            [
                InlineKeyboardButton(text="◀️ Назад", callback_data="cal_back_result"),
                InlineKeyboardButton(text="❌ Скасувати", callback_data="cal_cancel"),
            ],
        ]
    )


def calorie_custom_date_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="◀️ До вибору дня", callback_data="cal_back_day_picker"),
                InlineKeyboardButton(text="❌ Скасувати", callback_data="cal_cancel"),
            ]
        ]
    )


def sex_keyboard(prefix: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Чоловік", callback_data=f"{prefix}_sex:male"),
                InlineKeyboardButton(text="Жінка", callback_data=f"{prefix}_sex:female"),
            ],
        ]
    )


def goal_keyboard(prefix: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📉 Схуднення", callback_data=f"{prefix}_goal:lose")],
            [InlineKeyboardButton(text="⚖️ Підтримка ваги", callback_data=f"{prefix}_goal:maintain")],
            [InlineKeyboardButton(text="📈 Набір маси", callback_data=f"{prefix}_goal:gain")],
        ]
    )


def profile_edit_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="✏️ Змінити дані", callback_data="profile_edit_start")]]
    )



UKRAINIAN_MONTHS = [
    "Січень", "Лютий", "Березень", "Квітень", "Травень", "Червень",
    "Липень", "Серпень", "Вересень", "Жовтень", "Листопад", "Грудень"
]
UKRAINIAN_DAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Нд"]

def create_calendar(user_id, year=None, month=None):
    now = datetime.now()
    year = year or now.year
    month = month or now.month
    today_day = now.day if (year == now.year and month == now.month) else None
    marked_days = get_ration_days_with_entries(user_id, year, month)
    
    if month == 1:
        prev_month = 12
        prev_year = year - 1
    else:
        prev_month = month - 1
        prev_year = year

    if month == 12:
        next_month = 1
        next_year = year + 1
    else:
        next_month = month + 1
        next_year = year
    

    keyboard = []
    keyboard.append([
        InlineKeyboardButton(text="<", callback_data=f"prev:{prev_year}-{prev_month:02d}"),
        InlineKeyboardButton(
            text=f"{UKRAINIAN_MONTHS[month - 1]} {year}",
            callback_data="ignore"
        ),
        InlineKeyboardButton(text=">", callback_data=f"next:{next_year}-{next_month:02d}"),
    ])
    keyboard.append([InlineKeyboardButton(text=day, callback_data="ignore") for day in UKRAINIAN_DAYS])
    my_calendar = calendar.monthcalendar(year, month)
    for week in my_calendar:
        row = []
        for day in week:
            if day == 0: 
                row.append(InlineKeyboardButton(text=" ", callback_data="ignore"))
            else:
                day_text = str(day)
                if day == today_day:
                    day_text = f"🔹{day_text}"
                if day in marked_days:
                    day_text = f"{day_text}✅"
                row.append(
                    InlineKeyboardButton(
                        text=day_text,
                        callback_data=f"ration_cal:{year}-{month:02d}-{day:02d}"
                    )
                )
        keyboard.append(row)
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
