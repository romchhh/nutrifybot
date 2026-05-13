#!/usr/bin/env python3
"""
Скрипт для повної перебудови бази знань ChromaDB.
Використовується після оновлення даних у Content/knowledge_base.py
"""

from utils.nutrition_kb import NutritionKnowledgeBase

if __name__ == "__main__":
    kb = NutritionKnowledgeBase()
    
    print("🔄 Перебудова бази знань...")
    count_before = kb.count()
    print(f"   Записів до перебудови: {count_before}")
    
    added = kb.rebuild()
    count_after = kb.count()
    
    print(f"✅ Перебудова завершена!")
    print(f"   Оброблено записів: {added}")
    print(f"   Всього у базі: {count_after}")
    
    # Перевірка конкретного запису
    grechka = kb.get_by_name("Гречка варена")
    if grechka:
        print(f"\n📊 Гречка варена (на 100 г):")
        print(f"   Калорії: {grechka['calories']} ккал")
        print(f"   Білки: {grechka['protein']} г")
        print(f"   Жири: {grechka['fat']} г")
        print(f"   Вуглеводи: {grechka['carbs']} г")
