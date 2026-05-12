import sqlite3
from datetime import datetime
from typing import Any


conn = sqlite3.connect("database/data.db")
cursor = conn.cursor()


def _ensure_column(table: str, column: str, definition: str) -> None:
    cursor.execute(f"PRAGMA table_info({table})")
    names = {row[1] for row in cursor.fetchall()}
    if column not in names:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def create_table():
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            user_id NUMERIC,
            user_name TEXT,
            user_first_name TEXT,
            user_last_name TEXT,
            user_phone TEXT,
            language TEXT,
            join_date TEXT,
            last_activity TEXT,
            ref_link INTEGER
        )
        """
    )
    conn.commit()

    for col, definition in (
        ("display_name", "TEXT"),
        ("age", "INTEGER"),
        ("sex", "TEXT"),
        ("weight", "REAL"),
        ("height", "REAL"),
        ("goal", "TEXT"),
        ("daily_calories", "INTEGER"),
        ("daily_protein", "REAL"),
        ("daily_fat", "REAL"),
        ("daily_carbs", "REAL"),
        ("registration_completed", "INTEGER DEFAULT 0"),
    ):
        _ensure_column("users", col, definition)

def add_user(
    user_id: str,
    user_name: str,
    user_first_name: str,
    user_last_name: str,
    language: str,
    ref_link: int | None = None,
):
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    existing_user = cursor.fetchone()
    if existing_user is None:
        current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            """
            INSERT INTO users (user_id, user_name, user_first_name, user_last_name, language, join_date, last_activity, ref_link)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                user_name,
                user_first_name,
                user_last_name,
                language,
                current_date,
                current_date,
                ref_link,
            ),
        )
        conn.commit()


def check_user(user_id: str) -> bool:
    cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
    return cursor.fetchone() is not None


def is_registration_complete(user_id: int) -> bool:
    cursor.execute(
        "SELECT registration_completed FROM users WHERE user_id = ?",
        (user_id,),
    )
    row = cursor.fetchone()
    if not row:
        return False
    return bool(row[0])


def update_user_activity(user_id: str) -> None:
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    cursor.execute(
        """
        UPDATE users
        SET last_activity = ?
        WHERE user_id = ?
        """,
        (current_time, user_id),
    )
    conn.commit()


def get_user_profile(user_id: int) -> dict[str, Any] | None:
    cursor.execute(
        """
        SELECT display_name, age, sex, weight, height, goal,
               daily_calories, daily_protein, daily_fat, daily_carbs, registration_completed
        FROM users WHERE user_id = ?
        """,
        (user_id,),
    )
    row = cursor.fetchone()
    if not row:
        return None
    keys = (
        "display_name",
        "age",
        "sex",
        "weight",
        "height",
        "goal",
        "daily_calories",
        "daily_protein",
        "daily_fat",
        "daily_carbs",
        "registration_completed",
    )
    return dict(zip(keys, row))


def save_profile_and_norm(
    user_id: int,
    *,
    display_name: str,
    age: int,
    sex: str,
    weight: float,
    height: float,
    goal: str,
    daily_calories: int,
    daily_protein: float,
    daily_fat: float,
    daily_carbs: float,
) -> None:
    cursor.execute(
        """
        UPDATE users SET
            display_name = ?,
            age = ?,
            sex = ?,
            weight = ?,
            height = ?,
            goal = ?,
            daily_calories = ?,
            daily_protein = ?,
            daily_fat = ?,
            daily_carbs = ?,
            registration_completed = 1
        WHERE user_id = ?
        """,
        (
            display_name,
            age,
            sex,
            weight,
            height,
            goal,
            daily_calories,
            daily_protein,
            daily_fat,
            daily_carbs,
            user_id,
        ),
    )
    conn.commit()


def get_user_id_by_username(username: str) -> Any:
    cursor.execute("SELECT user_id FROM users WHERE user_name = ?", (username,))
    result = cursor.fetchone()
    return result[0] if result else None


def get_username_by_user_id(user_id: str) -> Any:
    cursor.execute("SELECT user_name FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    return result[0] if result else None
