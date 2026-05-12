from datetime import date, datetime

from database_functions.client_db import conn, cursor


def create_ration_table() -> None:
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS ration_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id NUMERIC NOT NULL,
            entry_date TEXT NOT NULL,
            dish_name TEXT NOT NULL,
            calories REAL NOT NULL,
            protein REAL NOT NULL,
            fat REAL NOT NULL,
            carbs REAL NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.commit()


def add_ration_entry(
    user_id: int,
    entry_date: str,
    dish_name: str,
    calories: float,
    protein: float,
    fat: float,
    carbs: float,
) -> None:
    created = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        """
        INSERT INTO ration_entries (user_id, entry_date, dish_name, calories, protein, fat, carbs, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (user_id, entry_date, dish_name, calories, protein, fat, carbs, created),
    )
    conn.commit()


def get_ration_day_totals(user_id: int, entry_date: str) -> tuple[float, float, float, float, list[tuple[str, float]]]:
    cursor.execute(
        """
        SELECT dish_name, calories, protein, fat, carbs
        FROM ration_entries
        WHERE user_id = ? AND entry_date = ?
        ORDER BY id
        """,
        (user_id, entry_date),
    )
    rows = cursor.fetchall()
    total_kcal = total_p = total_f = total_c = 0.0
    items: list[tuple[str, float]] = []
    for name, kcal, p, f, c in rows:
        total_kcal += kcal
        total_p += p
        total_f += f
        total_c += c
        items.append((name, kcal))
    return total_kcal, total_p, total_f, total_c, items


def get_ration_days_with_entries(user_id: int, year: int, month: int) -> set[int]:
    month_start = date(year, month, 1)
    if month == 12:
        next_month_start = date(year + 1, 1, 1)
    else:
        next_month_start = date(year, month + 1, 1)
    cursor.execute(
        """
        SELECT DISTINCT CAST(strftime('%d', entry_date) AS INTEGER)
        FROM ration_entries
        WHERE user_id = ? AND entry_date >= ? AND entry_date < ?
        """,
        (user_id, month_start.isoformat(), next_month_start.isoformat()),
    )
    return {int(row[0]) for row in cursor.fetchall()}


def get_ration_entries_for_day(
    user_id: int, entry_date: str
) -> list[tuple[int, str, float, float, float, float]]:
    cursor.execute(
        """
        SELECT id, dish_name, calories, protein, fat, carbs
        FROM ration_entries
        WHERE user_id = ? AND entry_date = ?
        ORDER BY id
        """,
        (user_id, entry_date),
    )
    return cursor.fetchall()


def get_ration_entry(entry_id: int, user_id: int) -> tuple[int, str, str, float, float, float, float] | None:
    cursor.execute(
        """
        SELECT id, entry_date, dish_name, calories, protein, fat, carbs
        FROM ration_entries
        WHERE id = ? AND user_id = ?
        """,
        (entry_id, user_id),
    )
    return cursor.fetchone()


def update_ration_entry(
    entry_id: int,
    user_id: int,
    dish_name: str,
    calories: float,
    protein: float,
    fat: float,
    carbs: float,
) -> None:
    cursor.execute(
        """
        UPDATE ration_entries
        SET dish_name = ?, calories = ?, protein = ?, fat = ?, carbs = ?
        WHERE id = ? AND user_id = ?
        """,
        (dish_name, calories, protein, fat, carbs, entry_id, user_id),
    )
    conn.commit()
