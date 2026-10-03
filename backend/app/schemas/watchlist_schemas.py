from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.core.utc_time import UtcDatetime


class WatchlistTickerCreate(BaseModel):
    ticker: str = Field(min_length=1, max_length=32)


class WatchlistTickerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticker: str
    added_at: UtcDatetime
