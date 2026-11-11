import io
from typing import List, Dict, Any, Optional
import pandas as pd
from app.core.security import sanitize_spreadsheet_cell
from app.core.logging import logger

EXPORT_COLUMNS = [
    "Company",
    "Contact Name",
    "Email",
    "Phone",
    "Website",
    "Sector",
    "Confidence",
    "Reason",
    "Status",
    "Duplicate Flag"
]


def format_lead_records_for_export(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Sanitizes each cell against formula injection and formats export fields."""
    sanitized_rows = []
    for r in records:
        row = {
            "Company": sanitize_spreadsheet_cell(r.get("company_name")),
            "Contact Name": sanitize_spreadsheet_cell(r.get("contact_name")),
            "Email": sanitize_spreadsheet_cell(r.get("email")),
            "Phone": sanitize_spreadsheet_cell(r.get("phone")),
            "Website": sanitize_spreadsheet_cell(r.get("website")),
            "Sector": sanitize_spreadsheet_cell(r.get("sector_name") or r.get("sector")),
            "Confidence": round(float(r.get("confidence") or 0.0), 2),
            "Reason": sanitize_spreadsheet_cell(r.get("classification_reason") or r.get("reason")),
            "Status": sanitize_spreadsheet_cell(r.get("status")),
            "Duplicate Flag": "Yes" if r.get("is_duplicate") else "No"
        }
        sanitized_rows.append(row)
    return sanitized_rows


def generate_csv_export(records: List[Dict[str, Any]]) -> bytes:
    """Generates sanitized CSV bytes."""
    formatted = format_lead_records_for_export(records)
    df = pd.DataFrame(formatted, columns=EXPORT_COLUMNS)
    output = io.StringIO()
    df.to_csv(output, index=False)
    return output.getvalue().encode("utf-8")


def generate_excel_export(records: List[Dict[str, Any]], split_by_sector: bool = True) -> bytes:
    """
    Generates Excel workbook (.xlsx) using openpyxl:
    - Sheet 1: 'All Leads'
    - Subsequent sheets: One sheet per distinct sector (if split_by_sector=True)
    """
    formatted = format_lead_records_for_export(records)
    df_all = pd.DataFrame(formatted, columns=EXPORT_COLUMNS)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_all.to_excel(writer, sheet_name="All Leads", index=False)

        if split_by_sector and not df_all.empty:
            # Group by sector
            sectors = df_all["Sector"].unique()
            for sec in sectors:
                sec_str = str(sec).strip() or "Unclassified"
                # Excel sheet names max 31 characters, no invalid chars like : \ / ? * [ ]
                safe_name = "".join(c for c in sec_str if c not in r":\/?*[]")[:31].strip() or "Sector"
                sec_df = df_all[df_all["Sector"] == sec]
                sec_df.to_excel(writer, sheet_name=safe_name, index=False)

    return output.getvalue()
