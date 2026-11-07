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

# Danh mục dự phòng nằm trực tiếp trong mã Python, hoạt động cả khi EXE
# bị thiếu CSV trong _MEIPASS hoặc file danh mục người dùng từ bản cũ rỗng.
BUILTIN_NAMES={
 '01':'Dự toán đầu năm', '02':'Dự toán bổ sung',
 '03':'Dự toán điều chỉnh theo quyết định của cấp có thẩm quyền',
 '04':'Dự toán chuyển sang năm tiếp theo', '06':'Dự toán năm trước chuyển sang',
 '08':'Dự toán tạm cấp', '09':'Dự toán ứng trước',
 '10':'Dự toán hủy bỏ', '11':'Dự toán tạm ứng',
 '19':'Dự toán điều chỉnh', '91':'Giảm trừ dự toán',
}
def builtin_rows():
    return [dict(code=code,name=name,source='CV 15602/BTC-KBNN – kiểm tra áp dụng',
                 keywords='',origins='',kinds='',note='Đối chiếu nghiệp vụ và văn bản hiện hành trước khi xuất')
            for code,name in BUILTIN_NAMES.items()]


def norm(value):
    text=unicodedata.normalize('NFD',str(value).lower().replace('đ','d'))
    return ' '.join(''.join(c for c in text if unicodedata.category(c)!='Mn').split())

class BudgetCatalog:
    def __init__(self):
        self.path=CATALOG
        self.reload()

    def reload(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        defaults=builtin_rows()
        if DEFAULT_CATALOG.exists():
            with DEFAULT_CATALOG.open('r',encoding='utf-8-sig',newline='') as f:
                csv_rows=[{k:(r.get(k) or '').strip() for k in HEADERS}
                          for r in csv.DictReader(f) if (r.get('code') or '').strip()]
                defaults=list({r['code']:r for r in defaults+csv_rows}.values())
        if not self.path.exists():
            with self.path.open('w',encoding='utf-8-sig',newline='') as f:
                writer=csv.DictWriter(f,fieldnames=HEADERS)
                writer.writeheader();writer.writerows(defaults)
        try:
            with self.path.open('r',encoding='utf-8-sig',newline='') as f:
                reader=csv.DictReader(f)
                rows=[{k:(r.get(k) or '').strip() for k in HEADERS}
                      for r in reader if (r.get('code') or '').strip()]
        except (OSError,UnicodeError,csv.Error,KeyError):
            rows=[]
        # Luôn có danh mục gốc trong bộ cài; bổ sung những mã thiếu từ các bản cũ.
        # Không ghi đè mã người dùng đã chỉnh sửa.
        by_code={r['code']:r for r in rows}
        # Các bản cũ có thể lưu dòng chỉ có mã, không có tên.
        missing=[r for r in defaults if r['code'] not in by_code or not by_code[r['code']]['name']]
        if missing:
            by_code.update({r['code']:r for r in missing})
            try:
                with self.path.open('w',encoding='utf-8-sig',newline='') as f:
                    writer=csv.DictWriter(f,fieldnames=HEADERS)
                    writer.writeheader();writer.writerows(by_code.values())
            except OSError:
                pass  # Danh mục tích hợp vẫn sử dụng được khi file bị khóa
        self.items=sorted(by_code.values(),key=lambda r:r['code'])
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
        # Nguồn gốc là trường nghiệp vụ độc lập: chỉ dùng khi diễn giải
        # chưa chỉ rõ một loại dự toán khác.
        o=norm(origin)
        if 'bo sung' in o:code='02'
        elif 'giao dau nam' in o:code='01'
        else:code=None
        if code:return self.by_code.get(code)
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
