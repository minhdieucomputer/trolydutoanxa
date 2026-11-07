"""Danh mục mã nguồn chi trích từ Công văn 15602; không tự suy diễn mã từ tên nguồn gốc dự toán."""
import csv,sys
from pathlib import Path
from budget_catalog import norm
FILE=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent))/'MA_NGUON_CHI_15602.csv'
def load_sources():
    if not FILE.exists():return []
    with FILE.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
SOURCES=load_sources()
BY_CODE={r['code']:r for r in SOURCES}
def suggest_source(description):
    q=norm(description)
    # Chỉ chọn khi ngữ cảnh mã nguồn rõ ràng; 'tăng thu' không phải mã nguồn 15.
    rules=[('27',['du toan tam ung','tam ung du toan']),('28',['kinh phi giu lai']),
           ('14',['cai cach tien luong','nguon cai cach tien luong']),
           ('16',['nghien cuu khoa hoc','de tai khoa hoc']),
           ('44',['von tu nguon su dung dat','nguon thu su dung dat']),
           ('45',['von xo so kien thiet','nguon xo so kien thiet'])]
    for code,terms in rules:
        if code in BY_CODE and any(t in q for t in terms):return BY_CODE[code]
    return None


def source_display_values():
    """Mã 99 là mặc định thao tác theo yêu cầu người dùng, không khẳng định là mã hợp lệ cho mọi nghiệp vụ."""
    return ['99 – Mặc định nhập liệu (cần xác minh theo nghiệp vụ)'] + [f"{r['code']} – {r['name']}" for r in SOURCES if r['code'] != '99']
