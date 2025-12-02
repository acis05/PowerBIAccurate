from __future__ import annotations

import re
from datetime import datetime, date as _date

from bs4 import BeautifulSoup

from . import models

# ===================== HELPER =====================

# Map singkatan bulan Accurate -> Inggris 3 huruf
MONTH_MAP = {
    "JAN": "Jan",
    "FEB": "Feb",
    "MAR": "Mar",
    "APR": "Apr",
    "MEI": "May",
    "MAY": "May",
    "JUN": "Jun",
    "JUL": "Jul",
    "AGU": "Aug",
    "AUG": "Aug",
    "SEP": "Sep",
    "OKT": "Oct",
    "OCT": "Oct",
    "NOP": "Nov",
    "NOV": "Nov",
    "DES": "Dec",
    "DEC": "Dec",
}


def parse_date_id(raw: str) -> _date | None:
    """
    Parse tanggal Accurate:
    '06 Jan 2025', '27 Nop 2025', dsb.
    """
    raw = raw.strip()
    parts = raw.split()
    if len(parts) != 3:
        return None
    try:
        d = int(parts[0])
        m_key = parts[1][:3].upper()
        y = int(parts[2])
        m_eng = MONTH_MAP.get(m_key, m_key.title())
        return datetime.strptime(f"{d} {m_eng} {y}", "%d %b %Y").date()
    except Exception:
        return None


_amount_re = re.compile(r"[^\d.,-]")


def parse_amount(text: str) -> float | None:
    """
    Baca angka gaya Indonesia / US, dengan trik khusus:
    - '3,850,000'  -> 3850000.0  (koma = ribuan)
    - '100,000'    -> 100000.0
    - '3,850,000.00' -> 3850000.0
    - '3.850.000,00' -> 3850000.0
    - '-260,000'   -> -260000.0
    """
    if not text:
        return None

    s = text.strip()
    s = _amount_re.sub("", s)  # sisakan digit, . , , dan -
    if not s:
        return None

    # Tangani minus
    negative = s.startswith("-")
    core = s[1:] if negative else s

    # Posisi semua pemisah (.,)
    seps = [i for i, ch in enumerate(core) if ch in ".,"]

    if seps:
        last = seps[-1]
        digits_after = len(core) - last - 1
        sep_chars = {core[i] for i in seps}

        # 🔴 Kasus seperti '3,850,000' atau '100,000'
        #    -> hanya ada 1 jenis pemisah, dan selalu 3 digit di belakang pemisah terakhir
        #    -> anggap SEMUA pemisah = pemisah ribuan, BUKAN desimal
        if digits_after == 3 and len(sep_chars) == 1:
            digits_only = re.sub(r"[.,]", "", core)
            if negative:
                digits_only = "-" + digits_only
            try:
                return float(digits_only)
            except Exception:
                return None

    # ------ fallback: logika umum (yang lama) ------

    last_dot = core.rfind(".")
    last_comma = core.rfind(",")
    dec_index = max(last_dot, last_comma)

    # tidak ada . atau , -> integer biasa
    if dec_index == -1:
        try:
            return float("-" + core if negative else core)
        except Exception:
            return None

    out_chars: list[str] = []
    for i, ch in enumerate(core):
        if ch in ".,":  # kandidat pemisah
            if i == dec_index:
                out_chars.append(".")  # desimal
            else:
                continue  # ribuan -> buang
        else:
            out_chars.append(ch)

    out = "".join(out_chars)
    if negative:
        out = "-" + out
    try:
        return float(out)
    except Exception:
        return None


# ===================== FUNGSI UTAMA =====================


def import_sales_html(html_bytes: bytes, db) -> None:
    """
    Import laporan HTML format:
    'Tgl Faktur | Customer | Salesman | Item | Qty | [Unit] | Amount | No. Faktur'

    Contoh baris (sesuai file kamu):
    ['06 Jan 2025', 'Multi Jaya Makmur', 'Fajar',
     'Besi Beton Diameter 10mm - 12m', '1', 'btg', '100,000', 'inv001']

    Atau (tanpa unit):
    ['27 Nop 2025', 'CASH IDR', 'Ersyah',
     'Potong Rambut Dewasa', '1', '50,000', 'inv004']
    """

    # ---- decode & parse HTML ----
    html = html_bytes.decode("utf-8", errors="ignore")
    soup = BeautifulSoup(html, "html.parser")

    # (Opsional) ambil periode dari header, tapi untuk dashboard kita pakai invoice_date per baris
    full_text = soup.get_text(" ", strip=True)
    _ = full_text  # tidak dipakai dulu

    # ---- Hapus semua data lama ----
    db.query(models.SalesDetail).delete()

    table = soup.find("table")
    if not table:
        db.commit()
        return

    for tr in table.find_all("tr"):
        tds = tr.find_all("td")
        if not tds:
            continue

        raw_texts = [td.get_text(strip=True) for td in tds]
        # buang kosong / spasi
        clean = [t.replace("\xa0", "").strip() for t in raw_texts if t and t.strip()]
        if len(clean) < 6:
            continue

        # Header utama
        if "Tgl Faktur" in clean and "Customer" in clean and "Salesman" in clean:
            continue

        # Coba parse tanggal di kolom pertama
        invoice_date = parse_date_id(clean[0])
        if invoice_date is None:
            # baris total / footer, skip
            continue

        # Struktur ideal:
        # 0: tanggal
        # 1: customer
        # 2: salesman
        # 3: item
        # 4: qty
        # ... [unit?]
        # -2: amount
        # -1: invoice_no

        if len(clean) < 7:
            # minimal: [tgl, cust, sales, item, qty, amount, no]
            continue

        customer_name = clean[1]
        salesman_name = clean[2]
        item_name = clean[3]

        qty = parse_amount(clean[4])

        amount = parse_amount(clean[-2])
        if amount is None:
            continue

        invoice_no = clean[-1]

        rec = models.SalesDetail(
            customer_name=customer_name,
            salesman_name=salesman_name,
            item_name=item_name,
            invoice_no=invoice_no,
            invoice_date=invoice_date,
            qty=qty,
            amount=amount,
        )
        db.add(rec)

    db.commit()