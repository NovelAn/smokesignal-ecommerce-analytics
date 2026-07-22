"""Deterministic, privacy-safe chat preparation for AI Analysis V2."""

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Literal, Sequence


PHONE_RE = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")
LONG_ID_RE = re.compile(r"(?<!\d)\d{12,}(?!\d)")
URL_RE = re.compile(r"https?://\S+")
EMAIL_RE = re.compile(r"\b[^\s@]+@[^\s@]+\.[^\s@]+\b")


@dataclass(frozen=True)
class PreparedMessage:
    msg_time: datetime
    role: Literal["buyer", "service"]
    content: str


@dataclass(frozen=True)
class MessageWindow:
    messages: tuple[PreparedMessage, ...]
    new_messages: tuple[PreparedMessage, ...]
    context_messages: tuple[PreparedMessage, ...]
    fingerprint: str

    @property
    def source_from_msg_time(self) -> datetime:
        return self.new_messages[0].msg_time

    @property
    def source_to_msg_time(self) -> datetime:
        return self.new_messages[-1].msg_time

    @property
    def source_message_count(self) -> int:
        return len(self.new_messages)


def mask_content(content: str) -> str:
    content = URL_RE.sub("[链接]", str(content or ""))
    content = EMAIL_RE.sub("[邮箱]", content)
    content = PHONE_RE.sub("[手机号]", content)
    return LONG_ID_RE.sub("[长编号]", content).strip()


def fingerprint(
    messages: Sequence[PreparedMessage], prompt_version: str
) -> str:
    source = "\n".join(
        f"{message.msg_time.isoformat()}|{message.role}|{message.content}"
        for message in messages
    )
    return hashlib.sha256(f"{prompt_version}\n{source}".encode()).hexdigest()


def prepare_windows(
    buyer_nick: str,
    rows: Sequence[dict[str, Any]],
    checkpoint: datetime | None = None,
    context_limit: int = 20,
    prompt_version: str = "ai-analysis-v2.0",
    full_limit: int = 50,
) -> list[MessageWindow]:
    prepared = sorted(
        (
            message
            for row in rows
            if (message := _prepare_message(buyer_nick, row)) is not None
        ),
        key=lambda message: message.msg_time,
    )
    if checkpoint is None:
        new_messages = prepared[-full_limit:]
    else:
        new_messages = [
            message for message in prepared if message.msg_time > checkpoint
        ]
    if not new_messages:
        return []

    groups: list[list[PreparedMessage]] = []
    for message in new_messages:
        if not groups or message.msg_time - groups[-1][-1].msg_time > timedelta(hours=24):
            groups.append([message])
        else:
            groups[-1].append(message)

    windows = []
    for group in groups:
        context = (
            [message for message in prepared if message.msg_time < group[0].msg_time][
                -context_limit:
            ]
            if checkpoint is not None
            else []
        )
        messages = (*context, *group)
        windows.append(
            MessageWindow(
                messages=messages,
                new_messages=tuple(group),
                context_messages=tuple(context),
                fingerprint=fingerprint(messages, prompt_version),
            )
        )
    return windows


def _prepare_message(
    buyer_nick: str, row: dict[str, Any]
) -> PreparedMessage | None:
    content = mask_content(row.get("content", ""))
    if not content:
        return None
    raw_time = row.get("msg_time")
    msg_time = (
        raw_time
        if isinstance(raw_time, datetime)
        else datetime.fromisoformat(str(raw_time))
    )
    sender = row.get("sender_nick") or row.get("sender")
    return PreparedMessage(
        msg_time=msg_time,
        role="buyer" if sender == buyer_nick else "service",
        content=content,
    )
