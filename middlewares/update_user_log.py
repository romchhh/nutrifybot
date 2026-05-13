"""Логування обробки update з Telegram user id (доповнення до стандартного виводу aiogram)."""

from __future__ import annotations

import logging
import time
from typing import Any, Awaitable, Callable, Optional

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update

logger = logging.getLogger("nutrify.update")


def _user_id_from_update(update: Update) -> Optional[int]:
    pairs = (
        ("message", "from_user"),
        ("edited_message", "from_user"),
        ("channel_post", "from_user"),
        ("edited_channel_post", "from_user"),
        ("business_message", "from_user"),
        ("edited_business_message", "from_user"),
        ("inline_query", "from_user"),
        ("chosen_inline_result", "from_user"),
        ("callback_query", "from_user"),
        ("shipping_query", "from_user"),
        ("pre_checkout_query", "from_user"),
        ("poll_answer", "user"),
        ("my_chat_member", "from_user"),
        ("chat_member", "from_user"),
        ("chat_join_request", "from_user"),
    )
    for part_attr, user_attr in pairs:
        part = getattr(update, part_attr, None)
        if part is None:
            continue
        u = getattr(part, user_attr, None)
        if u is not None:
            return u.id
    return None


class UpdateUserLogMiddleware(BaseMiddleware):
    """Один рядок на update: id, тривалість, bot id, user id (як у aiogram + user id)."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        start = time.perf_counter()
        try:
            return await handler(event, data)
        finally:
            if isinstance(event, Update):
                bot = data.get("bot")
                bot_id = bot.id if bot is not None else 0
                uid = _user_id_from_update(event)
                elapsed_ms = (time.perf_counter() - start) * 1000
                user_part = str(uid) if uid is not None else "n/a"
                logger.info(
                    "Update id=%s is handled. Duration %.0f ms by bot id=%s user id=%s",
                    event.update_id,
                    elapsed_ms,
                    bot_id,
                    user_part,
                )
