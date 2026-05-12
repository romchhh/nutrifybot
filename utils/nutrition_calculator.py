from typing import TypedDict


class NutritionPlan(TypedDict):
    calories: int
    protein: float
    fat: float
    carbs: float


def calculate_daily_norm(
    *,
    weight_kg: float,
    height_cm: float,
    age: int,
    sex: str,
    goal: str,
) -> NutritionPlan:
    if sex == "male":
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
    else:
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age - 161

    tdee = bmr * 1.375
    if goal == "lose":
        target_kcal = tdee * 0.85
        protein_per_kg = 2.0
    elif goal == "gain":
        target_kcal = tdee * 1.12
        protein_per_kg = 1.8
    else:
        target_kcal = tdee * 1.0
        protein_per_kg = 1.7

    calories = int(round(target_kcal))
    protein = round(weight_kg * protein_per_kg, 1)
    fat = round((calories * 0.28) / 9, 1)
    carb_kcal = calories - protein * 4 - fat * 9
    carbs = round(max(0.0, carb_kcal) / 4, 1)

    return NutritionPlan(
        calories=calories,
        protein=protein,
        fat=fat,
        carbs=carbs,
    )
