"""Geração de títulos descritivos para novos chats."""

from __future__ import annotations

import datetime
import re
import secrets
from typing import Iterable

_ADJECTIVES: Iterable[str] = (
    "Ideias",
    "Insights",
    "Exploracoes",
    "Analises",
    "Descobertas",
    "Planos",
    "Solucoes",
    "Conceitos",
    "Estrategias",
    "Curiosidades",
)

_TOPICS: Iterable[str] = (
    "Criativas",
    "Tecnologicas",
    "de Produto",
    "de Negocios",
    "de Conteudo",
    "de Pesquisa",
    "Educacionais",
    "Colaborativas",
    "Experimentais",
    "de Aprendizado",
)

_TIME_LABELS = {
    "manha": "Matinais",
    "tarde": "da Tarde",
    "noite": "Noturnas",
}

_MAX_TITLE_LEN = 60
_MAX_WORDS_FROM_SEED = 6


def _periodo_do_dia(now: datetime.datetime) -> str:
    hora = now.hour
    if 5 <= hora < 12:
        return _TIME_LABELS["manha"]
    if 12 <= hora < 18:
        return _TIME_LABELS["tarde"]
    return _TIME_LABELS["noite"]


def _choice(options: Iterable[str]) -> str:
    options = tuple(options)
    if not options:
        raise ValueError("Options list must not be empty")
    return secrets.choice(options)


def generate_chat_title(seed_text: str | None = None) -> str:
    """Retorna um título amigável explorando o texto inicial quando disponível."""

    if seed_text:
        candidate = _title_from_seed(seed_text)
        if candidate:
            return candidate

    now = datetime.datetime.now()
    periodo = _periodo_do_dia(now)
    first = _choice(_ADJECTIVES)
    second = _choice(_TOPICS)

    base = f"{first} {second}"
    return f"{base} {periodo}".strip()


def _title_from_seed(seed_text: str) -> str:
    normalized = " ".join(seed_text.strip().split())
    if not normalized:
        return ""

    sentence = re.split(r"[.!?]", normalized, maxsplit=1)[0].strip()
    sentence = sentence or normalized

    words = sentence.split()
    excerpt = " ".join(words[:_MAX_WORDS_FROM_SEED])
    excerpt = excerpt[:_MAX_TITLE_LEN].rstrip(" ,;:-")

    if not excerpt:
        return ""

    return excerpt[0].upper() + excerpt[1:]


__all__ = ["generate_chat_title"]
