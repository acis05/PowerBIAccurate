from datetime import date
from pydantic import BaseModel, ConfigDict


class UploadResponse(BaseModel):
    message: str


class TopEntry(BaseModel):
    name: str
    total_sales: float


class CompareEntry(BaseModel):
    name: str
    current_month: float
    previous_month: float
    change: float
    change_percent: float


class ChangeOverall(BaseModel):
    current_month_total: float
    previous_month_total: float
    change: float
    change_percent: float


class DashboardOut(BaseModel):
    period_start: date | None
    period_end: date | None
    total_sales: float
    customer_count: int

    top_customers: list[TopEntry]
    top_salesmen: list[TopEntry]
    top_items: list[TopEntry]

    salesman_compare: list[CompareEntry]
    item_compare: list[CompareEntry]

    overall_change: ChangeOverall

    model_config = ConfigDict(from_attributes=True)