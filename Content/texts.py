from html import escape


def get_greeting_message() -> str:
    return (
        "👋 <b>Привіт!</b> Я <b>Nutrify</b> — твій особистий помічник з харчування.\n\n"
        "<b>Я допоможу тобі:</b>\n"
        "🥗 Вести щоденний раціон та стежити за <b>КБЖУ</b>\n"
        "📸 Підрахувати калорії з <i>фото</i> або <i>опису</i> страви\n"
        "⚙️ Налаштувати профіль та отримати <b>персональну норму</b>\n\n"
        "Обери, з чого почнемо 👇"
    )


def ration_section_entry() -> str:
    return (
        "📅 <b>Твій раціон</b>\n\n"
        "Переглядай <b>підсумок КБЖУ</b> за день, додавай страви та відстежуй прогрес до цілі.\n\n"
        "<i>Обери дату в календарі нижче 👇</i>"
    )


def ration_day_view(
    date_label: str,
    kcal: float,
    norm_kcal: int,
    p: float,
    norm_p: float,
    f: float,
    norm_f: float,
    c: float,
    norm_c: float,
    lines: list[str],
) -> str:
    safe_lines = [escape(line) for line in lines] if lines else []
    entries_block = "\n".join(safe_lines) if safe_lines else "<i>— поки немає записів</i>"
    kcal_i = int(round(kcal))
    left_kcal = max(0, int(round(norm_kcal - kcal)))
    left_p = max(0.0, norm_p - p)
    left_f = max(0.0, norm_f - f)
    left_c = max(0.0, norm_c - c)
    return (
        f"📊 <b>Раціон за {escape(date_label)}</b>\n\n"
        f"🔥 <b>Калорії:</b> <code>{kcal_i}</code> / <code>{norm_kcal}</code> ккал\n"
        f"🥩 <b>Білки:</b> <code>{p:.1f}</code> / <code>{norm_p:.1f}</code> г\n"
        f"🧈 <b>Жири:</b> <code>{f:.1f}</code> / <code>{norm_f:.1f}</code> г\n"
        f"🌾 <b>Вуглеводи:</b> <code>{c:.1f}</code> / <code>{norm_c:.1f}</code> г\n\n"
        "<b>Залишилось до цілі:</b>\n"
        f"🔥 <code>{left_kcal}</code> ккал · "
        f"🥩 <code>{left_p:.1f}</code> г · "
        f"🧈 <code>{left_f:.1f}</code> г · "
        f"🌾 <code>{left_c:.1f}</code> г\n\n"
        f"<b>Записи:</b>\n{entries_block}\n\n"
        "➕ <b>Додати страву</b>"
    )


def ration_manual_add_hint() -> str:
    return (
        "✏️ <b>Ручне додавання</b>\n\n"
        "Введи <b>назву страви</b> та її <b>КБЖУ</b> вручну або скористайся аналізом — "
        "надішли <i>фото</i> чи <i>опис</i>, і я все порахую сам."
    )


def ration_entry_added(date_label: str, kcal: float, norm: int) -> str:
    kcal_i = int(round(kcal))
    return (
        f"✅ <b>Додано до раціону</b> за <b>{escape(date_label)}</b>!\n\n"
        "<b>Оновлений баланс:</b>\n"
        f"🔥 <code>{kcal_i}</code> / <code>{norm}</code> ккал"
    )


def calories_section_entry() -> str:
    return (
        "📸 <b>Аналіз страви</b>\n\n"
        "Надішли мені <b>фото</b> або <b>опис</b> страви — і я одразу розрахую "
        "її <b>калорійність</b> та <b>КБЖУ</b>.\n\n"
        "<b>Обери спосіб:</b>"
    )


def calories_ask_photo() -> str:
    return (
        "📷 <b>Запит фото</b>\n\n"
        "Зроби або надішли <b>фото страви</b>.\n"
        "<i>Постарайся, щоб тарілка була добре видна — так аналіз буде точнішим.</i>"
    )


def calories_ask_text() -> str:
    return (
        "✍️ <b>Запит опису</b>\n\n"
        "Опиши страву <b>текстом</b>.\n"
        "<i>Наприклад:</i> <code>гречка 200г, куряча грудка 150г, огірок</code>"
    )


def calories_analysis_result(name: str, kcal: float, p: float, f: float, c: float) -> str:
    safe_name = escape(name)
    return (
        "🔍 <b>Результат аналізу</b>\n\n"
        f"🍽 <b>{safe_name}</b>\n"
        f"🔥 <b>Калорії:</b> ~<code>{kcal:.1f}</code> ккал\n"
        f"🥩 <b>Білки:</b> ~<code>{p:.1f}</code> г\n"
        f"🧈 <b>Жири:</b> ~<code>{f:.1f}</code> г\n"
        f"🌾 <b>Вуглеводи:</b> ~<code>{c:.1f}</code> г"
    )


_CONFIDENCE_UK_LABELS = {
    "high": "висока",
    "medium": "середня",
    "low": "низька",
}

_CONFIDENCE_EXPLANATIONS_UK = {
    "high": (
        "Модель впевнена в оцінці: вхідні дані достатньо конкретні, порція та склад "
        "виглядають передбачувано; за наявності використано перевірені дані з бази знань."
    ),
    "medium": (
        "Є помірна невизначеність: наприклад, розмір порції, спосіб приготування або частина "
        "інгредієнтів описані нечітко — цифри орієнтовні, уточнення покращать точність."
    ),
    "low": (
        "Оцінка дуже орієнтовна: у тексті мало конкретики (вага, склад) або слабкий збіг з базою — "
        "КБЖУ можуть сильно відрізнятися від реальності; варто вказати грами та інгредієнти."
    ),
}


def calories_confidence_explanation_plain(confidence: str) -> str:
    """Коротке пояснення рівня confidence без HTML (наприклад, для stdout)."""
    key = (confidence or "medium").strip().lower()
    return _CONFIDENCE_EXPLANATIONS_UK.get(key, _CONFIDENCE_EXPLANATIONS_UK["medium"])


def calories_confidence_block(confidence: str, icon: str) -> str:
    """
    Рядок точності (high | medium | low) + коротке пояснення в цитаті.
    """
    key = (confidence or "medium").strip().lower()
    label = _CONFIDENCE_UK_LABELS.get(key, _CONFIDENCE_UK_LABELS["medium"])
    expl = _CONFIDENCE_EXPLANATIONS_UK.get(key, _CONFIDENCE_EXPLANATIONS_UK["medium"])
    return (
        f"{icon} <b>Точність оцінки (confidence):</b> <code>{escape(key)}</code> "
        f"(<i>{escape(label)}</i>)\n\n"
        f"<blockquote>{escape(expl)}</blockquote>"
    )


def calories_ai_notes_block(notes: str) -> str:
    """Блок приміток від моделі; якщо порожньо — короткий підказковий текст."""
    body = (notes or "").strip()
    if not body:
        body = (
            "Додай до прийому їжі овочі або салат для клітковини, пий воду. "
            "Наступного разу вкажи вагу порції грамами — так легше тримати баланс КБЖУ протягом дня."
        )
    return (
        "<b>Примітки від моделі (AI)</b>\n\n"
        f"<i>{escape(body)}</i>"
    )


def calories_pick_day_add() -> str:
    return (
        "📅 <b>До якого дня додати цю страву?</b>\n\n"
        "<i>Обери варіант нижче або вкажи свою дату.</i>\n\n"
        "• <b>Сьогодні</b>\n"
        "• <b>Вчора</b>\n"
        "• <b>Завтра</b>\n"
        "• <b>Інший день</b>"
    )


def profile_view(
    name: str,
    age: int,
    sex_label: str,
    weight: float,
    height: float,
    goal_label: str,
    kcal: int,
    p: float,
    f: float,
    c: float,
) -> str:
    return (
        "👤 <b>Твій профіль</b>\n\n"
        f"<b>Ім'я:</b> {escape(name)}\n"
        f"<b>Вік:</b> <code>{age}</code> р · <b>Стать:</b> {escape(sex_label)}\n"
        f"<b>Вага:</b> <code>{weight:.1f}</code> кг · <b>Зріст:</b> <code>{height:.0f}</code> см\n"
        f"<b>Ціль:</b> {escape(goal_label)}\n\n"
        "📊 <b>Рекомендована норма на день:</b>\n"
        f"🔥 <code>{kcal}</code> ккал  "
        f"🥩 <code>{p:.0f}</code>г  "
        f"🧈 <code>{f:.0f}</code>г  "
        f"🌾 <code>{c:.0f}</code>г\n\n"
        "✏️ <i>Змінити дані — натисни кнопку нижче</i>"
    )


def profile_ask_name() -> str:
    return "👋 <b>Як тебе звати?</b>\n\n<i>Напиши ім'я одним повідомленням.</i>"


def profile_ask_weight() -> str:
    return "⚖️ <b>Поточна вага</b>\n\nВведи вагу в <b>кілограмах</b>:\n<i>Наприклад:</i> <code>70.5</code>"


def profile_ask_height() -> str:
    return "📏 <b>Зріст</b>\n\nВведи зріст у <b>сантиметрах</b>:\n<i>Наприклад:</i> <code>175</code>"


def profile_ask_age() -> str:
    return "🎂 <b>Вік</b>\n\nСкільки тобі <b>повних років</b>?\n<i>Наприклад:</i> <code>28</code>"


def profile_ask_sex_prompt() -> str:
    return "⚧️ <b>Стать</b>\n\n<i>Обери варіант кнопкою нижче.</i>"


def profile_ask_goal() -> str:
    return (
        "🎯 <b>Яка твоя ціль?</b>\n\n"
        "• 📉 <b>Схуднення</b>\n"
        "• ⚖️ <b>Підтримка ваги</b>\n"
        "• 📈 <b>Набір маси</b>\n\n"
        "<i>Обери кнопкою нижче.</i>"
    )


def profile_saved(kcal: int, p: float, f: float, c: float) -> str:
    return (
        "✅ <b>Профіль збережено!</b>\n\n"
        "На основі твоїх даних я розрахував <b>рекомендовану норму</b>:\n"
        f"🔥 <code>{kcal}</code> ккал на день\n"
        f"🥩 <b>Білки:</b> <code>{p:.0f}</code> г · "
        f"🧈 <b>Жири:</b> <code>{f:.0f}</code> г · "
        f"🌾 <b>Вуглеводи:</b> <code>{c:.0f}</code> г\n\n"
        "Тепер ти готовий стежити за своїм харчуванням! 💪"
    )


def registration_intro_welcome() -> str:
    return (
        "👋 <b>Вітаю!</b>\n\n"
        "Щоб порахувати твою персональну норму <b>КБЖУ</b>, мені потрібні кілька даних. "
        "<i>Це займе хвилину.</i>"
    )


def parse_macros_help() -> str:
    return (
        "📐 <b>Формат КБЖУ</b>\n\n"
        "Надішли в <b>один рядок</b> через пробіл:\n"
        "<code>ккал білки жири вуглеводи</code>\n\n"
        "<b>Приклад:</b> <code>350 20 12 40</code>"
    )


def msg_need_registration() -> str:
    return (
        "🔒 <b>Потрібна реєстрація</b>\n\n"
        "<i>Спочатку заверш налаштування профілю.</i>\n"
        "Натисни: /start"
    )


def msg_profile_missing() -> str:
    return (
        "❓ <b>Профіль не знайдено</b>\n\n"
        "<i>Запусти бота знову:</i> /start"
    )


def msg_enter_date_ration() -> str:
    return (
        "📆 <b>Інший день</b>\n\n"
        "Введи дату у форматі <code>ДД.ММ.РРРР</code>\n"
        "<i>Наприклад:</i> <code>15.04.2026</code>"
    )


def msg_enter_date_calories() -> str:
    return (
        "📆 <b>Своя дата</b>\n\n"
        "Введи дату: <code>ДД.ММ.РРРР</code>"
    )


def msg_bad_date_format() -> str:
    return "⚠️ <b>Некоректний формат</b>\n\nОчікується: <code>ДД.ММ.РРРР</code>"


def msg_bad_date_value() -> str:
    return "⚠️ <b>Некоректна дата</b>\n\nПеревір день, місяць і рік."


def msg_cancelled() -> str:
    return "👌 <b>Скасовано</b>\n\n<i>Якщо знадоблюсь — пиши знову.</i>"


def msg_enter_dish_name() -> str:
    return "🍽 <b>Назва страви</b>\n\n<i>Напиши, як назвемо запис у раціоні.</i>"


def msg_enter_name_plain() -> str:
    return "⚠️ Введи <b>ім'я</b> текстом."


def msg_enter_age_number() -> str:
    return "⚠️ Введи <b>вік числом</b>, наприклад <code>25</code>."


def msg_enter_age_invalid() -> str:
    return "⚠️ <b>Некоректний вік</b>\n\n<i>Очікується значення від 10 до 120.</i>"


def msg_enter_weight_number() -> str:
    return "⚠️ Введи <b>вагу числом</b>, наприклад <code>70.5</code>"


def msg_enter_weight_range() -> str:
    return "⚠️ Перевір <b>вагу (кг)</b> і спробуй ще раз."


def msg_enter_height_number() -> str:
    return "⚠️ Введи <b>зріст числом</b>, наприклад <code>175</code>"


def msg_enter_height_range() -> str:
    return "⚠️ Перевір <b>зріст (см)</b> і спробуй ще раз."


mailing_text = (
    "<b>СТВОРЕННЯ ПОСТУ:</b>\n\n"
    "Ця функція дозволяє створити пост і розіслати його всім користувачам бота. "
    "Ви можете додати текст, фото, відео або документ, а також URL-кнопки для посилання на зовнішні ресурси. "
    "Після створення поста, ви зможете переглянути його і підтвердити розсилку.\n\n"
    "<b>Кроки для створення поста:</b>\n"
    "1. Надішліть текст, фото, відео або документ, який ви хочете розіслати.\n"
    "2. Додайте опис, якщо потрібно.\n"
    "3. Додайте URL-кнопки, якщо потрібно.\n"
    "4. Перегляньте пост і підтвердьте розсилку.\n\n"
    "<i>Після підтвердження розсилки, пост буде відправлено всім користувачам бота.</i>"
)
