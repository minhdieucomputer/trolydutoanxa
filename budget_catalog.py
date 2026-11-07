"""Danh mục mã loại dự toán: không phát sinh mã chưa được kiểm chứng."""
import csv
import sys
import unicodedata
from pathlib import Path
import tkinter as tk

DATA_DIR=Path.home()/'TroLyDuToanXa'
CATALOG=DATA_DIR/'danh_muc_ma_loai_du_toan.csv'
DEFAULT_CATALOG=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent))/'MA_LOAI_DU_TOAN_HUONG_DAN.csv'
HEADERS=['code','name','source','keywords','origins','kinds','note']

def norm(value):
    text=unicodedata.normalize('NFD',str(value).lower().replace('đ','d'))
    return ' '.join(''.join(c for c in text if unicodedata.category(c)!='Mn').split())

class BudgetCatalog:
    def __init__(self):
        self.path=CATALOG
        self.reload()

    def reload(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        if not self.path.exists():
            with self.path.open('w',encoding='utf-8-sig',newline='') as f:
                writer=csv.DictWriter(f,fieldnames=HEADERS)
                writer.writeheader()
                if DEFAULT_CATALOG.exists():
                    with DEFAULT_CATALOG.open('r',encoding='utf-8-sig',newline='') as seed:
                        for item in csv.DictReader(seed):
                            writer.writerow({key:item.get(key,'') for key in HEADERS})
        with self.path.open('r',encoding='utf-8-sig',newline='') as f:
            self.items=[{k:(row.get(k) or '').strip() for k in HEADERS}
                        for row in csv.DictReader(f) if (row.get('code') or '').strip()]
        # Nạp bổ sung mã mặc định khi người dùng đã có file CSV rỗng từ bản cũ.
        existing={item['code'] for item in self.items}
        if DEFAULT_CATALOG.exists():
            with DEFAULT_CATALOG.open('r',encoding='utf-8-sig',newline='') as seed:
                additions=[{k:(r.get(k) or '').strip() for k in HEADERS} for r in csv.DictReader(seed) if r.get('code') and r['code'] not in existing]
            if additions:
                with self.path.open('a',encoding='utf-8-sig',newline='') as f:
                    writer=csv.DictWriter(f,fieldnames=HEADERS);writer.writerows(additions)
                self.items.extend(additions)
        self.items.sort(key=lambda r:r['code'])
        self.by_code={item['code']:item for item in self.items}

    def codes(self):return set(self.by_code)
    def get(self,code):return self.by_code.get(self.extract_code(code))
    def display_values(self):return [f"{r['code']} – {r['name']}" for r in self.items]
    def extract_code(self,text):return str(text).split(' – ')[0].strip()

    def match(self,description,origin,kind):
        q=norm(description)
        if any(t in q for t in ('giam tru du toan','thu hoi theo kien nghi kiem toan','thu hoi theo kien nghi thanh tra')): code='91'
        elif any(t in q for t in ('du toan tam ung','tam ung du toan')):code='11'
        elif any(t in q for t in ('du toan ung truoc','ung truoc du toan')):code='09'
        elif any(t in q for t in ('du toan tam cap','tam cap du toan')):code='08'
        elif any(t in q for t in ('du toan huy bo','huy bo du toan')):code='10'
        elif any(t in q for t in ('nam truoc chuyen sang','nguon nam truoc chuyen sang','du toan chuyen nguon nam truoc')):code='06'
        elif any(t in q for t in ('chuyen sang nam sau','chuyen sang nam tiep theo')):code='04'
        elif any(t in q for t in ('dieu chinh sau chuyen nguon','dieu chinh sau khu so du am')):code='19'
        elif 'dieu chinh' in q:code='03'
        elif any(t in q for t in ('du toan dau nam','giao dau nam','giao du toan dau nam','du toan giao dau nam')):code='01'
        elif any(t in q for t in ('bo sung du toan','du toan bo sung','giao bo sung','bo sung kinh phi','bo sung tu nguon')):code='02'
        else:code=None
        if code:return self.by_code.get(code)
        q=norm(description)
        q=norm(description)
        o=norm(origin)
        k=norm(kind)
        results=[]
        for item in self.items:
            keywords=[norm(x) for x in item['keywords'].split(';') if x.strip()]
            origins=[norm(x) for x in item['origins'].split(';') if x.strip()]
            kinds=[norm(x) for x in item['kinds'].split(';') if x.strip()]
            if not keywords and not origins and not kinds:continue
            if keywords and not any(x in q for x in keywords):continue
            if origins and not any(x in o for x in origins):continue
            if kinds and not any(x in k for x in kinds):continue
            score=sum(len(x) for x in keywords if x in q)+len(origins)*3+len(kinds)*3
            results.append((score,item))
        results.sort(key=lambda pair:pair[0],reverse=True)
        # Không tự chọn khi nhiều mã cùng độ ưu tiên.
        if len(results)>1 and results[0][0]==results[1][0]:return None
        return results[0][1] if results else None

def infer_origin(description):
    q=norm(description)
    if not q:return None
    if 'chuyen nguon' in q or 'nam truoc chuyen sang' in q:return 'Chuyển nguồn'
    if 'du phong' in q:return 'Dự phòng'
    if 'tang thu' in q:
        return 'Nguồn đầu tư phát triển từ tăng thu' if any(x in q for x in ('dau tu','xay dung co ban','dtxd')) else 'Tăng thu'
    if 'bo sung' in q:return 'Bổ sung dự toán'
    if any(x in q for x in ('dau tu','xay dung co ban','dtxd')):return 'Nguồn đầu tư phát triển giao đầu năm'
    if 'thuong xuyen' in q or 'giao dau nam' in q:return 'Giao đầu năm / thường xuyên'
    return None

class HoverTip:
    def __init__(self,widget,text_fn):
        self.widget=widget;self.text_fn=text_fn;self.popup=None
        widget.bind('<Enter>',self.show,add='+')
        widget.bind('<Leave>',self.hide,add='+')
        widget.bind('<FocusOut>',self.hide,add='+')
    def show(self,event=None):
        self.hide()
        value=self.text_fn()
        if not value:return
        try:
            popup=tk.Toplevel(self.widget);popup.wm_overrideredirect(True)
            popup.wm_geometry(f'+{self.widget.winfo_rootx()+15}+{self.widget.winfo_rooty()+self.widget.winfo_height()+3}')
            tk.Label(popup,text=value,justify='left',wraplength=480,bg='#fff7d6',fg='#252525',
                     relief='solid',bd=1,padx=9,pady=7,font=('Segoe UI',9)).pack()
            self.popup=popup
        except tk.TclError:pass
    def hide(self,event=None):
        if self.popup:
            try:self.popup.destroy()
            except tk.TclError:pass
            self.popup=None
