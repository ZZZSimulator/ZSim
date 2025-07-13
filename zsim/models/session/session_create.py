from datetime import datetime
from uuid import uuid4
from typing import Literal

from pydantic import BaseModel, Field

from .session_run import SessionRun
from .session_result import SessionResult


def generate_session_id() -> str:
    """Generate a unique session ID: YYYYMMDD + first 8 chars of uuid4."""
    date_str = datetime.now().strftime("%Y%m%d")
    uuid_part = str(uuid4())[:8]
    return f"{date_str}-{uuid_part}"


class Session(BaseModel):
    """Session configuration model."""

    session_id: str = Field(
        default_factory=generate_session_id, description="随机生成的会话ID，为本日日期+8位UUID前缀"
    )
    create_time: datetime = Field(
        default_factory=datetime.now, description="会话创建时间，默认当前时间"
    )
    session_run: SessionRun | None = None
    session_result: list[SessionResult] | None = None
    status: Literal["pending", "running", "completed", "stopped", "failed"] = Field(
        default="pending", description="会话状态"
    )


if __name__ == "__main__":
    print(Session())
