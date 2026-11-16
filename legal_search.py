"""Offline document retrieval. Never invents accounting entries."""
from pathlib import Path
import re, unicodedata, shutil
from datetime import datetime

LIBRARY = Path.home() / 'TroLyDuToanXa' / 'VanBanNghiepVu'
SUPPORTED = {'.pdf', '.docx', '.txt', '.doc'}

def normalized(s):
    s=unicodedata.normalize('NFD', str(s).lower().replace('đ','d'))
    return re.sub(r'\s+', ' ', ''.join(c for c in s if unicodedata.category(c)!='Mn')).strip()

def read_document(path):
    path=Path(path)
    ext=path.suffix.lower()
    if ext=='.pdf':
        from pypdf import PdfReader
        return [(f'Trang {i+1}', p.extract_text() or '') for i,p in enumerate(PdfReader(str(path)).pages)]
    if ext=='.docx':
        from docx import Document
        d=Document(str(path))
        blocks=[p.text for p in d.paragraphs if p.text.strip()]
        for table in d.tables:
            for row in table.rows:
                blocks.append(' | '.join(c.text for c in row.cells))
        return [('Noi dung', '\n'.join(blocks))]
    if ext=='.txt':
        return [('Noi dung', path.read_text(encoding='utf-8-sig',errors='replace'))]
    if ext=='.doc':
        # Legacy binary DOC cannot be parsed by python-docx; use a converted TXT/DOCX/PDF.
        raise ValueError('File .doc cu: hay mo bang Word, chon Save As .docx hoac PDF roi tai len.')
    raise ValueError('Dinh dang chua duoc ho tro: '+ext)

def import_file(path):
    path=Path(path)
    if path.suffix.lower() not in SUPPORTED: raise ValueError('Chi ho tro PDF, DOCX, TXT; DOC cu can chuyen doi.')
    sections=read_document(path)
    if not any(t.strip() for _,t in sections): raise ValueError('Khong trich duoc chu. PDF scan can OCR truoc.')
    LIBRARY.mkdir(parents=True,exist_ok=True)
    dest=LIBRARY/path.name
    if dest.exists() and dest.resolve()!=path.resolve():
        dest=LIBRARY/(path.stem+'_'+datetime.now().strftime('%Y%m%d_%H%M%S')+path.suffix)
    if dest.resolve()!=path.resolve(): shutil.copy2(path,dest)
    return dest

def list_files():
    LIBRARY.mkdir(parents=True,exist_ok=True)
    return sorted((p for p in LIBRARY.iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED),key=lambda p:p.name.lower())

def search(query, limit=25):
    tokens=[w for w in normalized(query).split() if len(w)>=3]
    if not tokens: return []
    found=[]
    for path in list_files():
        try: sections=read_document(path)
        except Exception: continue
        for location,raw in sections:
            # Group adjacent lines, retain original source wording for audit.
            lines=[x.strip() for x in raw.splitlines() if x.strip()]
            for i in range(len(lines)):
                fragment=' '.join(lines[max(0,i-2):min(len(lines),i+5)])[:1600]
                n=normalized(fragment)
                score=sum(2 if t in normalized(lines[i]) else 1 for t in tokens if t in n)
                if score:
                    found.append((score,path.name,location,fragment))
    found.sort(key=lambda x:-x[0])
    unique=[]; seen=set()
    for r in found:
        key=(r[1],r[2],r[3][:100])
        if key not in seen: unique.append(r);seen.add(key)
        if len(unique)>=limit:break
    return unique


def install_seed():
    import sys
    base=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent))
    seed=base/'legal_seed'/'CV_15602_BTC_KBNN_2017.txt'
    LIBRARY.mkdir(parents=True,exist_ok=True)
    target=LIBRARY/seed.name
    if seed.exists() and not target.exists(): shutil.copy2(seed,target)
