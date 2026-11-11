import pytest
from app.export.exporter import generate_csv_export, generate_excel_export
from app.core.security import sanitize_spreadsheet_cell


def test_sanitize_spreadsheet_formula_injection():
    # Should prepend single quote to prevent DDE / command execution
    assert sanitize_spreadsheet_cell("=1+1") == "'=1+1"
    assert sanitize_spreadsheet_cell("+cmd|' /C calc'!A0") == "'+cmd|' /C calc'!A0"
    assert sanitize_spreadsheet_cell("-2+3") == "'-2+3"
    assert sanitize_spreadsheet_cell("@SUM(A1:A10)") == "'@SUM(A1:A10)"
    assert sanitize_spreadsheet_cell("Normal Text") == "Normal Text"


def test_csv_and_excel_generation():
    records = [
        {
            "company_name": "=Malicious Corp",
            "contact_name": "Eve",
            "email": "eve@evil.com",
            "phone": "+1 555-0199",
            "website": "https://evil.com",
            "sector_name": "IT & Software",
            "confidence": 0.95,
            "classification_reason": "Cloud services",
            "status": "classified",
            "is_duplicate": False
        }
    ]
    csv_bytes = generate_csv_export(records)
    assert b"'=Malicious Corp" in csv_bytes

    xlsx_bytes = generate_excel_export(records, split_by_sector=True)
    assert len(xlsx_bytes) > 200
