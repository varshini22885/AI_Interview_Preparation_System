"""Strict WebSocket event contracts."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class FacePose(BaseModel):
    yaw: float = Field(ge=-90, le=90)
    pitch: float = Field(ge=-90, le=90)


class FaceStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["face_status"]
    timestamp: datetime
    face_present: bool
    face_count: int = Field(ge=0, le=2)
    head_pose: FacePose | None = None


class Heartbeat(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["heartbeat"]


class SessionStart(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["session_start"]


class SessionEnd(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["session_end"]


class AnswerComplete(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["answer_complete"]
    question_id: str
    transcript: str = Field(min_length=1, max_length=20000)
    idempotency_key: str = Field(min_length=8, max_length=128)


class AudioStart(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["audio_start"]


class AudioEnd(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["audio_end"]


class AudioChunk(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["audio_chunk"]
    data: str = Field(min_length=1, max_length=128000)


CLIENT_MESSAGES = (SessionStart, Heartbeat, SessionEnd, FaceStatus, AnswerComplete, AudioStart, AudioEnd, AudioChunk)
