from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Health(BaseModel):
    status: Literal["ok", "degraded"]
    database: Literal["ok", "unreachable"]
    monitor: Literal["running", "stopped"]


class DomainStatus(BaseModel):
    hostname: str
    display_name: str
    is_up: bool | None
    last_checked_at: datetime | None
    status_code: int | None
    response_time_ms: int | None
    error: str | None
    uptime_1h: float | None
    uptime_24h: float | None
    checks_24h: int


class StatusResponse(BaseModel):
    generated_at: datetime
    interval_seconds: int
    domains: list[DomainStatus]


class CheckResultOut(BaseModel):
    checked_at: datetime
    is_up: bool
    status_code: int | None
    response_time_ms: int | None
    error: str | None


class ChecksResponse(BaseModel):
    hostname: str
    checks: list[CheckResultOut]


class ErrorOut(BaseModel):
    detail: str


class ChartPoint(BaseModel):
    t: datetime
    avg_ms: float | None
    max_ms: int | None
    checks: int
    down: int


class DowntimePeriod(BaseModel):
    started_at: datetime
    ended_at: datetime
    failed_checks: int
    errors: list[str]
    ongoing: bool


class Gap(BaseModel):
    started_at: datetime
    ended_at: datetime


class ChartSummary(BaseModel):
    down_periods: int
    total_downtime_seconds: int
    checks: int


class ChartResponse(BaseModel):
    hostname: str
    range: Literal["1h", "24h", "7d"]
    from_: datetime = Field(alias="from")
    to: datetime
    bucket_seconds: Literal[30, 300, 1800]
    points: list[ChartPoint]
    downtime: list[DowntimePeriod]
    gaps: list[Gap]
    summary: ChartSummary

    model_config = ConfigDict(populate_by_name=True)
