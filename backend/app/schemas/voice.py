from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

VoiceCleanupContext = Literal[
    "scope_of_work",
    "internal_notes",
    "engineer_findings",
    "client_description",
    "manager_review_notes",
]


class ElevenLabsTokenResponse(BaseModel):
    token: str


class CleanTextRequest(BaseModel):
    text: str = Field(min_length=1)
    context: VoiceCleanupContext


class CleanTextResponse(BaseModel):
    text: str
