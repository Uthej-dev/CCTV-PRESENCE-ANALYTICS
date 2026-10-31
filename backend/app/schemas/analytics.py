from datetime import date, datetime

from pydantic import BaseModel


class HourlyBucket(BaseModel):
    hour: int  # 0-23 in the requested timezone
    visitors: int
    entries: int
    exits: int


class DailyAnalytics(BaseModel):
    date: date
    timezone: str
    visitors: int                  # people seen (sessions >= MIN_VISIT_SECONDS)
    entries: int                   # line crossings into the area
    exits: int
    avg_duration_seconds: float
    max_duration_seconds: float
    peak_occupancy: int            # max people in view at the same time
    peak_occupancy_time: datetime | None
    peak_hour: int | None          # hour with most visitors
    hourly: list[HourlyBucket]


class DaySummary(BaseModel):
    date: date
    visitors: int
    entries: int
    exits: int
    avg_duration_seconds: float
    peak_occupancy: int


class WeeklyAnalytics(BaseModel):
    start_date: date
    end_date: date
    timezone: str
    total_visitors: int
    total_entries: int
    total_exits: int
    avg_duration_seconds: float
    busiest_day: date | None
    peak_hour: int | None
    days: list[DaySummary]
    visitors_by_hour: list[int]    # 24 values, summed over the period


class OccupancyPoint(BaseModel):
    timestamp: datetime
    occupancy: int   # max people in view during the bucket
    inside: int      # max net occupancy (entries - exits) during the bucket


class OccupancySeries(BaseModel):
    start: datetime
    end: datetime
    interval_minutes: int
    timezone: str
    peak_occupancy: int
    points: list[OccupancyPoint]
