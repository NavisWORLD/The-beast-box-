from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .models import LocalChatModel, Message

OWNER_PROFILE = """You are the local language model selected by the owner of this COSMOS/CST runtime.
Answer the owner's message directly and naturally. Use retrieved memory and measured software state as context when useful.
Do not claim that software persistence, autonomy, quantum provenance, or self-description proves consciousness.
Synthetic Beast Box capabilities are simulations; do not describe them as real host authority.
"""


@dataclass
class BackendTextProvider:
    backend: LocalChatModel

    def generate(self, prompt: str) -> str:
        return self.backend.complete(prompt)


class DirectChatSession:
    def __init__(self, backend: LocalChatModel, system_prompt: str = OWNER_PROFILE) -> None:
        self.backend = backend
        self.messages: list[Message] = []
        if system_prompt:
            self.messages.append({"role": "system", "content": system_prompt})

    def send(self, text: str) -> str:
        self.messages.append({"role": "user", "content": text})
        answer = self.backend.chat(self.messages)
        self.messages.append({"role": "assistant", "content": answer})
        return answer

    def history(self) -> Sequence[Message]:
        return tuple(self.messages)
