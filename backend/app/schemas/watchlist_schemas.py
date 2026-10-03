from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class WatchlistTickerCreate(BaseModel):
    ticker: str = Field(min_length=1, max_length=32)


class WatchlistTickerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticker: str
    added_at: datetime
