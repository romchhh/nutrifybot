from __future__ import annotations

import base64
import json
import logging
from dataclasses import dataclass, replace
from typing import Optional

from openai import AsyncOpenAI

from config import (
    OPENAI_API_KEY,
    OPENAI_FREQUENCY_PENALTY,
    OPENAI_MAX_COMPLETION_TOKENS,
    OPENAI_MODEL,
    OPENAI_PRESENCE_PENALTY,
    OPENAI_SEED,
    OPENAI_TEMPERATURE,
    OPENAI_TOP_P,
)
from utils.nutrition_kb import NutritionKnowledgeBase

logger = logging.getLogger(__name__)


def _user_content_for_log(user_content: list) -> list:
    """Strip huge base64 payloads from user message parts for structured logging."""
    out: list = []
    for part in user_content:
        if not isinstance(part, dict):
            out.append(part)
            continue
        if part.get("type") == "image_url":
            iu = part.get("image_url") or {}
            url = iu.get("url", "")
            if isinstance(url, str) and url.startswith("data:"):
                out.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"<omitted data URL length_chars={len(url)}>",
                        "detail": iu.get("detail"),
                    },
                })
            else:
                out.append(part)
        else:
            out.append(part)
    return out

# ---------------------------------------------------------------------------
# System prompt — з базою знань (RAG знайшов результати)
# ---------------------------------------------------------------------------
SYSTEM_PROMPT_WITH_KB = """\
Ти — точний нутриціолог та дієтолог. Твоя задача — проаналізувати страву та надати \
точну інформацію про калорійність та макронутрієнти.

КРИТИЧНО ВАЖЛИВО:
- Тобі надані ПЕРЕВІРЕНІ довідкові дані з бази знань (КБЖУ на 100г).
- Ти ЗОБОВ'ЯЗАНИЙ використовувати ці дані як основу розрахунку.
- НЕ вигадуй значення якщо є відповідний продукт в довідкових даних.
- Якщо страва складається з кількох інгредієнтів — сумуй їх внески пропорційно.
- Якщо конкретного продукту немає в базі — для чисел використовуй найближчий аналог з бази; \
  у полі notes не пояснюй це — там лише харчові поради для людини.

Правила розрахунку порції:
1. Якщо вага вказана явно — використовуй її.
2. Якщо не вказана — оціни стандартну порцію (суп 250мл=250г, каша 200г, м'ясо 150г тощо).
3. КБЖУ для порції = КБЖУ_на_100г × (вага_порції / 100).

Поле confidence (лише одне з рядків: high, medium, low):
- high — дані однозначні, порція та склад зрозумілі, довідкові збіги релевантні.
- medium — є припущення щодо порції, частини інгредієнтів або способу приготування.
- low — мало конкретики, висока невизначеність або слабкий збіг з довідником.

Поле notes (ОБОВ'ЯЗКОВО, 2–5 речень українською): лише практичні поради щодо харчування \
для людини — баланс БЖВ у прийомі їжі, клітковина, вода, помірність порцій, що доречно \
додати (овочі, білок), чого скоротити (соуси, цукор, смажене). Заборонено згадувати базу \
даних, довідник, RAG, модель, «типові значення» чи технічні причини оцінки. Не залишай notes порожнім.

Відповідай ТІЛЬКИ валідним JSON без жодного додаткового тексту.

Формат відповіді (суворо JSON):
{
  "name": "назва страви українською",
  "portion_g": число (вага порції в грамах),
  "calories": число (ккал для всієї порції),
  "protein": число (білки г для всієї порції),
  "fat": число (жири г для всієї порції),
  "carbs": число (вуглеводи г для всієї порції),
  "per_100g": {
    "calories": число,
    "protein": число,
    "fat": число,
    "carbs": число
  },
  "confidence": "high" | "medium" | "low",
  "kb_used": true,
  "notes": "2–5 речень: лише харчові поради, без згадки бази чи техніки"
}
"""

# ---------------------------------------------------------------------------
# System prompt — без бази знань (RAG нічого не знайшов)
# ---------------------------------------------------------------------------
SYSTEM_PROMPT_NO_KB = """\
Ти — точний нутриціолог та дієтолог. Твоя задача — проаналізувати страву та надати \
точну інформацію про калорійність та макронутрієнти на основі загальновідомих даних.

Правила:
1. Використовуй середньостатистичні значення КБЖУ з авторитетних джерел.
2. Якщо вага не вказана — оціни стандартну порцію.
3. Відповідай ТІЛЬКИ валідним JSON без жодного додаткового тексту.

Поле confidence (лише одне з рядків: high, medium, low):
- high — опис або фото дають чітку картину порції та складу.
- medium — є помірні припущення (розмір порції, невідомі добавки).
- low — дуже мало інформації або сильна невизначеність; оцінка груба.

Поле notes (ОБОВ'ЯЗКОВО, 2–5 речень українською): лише практичні поради щодо харчування \
(білки/жири/вуглеводи, клітковина, вода, помірність, корисні доповнення до страви). \
Заборонено згадувати базу даних, модель чи «загальні середні значення» як пояснення. Не залишай notes порожнім.

Формат відповіді (суворо JSON):
{
  "name": "назва страви українською",
  "portion_g": число,
  "calories": число (для порції),
  "protein": число (для порції),
  "fat": число (для порції),
  "carbs": число (для порції),
  "per_100g": {
    "calories": число,
    "protein": число,
    "fat": число,
    "carbs": число
  },
  "confidence": "high" | "medium" | "low",
  "kb_used": false,
  "notes": "2–5 речень: лише харчові поради"
}
"""


# Додається до system prompt лише для аналізу за фото.
SYSTEM_PROMPT_PHOTO_ADDENDUM = """\

УВАГА: у запиті є ФОТО страви (зображення видно моделі).

Поле confidence для фото:
- Дозволені ЛИШЕ значення "high" або "medium". Значення "low" заборонено: зображення дає \
  достатньо візуальної інформації для обґрунтованої оцінки порції та складу.
- "high" — страва, об'єм порції та основні інгредієнти добре видно.
- "medium" — частина страви закрита, невдалий ракурс або розмиття; оцінка все одно обґрунтована, але з більшими припущеннями.

Поле notes для фото — так само: лише харчові поради для людини, без згадки бази, довідника чи способу отримання цифр.
"""


@dataclass
class NutritionResult:
    name: str
    portion_g: float
    calories: float
    protein: float
    fat: float
    carbs: float
    per_100g: dict
    confidence: str
    kb_used: bool = False
    notes: str = ""

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "portion_g": self.portion_g,
            "calories": self.calories,
            "protein": self.protein,
            "fat": self.fat,
            "carbs": self.carbs,
            "per_100g": self.per_100g,
            "confidence": self.confidence,
            "kb_used": self.kb_used,
            "notes": self.notes,
        }


class CalorieAnalyzer:
    """
    Аналізує страву через GPT-4o.

    Потік:
      1. ОБОВ'ЯЗКОВИЙ multi_search по NutritionKnowledgeBase
      2. Якщо знайдено → System prompt з інструкцією використовувати KB
         Якщо не знайдено → System prompt без KB (загальні знання GPT)
      3. Результати KB вставляються в user prompt як структурований контекст
      4. GPT повертає JSON → NutritionResult

    Для фото: до system prompt додається блок (confidence лише high або medium); якщо модель
    повернула low, воно піднімається до medium.

    Використання:
        analyzer = CalorieAnalyzer()
        result = await analyzer.analyze_text("гречка з куркою 300г")
        result = await analyzer.analyze_photo(photo_bytes, caption="борщ")
    """

    MODEL = OPENAI_MODEL
    # Кількість результатів на компонент при multi_search
    RAG_TOP_K_PER_COMPONENT = 3
    # Максимум результатів що передаємо в GPT (щоб не перевантажувати prompt)
    RAG_MAX_CONTEXT_ITEMS = 8

    def __init__(
        self,
        api_key: Optional[str] = None,
        kb: Optional[NutritionKnowledgeBase] = None,
        temperature: float = OPENAI_TEMPERATURE,
        top_p: float = OPENAI_TOP_P,
        frequency_penalty: float = OPENAI_FREQUENCY_PENALTY,
        presence_penalty: float = OPENAI_PRESENCE_PENALTY,
        max_completion_tokens: int = OPENAI_MAX_COMPLETION_TOKENS,
        seed: int = OPENAI_SEED,
    ):
        self._client = AsyncOpenAI(api_key=api_key or OPENAI_API_KEY)
        self._kb = kb or NutritionKnowledgeBase()
        self._temperature = temperature
        self._top_p = top_p
        self._frequency_penalty = frequency_penalty
        self._presence_penalty = presence_penalty
        self._max_completion_tokens = max_completion_tokens
        self._seed = seed

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    async def analyze_text(self, text: str) -> NutritionResult:
        """Аналізує текстовий опис страви."""
        kb_items = self._rag_search(text)
        system_prompt = SYSTEM_PROMPT_WITH_KB if kb_items else SYSTEM_PROMPT_NO_KB
        user_content = self._build_text_prompt(text, kb_items)
        return await self._call_gpt(user_content, system_prompt)

    async def analyze_photo(
        self, photo_bytes: bytes, caption: str = ""
    ) -> NutritionResult:
        """Аналізує фото страви (+ необов'язковий підпис)."""
        # Для фото: спочатку шукаємо по підпису, якщо є
        search_query = caption if caption else "їжа страва"
        kb_items = self._rag_search(search_query)
        system_prompt = (SYSTEM_PROMPT_WITH_KB if kb_items else SYSTEM_PROMPT_NO_KB) + SYSTEM_PROMPT_PHOTO_ADDENDUM
        b64 = base64.b64encode(photo_bytes).decode()
        user_content = self._build_photo_prompt(b64, caption, kb_items)
        result = await self._call_gpt(user_content, system_prompt)
        return self._apply_photo_confidence_floor(result)

    @staticmethod
    def _apply_photo_confidence_floor(result: NutritionResult) -> NutritionResult:
        """Для фото не показуємо low: піднімаємо до medium (дублює інструкцію в промпті)."""
        if result.confidence != "low":
            return result
        logger.info(
            "CalorieAnalyzer photo confidence clamp low_to_medium name=%s",
            json.dumps(result.name, ensure_ascii=False),
        )
        return replace(result, confidence="medium")

    # ------------------------------------------------------------------ #
    #  RAG                                                                 #
    # ------------------------------------------------------------------ #

    def _rag_search(self, query: str) -> list[dict]:
        """
        ОБОВ'ЯЗКОВИЙ RAG-пошук через multi_search.
        Повертає топ-N найрелевантніших результатів.
        Логує що знайдено для дебагу.
        """
        if not self._kb:
            logger.warning("CalorieAnalyzer._rag_search knowledge_base missing")
            return []

        results = self._kb.multi_search(
            query,
            top_k_per_component=self.RAG_TOP_K_PER_COMPONENT,
        )

        results = results[: self.RAG_MAX_CONTEXT_ITEMS]

        logger.info(
            "CalorieAnalyzer._rag_search query=%s top_k_per_component=%d max_context_items=%d "
            "after_cap_count=%d context_items=%s",
            json.dumps(query, ensure_ascii=False),
            self.RAG_TOP_K_PER_COMPONENT,
            self.RAG_MAX_CONTEXT_ITEMS,
            len(results),
            json.dumps(results, ensure_ascii=False, default=str),
        )

        return results

    # ------------------------------------------------------------------ #
    #  Prompt builders                                                     #
    # ------------------------------------------------------------------ #

    def _build_text_prompt(self, text: str, kb_items: list[dict]) -> list:
        parts = [{"type": "text", "text": f"Страва для аналізу: {text}"}]
        if kb_items:
            parts.append({"type": "text", "text": self._format_kb_context(kb_items)})
        return parts

    def _build_photo_prompt(
        self, b64: str, caption: str, kb_items: list[dict]
    ) -> list:
        parts: list = [
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{b64}",
                    "detail": "high",
                },
            }
        ]
        if caption:
            parts.append(
                {"type": "text", "text": f"Підпис до фото: {caption}"}
            )
        if kb_items:
            parts.append(
                {"type": "text", "text": self._format_kb_context(kb_items)}
            )
        parts.append(
            {
                "type": "text",
                "text": (
                    "Визнач страву(и) на фото та надай точне КБЖУ у вказаному JSON-форматі. "
                    "Використовуй довідкові дані вище як основу розрахунку."
                    if kb_items
                    else "Визнач страву на фото та надай КБЖУ у вказаному JSON-форматі."
                ),
            }
        )
        return parts

    @staticmethod
    def _format_kb_context(items: list[dict]) -> str:
        """
        Форматує результати бази знань у структурований текст для prompt.
        Включає score для прозорості (GPT може врахувати релевантність).
        """
        lines = [
            "═══ ДОВІДКОВІ ДАНІ З БАЗИ ЗНАНЬ (КБЖУ на 100г) ═══",
            "Використовуй ці дані як ОСНОВУ для розрахунку. Дані відсортовані за релевантністю.\n",
        ]
        for item in items:
            score_pct = int(item.get("score", 0) * 100)
            category = item.get("category", "")
            lines.append(
                f"[{score_pct}% схожість | {category}] {item['name']}:\n"
                f"  Калорії: {item['calories']} ккал | "
                f"Б: {item['protein']}г | "
                f"Ж: {item['fat']}г | "
                f"В: {item['carbs']}г"
            )
        lines.append("\n═══════════════════════════════════════════════")
        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    #  GPT call                                                            #
    # ------------------------------------------------------------------ #

    async def _call_gpt(
        self, user_content: list, system_prompt: str
    ) -> NutritionResult:
        request_payload = {
            "model": self.MODEL,
            "max_tokens": self._max_completion_tokens,
            "temperature": self._temperature,
            "top_p": self._top_p,
            "frequency_penalty": self._frequency_penalty,
            "presence_penalty": self._presence_penalty,
            "seed": self._seed,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": _user_content_for_log(user_content)},
            ],
        }
        logger.info(
            "OpenAI chat.completions.create request=%s",
            json.dumps(request_payload, ensure_ascii=False, default=str),
        )

        try:
            response = await self._client.chat.completions.create(
                model=self.MODEL,
                max_tokens=self._max_completion_tokens,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                temperature=self._temperature,
                top_p=self._top_p,
                frequency_penalty=self._frequency_penalty,
                presence_penalty=self._presence_penalty,
                seed=self._seed,
                response_format={"type": "json_object"},
            )
            try:
                response_body = response.model_dump()
            except AttributeError:
                response_body = {"repr": repr(response)}
            logger.info(
                "OpenAI chat.completions.create response=%s",
                json.dumps(response_body, ensure_ascii=False, default=str),
            )

            raw = response.choices[0].message.content or "{}"
            data = json.loads(raw)
            result = self._parse_result(data)

            logger.info(
                "CalorieAnalyzer._call_gpt parsed_result=%s",
                json.dumps(result.as_dict(), ensure_ascii=False),
            )
            return result

        except Exception:
            logger.exception("OpenAI chat.completions.create failed")
            raise

    @staticmethod
    def _parse_result(data: dict) -> NutritionResult:
        per_100g = data.get("per_100g") or {
            "calories": 0, "protein": 0, "fat": 0, "carbs": 0,
        }
        raw_conf = str(data.get("confidence", "medium") or "medium").strip().lower()
        if raw_conf not in ("high", "medium", "low"):
            raw_conf = "medium"
        return NutritionResult(
            name=data.get("name", "Невідома страва"),
            portion_g=float(data.get("portion_g", 300)),
            calories=float(data.get("calories", 0)),
            protein=float(data.get("protein", 0)),
            fat=float(data.get("fat", 0)),
            carbs=float(data.get("carbs", 0)),
            per_100g=per_100g,
            confidence=raw_conf,
            kb_used=bool(data.get("kb_used", False)),
            notes=data.get("notes", ""),
        )