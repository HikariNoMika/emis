import io
from openpyxl import load_workbook
from app.config import get_settings
from app.extensions import db
from app.services.measurement_service import export_source_xlsx

db.init(get_settings())
for sid in (1, 5):
    content = export_source_xlsx(sid)
    wb = load_workbook(io.BytesIO(content))
    ws = wb[wb.sheetnames[0]]
    rows = list(ws.values)
    header = rows[0]
    zero_rows = [r for r in rows[1:] if isinstance(r[0], str) and r[0].startswith('202') and all(isinstance(v, (int, float)) and v == 0 for v in r[1:] if v is not None) and any(v is not None for v in r[1:])]
    print(f'station {sid}: sheets={wb.sheetnames} rows={len(rows)} header={header}')
    print(f'  zero-filled gap rows: {len(zero_rows)}')
    print(f'  sample gap row: {zero_rows[0] if zero_rows else None}')
