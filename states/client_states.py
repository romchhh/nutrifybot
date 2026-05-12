from aiogram.fsm.state import State, StatesGroup


class Registration(StatesGroup):
    name = State()
    age = State()
    sex = State()
    weight = State()
    height = State()
    goal = State()


class Ration(StatesGroup):
    pick_custom_date = State()
    add_dish_name = State()
    add_dish_macros = State()
    edit_dish_name = State()
    edit_dish_macros = State()


class CalorieCount(StatesGroup):
    waiting_input = State()      # чекаємо фото або текст
    pick_day_add = State()       # обираємо день для збереження
    custom_day_date = State() 

class ProfileEdit(StatesGroup):
    name = State()
    age = State()
    sex = State()
    weight = State()
    height = State()
    goal = State()
