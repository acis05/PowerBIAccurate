from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Generator

from fastapi import FastAPI, Depends, File, UploadFile, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from .database import SessionLocal, engine, Base
from . import models, schemas
from .sales_import_html import import_sales_html

# Buat tabel
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Power BI Accurate")

# Static files (HTML, JS, CSS)
app.mount("/static", StaticFiles(directory="app/static"), name="static")


# =============== DEPENDENCY DB ===============

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =============== ROUTES ===============

@app.get("/", response_class=HTMLResponse)
def read_root():
    # Sesuaikan kalau index.html ada di lokasi lain
    return FileResponse("app/static/index.html")


# ---- Upload HTML ----

@app.post("/api/upload/sales-html", response_model=schemas.UploadResponse)
async def upload_sales_html_endpoint(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not file.filename.lower().endswith(".html"):
        raise HTTPException(status_code=400, detail="Harap upload file HTML laporan Accurate.")

    content = await file.read()
    import_sales_html(content, db)
    return schemas.UploadResponse(message="Berhasil diimport.")


# Alias untuk kompatibel dengan JS lama: /api/upload/sales
@app.post("/api/upload/sales", response_model=schemas.UploadResponse)
async def upload_sales_alias(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    content = await file.read()
    import_sales_html(content, db)
    return schemas.UploadResponse(message="Berhasil diimport.")


# ---- Helper agregasi dashboard ----

def build_dashboard(rows: list[models.SalesDetail]) -> schemas.DashboardOut:
    if not rows:
        return schemas.DashboardOut(
            period_start=None,
            period_end=None,
            total_sales=0.0,
            customer_count=0,
            top_customers=[],
            top_salesmen=[],
            top_items=[],
            salesman_compare=[],
            item_compare=[],
            overall_change=schemas.ChangeOverall(
                current_month_total=0.0,
                previous_month_total=0.0,
                change=0.0,
                change_percent=0.0,
            ),
        )

    dates = [r.invoice_date for r in rows if r.invoice_date is not None]
    if dates:
        period_start = min(dates)
        period_end = max(dates)
    else:
        period_start = None
        period_end = None

    total_sales = sum(r.amount or 0.0 for r in rows)
    customers = {r.customer_name for r in rows if r.customer_name}
    customer_count = len(customers)

    def top_n(key_func, n=10):
        agg = defaultdict(float)
        for r in rows:
            k = key_func(r)
            if not k:
                continue
            agg[k] += r.amount or 0.0
        sorted_items = sorted(agg.items(), key=lambda x: x[1], reverse=True)
        return [
            schemas.TopEntry(name=name, total_sales=value)
            for name, value in sorted_items[:n]
        ]

    top_customers = top_n(lambda r: r.customer_name)
    top_salesmen = top_n(lambda r: r.salesman_name)
    top_items = top_n(lambda r: r.item_name)

    # --- Perbandingan bulan ini vs bulan lalu ---
    if dates:
        base = max(dates)
    else:
        base = date.today()

    this_y, this_m = base.year, base.month
    if this_m == 1:
        prev_y, prev_m = this_y - 1, 12
    else:
        prev_y, prev_m = this_y, this_m - 1

    def compare_by(key_func):
        data = defaultdict(lambda: {"cur": 0.0, "prev": 0.0})
        for r in rows:
            if not r.invoice_date:
                continue
            k = key_func(r)
            if not k:
                continue
            y, m = r.invoice_date.year, r.invoice_date.month
            if (y, m) == (this_y, this_m):
                data[k]["cur"] += r.amount or 0.0
            elif (y, m) == (prev_y, prev_m):
                data[k]["prev"] += r.amount or 0.0

        result: list[schemas.CompareEntry] = []
        for name, d in data.items():
            cur = d["cur"]
            prev = d["prev"]
            change = cur - prev
            if prev != 0:
                change_pct = (change / prev) * 100.0
            else:
                change_pct = 0.0 if cur == 0 else 100.0
            result.append(
                schemas.CompareEntry(
                    name=name,
                    current_month=cur,
                    previous_month=prev,
                    change=change,
                    change_percent=change_pct,
                )
            )

        result.sort(key=lambda x: x.change, reverse=True)
        return result

    salesman_compare = compare_by(lambda r: r.salesman_name)
    item_compare = compare_by(lambda r: r.item_name)

    # --- Overall change ---
    cur_total = 0.0
    prev_total = 0.0
    for r in rows:
        if not r.invoice_date:
            continue
        y, m = r.invoice_date.year, r.invoice_date.month
        if (y, m) == (this_y, this_m):
            cur_total += r.amount or 0.0
        elif (y, m) == (prev_y, prev_m):
            prev_total += r.amount or 0.0

    overall_change_val = cur_total - prev_total
    if prev_total != 0:
        overall_change_pct = (overall_change_val / prev_total) * 100.0
    else:
        overall_change_pct = 0.0 if cur_total == 0 else 100.0

    overall_change = schemas.ChangeOverall(
        current_month_total=cur_total,
        previous_month_total=prev_total,
        change=overall_change_val,
        change_percent=overall_change_pct,
    )

    return schemas.DashboardOut(
        period_start=period_start,
        period_end=period_end,
        total_sales=total_sales,
        customer_count=customer_count,
        top_customers=top_customers,
        top_salesmen=top_salesmen,
        top_items=top_items,
        salesman_compare=salesman_compare,
        item_compare=item_compare,
        overall_change=overall_change,
    )


# ---- API DASHBOARD ----

@app.get("/api/dashboard/sales", response_model=schemas.DashboardOut)
def get_dashboard(db: Session = Depends(get_db)):
    rows = db.query(models.SalesDetail).all()
    return build_dashboard(rows)


# Endpoint tambahan kalau JS butuh khusus
@app.get("/api/dashboard/sales-by-salesman", response_model=list[schemas.TopEntry])
def get_sales_by_salesman(db: Session = Depends(get_db)):
    rows = db.query(models.SalesDetail).all()
    dash = build_dashboard(rows)
    return dash.top_salesmen


@app.get("/api/dashboard/sales-by-item", response_model=list[schemas.TopEntry])
def get_sales_by_item(db: Session = Depends(get_db)):
    rows = db.query(models.SalesDetail).all()
    dash = build_dashboard(rows)
    return dash.top_items