import io
from openpyxl import load_workbook
from app.config import get_settings
from app.extensions import db
from app.services.measurement_service import export_source_xlsx

db.init(get_settings())
content = export_source_xlsx(1)
wb = load_workbook(io.BytesIO(content))
print("sheets:", wb.sheetnames)
ws = wb[wb.sheetnames[0]]
rows = list(ws.values)
print("total rows:", len(rows))
print("header:", rows[0])
print("first data:", rows[1])
# Check gap rows (Timestamp present, all measurement cells == 0)
zero_rows = [r for r in rows[1:] if all(isinstance(v, (int, float)) and v == 0 for v in r[1:])]
print("zero-filled rows:", len(zero_rows))
print("sample zero row:", zero_rows[0] if zero_rows else None)
