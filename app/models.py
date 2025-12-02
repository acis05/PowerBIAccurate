from datetime import datetime, date

from sqlalchemy import Column, Integer, String, Float, Date, DateTime
from sqlalchemy.orm import Mapped

from .database import Base


class SalesDetail(Base):
    __tablename__ = "sales_detail"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)

    customer_name: Mapped[str | None] = Column(String, index=True, nullable=True)
    salesman_name: Mapped[str | None] = Column(String, index=True, nullable=True)
    item_name: Mapped[str | None] = Column(String, index=True, nullable=True)
    invoice_no: Mapped[str | None] = Column(String, nullable=True)

    invoice_date: Mapped[date | None] = Column(Date, index=True, nullable=True)
    qty: Mapped[float | None] = Column(Float, nullable=True)
    amount: Mapped[float | None] = Column(Float, default=0.0)

    created_at: Mapped[datetime] = Column(
        DateTime, default=datetime.utcnow, nullable=False
    )