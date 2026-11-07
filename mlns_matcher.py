"""So khớp diễn giải với danh mục Loại/Khoản từ văn bản người dùng cung cấp.
Đây là đề xuất hỗ trợ, không tự xác nhận mã hạch toán.
"""
import csv, re, unicodedata
from pathlib import Path
import sys
from difflib import SequenceMatcher

CATALOG_PATH = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent)) / 'mlns_loai_khoan.csv'
EXCLUDED = {'121','314','315'}  # Bãi bỏ theo TT123/2026, không tự gợi ý
SYNONYMS = {
 '071':['mam non','nha tre','mau giao'],
 '072':['tieu hoc','truong cap 1'],
 '073':['trung hoc co so','thcs'],
 '074':['trung hoc pho thong','thpt'],
 '075':['giao duc thuong xuyen','giao duc nghe nghiep'],
 '131':['y te du phong'],
 '132':['kham benh','chua benh','kham chua benh'],
}

def normalize(text):
    s=unicodedata.normalize('NFD',str(text).lower().replace('đ','d'))
    return ' '.join(re.sub(r'[^a-z0-9 ]+',' ', ''.join(c for c in s if unicodedata.category(c)!='Mn')).split())

def load_catalog():
    with CATALOG_PATH.open(encoding='utf-8-sig',newline='') as f:
        return list(csv.DictReader(f))

CATALOG=load_catalog()
BY_CODE={r['khoan']:r for r in CATALOG}

def rank(description,limit=12):
    q=normalize(description)
    if not q:return []
    words=set(q.split());result=[]
    for row in CATALOG:
        if row['khoan'] in EXCLUDED:continue
        name=normalize(row['ten']);note=normalize(row['ghi_chu'])
        name_words=set(name.split())-{'va','cac','cho','cua','khac','hoat','dong'}
        overlap=len(words & name_words)/max(len(name_words),1)
        phrases=[name]+SYNONYMS.get(row['khoan'],[])
        hits=[p for p in phrases if len(p)>3 and p in q]
        score=round(70*overlap+35*(max(map(len,hits))/max(len(name),1) if hits else 0)+ (12 if any(p in q for p in SYNONYMS.get(row['khoan'],[])) else 0),1)
        # Ghi chú là ngữ cảnh hỗ trợ, không lấy các cụm 'không bao gồm' làm tín hiệu khẳng định.
        positive=note.split('khong bao gom')[0].split('tru ')[0]
        note_terms=set(positive.split())-{'bao','gom','cac','cho','cua','va','theo','trong','duoc','ngan','sach','nha','nuoc','hoat','dong','chi'}
        if len(words & note_terms)>=2:score+=min(12,2*len(words & note_terms))
        if score<15:continue
        result.append({'loai':row['loai'],'khoan':row['khoan'],'ten':row['ten'],
                       'ghi_chu':row['ghi_chu'],'score':round(min(score,99),1),
                       'match':', '.join(hits[:2]) or 'từ ngữ liên quan',
                       'tinh_trang':row['tinh_trang']})
    return sorted(result,key=lambda r:(-r['score'],r['khoan']))[:limit]

def auto_candidate(description):
    hits=rank(description,2)
    # Không tự chốt khi thiếu độ tin cậy hoặc nhiều mã gần điểm nhau.
    if not hits:return None
    # Tên ngành hoặc từ đồng nghĩa chính xác có thể được đề xuất với ngưỡng thấp hơn.
    top=hits[0]
    exact_synonym=any(normalize(alias) in normalize(description) for alias in SYNONYMS.get(top['khoan'],[]) if len(alias)>3)
    if top['score']<(60 if exact_synonym else 70):return None
    if len(hits)>1 and hits[0]['score']-hits[1]['score']<18:return None
    return hits[0]
