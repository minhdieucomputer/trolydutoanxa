from funding_inference import analyze as analyze_funding
"""Trợ lý dự toán ngân sách xã — bản thử nghiệm, không kết nối TABMIS."""
import csv
import unicodedata
import json
import os
import sys
import shutil
import webbrowser
from urllib.parse import urlencode
import sqlite3
import tempfile
import time
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from datetime import datetime

APP_DIR = Path.home() / 'TroLyDuToanXa'
APP_DIR.mkdir(parents=True, exist_ok=True)
DB = APP_DIR / 'du_toan_xa.sqlite3'


def connect():
    con = sqlite3.connect(DB)
    con.execute('PRAGMA foreign_keys=ON')
    con.execute('''CREATE TABLE IF NOT EXISTS communes(id INTEGER PRIMARY KEY, name TEXT NOT NULL,
        area_code TEXT, qhns TEXT, org_code TEXT, treasury TEXT, UNIQUE(name, area_code))''')
    con.execute('''CREATE TABLE IF NOT EXISTS vouchers(id INTEGER PRIMARY KEY, commune_id INTEGER NOT NULL,
        year INTEGER NOT NULL, date TEXT NOT NULL, kind TEXT NOT NULL, description TEXT NOT NULL,
        amount INTEGER NOT NULL, budget_level TEXT, account_debit TEXT, account_credit TEXT,
        budget_type TEXT, chapter TEXT, sector_type TEXT, sector_item TEXT, econ_item TEXT,
        source_code TEXT, status TEXT NOT NULL DEFAULT 'DỰ THẢO', legal_note TEXT,
        FOREIGN KEY(commune_id) REFERENCES communes(id))''')
    if 'origin' not in [c[1] for c in con.execute('PRAGMA table_info(vouchers)')]:
        con.execute("ALTER TABLE vouchers ADD COLUMN origin TEXT DEFAULT ''")
    con.commit()
    return con

FIELDS = ['date','kind','description','amount','budget_level','account_debit','account_credit',
          'budget_type','chapter','sector_type','sector_item','econ_item','source_code']
LABELS = ['Ngày chứng từ (YYYY-MM-DD)','Nghiệp vụ','Diễn giải','Số tiền (VND)','Cấp ngân sách',
          'Tài khoản Nợ','Tài khoản Có','Mã loại dự toán','Mã Chương','Mã Loại',
          'Mã Khoản','Tiểu mục','Mã nguồn NSNN']
KINDS = ['Nhập dự toán cấp 0','Phân bổ cấp 0 → cấp 1','Phân bổ cấp 1 → cấp 4',
         'Bổ sung dự toán','Điều chỉnh tăng','Điều chỉnh giảm','Điều chỉnh sai mã/số tiền','Khác']

# Quy tắc chỉ phục vụ tham khảo, trích từ Công văn 15602/BTC-KBNN (2017).
# Không tự động áp dụng cho niên độ 2026 khi chưa được xác nhận hiệu lực.
REFERENCE = {
 'Nhập dự toán cấp 0': 'Phụ lục II, mục 1: mã NDKT 9999, địa bàn 99999, Chương 999; tài khoản cấp 0 tùy tính chất dự toán (ví dụ 9213, 9216).',
 'Phân bổ cấp 0 → cấp 1': 'Phụ lục II, mục 1–2: cấp 0 dùng mã tổ chức ngân sách; cấp 1 dùng mã ĐVQHNS được giao, Chương tương ứng.',
 'Phân bổ cấp 1 → cấp 4': 'Phụ lục II, mục 2–3: cấp 1 dùng NDKT 9999; cấp 4 dùng NDKT 0000, địa bàn 00000 và Khoản chi tiết.',
 'Điều chỉnh tăng': 'Phụ lục V, mục 1.4.2 và 2.5.2: bổ sung theo đúng quy trình phân bổ.',
 'Điều chỉnh giảm': 'Phụ lục V, mục 1.4.2 và 2.5.2: định khoản đảo chiều tùy phân hệ, trạng thái và mã KBNN.',
 'Điều chỉnh sai mã/số tiền': 'Phụ lục V, mục 1.4.1 và 2.5.1: cần phân biệt bút toán đã kết sổ, cùng/khác KBNN.',
}

# Danh mục được đọc từ Phụ lục II VBHN TT130/2025 và TT123/2026.
from mlns_matcher import CATALOG as MLNS_CATALOG, BY_CODE as MLNS_BY_CODE, rank as rank_mlns, auto_candidate
SECTORS=[(r['loai'],r['khoan'],r['ten'],'') for r in MLNS_CATALOG if r['khoan'] not in ('121','314','315')]

# Các tình huống đã trích từ CV 15602 và tài liệu nhập cấp 0; ngoài các tình huống này không đoán định khoản.
ORIGIN_RULES={
 'Giao đầu năm / thường xuyên':{'debit':'9213','credit':'9111','guide':'Ví dụ nhập cấp 0 chi thường xuyên: Nợ 9213 / Có 9111. Căn cứ hướng dẫn phương pháp kế toán tại CV 15602; chỉ áp dụng khi đúng bản chất nguồn và cấp.'},
 'Tăng thu':{'debit':'9213','credit':'9151','guide':'Ví dụ nguồn tăng thu dành cho chi thường xuyên: Nợ 9213 / Có 9151. Với đầu tư phát triển hoặc nghiệp vụ khác phải tra cứu quy tắc khác.'},
 'Dự phòng':{'debit':'','credit':'','guide':'Cần xác định chi thường xuyên/đầu tư và quyết định sử dụng dự phòng; chưa tự suy ra tài khoản nguồn.'},
 'Chuyển nguồn':{'debit':'','credit':'','guide':'Cần phân biệt năm trước chuyển sang và nguồn năm hiện hành; chưa có quy tắc đủ điều kiện để tự điền.'},
 'Bổ sung dự toán':{'debit':'','credit':'','guide':'Phân biệt bổ sung cân đối, có mục tiêu, tăng thu hoặc dự phòng trước khi định khoản.'},
 'Nguồn đầu tư phát triển giao đầu năm':{'debit':'9216','credit':'9111','guide':'Ví dụ nhập cấp 0 chi đầu tư phát triển: Nợ 9216 / Có 9111 theo hướng dẫn CV 15602.'},
 'Nguồn đầu tư phát triển từ tăng thu':{'debit':'9216','credit':'9151','guide':'Ví dụ nhập cấp 0 chi đầu tư phát triển từ tăng thu: Nợ 9216 / Có 9151 theo hướng dẫn CV 15602.'},
}
ORIGINAL_FORMS={
 'C6-01':'1.C6-01 (Phieu nhap DTNS).DOC',
 'C6-02':'2.C6-02 Phieu nhap DT C0(1).xls',
 'C6-03':'3.C6-03 Chung tu phan bo du toan.xls',
 'C6-04':'4.C6-04 (Phieu dieu chinh du toan)(1).DOC',
}

def normalize(text):
    text=unicodedata.normalize('NFD',text.lower().replace('đ','d'))
    return ' '.join(''.join(ch for ch in text if unicodedata.category(ch)!='Mn').split())

def find_sectors(description):
    return [(r['score'],r['loai'],r['khoan'],r['ten'],r['match']) for r in rank_mlns(description)]


# Danh mục mã loại dự toán có thể bổ sung qua CSV, không tự đặt mã số chưa xác minh.
from budget_catalog import BudgetCatalog, HoverTip, infer_origin
from source_catalog import SOURCES, BY_CODE as SOURCE_BY_CODE, suggest_source, source_display_values
BUDGET_CATALOG = BudgetCatalog()

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('TRỢ LÝ DỰ TOÁN NGÂN SÁCH XÃ — 0.8.9.6')
        self.geometry('1350x870')
        self.minsize(960, 640)
        self.con = connect()
        self.communes = {}
        self.selected_id = None
        style = ttk.Style(self)
        if 'clam' in style.theme_names(): style.theme_use('clam')
        style.configure('Title.TLabel',font=('Segoe UI',17,'bold'))
        style.configure('TButton',padding=7)
        top = ttk.Frame(self,padding=14); top.pack(fill='x')
        ttk.Label(top,text='TRỢ LÝ DỰ TOÁN NGÂN SÁCH XÃ',style='Title.TLabel').pack(anchor='w')
        ttk.Label(top,text='KHO BẠC NHÀ NƯỚC KHU VỰC IV-PHÒNG GIAO DỊCH SỐ 4',font=('Segoe UI', 11, 'bold'),foreground='#17456d').pack(anchor='w',pady=(3,0))
        ttk.Label(top,text='Tác giả: Đoàn Minh Điều-Mai Thị Huế',font=('Segoe UI', 10, 'bold'),foreground='#17456d').pack(anchor='w',pady=(1,4))
        ttk.Label(top,text='Nhiều xã/phường • Dữ liệu lưu tại máy • Định khoản chỉ được xác nhận sau kiểm tra nghiệp vụ',foreground='#555').pack(anchor='w')
        choose = ttk.Frame(self,padding=(14,0,14,8)); choose.pack(fill='x')
        ttk.Label(choose,text='Xã/phường đang làm việc:').pack(side='left')
        self.commune_var=tk.StringVar()
        self.commune_box=ttk.Combobox(choose,textvariable=self.commune_var,state='readonly',width=48)
        self.commune_box.pack(side='left',padx=8)
        self.commune_box.bind('<<ComboboxSelected>>',lambda e:self.refresh_vouchers())
        ttk.Button(choose,text='Quản lý xã/phường',command=self.manage_communes).pack(side='left')
        ttk.Button(choose,text='Sao lưu dữ liệu',command=self.backup).pack(side='left',padx=8)
        ttk.Button(choose,text='Khôi phục dữ liệu',command=self.restore_backup).pack(side='left',padx=4)
        ttk.Button(choose,text='Thoát',command=self.safe_exit).pack(side='right')
        ttk.Button(choose,text='Gửi ý kiến phản hồi',command=self.show_feedback).pack(side='right',padx=8)
        self.protocol('WM_DELETE_WINDOW',self.safe_exit)
        self.tabs=ttk.Notebook(self); self.tabs.pack(fill='both',expand=True,padx=14,pady=5)
        self.tab_entry=ttk.Frame(self.tabs,padding=12); self.tabs.add(self.tab_entry,text='Nhập nghiệp vụ')
        self.tab_history=ttk.Frame(self.tabs,padding=12); self.tabs.add(self.tab_history,text='Lịch sử / Xuất phiếu')
        self.tab_catalog=ttk.Frame(self.tabs,padding=12); self.tabs.add(self.tab_catalog,text='Tra cứu MLNS / Gợi ý mã ngành')
        self.tab_batch=ttk.Frame(self.tabs,padding=12); self.tabs.add(self.tab_batch,text='Bộ 3 chứng từ / Phụ lục QĐ')
        self.tab_guide=ttk.Frame(self.tabs,padding=12); self.tabs.add(self.tab_guide,text='Hướng dẫn hạch toán')
        self.make_entry(); self.apply_origin(); self.make_history(); self.make_catalog(); self.make_batch(); self.make_guide(); self.refresh_communes()

    def show_feedback(self):
        """Soạn phản hồi trên máy; chỉ mở ứng dụng email khi người dùng xác nhận."""
        win = tk.Toplevel(self)
        win.title('Gửi ý kiến phản hồi / Hỗ trợ phần mềm')
        win.geometry('690x510')
        win.minsize(550, 420)
        win.transient(self)
        panel = ttk.Frame(win, padding=18)
        panel.pack(fill='both', expand=True)
        ttk.Label(panel, text='GỬI Ý KIẾN PHẢN HỒI', font=('Segoe UI', 14, 'bold')).pack(anchor='w')
        ttk.Label(panel, text='Email tiếp nhận: dieudm@vst.gov.vn').pack(anchor='w', pady=(10, 2))
        ttk.Label(panel, text='Điện thoại hỗ trợ: 0983.036.248').pack(anchor='w', pady=(0, 14))
        ttk.Label(panel, text='Tiêu đề phản hồi:').pack(anchor='w')
        subject = tk.StringVar(value='Góp ý phần mềm Trợ lý dự toán ngân sách xã')
        ttk.Entry(panel, textvariable=subject).pack(fill='x', pady=(3, 12))
        ttk.Label(panel, text='Nội dung góp ý / mô tả lỗi:').pack(anchor='w')
        content = tk.Text(panel, wrap='word', height=10, font=('Segoe UI', 10))
        content.pack(fill='both', expand=True, pady=(3, 8))
        ttk.Label(panel, text='Nút Gửi mở ứng dụng email mặc định; bạn kiểm tra và nhấn Gửi trong ứng dụng email.',
                  foreground='#555', wraplength=620).pack(anchor='w', pady=(0, 10))
        actions = ttk.Frame(panel)
        actions.pack(fill='x')
        def draft():
            title = subject.get().strip()
            body = content.get('1.0', 'end-1c').strip()
            if not title or not body:
                messagebox.showwarning('Thiếu thông tin', 'Vui lòng nhập tiêu đề và nội dung phản hồi.', parent=win)
                return None
            return title, body
        def send():
            data = draft()
            if not data: return
            url = 'mailto:dieudm@vst.gov.vn?' + urlencode({'subject': data[0], 'body': data[1]})
            try:
                opened = webbrowser.open(url)
                if not opened:
                    messagebox.showwarning('Chưa mở được email', 'Không mở được ứng dụng email mặc định. Hãy dùng nút Sao chép nội dung để gửi thủ công.', parent=win)
            except Exception as exc:
                messagebox.showerror('Lỗi mở email', f'Không thể mở ứng dụng email: {exc}', parent=win)
        def copy_feedback():
            data = draft()
            if not data: return
            win.clipboard_clear()
            win.clipboard_append(f'Đến: dieudm@vst.gov.vn\nTiêu đề: {data[0]}\n\n{data[1]}')
            win.update()
            messagebox.showinfo('Đã sao chép', 'Đã sao chép phản hồi. Bạn có thể dán vào email để gửi.', parent=win)
        ttk.Button(actions, text='Mở email để gửi', command=send).pack(side='left')
        ttk.Button(actions, text='Sao chép nội dung', command=copy_feedback).pack(side='left', padx=8)
        ttk.Button(actions, text='Đóng', command=win.destroy).pack(side='right')

    def refresh_communes(self):
        rows=self.con.execute('SELECT id,name,area_code FROM communes ORDER BY name').fetchall()
        self.communes={f'{name} | {area or "chưa có mã địa bàn"} | ID {cid}':cid for cid,name,area in rows}
        self.commune_box['values']=list(self.communes)
        if self.commune_var.get() not in self.communes:
            self.commune_var.set(next(iter(self.communes),'(Chưa có xã/phường)'))
        self.refresh_vouchers()

    def commune_id(self): return self.communes.get(self.commune_var.get())

    def manage_communes(self):
        win=tk.Toplevel(self);win.title('Thêm xã/phường');win.geometry('500x370');win.transient(self)
        names=['Tên xã/phường (*)','Mã địa bàn','Mã ĐVQHNS','Mã tổ chức ngân sách','Mã KBNN']
        ent=[]
        for i,n in enumerate(names):
            ttk.Label(win,text=n).grid(row=i,column=0,sticky='w',padx=12,pady=12)
            e=ttk.Entry(win,width=34);e.grid(row=i,column=1,padx=12,pady=8);ent.append(e)
        def save():
            vals=[e.get().strip() for e in ent]
            if not vals[0]:return messagebox.showwarning('Thiếu dữ liệu','Nhập tên xã/phường.',parent=win)
            try:
                self.con.execute('INSERT INTO communes(name,area_code,qhns,org_code,treasury) VALUES(?,?,?,?,?)',vals)
                self.con.commit();win.destroy();self.refresh_communes()
            except sqlite3.IntegrityError:messagebox.showerror('Trùng','Xã/phường và mã địa bàn đã tồn tại.',parent=win)
        ttk.Button(win,text='Lưu xã/phường',command=save).grid(row=5,column=1,sticky='e',padx=12,pady=10)

    def make_entry(self):
        # Nút thao tác quan trọng luôn ở đầu tab, không bị đẩy ra ngoài màn hình.
        quick=ttk.Frame(self.tab_entry)
        quick.pack(fill='x',pady=(0,8))
        ttk.Button(quick,text='➕ ĐƯA NGHIỆP VỤ VÀO PHIẾU / QĐ',command=self.add_entry_to_package).pack(side='left',padx=(0,8))
        ttk.Button(quick,text='Xem bộ phiếu / Quyết định',command=self.open_package).pack(side='left',padx=(0,8))
        ttk.Button(quick,text='Xem trước nghiệp vụ',command=self.preview_current_entry).pack(side='left')
        main=ttk.Frame(self.tab_entry);main.pack(fill='both',expand=True)
        left=ttk.Frame(main);left.pack(side='left',fill='both',expand=True)
        self.vars={k:tk.StringVar() for k in FIELDS}
        self.vars['date'].set(datetime.now().strftime('%Y-%m-%d'))
        self.vars['kind'].set(KINDS[0]);self.vars['budget_level'].set('4')
        self.vars['source_code'].set('99')  # Mặc định người dùng yêu cầu; cần xác minh mã nguồn trước khi xuất chính thức
        self.origin=tk.StringVar(value='Giao đầu năm / thường xuyên')
        self.decision_total=tk.StringVar(value='')  # Tổng tiền nhập tại tab Bộ phiếu / Quyết định
        self.field_widgets={}
        self.style=ttk.Style(self)
        self.style.configure('Review.TCombobox', fieldbackground='#ffe2e2', foreground='#9d1010')
        self.style.map('Review.TCombobox', fieldbackground=[('readonly','#ffe2e2')], foreground=[('readonly','#9d1010')])
        self.style.configure('NormalReview.TCombobox', fieldbackground='white')
        visible_fields=[(k,label) for k,label in zip(FIELDS,LABELS) if k!='econ_item']
        for i,(k,label) in enumerate(visible_fields):
            ttk.Label(left,text=label).grid(row=i,column=0,sticky='w',pady=5)
            if k=='kind': widget=ttk.Combobox(left,textvariable=self.vars[k],values=KINDS,state='readonly',width=49)
            elif k=='source_code': widget=ttk.Combobox(left,textvariable=self.vars[k],values=source_display_values(),width=49,state='readonly')
            elif k=='budget_type': widget=ttk.Combobox(left,textvariable=self.vars[k],values=BUDGET_CATALOG.display_values(),width=49,state='readonly')
            elif k in ('sector_type','sector_item'): widget=ttk.Combobox(left,textvariable=self.vars[k],values=[],width=49,state='readonly')
            elif k=='chapter': widget=ttk.Combobox(left,textvariable=self.vars[k],values=['999','800','819','820','821','822','823','829','830','831'],width=49)
            elif k in ('account_debit','account_credit'): widget=ttk.Combobox(left,textvariable=self.vars[k],values=['9213','9216','9111','9151','9219','9233','9229','9239','9241'],width=49)
            else:widget=ttk.Entry(left,textvariable=self.vars[k],width=52)
            widget.grid(row=i,column=1,sticky='ew',padx=10,pady=5)
            self.field_widgets[k]=widget
            if k in ('budget_type','chapter','sector_type','sector_item','account_debit','account_credit','source_code'):
                HoverTip(widget, lambda key=k: self.describe_code(key))
            if k=='source_code':widget.bind('<<ComboboxSelected>>',lambda e:self.on_source_selected())
            if k=='budget_type':
                widget.bind('<<ComboboxSelected>>', lambda e:self.on_budget_type_selected())
            if k=='sector_item': widget.bind('<<ComboboxSelected>>',lambda e:self.on_sector_item_selected())
            if k=='sector_type': widget.bind('<<ComboboxSelected>>',lambda e:self.on_sector_type_selected())
        origin_row=len(FIELDS)
        ttk.Label(left,text='Nguồn gốc cấp dự toán').grid(row=origin_row,column=0,sticky='w',pady=5)
        origin_box=ttk.Combobox(left,textvariable=self.origin,state='readonly',width=49,values=list(ORIGIN_RULES))
        origin_box.grid(row=origin_row,column=1,sticky='ew',padx=10,pady=5)
        origin_box.bind('<<ComboboxSelected>>',lambda e:self.apply_origin())
        HoverTip(origin_box, lambda: ORIGIN_RULES.get(self.origin.get(),{}).get('guide','Chọn nguồn dự toán'))
        self.decision_total.trace_add('write',lambda *_:self.update_package_reconciliation() if hasattr(self,'batch_rows') else None)
        ttk.Button(left,text='Danh sách mã loại dự toán / tra cứu',command=self.open_budget_catalog).grid(
            row=origin_row+1,column=0,columnspan=2,sticky='w',pady=3)
        ttk.Button(left,text='Nạp lại danh mục CSV',command=self.reload_budget_catalog).grid(
            row=origin_row+2,column=0,columnspan=2,sticky='w',pady=3)
        self._auto_suggestion={'sector':None,'budget':None,'source':None}
        self.review_text=tk.StringVar(value='Chưa nhập diễn giải. Các ô cần kiểm tra sẽ được tô đỏ.')
        ttk.Label(left,textvariable=self.review_text,foreground='#9d1010',wraplength=600).grid(row=origin_row+3,column=0,columnspan=2,sticky='w',pady=4)
        self.populate_sector_lists()
        for key in ('budget_type','source_code','sector_item','chapter','account_debit','account_credit'):
            self.field_widgets[key].bind('<<ComboboxSelected>>',lambda e:self.after_idle(self.refresh_review_flags),add='+')
        self.vars['description'].trace_add('write',lambda *_:self.update_keyword_hints())
        self.vars['kind'].trace_add('write',lambda *_:self.apply_origin())
        left.columnconfigure(1,weight=1)
        controls=ttk.Frame(left);controls.grid(row=len(FIELDS)+4,column=0,columnspan=2,sticky='w',pady=12)
        ttk.Button(controls,text='Gợi ý tài khoản và mã',command=self.apply_origin).pack(side='left',padx=4)
        ttk.Button(controls,text='Mở mẫu C6 gốc',command=self.open_original_forms).pack(side='left',padx=4)
        ttk.Button(controls,text='Xem hướng dẫn nghiệp vụ',command=self.suggest).pack(side='left')
        ttk.Button(controls,text='Gợi ý mã ngành từ diễn giải',command=self.suggest_sector).pack(side='left',padx=8)
        ttk.Button(controls,text='Kiểm tra và lưu dự thảo',command=self.save_voucher).pack(side='left',padx=8)
        ttk.Button(controls,text='Đưa nghiệp vụ vào phiếu / QĐ',command=self.add_entry_to_package).pack(side='left',padx=8)
        ttk.Button(controls,text='Xem trước nghiệp vụ',command=self.preview_current_entry).pack(side='left',padx=5)
        ttk.Button(controls,text='Xem bộ phiếu / Quyết định',command=self.open_package).pack(side='left',padx=8)
        right=ttk.LabelFrame(main,text='Căn cứ và lưu ý kiểm soát',padding=12);right.pack(side='left',fill='both',expand=True,padx=(16,0))
        self.guidance=tk.Text(right,wrap='word',width=44,height=25,font=('Segoe UI',10))
        self.guidance.pack(fill='both',expand=True)
        self.set_guidance('Chọn nghiệp vụ và bấm “Xem hướng dẫn nghiệp vụ”.\n\nỨng dụng KHÔNG tự điền tài khoản Nợ/Có khi thiếu dữ liệu nghiệp vụ hoặc chưa xác minh hiệu lực văn bản.')
        self.refresh_review_flags()

    def populate_sector_lists(self, matches=None):
        """Danh sách Loại/Khoản: ưu tiên gợi ý, vẫn cho chọn mọi mã hợp lệ."""
        all_rows=[r for r in MLNS_CATALOG if r['khoan'] not in ('121','314','315')]
        ordered=[]; seen=set()
        for hit in (matches or []):
            code=hit[2]
            if code not in seen and code in MLNS_BY_CODE:
                ordered.append(MLNS_BY_CODE[code]);seen.add(code)
        ordered.extend(r for r in all_rows if r['khoan'] not in seen)
        self.field_widgets['sector_item']['values']=[f"{r['khoan']} – {r['ten']}" for r in ordered]
        loai_names={}
        for r in all_rows:
            loai_names.setdefault(r['loai'],r.get('ten_loai') or 'Lĩnh vực '+r['loai'])
        self.field_widgets['sector_type']['values']=[f'{code} – {name}' for code,name in sorted(loai_names.items())]

    def on_sector_item_selected(self):
        raw=self.vars['sector_item'].get()
        code=raw.split(' – ')[0].strip()
        self.vars['sector_item'].set(code)
        row=MLNS_BY_CODE.get(code)
        if row:
            self.vars['sector_type'].set(row['loai'])
            self.set_guidance(f"KHOẢN {code} – {row['ten']}\nLoại: {row['loai']}\nGhi chú: {row.get('ghi_chu','')}\nNguồn: {row.get('nguon','')}\n\nNgười dùng cần xác nhận bản chất nghiệp vụ.")

    def on_sector_type_selected(self):
        code=self.vars['sector_type'].get().split(' – ')[0].strip()
        self.vars['sector_type'].set(code)
        current=self.vars['sector_item'].get().split(' – ')[0].strip()
        if current and MLNS_BY_CODE.get(current,{}).get('loai')!=code:
            self.vars['sector_item'].set('')
        rows=[r for r in MLNS_CATALOG if r['loai']==code and r['khoan'] not in ('121','314','315')]
        self.field_widgets['sector_item']['values']=[f"{r['khoan']} – {r['ten']}" for r in rows]

    def update_keyword_hints(self):
        if not hasattr(self,'guidance'):return
        desc=self.vars['description'].get().strip()
        if len(desc)<4:return
        detected=infer_origin(desc)
        if detected and detected!=self.origin.get():self.origin.set(detected)
        matches=find_sectors(desc)
        self.populate_sector_lists(matches)
        candidate=auto_candidate(desc)
        if candidate:
            self.vars['sector_type'].set(candidate['loai'])
            self.vars['sector_item'].set(candidate['khoan'])
            self._auto_suggestion['sector']=candidate['khoan']
        elif self.vars['sector_item'].get()==self._auto_suggestion.get('sector'):
            self.vars['sector_type'].set('');self.vars['sector_item'].set('')
            self._auto_suggestion['sector']=None
        self.apply_origin()
        self.refresh_review_flags()
        if matches:
            score,loai,khoan,name,_=matches[0]
            note=MLNS_BY_CODE.get(khoan,{}).get('ghi_chu','')
            self.set_guidance(self.guidance.get('1.0','end').strip()+
                f'\n\nXẾP HẠNG MLNS: Loại {loai} / Khoản {khoan} – {name} ({score} điểm)\nGhi chú: {note}\n'+
                ('Đã điền mã gợi ý có độ phù hợp cao, cần xác nhận.' if candidate else 'Chưa đủ tin cậy để tự điền mã. Mở danh sách Khoản để chọn.'))

    def refresh_review_flags(self):
        """Cảnh báo trực quan; không thay thế kiểm tra nghiệp vụ."""
        if not hasattr(self,'review_text'):return
        info=analyze_funding(self.vars['description'].get())
        uncertain=[]
        for key,title in [('budget_type','Mã loại dự toán'),('source_code','Mã nguồn NSNN'),
                          ('sector_item','Mã Khoản'),('chapter','Mã Chương'),
                          ('account_debit','Tài khoản Nợ'),('account_credit','Tài khoản Có')]:
            value=self.vars[key].get().strip()
            auto=self._auto_suggestion.get({'budget_type':'budget','source_code':'source','sector_item':'sector'}.get(key,''))
            ambiguous=not value or (key=='source_code' and not auto) or (key=='chapter' and value=='999' and self.vars['kind'].get()!='Nhập dự toán cấp 0')
            if ambiguous:uncertain.append(title)
            widget=self.field_widgets.get(key)
            if isinstance(widget,ttk.Combobox):widget.configure(style='Review.TCombobox' if ambiguous else 'TCombobox')
        if info['uncertain']:uncertain.extend(info['uncertain'])
        nature=info['nature'] or 'Chưa xác định'
        self.review_text.set('TÍNH CHẤT KINH PHÍ: '+nature+' | CẦN KIỂM TRA (đỏ): '+(', '.join(uncertain) if uncertain else 'Không có ô trống; vẫn cần duyệt nghiệp vụ'))

    def apply_origin(self):
        if not hasattr(self,'guidance'):return
        rule=ORIGIN_RULES.get(self.origin.get())
        if not rule:return
        # Đồng bộ lại danh mục khi bản cài trước đã tạo CSV rỗng.
        if not BUDGET_CATALOG.items:
            BUDGET_CATALOG.reload()
        self.field_widgets['budget_type']['values']=BUDGET_CATALOG.display_values()
        desc=self.vars['description'].get().strip()
        suggestions=find_sectors(desc)
        sector='Chưa nhận diện Loại/Khoản từ mô tả.'
        if suggestions:
            _,loai,khoan,name,_=suggestions[0]
            sector=f'Gợi ý Loại {loai} / Khoản {khoan} – {name} (cần xác nhận)'
        detected=infer_origin(desc)
        if detected and detected!=self.origin.get():
            self.origin.set(detected)
            rule=ORIGIN_RULES.get(detected,rule)
        source_candidate=suggest_source(desc)
        if source_candidate:
            self.vars['source_code'].set(source_candidate['code'])
            self._auto_suggestion['source']=source_candidate['code']
        elif self.vars['source_code'].get()==self._auto_suggestion.get('source'):
            self.vars['source_code'].set('99');self._auto_suggestion['source']=None
        candidate=BUDGET_CATALOG.match(desc,self.origin.get(),self.vars['kind'].get())
        if candidate and (not self.vars['budget_type'].get() or self.vars['budget_type'].get()==self._auto_suggestion.get('budget')):
            self.vars['budget_type'].set(candidate['code']+' – '+candidate['name'])
            self._auto_suggestion['budget']=candidate['code']+' – '+candidate['name']
        elif self.vars['budget_type'].get()==self._auto_suggestion.get('budget'):
            self.vars['budget_type'].set('')
            self._auto_suggestion['budget']=None
        is_zero=self.vars['kind'].get()=='Nhập dự toán cấp 0'
        debit,credit=rule['debit'],rule['credit']
        if is_zero and debit and credit:
            self.vars['account_debit'].set(debit);self.vars['account_credit'].set(credit)
        chapter_note='Cấp 0 thường dùng Chương 999 theo PL II CV 15602; xác minh niên độ.' if is_zero else 'Chương phải dựa trên đơn vị nhận dự toán, không chỉ từ khóa nghiệp vụ.'
        if is_zero:self.vars['chapter'].set('999')
        self.set_guidance('NGUỒN GỐC: '+self.origin.get()+'\n\n'+rule['guide']+'\n\n'+sector+'\n\n'+chapter_note+'\n\n'+('Gợi ý tài khoản: Nợ '+debit+' / Có '+credit if is_zero and debit and credit else 'Không tự điền Nợ/Có: chưa đủ căn cứ hoặc không phải nhập cấp 0.')+'\n\nMã nguồn chi NSNN: '+(source_candidate['code']+' – '+source_candidate['name'] if source_candidate else 'cần xác định theo tính chất kinh phí và cấp dự toán; không suy từ tên nguồn tăng thu/dự phòng.')+'\n\nMã loại dự toán: '+(candidate['code']+' – '+candidate['name']+' (kiểm tra trước khi lưu)' if candidate else 'chưa có mã được đối chiếu trong danh mục CSV; cần bổ sung/kiểm tra.')+'\n\nLƯU Ý: Hướng dẫn theo CV 15602 (2017), chưa xác minh đầy đủ hiệu lực cho niên độ hiện hành.')

    def describe_code(self,key):
        code=self.vars[key].get().split(' – ')[0].strip()
        if key=='source_code':
            item=SOURCE_BY_CODE.get(self.vars['source_code'].get().split(' – ')[0].strip())
            return f"{item['code']} – {item['name']}\n{item['note']}\n{item['source']}" if item else 'Chọn mã nguồn chi NSNN theo tính chất kinh phí.'
        if key=='budget_type':
            item=BUDGET_CATALOG.get(code)
            return (f"{item['code']} – {item['name']}\nNguồn: {item['source']}\n{item['note']}" if item else 'Chưa có tên mã trong danh mục đã xác minh. Mở Danh sách mã loại dự toán để tra cứu.')
        if key in ('sector_type','sector_item'):
            hits=[f"{r['loai']}/{r['khoan']} – {r['ten']}\nGhi chú: {r['ghi_chu']}\nNguồn: {r['nguon']}" for r in MLNS_CATALOG if code in (r['loai'],r['khoan'])]
            return '\n'.join(hits[:4]) if hits else 'Chưa có tên trong danh mục Loại/Khoản.'
        if key=='chapter':
            return 'Mã Chương phải xác định theo đơn vị và cấp dự toán; 999 là mã theo hướng dẫn cấp 0 lịch sử CV 15602.' if code=='999' else 'Đối chiếu Phụ lục I TT 130 và sửa đổi TT 123 trước khi xác nhận mã Chương.'
        names={'9213':'Dự toán chi thường xuyên phân bổ cấp 0','9216':'Dự toán chi đầu tư phát triển phân bổ cấp 0',
               '9111':'Nguồn dự toán giao trong năm','9151':'Nguồn dự toán tăng thu'}
        return f'{code} – {names.get(code,"Cần tra cứu danh mục tài khoản và phạm vi áp dụng")}. Theo tài liệu CV 15602 (2017); xác minh hiệu lực.'

    def on_source_selected(self):
        code=self.vars['source_code'].get().split(' – ')[0].strip()
        self.vars['source_code'].set(code)
        self._auto_suggestion['source']=None
        item=SOURCE_BY_CODE.get(code)
        if item:self.set_guidance(f"MÃ NGUỒN {code} – {item['name']}\nNhóm: {item['group']}\n{item['note']}\nCăn cứ: {item['source']}\n\nKiểm tra cấp dự toán và hiệu lực áp dụng.")

    def on_budget_type_selected(self):
        code=BUDGET_CATALOG.extract_code(self.vars['budget_type'].get())
        self.vars['budget_type'].set(code)
        self._auto_suggestion['budget']=None
        self.set_guidance(self.describe_code('budget_type'))

    def reload_budget_catalog(self):
        BUDGET_CATALOG.reload()
        self.field_widgets['budget_type']['values']=BUDGET_CATALOG.display_values()
        self.apply_origin()
        messagebox.showinfo('Danh mục',f'Đã nạp {len(BUDGET_CATALOG.items)} mã có số hiệu từ CSV.\nTệp: {BUDGET_CATALOG.path}')

    def open_budget_catalog(self):
        win=tk.Toplevel(self);win.title('Danh mục mã loại dự toán – tra cứu và lựa chọn');win.geometry('1000x580')
        win.transient(self)
        ttk.Label(win,text='MÃ LOẠI DỰ TOÁN – CHỈ DÙNG MÃ ĐÃ ĐỐI CHIẾU',font=('Segoe UI',12,'bold')).pack(anchor='w',padx=12,pady=9)
        ttk.Label(win,text='Danh mục CSV do cán bộ kiểm tra và bổ sung. Các nhóm nguồn chỉ là gợi ý, không phải mã số.',wraplength=900).pack(anchor='w',padx=12)
        search=tk.StringVar()
        ttk.Entry(win,textvariable=search,width=65).pack(fill='x',padx=12,pady=9)
        cols=('code','name','source','keywords','note')
        tree=ttk.Treeview(win,columns=cols,show='headings',height=15)
        for col,label,width in [('code','Mã',85),('name','Tên mã',250),('source','Căn cứ',210),('keywords','Từ khóa',180),('note','Ghi chú',240)]:
            tree.heading(col,text=label);tree.column(col,width=width)
        tree.pack(fill='both',expand=True,padx=12)
        HoverTip(tree,lambda: 'Chọn một dòng để đưa mã loại dự toán vào nghiệp vụ. Di chuột vào ô mã trên phiếu để xem tên và căn cứ.')
        def refresh(*_):
            for item in tree.get_children():tree.delete(item)
            q=normalize(search.get())
            for item in BUDGET_CATALOG.items:
                if not q or q in normalize(' '.join(str(v) for v in item.values())):
                    tree.insert('','end',values=tuple(item.get(k,'') for k in cols))
        search.trace_add('write',refresh);refresh()
        def choose():
            sel=tree.selection()
            if not sel:return
            code=tree.item(sel[0],'values')[0]
            self.vars['budget_type'].set(code)
            self.on_budget_type_selected();win.destroy()
        buttons=ttk.Frame(win);buttons.pack(fill='x',padx=12,pady=10)
        ttk.Button(buttons,text='Chọn mã vào nghiệp vụ',command=choose).pack(side='left')
        ttk.Button(buttons,text='Mở thư mục CSV',command=lambda:os.startfile(str(BUDGET_CATALOG.path.parent)) if sys.platform=='win32' else None).pack(side='left',padx=10)
        ttk.Label(buttons,text=f'Tổng {len(BUDGET_CATALOG.items)} mã đã khai báo').pack(side='right')

    def open_original_forms(self):
        win=tk.Toplevel(self);win.title('Bốn mẫu C6 gốc - chỉ xem, không tự điền');win.geometry('650x330')
        ttk.Label(win,text='MẪU C6 DO NGƯỜI DÙNG CUNG CẤP',font=('Segoe UI',13,'bold')).pack(pady=14)
        ttk.Label(win,text='Mở mẫu gốc bằng Word/Excel trên Windows. Chưa phải phiếu đã điền.',wraplength=600).pack(pady=4)
        base=Path(getattr(sys,'_MEIPASS',Path(__file__).parent))/'templates'
        for code,filename in ORIGINAL_FORMS.items():
            def open_file(fn=filename):
                target=base/fn
                if not target.exists():return messagebox.showerror('Thiếu file',str(target),parent=win)
                try:os.startfile(str(target))
                except Exception as e:messagebox.showerror('Không mở được mẫu',str(e),parent=win)
            ttk.Button(win,text='Mở '+code+' – '+filename,command=open_file).pack(fill='x',padx=25,pady=5)

    def set_guidance(self,s):
        self.guidance.config(state='normal');self.guidance.delete('1.0','end');self.guidance.insert('1.0',s);self.guidance.config(state='disabled')

    def suggest(self):
        kind=self.vars['kind'].get()
        ref=REFERENCE.get(kind,'Chưa có quy tắc hạch toán xác nhận cho nghiệp vụ này.')
        self.set_guidance('NGHIỆP VỤ: '+kind+'\n\nCĂN CỨ LỊCH SỬ (2017):\n'+ref+
           '\n\nBẮT BUỘC KIỂM TRA:\n• Niên độ và hiệu lực văn bản hiện hành.\n• Tài khoản nguồn/đích, cấp dự toán, loại chi.\n• Mã Kho bạc, đơn vị và mã nguồn.\n• Trạng thái phê duyệt/kết sổ nếu điều chỉnh.\n\nKhông tự suy diễn tài khoản Nợ/Có hoặc mã loại dự toán từ mô tả chung. Người dùng phải xác minh và nhập các mã đã được phê duyệt.')

    def safe_exit(self):
        if messagebox.askyesno('Thoát phần mềm','Bạn muốn thoát Trợ lý dự toán ngân sách xã?\nDữ liệu đã lưu sẽ được giữ lại.'):
            self.con.close()
            self.destroy()

    def suggest_sector(self):
        desc=self.vars['description'].get().strip()
        if not desc:
            return messagebox.showwarning('Thiếu nghiệp vụ','Nhập nội dung nghiệp vụ vào ô Diễn giải trước.')
        results=find_sectors(desc)
        self.tabs.select(self.tab_catalog)
        self.catalog_search.set(desc)
        self.render_catalog(results)
        if not results:
            self.catalog_status.set('Không tìm được mã phù hợp trong danh mục mẫu. Không được tự suy đoán mã ngành.')
        else:
            self.catalog_status.set(f'Tìm thấy {len(results)} gợi ý theo từ khóa. Chọn một dòng và bấm “Đưa vào phiếu”.')

    def make_catalog(self):
        ttk.Label(self.tab_catalog,text='TRA CỨU LOẠI / KHOẢN (MÃ NGÀNH KINH TẾ)',font=('Segoe UI',13,'bold')).pack(anchor='w')
        ttk.Label(self.tab_catalog,text='Danh mục đọc từ Phụ lục II văn bản hợp nhất TT130/2025, sửa đổi TT123/2026. Kết quả xếp hạng là gợi ý; kiểm tra hiệu lực và ghi chú trước khi dùng.',foreground='#92430d',wraplength=1000).pack(anchor='w',pady=5)
        bar=ttk.Frame(self.tab_catalog);bar.pack(fill='x',pady=9)
        ttk.Label(bar,text='Mã hoặc nghiệp vụ:').pack(side='left')
        self.catalog_search=tk.StringVar()
        entry=ttk.Entry(bar,textvariable=self.catalog_search,width=75);entry.pack(side='left',fill='x',expand=True,padx=8)
        entry.bind('<Return>',lambda e:self.search_catalog())
        ttk.Button(bar,text='Tra cứu / Gợi ý',command=self.search_catalog).pack(side='left')
        ttk.Button(bar,text='Xem tất cả',command=lambda:(self.catalog_search.set(''),self.search_catalog())).pack(side='left',padx=5)
        ttk.Button(bar,text='➕ ĐƯA MÃ NGÀNH VÀO NGHIỆP VỤ',command=self.apply_sector).pack(side='left',padx=8)
        cols=('loai','khoan','name','match')
        self.catalog_tree=ttk.Treeview(self.tab_catalog,columns=cols,show='headings',height=15)
        for key,title,width in [('loai','Mã Loại',95),('khoan','Mã Khoản',95),('name','Tên ngành / lĩnh vực',510),('match','Từ khóa khớp',210)]:
            self.catalog_tree.heading(key,text=title);self.catalog_tree.column(key,width=width)
        self.catalog_tree.pack(fill='both',expand=True)
        # Hover tooltip và khung hướng dẫn, dùng nguyên văn phần ghi chú có trong CSV.
        self.catalog_hover_window = None
        self.catalog_hover_item = None
        self.catalog_hover_after = None
        self.catalog_detail = tk.StringVar(value='Di chuột lên mã Khoản hoặc chọn một dòng để xem tên, ghi chú và nguồn văn bản.')
        detail_frame = ttk.LabelFrame(self.tab_catalog, text='Nội dung chi tiết theo danh mục MLNS', padding=8)
        detail_frame.pack(fill='x', pady=(6, 0))
        ttk.Label(detail_frame, textvariable=self.catalog_detail, wraplength=1050, justify='left').pack(anchor='w', fill='x')
        self.catalog_tree.bind('<Motion>', self._catalog_hover_motion)
        self.catalog_tree.bind('<Leave>', self._catalog_hide_hover)
        self.catalog_tree.bind('<<TreeviewSelect>>', self._catalog_select_detail)
        self.catalog_tree.bind('<MouseWheel>', self._catalog_hide_hover, add='+')

        foot=ttk.Frame(self.tab_catalog);foot.pack(fill='x',pady=9)
        ttk.Button(foot,text='Đưa mã Loại / Khoản vào phiếu',command=self.apply_sector).pack(side='left')
        self.catalog_status=tk.StringVar(value='Tra cứu theo tên, mã hoặc nhập một nghiệp vụ để tìm mã ngành.')
        ttk.Label(foot,textvariable=self.catalog_status,foreground='#555',wraplength=730).pack(side='left',padx=15)
        self.render_catalog([] ,all_items=True)

    def _catalog_info(self, item):
        if not item:
            return ''
        values = self.catalog_tree.item(item, 'values')
        if len(values) < 2:
            return ''
        loai, khoan = str(values[0]), str(values[1])
        record = MLNS_BY_CODE.get(khoan)
        if not record:
            return f'Loại {loai} / Khoản {khoan}: chưa có thông tin chi tiết trong danh mục.'
        note = (record.get('ghi_chu') or '').strip()
        source = (record.get('nguon') or '').strip()
        status = (record.get('tinh_trang') or '').strip()
        return (f"LOẠI {loai} / KHOẢN {khoan} — {record.get('ten','')}\n"
                f"Nội dung hướng dẫn/ghi chú: {note if note else 'Danh mục chưa có ghi chú riêng cho Khoản này.'}\n"
                f"Tình trạng: {status or 'Chưa xác định'}\n"
                f"Nguồn: {source or 'Chưa ghi nguồn trong CSV'}. "
                'Kiểm tra quy định hiện hành trước khi hạch toán.')

    def _catalog_select_detail(self, event=None):
        selected = self.catalog_tree.selection()
        if selected:
            self.catalog_detail.set(self._catalog_info(selected[0]))

    def _catalog_hide_hover(self, event=None):
        if self.catalog_hover_after is not None:
            try: self.after_cancel(self.catalog_hover_after)
            except Exception: pass
            self.catalog_hover_after = None
        if self.catalog_hover_window is not None:
            try: self.catalog_hover_window.destroy()
            except Exception: pass
            self.catalog_hover_window = None
        self.catalog_hover_item = None

    def _catalog_hover_motion(self, event):
        item = self.catalog_tree.identify_row(event.y)
        if item == self.catalog_hover_item:
            return
        self._catalog_hide_hover()
        if not item:
            return
        self.catalog_hover_item = item
        self.catalog_hover_after = self.after(450, lambda item=item: self._catalog_show_hover(item))

    def _catalog_show_hover(self, item):
        self.catalog_hover_after = None
        if item != self.catalog_hover_item or not self.catalog_tree.exists(item):
            return
        text = self._catalog_info(item)
        if not text:
            return
        self.catalog_detail.set(text)
        win = tk.Toplevel(self)
        win.wm_overrideredirect(True)
        try: win.wm_attributes('-topmost', True)
        except Exception: pass
        label = tk.Label(win, text=text, justify='left', anchor='w', bg='#fffbe6', fg='#1f2937',
                         relief='solid', bd=1, padx=12, pady=10, wraplength=610,
                         font=('Segoe UI', 10))
        label.pack()
        x = self.catalog_tree.winfo_pointerx() + 18
        y = self.catalog_tree.winfo_pointery() + 18
        # Tránh tooltip bị tràn ra khỏi màn hình.
        win.update_idletasks()
        x = min(x, max(0, win.winfo_screenwidth() - win.winfo_reqwidth() - 12))
        y = min(y, max(0, win.winfo_screenheight() - win.winfo_reqheight() - 12))
        win.wm_geometry(f'+{x}+{y}')
        self.catalog_hover_window = win

    def render_catalog(self,results,all_items=False):
        self._catalog_hide_hover()
        for row in self.catalog_tree.get_children():self.catalog_tree.delete(row)
        if all_items:
            rows=[(loai,khoan,name,'') for loai,khoan,name,_ in SECTORS]
        else:
            rows=[(loai,khoan,name,matched) for _,loai,khoan,name,matched in results]
        for row in rows:self.catalog_tree.insert('', 'end',values=row)

    def search_catalog(self):
        query=self.catalog_search.get().strip()
        if not query:
            self.render_catalog([],all_items=True)
            self.catalog_status.set(f'Đang hiển thị {len(SECTORS)} mã Khoản trong danh mục mẫu.')
            return
        normalized=normalize(query)
        if query.isdigit():
            matches=[(99,loai,khoan,name,'mã') for loai,khoan,name,_ in SECTORS if loai.startswith(query) or khoan.startswith(query)]
        else:
            matches=find_sectors(query)
            if not matches:
                matches=[(1,loai,khoan,name,'tên') for loai,khoan,name,_ in SECTORS if normalized in normalize(name)]
        self.render_catalog(matches)
        self.catalog_status.set(f'Có {len(matches)} mã được xếp hạng; chọn để xem và xác nhận.' if matches else 'Không thấy mã trong danh mục mẫu. Cần tra cứu Phụ lục II đầy đủ.')

    def apply_sector(self):
        selected=self.catalog_tree.selection()
        if not selected:return messagebox.showwarning('Chưa chọn','Chọn một dòng mã ngành trước.')
        loai,khoan,name,_=self.catalog_tree.item(selected[0],'values')
        detail=MLNS_BY_CODE.get(khoan,{})
        if messagebox.askyesno('Xác nhận mã ngành',f"Đưa mã Loại {loai} / Khoản {khoan} – {name} vào phiếu?\n\nGhi chú: {detail.get('ghi_chu','Không có')}\n\nCần đối chiếu bản chất nhiệm vụ chi và văn bản có hiệu lực."):
            self.vars['sector_type'].set(loai)
            self.vars['sector_item'].set(khoan)
            self._auto_suggestion['sector']=None
            self.tabs.select(self.tab_entry)
            self.set_guidance(f'GỢI Ý MÃ NGÀNH: Loại {loai}, Khoản {khoan} – {name}\n\nNguồn: Phụ lục II kèm TT 130/2025/TT-BTC (bản có ghi nhận sửa đổi theo TT 123/2026).\nĐây là gợi ý tra cứu, không phải xác nhận hạch toán. Kiểm tra nghiệp vụ, niên độ và hiệu lực trước khi sử dụng.')

    def save_voucher(self):
        cid=self.commune_id()
        if not cid:return messagebox.showwarning('Chưa chọn xã','Hãy thêm và chọn xã/phường trước.')
        data={k:v.get().strip() for k,v in self.vars.items()}
        for key in ('sector_type','sector_item'):
            data[key]=data[key].split(' – ')[0].strip()
        data['source_code']=data['source_code'].split(' – ')[0].strip()
        data['budget_type']=BUDGET_CATALOG.extract_code(data['budget_type'])
        if data['budget_type'] and data['budget_type'] not in BUDGET_CATALOG.codes():
            if not messagebox.askyesno('Mã ngoài danh mục',
                'Mã loại dự toán chưa có trong danh mục đối chiếu. Bạn đã kiểm tra văn bản và vẫn muốn lưu dự thảo?'):
                return
        if not data['description']:return messagebox.showwarning('Thiếu','Cần nhập diễn giải nghiệp vụ.')
        try: datetime.strptime(data['date'],'%Y-%m-%d')
        except ValueError:return messagebox.showerror('Ngày sai','Ngày phải đúng dạng YYYY-MM-DD.')
        try:
            amount=int(data['amount'].replace(',','').replace('.','').replace(' ',''))
            if amount<=0:raise ValueError
        except ValueError:return messagebox.showerror('Số tiền sai','Nhập số nguyên VND lớn hơn 0.')
        if bool(data['account_debit']) != bool(data['account_credit']):
            return messagebox.showerror('Thiếu tài khoản','Phải nhập cả tài khoản Nợ và Có, hoặc để trống cả hai.')
        if data['account_debit'] and not messagebox.askyesno('Xác nhận định khoản',
                'Tài khoản Nợ/Có do người sử dụng nhập, CHƯA được phần mềm kiểm chứng hiệu lực.\nBạn đã kiểm tra căn cứ và muốn lưu bản DỰ THẢO?'):
            return
        year=int(data['date'][:4]); keys=FIELDS
        self.con.execute('INSERT INTO vouchers(commune_id,year,'+','.join(keys)+',legal_note) VALUES('+','.join(['?']*(len(keys)+3))+')',
                         [cid,year]+[amount if k=='amount' else data[k] for k in keys]+[REFERENCE.get(data['kind'],'Chưa có quy tắc xác nhận')])
        self.con.execute('UPDATE vouchers SET origin=? WHERE id=last_insert_rowid()', (self.origin.get(),))
        self.con.commit();self.refresh_vouchers();messagebox.showinfo('Đã lưu','Đã lưu chứng từ ở trạng thái DỰ THẢO. Chưa phê duyệt hoặc ghi TABMIS.')

    def make_history(self):
        cols=['id','date','kind','description','amount','account_debit','account_credit','status']
        self.tree=ttk.Treeview(self.tab_history,columns=cols,show='headings',height=17)
        widths=[65,105,175,260,140,100,100,100]
        for c,w in zip(cols,widths):self.tree.heading(c,text={'id':'ID','date':'Ngày','kind':'Nghiệp vụ','description':'Diễn giải','amount':'Số tiền','account_debit':'TK Nợ','account_credit':'TK Có','status':'Trạng thái'}[c]);self.tree.column(c,width=w,anchor='w')
        self.tree.pack(fill='both',expand=True)
        bar=ttk.Frame(self.tab_history);bar.pack(fill='x',pady=10)
        ttk.Button(bar,text='Làm mới',command=self.refresh_vouchers).pack(side='left')
        ttk.Button(bar,text='Xuất Excel (.xlsx)',command=self.export_xlsx).pack(side='left',padx=8)
        ttk.Button(bar,text='Xuất phiếu PDF (dự thảo)',command=self.export_pdf).pack(side='left')
        ttk.Button(bar,text='Tạo phiếu từ dòng đã chọn',command=self.history_to_forms).pack(side='left',padx=8)
        ttk.Button(bar,text='Xóa chứng từ dự thảo',command=self.delete_voucher).pack(side='right')

    def refresh_vouchers(self):
        if not hasattr(self,'tree'):return
        for item in self.tree.get_children():self.tree.delete(item)
        cid=self.commune_id()
        if not cid:return
        for r in self.con.execute('SELECT id,date,kind,description,amount,account_debit,account_credit,status FROM vouchers WHERE commune_id=? ORDER BY id DESC',(cid,)):
            r=list(r);r[4]=f'{r[4]:,}';self.tree.insert('', 'end',values=r)

    def selected_voucher(self):
        sel=self.tree.selection()
        if not sel:messagebox.showwarning('Chưa chọn','Chọn một chứng từ trong lịch sử.');return None
        vid=int(self.tree.item(sel[0],'values')[0]);self.con.row_factory=sqlite3.Row
        row=self.con.execute('SELECT * FROM vouchers WHERE id=? AND commune_id=?',(vid,self.commune_id())).fetchone()
        self.con.row_factory=None
        return dict(row) if row else None

    def delete_voucher(self):
        row=self.selected_voucher()
        if row and row['status']=='DỰ THẢO' and messagebox.askyesno('Xác nhận',f'Xóa dự thảo #{row["id"]}?'):
            self.con.execute('DELETE FROM vouchers WHERE id=?',(row['id'],));self.con.commit();self.refresh_vouchers()

    def export_xlsx(self):
        cid=self.commune_id()
        if not cid:return
        path=filedialog.asksaveasfilename(defaultextension='.xlsx',filetypes=[('Excel','*.xlsx')],initialfile='Du_toan_xa.xlsx')
        if not path:return
        try:
            import xlsxwriter
            cols=['id','year']+FIELDS+['status','legal_note']
            rows=self.con.execute('SELECT '+','.join(cols)+' FROM vouchers WHERE commune_id=? ORDER BY id',(cid,)).fetchall()
            wb=xlsxwriter.Workbook(path);ws=wb.add_worksheet('Du thao')
            title=wb.add_format({'bold':True,'font_size':15,'font_color':'#163A5F'})
            head=wb.add_format({'bold':True,'bg_color':'#DCEBF7','border':1,'text_wrap':True})
            money=wb.add_format({'num_format':'#,##0','border':1})
            normal=wb.add_format({'border':1})
            ws.merge_range(0,0,0,len(cols)-1,'DỰ THẢO DỰ TOÁN NGÂN SÁCH XÃ — CHƯA PHÊ DUYỆT',title)
            for j,c in enumerate(cols):ws.write(2,j,c,head)
            for i,row in enumerate(rows,3):
                for j,v in enumerate(row):
                    if cols[j]=='amount':ws.write_number(i,j,v,money)
                    else:ws.write_string(i,j,str(v or ''),normal)
            ws.freeze_panes(3,0);ws.autofilter(2,0,max(3,len(rows)+2),len(cols)-1)
            ws.set_column(0,len(cols)-1,18);ws.set_column(4,4,42);ws.set_column(len(cols)-1,len(cols)-1,55)
            wb.close();messagebox.showinfo('Đã xuất',path)
        except ImportError:messagebox.showerror('Thiếu thư viện','Chạy: pip install -r requirements.txt')
        except Exception as e:messagebox.showerror('Lỗi xuất Excel',str(e))

    def export_pdf(self):
        row=self.selected_voucher()
        if not row:return
        path=filedialog.asksaveasfilename(defaultextension='.pdf',filetypes=[('PDF','*.pdf')],initialfile=f'Du_thao_{row["id"]}.pdf')
        if not path:return
        try:
            from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle
            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            from reportlab.lib.enums import TA_CENTER
            import html
            font_candidates=['C:/Windows/Fonts/arial.ttf','/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf']
            font=next((p for p in font_candidates if Path(p).exists()),None)
            if not font:raise RuntimeError('Không tìm thấy font Unicode Arial/DejaVuSans.')
            pdfmetrics.registerFont(TTFont('VNFont',font))
            styles=getSampleStyleSheet();styles.add(ParagraphStyle(name='Vn',fontName='VNFont',fontSize=9,leading=15))
            styles.add(ParagraphStyle(name='VnTitle',fontName='VNFont',fontSize=15,leading=22,alignment=TA_CENTER))
            commune=self.con.execute('SELECT name FROM communes WHERE id=?',(row['commune_id'],)).fetchone()[0]
            doc=SimpleDocTemplate(path,pagesize=(595,842),leftMargin=40,rightMargin=40)
            P=lambda x:Paragraph(html.escape(str(x or '')),styles['Vn'])
            story=[Paragraph('PHIẾU NGHIỆP VỤ DỰ TOÁN — DỰ THẢO',styles['VnTitle']),Spacer(1,12),P('Đơn vị: '+commune),Spacer(1,8)]
            display=[('Ngày',row['date']),('Năm ngân sách',row['year']),('Nghiệp vụ',row['kind']),('Diễn giải',row['description']),('Số tiền',f'{row["amount"]:,} VND'),('Cấp NS',row['budget_level']),('TK Nợ',row['account_debit']),('TK Có',row['account_credit']),('Mã loại dự toán',row['budget_type']),('Chương',row['chapter']),('Loại',row['sector_type']),('Khoản',row['sector_item']),('Mục/Tiểu mục',row['econ_item']),('Nguồn',row['source_code'])]
            table=Table([[P(a),P(b)] for a,b in display],colWidths=[155,350],hAlign='LEFT')
            table.setStyle(TableStyle([('GRID',(0,0),(-1,-1),.3,colors.grey),('VALIGN',(0,0),(-1,-1),'TOP'),('BACKGROUND',(0,0),(0,-1),colors.whitesmoke),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]))
            story.extend([table,Spacer(1,15),P('Căn cứ tham khảo: '+str(row['legal_note'])),Spacer(1,12),P('CHỈ LÀ PHIẾU KIỂM TRA NỘI BỘ — KHÔNG PHẢI MẪU C6-01/KB, C6-02/NS HOẶC C6-04/NS CHÍNH THỨC.'),P('Chưa xác minh hiệu lực quy định, chưa phê duyệt và chưa ghi TABMIS.')]);doc.build(story)
            messagebox.showinfo('Đã xuất',path)
        except Exception as e:messagebox.showerror('Lỗi xuất PDF',str(e))

    def backup(self):
        path=filedialog.asksaveasfilename(defaultextension='.sqlite3',filetypes=[('SQLite','*.sqlite3')],initialfile='Sao_luu_du_toan_xa.sqlite3')
        if path:
            dest=sqlite3.connect(path);self.con.backup(dest);dest.close();messagebox.showinfo('Đã sao lưu',path)

    def restore_backup(self):
        """Khôi phục toàn bộ SQLite; lưu bản dự phòng tự động trước khi thay thế."""
        source = filedialog.askopenfilename(
            title='Chọn tệp dữ liệu SQLite đã sao lưu',
            filetypes=[('Dữ liệu sao lưu SQLite', '*.sqlite3 *.db *.sqlite'), ('Tất cả tệp', '*.*')],
            parent=self)
        if not source:
            return
        src = Path(source)
        if src.resolve() == DB.resolve():
            return messagebox.showwarning('Không thể khôi phục',
                'Bạn đang chọn chính cơ sở dữ liệu đang sử dụng. Hãy chọn tệp sao lưu khác.', parent=self)
        try:
            # Mở ở chế độ chỉ đọc để tránh tự tạo tệp trống.
            check = sqlite3.connect(src.as_uri() + '?mode=ro', uri=True)
            try:
                result = check.execute('PRAGMA integrity_check').fetchone()[0]
                if result != 'ok':
                    raise ValueError('Tệp sao lưu không toàn vẹn: ' + str(result))
                tables = {r[0] for r in check.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                if not {'communes', 'vouchers'}.issubset(tables):
                    raise ValueError('Tệp không chứa đủ bảng communes và vouchers của phần mềm.')
                cols = {r[1] for r in check.execute('PRAGMA table_info(vouchers)')}
                needed = {'id','commune_id','year','date','kind','description','amount','account_debit','account_credit'}
                if not needed.issubset(cols):
                    raise ValueError('Cấu trúc dữ liệu sao lưu không tương thích với phần mềm.')
                counts = (check.execute('SELECT COUNT(*) FROM communes').fetchone()[0],
                          check.execute('SELECT COUNT(*) FROM vouchers').fetchone()[0])
            finally:
                check.close()
        except Exception as exc:
            return messagebox.showerror('Không đọc được sao lưu', str(exc), parent=self)

        if not messagebox.askyesno('Xác nhận khôi phục dữ liệu',
            f'Tệp: {src.name}\nSố xã/phường: {counts[0]}\nSố chứng từ: {counts[1]}\n\n'
            'KHÔI PHỤC SẼ THAY THẾ TOÀN BỘ dữ liệu hiện tại (không gộp).\n'
            'Phần mềm sẽ tự sao lưu dữ liệu hiện tại trước khi thay thế.\n\nBạn muốn tiếp tục?',
            icon='warning', parent=self):
            return
        safety = APP_DIR / ('Truoc_khoi_phuc_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f') + '.sqlite3')
        stage = None
        closed = False
        replaced = False
        try:
            # Backup qua SQLite API để bao gồm dữ liệu đang ở WAL và chưa checkpoint.
            with sqlite3.connect(safety) as dest:
                self.con.backup(dest)
            fd, temp_name = tempfile.mkstemp(prefix='restore_', suffix='.sqlite3', dir=APP_DIR)
            os.close(fd)
            stage = Path(temp_name)
            with sqlite3.connect(src.as_uri() + '?mode=ro', uri=True) as original:
                with sqlite3.connect(stage) as dest:
                    original.backup(dest)
            self.con.close()
            closed = True
            # Đảm bảo tệp WAL cũ không còn trước khi đổi dữ liệu.
            for suffix in ('-wal', '-shm'):
                (APP_DIR / (DB.name + suffix)).unlink(missing_ok=True)
            os.replace(stage, DB)
            replaced = True
            self.con = connect()  # Tự bổ sung cột mới khi mở bản sao lưu cũ.
            closed = False
            self.refresh_communes()
            messagebox.showinfo('Khôi phục thành công',
                f'Đã khôi phục {counts[0]} xã/phường và {counts[1]} chứng từ.\n\n'
                f'Bản sao dữ liệu trước khi khôi phục:\n{safety}\n\n'
                'Lưu ý: Các dòng bộ chứng từ chưa được lưu vào SQLite không nằm trong tệp sao lưu.', parent=self)
        except Exception as exc:
            if closed or replaced:
                try:
                    if not closed:
                        self.con.close()
                    shutil.copy2(safety, DB)
                    self.con = connect()
                    self.refresh_communes()
                except Exception:
                    pass
            messagebox.showerror('Khôi phục không thành công',
                f'{exc}\n\nBản dự phòng dữ liệu cũ (nếu đã tạo):\n{safety}', parent=self)
        finally:
            if stage is not None:
                stage.unlink(missing_ok=True)

    def current_org_code(self):
        """Mã tổ chức ngân sách của xã đang chọn, không suy diễn từ mã QHNS."""
        cid=self.commune_id()
        if not cid:return ''
        record=self.con.execute('SELECT org_code FROM communes WHERE id=?',(cid,)).fetchone()
        return str(record[0] or '').strip() if record else ''

    def batch_select_row(self, _event=None):
        """Chọn một dòng sẽ đưa dữ liệu lên các ô phía trên để sửa."""
        if not hasattr(self,'batch_tree'):return
        selected=self.batch_tree.selection()
        if len(selected)!=1:return
        idx=self.batch_tree.index(selected[0])
        if idx>=len(self.batch_rows):return
        row=self.batch_rows[idx]
        for key,var in self.batch_vars.items():
            value=row.get(key,'')
            var.set(str(value) if key!='so_tien' else f'{int(value or 0):,}')
        if hasattr(self,'batch_edit_status'):
            self.batch_edit_status.set(f'Đang sửa dòng {idx+1}: thay đổi các ô phía trên rồi bấm LƯU THAY ĐỔI DÒNG. Bấm XÓA DÒNG để xóa.')

    def batch_double_click(self, event):
        item=self.batch_tree.identify_row(event.y)
        if not item:return
        self.batch_tree.selection_set(item)
        self.batch_tree.focus(item)
        self.batch_select_row()
        if hasattr(self,'batch_first_widget'):
            self.batch_first_widget.focus_set()

    def batch_clear_selection(self):
        if not hasattr(self,'batch_tree'):return
        self.batch_tree.selection_remove(self.batch_tree.selection())
        for key,var in self.batch_vars.items():var.set('')
        self.batch_vars['nguon'].set('')
        self.batch_vars['nguon_cap0'].set('99')
        self.batch_vars['qhns_cap0'].set(self.current_org_code())
        if hasattr(self,'batch_edit_status'):
            self.batch_edit_status.set('Đang nhập dòng mới. Bấm Thêm dòng mới để thêm; chọn một dòng để sửa.')

    @staticmethod
    def validate_required_row(row):
        required=[('noi_dung','Nội dung/Diễn giải'),('ma_loai_du_toan','Mã loại dự toán'),
                  ('tk_no','Tài khoản Nợ'),('tk_co','Tài khoản Có'),
                  ('loai','Mã Loại'),('khoan','Mã Khoản'),('nguon','Mã nguồn cấp 4')]
        missing=[label for key,label in required if not str(row.get(key,'')).strip()]
        if missing:raise ValueError('Thiếu các ô bắt buộc: '+', '.join(missing))
        amount=int(row.get('so_tien',0))
        if amount<=0:raise ValueError('Số tiền phải lớn hơn 0.')
        code=str(row['ma_loai_du_toan']).split(' – ')[0].strip()
        if code not in BUDGET_CATALOG.codes():raise ValueError('Mã loại dự toán không có trong danh mục: '+code)
        row['ma_loai_du_toan']=code

    def validate_all_package_rows(self, rows=None):
        rows=self.batch_rows if rows is None else rows
        try:
            for i,row in enumerate(rows,1):
                try:self.validate_required_row(row)
                except (ValueError,TypeError) as exc:raise ValueError(f'Dòng {i}: {exc}')
        except ValueError as exc:
            messagebox.showerror('Chưa đủ điều kiện xuất phiếu',str(exc))
            return False
        return True

    def batch_update_selected(self):
        """Cập nhật dòng đang chọn, không thêm dòng trùng."""
        from batch_export import check_rows
        selected=self.batch_tree.selection()
        if len(selected)!=1:
            return messagebox.showwarning('Chọn dòng','Hãy chọn đúng một dòng trong bảng trước khi sửa.')
        item=selected[0];idx=self.batch_tree.index(item)
        row=dict(self.batch_rows[idx])
        for key,var in self.batch_vars.items():
            row[key]=var.get().split(' – ')[0].strip() if key in ('nguon','nguon_cap0') else var.get().strip()
        try:
            row['so_tien']=int(row['so_tien'].replace(',','').replace('.','').replace(' ',''))
            self.validate_required_row(row)
            check_rows([row])
        except (ValueError,KeyError) as exc:
            return messagebox.showerror('Không thể lưu sửa',str(exc))
        self.batch_rows[idx]=row
        self.batch_tree.item(item,values=[f'{row[k]:,}' if k=='so_tien' else row.get(k,'') for k in self.batch_vars])
        self.batch_total.set(f'{len(self.batch_rows)} dòng | Tổng: {sum(r["so_tien"] for r in self.batch_rows):,} VND')
        self.update_package_reconciliation()
        self.batch_select_row()
        if hasattr(self,'batch_edit_status'):self.batch_edit_status.set(f'Đã lưu thay đổi dòng {idx+1}.')

    def make_batch(self):
        from batch_export import FIELDS as BATCH_FIELDS
        self.batch_rows=[]
        # Chia khu vực nhập và bảng dữ liệu thành hai ngăn độc lập.
        # Phần nhập có thanh cuộn, bảng ở ngăn dưới luôn được cấp không gian hiển thị.
        splitter=ttk.Panedwindow(self.tab_batch,orient='vertical')
        splitter.pack(fill='both',expand=True)
        upper_shell=ttk.Frame(splitter)
        lower_shell=ttk.Frame(splitter)
        splitter.add(upper_shell,weight=3)
        splitter.add(lower_shell,weight=2)
        upper_canvas=tk.Canvas(upper_shell,highlightthickness=0,borderwidth=0)
        upper_scroll=ttk.Scrollbar(upper_shell,orient='vertical',command=upper_canvas.yview)
        upper_canvas.configure(yscrollcommand=upper_scroll.set)
        upper_scroll.pack(side='right',fill='y')
        upper_canvas.pack(side='left',fill='both',expand=True)
        upper=ttk.Frame(upper_canvas,padding=(3,3,8,3))
        canvas_window=upper_canvas.create_window((0,0),window=upper,anchor='nw')
        upper.bind('<Configure>',lambda event:upper_canvas.configure(scrollregion=upper_canvas.bbox('all')))
        upper_canvas.bind('<Configure>',lambda event:upper_canvas.itemconfigure(canvas_window,width=event.width))
        # Khởi tạo chiều cao hai ngăn khi giao diện đã tính xong kích thước.
        def set_initial_split():
            if not splitter.winfo_exists():return
            h=splitter.winfo_height()
            if h>200:
                try:splitter.sashpos(0,max(170,min(int(h*.56),h-170)))
                except tk.TclError:pass
        self.after(350,set_initial_split)
        ttk.Label(lower_shell,text='DANH SÁCH NGHIỆP VỤ ĐÃ ĐƯA VÀO PHIẾU – Chọn hoặc nháy đúp để sửa',
                  font=('Segoe UI',10,'bold')).pack(anchor='w',pady=(3,4))
        table_shell=ttk.Frame(lower_shell)
        table_shell.pack(fill='both',expand=True)
        ttk.Label(upper,text='LẬP ĐỒNG THỜI C6-02 CẤP 0, C6-01 CẤP 4 VÀ PHỤ LỤC QUYẾT ĐỊNH',font=('Segoe UI',12,'bold')).pack(anchor='w')
        ttk.Label(upper,text='Dữ liệu từ tab Nghiệp vụ được chuyển tự động khi bấm Đưa vào phiếu. Nguồn cấp 0 và nguồn chi tiết cấp 4 là hai trường độc lập.\nBản thử nghiệm: xuất 3 BẢNG CHUẨN BỊ Excel, chưa phải mẫu chứng từ KBNN chính thức. Mỗi dòng có thể khác Loại, Khoản, nguồn và đơn vị nhận.',foreground='#92430d',wraplength=1020).pack(anchor='w',pady=6)
        meta=ttk.Frame(upper);meta.pack(fill='x',pady=5)
        self.batch_meta={k:tk.StringVar(value=v) for k,v in [('year',str(datetime.now().year)),('decision',''),('decision_date',datetime.now().strftime('%Y-%m-%d'))]}
        for k,title in [('year','Năm ngân sách'),('decision','Số quyết định'),('decision_date','Ngày quyết định')]:
            ttk.Label(meta,text=title).pack(side='left',padx=(8,3));ttk.Entry(meta,textvariable=self.batch_meta[k],width=17).pack(side='left')
        # Thông tin quyết định được nhập duy nhất ở tab Bộ phiếu / Quyết định.
        decision=ttk.LabelFrame(upper,text='THÔNG TIN QUYẾT ĐỊNH GIAO DỰ TOÁN',padding=8)
        decision.pack(fill='x',pady=5)
        self.decision_vars={k:tk.StringVar(value=v) for k,v in [
            ('agency',''),('subject','Về việc giao dự toán ngân sách'),
            ('funding','Ngân sách xã'),('description','')]}
        info=[('agency','Tên UBND xã/phường'),('subject','Trích yếu quyết định'),
              ('funding','Nguồn hình thành kinh phí'),('description','Nội dung quyết định')]
        for i,(key,title) in enumerate(info):
            r,c=divmod(i,2)
            ttk.Label(decision,text=title).grid(row=r,column=c*2,sticky='w',padx=4,pady=4)
            ttk.Entry(decision,textvariable=self.decision_vars[key],width=44).grid(row=r,column=c*2+1,sticky='ew',padx=4,pady=4)
        decision.columnconfigure(1,weight=1);decision.columnconfigure(3,weight=1)
        self.decision_vars['agency'].set(self.commune_var.get().split(' | ')[0] if self.commune_id() else '')
        decision_actions=ttk.Frame(decision)
        decision_actions.grid(row=2,column=0,columnspan=4,sticky='w',pady=7)
        ttk.Button(decision_actions,text='XEM TRƯỚC QUYẾT ĐỊNH / PHỤ LỤC (PDF)',
                   command=self.preview_decision).pack(side='left',padx=(0,8))
        ttk.Button(decision_actions,text='IN QUYẾT ĐỊNH / PHỤ LỤC',
                   command=lambda:self.preview_decision(print_now=True)).pack(side='left')
        reconcile=ttk.LabelFrame(upper,text='ĐỐI CHIẾU TỔNG TIỀN QUYẾT ĐỊNH VỚI CÁC DÒNG MÃ NGÀNH',padding=8)
        reconcile.pack(fill='x',pady=5)
        ttk.Label(reconcile,text='Tổng số tiền quyết định giao dự toán (VND):').pack(side='left')
        ttk.Entry(reconcile,textvariable=self.decision_total,width=22).pack(side='left',padx=8)
        self.reconcile_text=tk.StringVar(value='Chưa nhập tổng số tiền quyết định.')
        self.reconcile_label=tk.Label(reconcile,textvariable=self.reconcile_text,fg='#a11919',font=('Segoe UI',10,'bold'))
        self.reconcile_label.pack(side='left',padx=12)
        form=ttk.LabelFrame(upper,text='Thêm dòng dự toán',padding=8);form.pack(fill='x',pady=6)
        self.batch_vars={k:tk.StringVar() for k in BATCH_FIELDS}
        self.batch_vars['ma_loai_du_toan']=tk.StringVar()
        self.batch_vars['tk_no']=tk.StringVar()
        self.batch_vars['tk_co']=tk.StringVar()
        self.batch_vars['nguon_cap0']=tk.StringVar(value='99')
        self.batch_vars['qhns_cap0']=tk.StringVar(value=self.current_org_code())
        self.batch_vars['nguon'].set('')
        labels={'noi_dung':'Nội dung nhiệm vụ','loai':'Mã Loại','khoan':'Mã Khoản','nguon':'Nguồn chi tiết cấp 4','nguon_cap0':'Nguồn cấp 0','chuong':'Mã Chương','don_vi':'Đơn vị nhận','qhns':'Mã ĐVQHNS','so_tien':'Số tiền (VND)','qhns_cap0':'Mã tổ chức NS cấp 0','ma_loai_du_toan':'Mã loại dự toán','tk_no':'Tài khoản Nợ','tk_co':'Tài khoản Có'}
        for i,k in enumerate([*BATCH_FIELDS,'nguon_cap0','qhns_cap0','ma_loai_du_toan','tk_no','tk_co']):
            r=i//4;c=(i%4)*2
            ttk.Label(form,text=labels[k]).grid(row=r,column=c,sticky='w',padx=3,pady=5)
            widget=(ttk.Combobox(form,textvariable=self.batch_vars[k],width=19,values=source_display_values()) if k in ('nguon','nguon_cap0') else ttk.Entry(form,textvariable=self.batch_vars[k],width=21))
            widget.grid(row=r,column=c+1,sticky='ew',padx=4,pady=5)
            if k=='noi_dung':self.batch_first_widget=widget
        bar=ttk.Frame(upper);bar.pack(fill='x',pady=5)
        ttk.Button(bar,text='Thêm dòng mới',command=self.batch_add).pack(side='left')
        ttk.Button(bar,text='GỢI Ý ĐỊNH KHOẢN 0→4',command=self.choose_allocation_accounts).pack(side='left',padx=5)
        ttk.Button(bar,text='LƯU THAY ĐỔI DÒNG',command=self.batch_update_selected).pack(side='left',padx=6)
        ttk.Button(bar,text='XÓA DÒNG',command=self.batch_remove).pack(side='left',padx=6)
        ttk.Button(bar,text='Bỏ chọn / Nhập dòng mới',command=self.batch_clear_selection).pack(side='left',padx=6)
        ttk.Button(bar,text='Xuất đồng thời 3 bảng Excel',command=self.batch_export).pack(side='left',padx=6)
        ttk.Button(bar,text='XEM TRƯỚC PHIẾU / QUYẾT ĐỊNH',command=self.choose_print_preview).pack(side='left',padx=6)
        ttk.Button(bar,text='Sửa nghiệp vụ đã chọn',command=self.batch_edit_selected).pack(side='left',padx=6)
        ttk.Button(bar,text='Thêm từ màn hình Nghiệp vụ',command=self.add_entry_to_package).pack(side='left',padx=6)
        cols=tuple([*BATCH_FIELDS,'nguon_cap0','qhns_cap0','ma_loai_du_toan','tk_no','tk_co'])
        self.batch_tree=ttk.Treeview(table_shell,columns=cols,show='headings',height=8,
                                     selectmode='extended')
        for k in cols:
            self.batch_tree.heading(k,text=labels[k]);self.batch_tree.column(k,width=180 if k in ('noi_dung','don_vi') else 95)
        ybar=ttk.Scrollbar(table_shell,orient='vertical',command=self.batch_tree.yview)
        xbar=ttk.Scrollbar(table_shell,orient='horizontal',command=self.batch_tree.xview)
        self.batch_tree.configure(yscrollcommand=ybar.set,xscrollcommand=xbar.set)
        table_shell.columnconfigure(0,weight=1)
        table_shell.rowconfigure(0,weight=1)
        self.batch_tree.grid(row=0,column=0,sticky='nsew')
        ybar.grid(row=0,column=1,sticky='ns')
        xbar.grid(row=1,column=0,sticky='ew')
        self.batch_edit_status=tk.StringVar(value='Chọn hoặc nháy đúp một dòng để đưa dữ liệu lên ô nhập phía trên; sửa xong nhấn LƯU THAY ĐỔI DÒNG.')
        ttk.Label(lower_shell,textvariable=self.batch_edit_status,foreground='#165a89',wraplength=1020).pack(anchor='w')
        self.batch_tree.bind('<<TreeviewSelect>>',self.batch_select_row)
        self.batch_tree.bind('<Double-1>',self.batch_double_click)
        self.batch_total=tk.StringVar(value='0 dòng | Tổng: 0 VND')
        ttk.Label(lower_shell,textvariable=self.batch_total,font=('Segoe UI',11,'bold')).pack(anchor='e')
        self.update_package_reconciliation()

    @staticmethod
    def parse_vnd(value):
        raw=str(value).strip().replace(' ', '').replace(',', '').replace('.', '')
        if not raw or not raw.isdigit():
            raise ValueError('Tổng số tiền quyết định phải là số nguyên dương (VND).')
        amount=int(raw)
        if amount<=0:raise ValueError('Tổng số tiền quyết định phải lớn hơn 0.')
        return amount

    def reconciliation(self, rows=None):
        rows=self.batch_rows if rows is None else rows
        allocated=sum(int(r.get('so_tien',0) or 0) for r in rows)
        try:expected=self.parse_vnd(self.decision_total.get())
        except ValueError:return None,allocated,None
        return expected,allocated,expected-allocated

    def update_package_reconciliation(self):
        if not hasattr(self,'reconcile_text'):return
        expected,allocated,difference=self.reconciliation()
        if expected is None:
            msg=f'Đã phân bổ: {allocated:,} VND | Chưa nhập tổng tiền quyết định'
            color='#a11919'
        elif difference>0:
            msg=f'Đã phân bổ: {allocated:,} / {expected:,} VND | CÒN THIẾU: {difference:,} VND'
            color='#a11919'
        elif difference<0:
            msg=f'Đã phân bổ: {allocated:,} / {expected:,} VND | VƯỢT: {-difference:,} VND'
            color='#a11919'
        else:
            msg=f'ĐÃ KHỚP: {allocated:,} / {expected:,} VND (chênh lệch 0)'
            color='#137333'
        self.reconcile_text.set(msg)
        self.reconcile_label.configure(fg=color)

    def confirm_reconciliation(self, rows=None):
        expected,allocated,difference=self.reconciliation(rows)
        if expected is None:
            messagebox.showwarning('Thiếu tổng tiền quyết định',
                'Nhập Tổng số tiền quyết định giao dự toán ở tab Bộ 3 chứng từ / Phụ lục QĐ trước khi xuất.')
            return False
        if difference:
            label='CÒN THIẾU' if difference>0 else 'PHÂN BỔ VƯỢT'
            messagebox.showwarning('Chưa khớp quyết định',
                f'Tổng tiền quyết định: {expected:,} VND\n'
                f'Tổng các dòng mã ngành: {allocated:,} VND\n'
                f'{label}: {abs(difference):,} VND\n\n'
                'Hãy bổ sung hoặc sửa các dòng trong bộ phiếu trước khi xuất.')
            return False
        return True

    def choose_allocation_accounts(self):
        """Chỉ điền sau khi người dùng chọn rõ nghiệp vụ và hình thức cấp phát."""
        from c6_accounting import choices
        win=tk.Toplevel(self);win.title('Chọn định khoản theo CV 15602 – mục B.II.2.2.2')
        win.geometry('620x270');win.transient(self);win.grab_set()
        ttk.Label(win,text='Chọn tính chất kinh phí và hình thức cấp phát:',font=('Segoe UI',11,'bold')).pack(pady=15)
        items=choices(); labels=[x[0] for x in items]
        choice=tk.StringVar(value=labels[0]);cb=ttk.Combobox(win,textvariable=choice,values=labels,state='readonly',width=75)
        cb.pack(padx=15,pady=8)
        ttk.Label(win,text='Chỉ là quy tắc tham chiếu CV 15602 (2017); cần kiểm tra hiệu lực,\nmã nguồn và tính chất kinh phí theo quyết định thực tế.',justify='center').pack(pady=10)
        def apply():
            for label,no,co in items:
                if choice.get()==label:
                    self.batch_vars['tk_no'].set(no);self.batch_vars['tk_co'].set(co);break
            win.destroy()
        ttk.Button(win,text='ÁP DỤNG TÀI KHOẢN NỢ/CÓ',command=apply).pack(pady=8)

    def export_c6_word(self, code):
        if not self.batch_rows:
            return messagebox.showwarning('Chưa có dữ liệu','Hãy thêm nghiệp vụ trước khi xuất Word.')
        from c6_word import create_c6_word
        filename=code.replace('C6','C6-')+'_DU_THAO.docx'
        path=filedialog.asksaveasfilename(title='Lưu chứng từ Word có thể chỉnh sửa',defaultextension='.docx',initialfile=filename,filetypes=[('Word','*.docx')])
        if not path:return
        try:
            create_c6_word(path,code,self.batch_rows,
                commune=self.commune_var.get().split(' | ')[0],year=self.batch_meta['year'].get(),
                decision=self.batch_meta['decision'].get(),decision_date=self.batch_meta['decision_date'].get())
            messagebox.showinfo('Đã tạo bản Word','Đã lưu bản Word có thể chỉnh sửa. Đây là bản đối chiếu, chưa phải mẫu C6 chính thức.')
            if os.name=='nt':os.startfile(path)
        except Exception as exc:messagebox.showerror('Không thể xuất Word',str(exc))

    def batch_add(self):
        from batch_export import check_rows
        row={k:(v.get().split(' – ')[0].strip() if k in ('nguon','nguon_cap0') else v.get().strip()) for k,v in self.batch_vars.items()}
        try:
            row['so_tien']=int(row['so_tien'].replace(',','').replace('.','').replace(' ',''))
            self.validate_required_row(row)
            check_rows([row])
        except (ValueError,KeyError) as e:
            return messagebox.showerror('Dữ liệu không hợp lệ',str(e))
        from c6_accounting import check_allocation
        try:check_allocation([row])
        except ValueError as exc:return messagebox.showerror('Kiểm tra định khoản cấp 0 → cấp 4',str(exc))
        self.batch_rows.append(row)
        self.batch_vars['nguon_cap0'].set('99')
        self.batch_vars['qhns_cap0'].set(self.current_org_code())
        self.batch_tree.insert('','end',values=[f'{row[k]:,}' if k=='so_tien' else row.get(k,'') for k in self.batch_vars])
        self.batch_total.set(f'{len(self.batch_rows)} dòng | Tổng: {sum(r["so_tien"] for r in self.batch_rows):,} VND')
        self.update_package_reconciliation()
        for k in ('noi_dung','so_tien'):self.batch_vars[k].set('')

    def batch_remove(self):
        selected=self.batch_tree.selection()
        if not selected:
            return messagebox.showwarning('Chọn dòng','Chọn một hoặc nhiều dòng cần xóa trong bảng.')
        if not messagebox.askyesno('Xác nhận xóa',f'Bạn có chắc muốn xóa {len(selected)} dòng đã chọn khỏi bộ phiếu?'):
            return
        for item in sorted(selected,key=lambda x:self.batch_tree.index(x),reverse=True):
            idx=self.batch_tree.index(item)
            self.batch_tree.delete(item)
            self.batch_rows.pop(idx)
        self.batch_total.set(f'{len(self.batch_rows)} dòng | Tổng: {sum(r["so_tien"] for r in self.batch_rows):,} VND')
        self.update_package_reconciliation()
        self.batch_clear_selection()

    def validate_batch_qhns(self):
        """Không tự điền mã QHNS cấp 4 từ mã tổ chức NS cấp 0."""
        missing0=[str(i) for i,r in enumerate(self.batch_rows,1) if not r.get('qhns_cap0','').strip()]
        missing4=[str(i) for i,r in enumerate(self.batch_rows,1) if not r.get('qhns','').strip()]
        if missing0 or missing4:
            messagebox.showwarning('Thiếu mã đơn vị',
                ('Chưa có mã tổ chức ngân sách cấp 0 tại dòng: '+', '.join(missing0)+'\n' if missing0 else '')+
                ('Chưa có mã ĐVQHNS đơn vị nhận cấp 4 tại dòng: '+', '.join(missing4)+'\n' if missing4 else '')+
                'Chọn dòng, nhập mã đúng rồi bấm Lưu sửa dòng đã chọn trước khi xuất.')
            return False
        return True

    def preview_decision(self, print_now=False):
        from decision_preview import create_decision_preview
        if not self.batch_rows:
            return messagebox.showwarning('Thiếu dữ liệu','Chưa có dòng phân bổ trong bộ phiếu.')
        try:
            total=self.parse_vnd(self.decision_total.get())
            agency=self.decision_vars['agency'].get().strip()
            number=self.batch_meta['decision'].get().strip()
            date=self.batch_meta['decision_date'].get().strip()
            if not agency or not number or not date:
                raise ValueError('Cần nhập tên UBND, số và ngày quyết định.')
            datetime.strptime(date,'%Y-%m-%d')
            metadata={k:v.get().strip() for k,v in self.decision_vars.items()}
            metadata.update(number=number,date=date,year=self.batch_meta['year'].get(),total=total)
            path=create_decision_preview(metadata,self.batch_rows)
            if print_now:
                self.print_pdf_file(path, 'quyết định và phụ lục')
            elif os.name=='nt':os.startfile(path)
            else:webbrowser.open(Path(path).as_uri())
        except Exception as exc:
            messagebox.showerror('Không xem trước / in được quyết định',str(exc))

    def export_decision_word(self):
        """Export editable draft; separate from PDF C6 printing."""
        from tkinter import filedialog
        from decision_word import create_decision_word, FORM_LABELS
        if not self.batch_rows:
            return messagebox.showwarning('Chưa có dữ liệu', 'Hãy thêm nghiệp vụ vào bảng trước khi xuất Word.')
        try:
            total=self.parse_vnd(self.decision_total.get())
            metadata={k:v.get().strip() for k,v in self.decision_vars.items()}
            metadata.update(number=self.batch_meta['decision'].get().strip(),
                            date=self.batch_meta['decision_date'].get().strip(),
                            year=self.batch_meta['year'].get().strip(), total=total)
        except Exception as exc:
            return messagebox.showerror('Thông tin quyết định',str(exc))
        win=tk.Toplevel(self);win.title('Xuất quyết định Word có thể chỉnh sửa')
        win.geometry('600x285');win.transient(self);win.grab_set()
        ttk.Label(win,text='CHỌN LOẠI DỰ THẢO QUYẾT ĐỊNH WORD',font=('Segoe UI',12,'bold')).pack(pady=(14,9))
        selected=tk.StringVar(value='UBND')
        for key,label in FORM_LABELS.items():
            ttk.Radiobutton(win,text=label,variable=selected,value=key).pack(anchor='w',padx=20,pady=4)
        ttk.Label(win,text='Mẫu B/C hiện là bản dự thảo tham chiếu, chưa được đối chiếu với mẫu Word gốc.\nKiểm tra thẩm quyền và thể thức trước khi ban hành.',foreground='#9a5300',wraplength=550).pack(pady=8)
        def do_export():
            form=selected.get()
            path=filedialog.asksaveasfilename(parent=win,title='Lưu quyết định Word',
                defaultextension='.docx',filetypes=[('Word (.docx)','*.docx')],
                initialfile='Quyet_dinh_du_toan_'+form+'.docx')
            if not path:return
            try:
                create_decision_word(path,metadata,self.batch_rows,form)
                win.destroy()
                messagebox.showinfo('Đã xuất Word','Đã tạo file Word có thể chỉnh sửa:\n'+path+'\n\nKiểm tra biểu mẫu và căn cứ pháp lý trước khi ký.')
                if os.name=='nt':os.startfile(path)
            except Exception as exc:messagebox.showerror('Không xuất được Word',str(exc),parent=win)
        ttk.Button(win,text='XUẤT FILE WORD (.DOCX)',command=do_export).pack(pady=6)

    def print_pdf_file(self, path, document_name='chứng từ'):
        """Windows: yêu cầu xác nhận trước khi gửi PDF đến máy in mặc định."""
        if os.name != 'nt':
            webbrowser.open(Path(path).as_uri())
            messagebox.showinfo('In chứng từ', 'Đã mở PDF. Chọn In (Ctrl+P) trong trình xem PDF để chọn máy in.')
            return
        if not messagebox.askyesno('Xác nhận in',
                f'Gửi {document_name} tới MÁY IN MẶC ĐỊNH của Windows?\n\n'
                'Chọn Không nếu muốn xem PDF rồi tự chọn máy in bằng Ctrl+P.'):
            os.startfile(path)
            return
        try:
            os.startfile(path, 'print')
            messagebox.showinfo('Đã gửi lệnh in',
                'Đã yêu cầu ứng dụng PDF in bằng máy in mặc định.\n'
                'Hãy kiểm tra hàng đợi in; việc in thành công phụ thuộc ứng dụng PDF và máy in.')
        except OSError as exc:
            os.startfile(path)
            messagebox.showwarning('Không in tự động được',
                f'Windows không có ứng dụng PDF hỗ trợ lệnh In: {exc}\n'
                'PDF đã được mở; hãy nhấn Ctrl+P để in.')

    def batch_export(self):
        from batch_export import export_package
        if not self.confirm_reconciliation():return
        if not self.validate_all_package_rows():return
        if not self.validate_batch_qhns():return
        if not self.commune_id():return messagebox.showwarning('Chưa chọn xã','Chọn xã/phường trước.')
        try:
            year=int(self.batch_meta['year'].get())
            if year<2000 or year>2100:raise ValueError('Năm ngân sách không hợp lệ.')
            datetime.strptime(self.batch_meta['decision_date'].get(),'%Y-%m-%d')
            if not self.batch_meta['decision'].get().strip():raise ValueError('Thiếu số quyết định.')
        except ValueError as e:return messagebox.showerror('Thông tin quyết định',str(e))
        folder=filedialog.askdirectory(title='Chọn thư mục lưu bộ 3 chứng từ')
        if not folder:return
        try:
            paths,total=export_package(folder,self.commune_var.get().split(' | ')[0],year,self.batch_meta['decision'].get(),self.batch_meta['decision_date'].get(),self.batch_rows)
            messagebox.showinfo('Đã tạo 3 bảng dự thảo',f'Tổng tiền: {total:,} VND\n\n'+ '\n'.join(str(p) for p in paths)+'\n\nCần kiểm tra, hoàn thiện theo mẫu chính thức trước khi gửi KBNN.')
        except Exception as e:messagebox.showerror('Không xuất được',str(e))

    def _preview_rows(self, rows, title):
        """Editable draft preview; not a rendering of the statutory template."""
        from form_export import FORM_NAMES
        if not rows:
            return messagebox.showwarning('Chưa có nghiệp vụ', 'Chưa có dữ liệu để xem trước.')
        win=tk.Toplevel(self); win.title(title+' - BẢN XEM TRƯỚC DỮ LIỆU');win.geometry('1100x690')
        win.transient(self)
        ttk.Label(win,text=title,font=('Segoe UI',15,'bold')).pack(anchor='w',padx=14,pady=(12,4))
        ttk.Label(win,text='Chọn mẫu rồi nhấn XEM TRƯỚC NHƯ IN (PDF); sửa dòng tại đây và mở lại bản PDF để cập nhật.',foreground='#a01a1a').pack(anchor='w',padx=14)
        selected=tk.StringVar(value='C601')
        frame=ttk.Frame(win);frame.pack(fill='x',padx=14,pady=8)
        ttk.Label(frame,text='Xem dữ liệu cho mẫu:').pack(side='left')
        cb=ttk.Combobox(frame,textvariable=selected,state='readonly',width=63,
            values=[f'{k} — {v}' for k,v in FORM_NAMES.items()]);cb.pack(side='left',padx=8)
        cb.set('C601 — '+FORM_NAMES['C601'])
        columns=('stt','noi_dung','ma_loai_du_toan','nguon','chuong','loai','khoan','tk_no','tk_co','so_tien')
        names=('STT','Diễn giải nghiệp vụ / Nội dung phiếu','Loại DT','Nguồn','Chương','Loại','Khoản','TK Nợ','TK Có','Số tiền')
        table_frame=ttk.Frame(win);table_frame.pack(fill='both',expand=True,padx=14,pady=6)
        tree=ttk.Treeview(table_frame,columns=columns,show='headings',height=15)
        for key,label in zip(columns,names):
            tree.heading(key,text=label)
            tree.column(key,width=320 if key=='noi_dung' else 88,anchor='e' if key=='so_tien' else 'w')
        tree.pack(side='left',fill='both',expand=True)
        sb=ttk.Scrollbar(table_frame,orient='vertical',command=tree.yview);sb.pack(side='right',fill='y');tree.configure(yscrollcommand=sb.set)
        item_map={}
        total=0; problems=[]
        for i,row in enumerate(rows,1):
            total+=int(row.get('so_tien',0) or 0)
            missing=[label for key,label in [('ma_loai_du_toan','Loại DT'),('nguon','Nguồn'),('chuong','Chương'),('loai','Loại'),('khoan','Khoản'),('tk_no','TK Nợ'),('tk_co','TK Có')] if not str(row.get(key,'')).strip()]
            if missing:problems.append(f'Dòng {i}: cần kiểm tra '+', '.join(missing))
            values=[i]+[row.get(k,'') for k in columns[1:-1]]+[f'{int(row.get("so_tien",0) or 0):,}']
            iid=tree.insert('','end',values=values,tags=('warning',) if missing else ())
            item_map[iid]=i-1
        tree.tag_configure('warning',background='#ffe0e0')
        ttk.Label(win,text=f'{len(rows)} nghiệp vụ  |  Tổng cộng: {total:,} VND',font=('Segoe UI',12,'bold')).pack(anchor='e',padx=18,pady=4)
        expected,allocated,difference=self.reconciliation(rows)
        if expected is None:
            status='CHƯA NHẬP TỔNG TIỀN QUYẾT ĐỊNH'
        elif difference>0:
            status=f'CÒN THIẾU {difference:,} VND so với quyết định {expected:,} VND'
        elif difference<0:
            status=f'PHÂN BỔ VƯỢT {-difference:,} VND so với quyết định {expected:,} VND'
        else:
            status=f'ĐÃ KHỚP QUYẾT ĐỊNH: {expected:,} VND'
        ttk.Label(win,text=status,font=('Segoe UI',12,'bold'),foreground='#137333' if difference==0 else '#a11919').pack(anchor='e',padx=18,pady=4)

        notes=tk.Text(win,height=5,wrap='word',font=('Segoe UI',10));notes.pack(fill='x',padx=14,pady=6)
        notes.insert('1.0','CÁC Ô CẦN XÁC NHẬN:\n'+('\n'.join(problems) if problems else 'Không có ô trống theo kiểm tra sơ bộ. Vẫn cần đối chiếu nghiệp vụ và căn cứ pháp lý.'))
        notes.configure(state='disabled')
        def edit_preview(event=None):
            selected_ids=tree.selection()
            if len(selected_ids)!=1:return
            index=item_map[selected_ids[0]]
            original=rows[index]
            editor=tk.Toplevel(win);editor.title(f'Sửa trực tiếp dòng {index+1} trong xem trước')
            editor.geometry('720x650');editor.transient(win);editor.grab_set()
            fields=[('noi_dung','Nội dung/Diễn giải'),('ma_loai_du_toan','Mã loại dự toán'),
                    ('tk_no','Tài khoản Nợ'),('tk_co','Tài khoản Có'),('nguon','Nguồn cấp 4'),
                    ('nguon_cap0','Nguồn cấp 0'),('chuong','Chương'),('loai','Loại'),
                    ('khoan','Khoản'),('don_vi','Đơn vị'),('qhns','Mã QHNS cấp 4'),
                    ('qhns_cap0','Mã tổ chức NS cấp 0'),('so_tien','Số tiền')]
            values={}
            for n,(key,label) in enumerate(fields):
                ttk.Label(editor,text=label).grid(row=n,column=0,sticky='w',padx=12,pady=5)
                var=tk.StringVar(value=str(original.get(key,'')));values[key]=var
                if key=='ma_loai_du_toan':
                    field=ttk.Combobox(editor,textvariable=var,values=BUDGET_CATALOG.display_values(),width=52)
                else:field=ttk.Entry(editor,textvariable=var,width=54)
                field.grid(row=n,column=1,sticky='ew',padx=8,pady=5)
            def save_preview():
                updated=dict(original)
                for key,var in values.items():updated[key]=var.get().strip()
                try:
                    updated['so_tien']=self.parse_vnd(updated['so_tien'])
                    self.validate_required_row(updated)
                except (ValueError,TypeError) as exc:
                    return messagebox.showerror('Không thể lưu',str(exc),parent=editor)
                original.update(updated)
                if rows is self.batch_rows:
                    for j,item in enumerate(self.batch_tree.get_children()):
                        if j==index:
                            self.batch_tree.item(item,values=[f'{original[k]:,}' if k=='so_tien' else original.get(k,'') for k in self.batch_vars]);break
                    self.batch_total.set(f'{len(self.batch_rows)} dòng | Tổng: {sum(int(r["so_tien"]) for r in self.batch_rows):,} VND')
                    self.update_package_reconciliation()
                elif len(rows)==1:
                    # preview of current entry: synchronize edited values with entry form
                    mapping={'noi_dung':'description','ma_loai_du_toan':'budget_type','tk_no':'account_debit',
                             'tk_co':'account_credit','nguon':'source_code','chuong':'chapter',
                             'loai':'sector_type','khoan':'sector_item','so_tien':'amount'}
                    for key,dest in mapping.items():
                        if dest in self.vars:self.vars[dest].set(str(updated.get(key,'')))
                editor.destroy();win.destroy()
                if rows is self.batch_rows:self.preview_package()
                else:self.preview_current_entry()
            ttk.Button(editor,text='LƯU THAY ĐỔI VÀ CẬP NHẬT XEM TRƯỚC',command=save_preview).grid(row=len(fields),column=1,sticky='e',padx=12,pady=12)
        tree.bind('<Double-1>',edit_preview)
        buttons=ttk.Frame(win);buttons.pack(pady=8)
        def print_view():
            from print_preview import create_preview
            try:
                code=selected.get().split(' — ')[0].strip()
                expected, _, _ = self.reconciliation(rows)
                path=create_preview(code, rows,
                    commune=self.commune_var.get().split(' | ')[0],
                    year=self.batch_meta['year'].get(),
                    decision=self.batch_meta['decision'].get(),
                    decision_date=self.batch_meta['decision_date'].get(), expected=expected)
                if os.name=='nt': os.startfile(path)
                else: webbrowser.open(Path(path).as_uri())
            except Exception as exc:
                messagebox.showerror('Không thể mở bản xem trước in',str(exc),parent=win)
        ttk.Button(buttons,text='XEM TRƯỚC NHƯ IN (PDF)',command=print_view).pack(side='left',padx=8)
        def print_selected_form():
            from print_preview import create_preview
            try:
                code=selected.get().split(' — ')[0].strip()
                expected, _, _ = self.reconciliation(rows)
                path=create_preview(code, rows,
                    commune=self.commune_var.get().split(' | ')[0],
                    year=self.batch_meta['year'].get(),
                    decision=self.batch_meta['decision'].get(),
                    decision_date=self.batch_meta['decision_date'].get(), expected=expected)
                self.print_pdf_file(path, 'phiếu '+code)
            except Exception as exc:
                messagebox.showerror('Không thể in phiếu',str(exc),parent=win)
        ttk.Button(buttons,text='IN PHIẾU ĐÃ CHỌN',command=print_selected_form).pack(side='left',padx=8)
        ttk.Button(buttons,text='SỬA DÒNG ĐÃ CHỌN',command=edit_preview).pack(side='left',padx=8)
        ttk.Button(buttons,text='Đóng xem trước',command=win.destroy).pack(side='left',padx=8)


    def preview_current_entry(self):
        data={k:v.get().strip() for k,v in self.vars.items()}
        try:amount=int(data['amount'].replace(',','').replace('.','').replace(' ',''))
        except ValueError:return messagebox.showwarning('Số tiền','Nhập số tiền trước khi xem trước.')
        if not data['description'].strip() or amount<=0:
            return messagebox.showwarning('Nghiệp vụ','Nhập diễn giải và số tiền lớn hơn 0.')
        def code(k):return data[k].split(' – ')[0].strip()
        row={'noi_dung':data['description'],'so_tien':amount,'ma_loai_du_toan':BUDGET_CATALOG.extract_code(data['budget_type']),
             'nguon':code('source_code') or '','chuong':code('chapter'),'loai':code('sector_type'),
             'khoan':code('sector_item'),'tk_no':code('account_debit'),'tk_co':code('account_credit')}
        self._preview_rows([row],'Xem trước nghiệp vụ đang nhập')

    def choose_print_preview(self):
        """Chọn đúng loại chứng từ, không hiển thị bảng dữ liệu trung gian."""
        win=tk.Toplevel(self)
        win.title('Chọn mẫu phiếu / quyết định để xem trước như in')
        win.geometry('720x610')
        win.transient(self)
        win.grab_set()
        ttk.Label(win,text='CHỌN BIỂU MẪU XEM TRƯỚC',font=('Segoe UI',13,'bold')).pack(pady=(18,8))
        options=[
            ('C601','C6-01 – Phiếu nhập dự toán (đã điền dữ liệu)'),
            ('C602','C6-02 – Phiếu nhập dự toán cấp 0 (tự điền số liệu)'),
            ('C603','C6-03 – Chứng từ phân bổ dự toán (mẫu gốc tham khảo)'),
            ('C604','C6-04 – Phiếu điều chỉnh dự toán (đã điền dữ liệu)'),
            ('C601_WORD','Xuất C6-01 Word (có thể chỉnh sửa)'),
            ('C602_WORD','Xuất C6-02 Word (có thể chỉnh sửa)'),
            ('C603_WORD','Xuất C6-03 Word (có thể chỉnh sửa)'),
            ('C604_WORD','Xuất C6-04 Word (có thể chỉnh sửa)'),
            ('QD','Quyết định giao dự toán và phụ lục (bản dự thảo)'),
            ('QD_WORD','Xuất Quyết định Word (UBND xã / Mẫu B / Mẫu C)'),
        ]
        chosen=tk.StringVar(value='C601')
        for key,label in options:
            ttk.Radiobutton(win,text=label,variable=chosen,value=key).pack(anchor='w',padx=28,pady=6)
        ttk.Label(win,text='C6-02 đã tự điền số liệu; C6-03 vẫn chỉ là mẫu tham khảo.',foreground='#9a5300').pack(pady=(8,4))
        buttons=ttk.Frame(win);buttons.pack(pady=12)
        def show():
            key=chosen.get()
            win.destroy()
            if key.endswith('_WORD') and key.startswith('C6'):
                self.export_c6_word(key[:-5])
            elif key in ('C601','C602','C604'):
                self.preview_package(key)
            elif key=='QD':
                self.preview_decision()
            elif key=='QD_WORD':
                self.export_decision_word()
            else:
                from print_preview import open_reference_template
                try:
                    path=open_reference_template(key)
                    messagebox.showwarning('Mẫu tham khảo chưa điền dữ liệu',
                        'Đây là bản sao bố cục mẫu C6 gốc, CHƯA có số liệu nghiệp vụ. '
                        'Không sử dụng bản này như phiếu đã lập.')
                    if os.name=='nt':os.startfile(path)
                    else:webbrowser.open(Path(path).as_uri())
                except Exception as exc:
                    messagebox.showerror('Không mở được biểu mẫu',str(exc))
        ttk.Button(buttons,text='XEM TRƯỚC MẪU ĐÃ CHỌN',command=show).pack(side='left',padx=8)
        ttk.Button(buttons,text='Đóng',command=win.destroy).pack(side='left',padx=8)

    def preview_package(self, code='C601'):
        """Tạo mẫu C6 trong tiến trình con để lỗi PyMuPDF không đóng giao diện."""
        if not self.batch_rows:
            return messagebox.showwarning('Chưa có dữ liệu', 'Hãy đưa nghiệp vụ vào bộ phiếu trước khi xem trước.')
        try:
            if code == 'C601':
                from c6_accounting import check_allocation
                check_allocation(self.batch_rows)
            from c6_safe_preview import generate_c6_safely
            expected, _, _ = self.reconciliation(self.batch_rows)
            path = generate_c6_safely(
                code, self.batch_rows,
                commune=self.commune_var.get().split(' | ')[0],
                year=self.batch_meta['year'].get(),
                decision=self.batch_meta['decision'].get(),
                decision_date=self.batch_meta['decision_date'].get(),
                expected=expected,
            )
            if os.name == 'nt':
                os.startfile(str(path))
            else:
                webbrowser.open(Path(path).as_uri())
        except Exception as exc:
            messagebox.showerror('Không thể xem trước mẫu C6', str(exc))

    def batch_edit_selected(self):
        selection=self.batch_tree.selection()
        if len(selection)!=1:return messagebox.showwarning('Chọn dòng','Chọn một nghiệp vụ cần sửa.')
        item=selection[0];idx=self.batch_tree.index(item);row=self.batch_rows[idx]
        win=tk.Toplevel(self);win.title('Sửa nghiệp vụ trong bộ phiếu');win.geometry('660x620');win.transient(self);win.grab_set()
        fields=[('noi_dung','Nội dung diễn giải'),('nguon_cap0','Nguồn cấp 0'),('qhns_cap0','Mã tổ chức NS cấp 0'),('ma_loai_du_toan','Mã loại dự toán'),('nguon','Mã nguồn'),('chuong','Chương'),('loai','Loại'),('khoan','Khoản'),('tk_no','Tài khoản Nợ'),('tk_co','Tài khoản Có'),('don_vi','Đơn vị nhận'),('qhns','Mã ĐVQHNS cấp 4'),('so_tien','Số tiền')]
        inputs={}
        for i,(key,label) in enumerate(fields):
            ttk.Label(win,text=label).grid(row=i,column=0,sticky='w',padx=14,pady=7)
            v=tk.StringVar(value=str(row.get(key,'')));inputs[key]=v
            ttk.Entry(win,textvariable=v,width=57).grid(row=i,column=1,sticky='ew',padx=10,pady=7)
        def save():
            try:
                amount=int(inputs['so_tien'].get().replace(',','').replace('.','').replace(' ',''))
                if amount<=0:raise ValueError()
            except ValueError:return messagebox.showerror('Số tiền','Số tiền phải là số nguyên dương.',parent=win)
            updated=dict(row)
            for key,_ in fields:updated[key]=amount if key=='so_tien' else inputs[key].get().strip()
            try:self.validate_required_row(updated)
            except (ValueError,TypeError) as exc:return messagebox.showerror('Thiếu thông tin',str(exc),parent=win)
            row.update(updated)
            self.batch_tree.item(item,values=[f'{row[k]:,}' if k=='so_tien' else row.get(k,'') for k in self.batch_vars])
            self.batch_total.set(f'{len(self.batch_rows)} dòng | Tổng: {sum(r["so_tien"] for r in self.batch_rows):,} VND')
            self.update_package_reconciliation()
            win.destroy()
        ttk.Button(win,text='Lưu chỉnh sửa',command=save).grid(row=len(fields),column=1,sticky='e',padx=14,pady=16)

    def add_entry_to_package(self):
        """Gom nhieu nghiep vu vao mot bo chung tu, chua xuat cho den khi nguoi dung yeu cau."""
        if not self.commune_id():
            return messagebox.showwarning('Chưa chọn xã', 'Chọn xã/phường trước khi thêm nghiệp vụ.')
        data={k:v.get().strip() for k,v in self.vars.items()}
        if not data['description']:
            return messagebox.showwarning('Thiếu diễn giải', 'Nhập nội dung diễn giải nghiệp vụ.')
        try:
            amount=int(data['amount'].replace(',','').replace('.','').replace(' ',''))
            if amount<=0: raise ValueError()
            datetime.strptime(data['date'],'%Y-%m-%d')
        except ValueError:
            return messagebox.showerror('Dữ liệu không hợp lệ','Kiểm tra ngày YYYY-MM-DD và số tiền VND lớn hơn 0.')
        def code(k): return data[k].split(' – ')[0].strip()
        row={'don_vi':'','qhns':'','chuong':code('chapter'),'loai':code('sector_type'),
             'khoan':code('sector_item'),'nguon':code('source_code') or '','nguon_cap0':'99','qhns_cap0':self.current_org_code(),
             'noi_dung':data['description'],'so_tien':amount,
             'ma_loai_du_toan':BUDGET_CATALOG.extract_code(data['budget_type']),
             'tk_no':code('account_debit'),'tk_co':code('account_credit'),
             'nguon_goc':self.origin.get(),'ngay_nghiep_vu':data['date']}
        try:self.validate_required_row(row)
        except (ValueError,TypeError) as exc:
            return messagebox.showerror('Thiếu thông tin bắt buộc',str(exc))
        self.batch_rows.append(row)
        self.batch_vars['nguon_cap0'].set('99')
        self.batch_vars['qhns_cap0'].set(self.current_org_code())
        self.batch_tree.insert('','end',values=[f'{row[k]:,}' if k=='so_tien' else row[k] for k in self.batch_vars])
        self.batch_total.set(f'{len(self.batch_rows)} dòng | Tổng: {sum(r["so_tien"] for r in self.batch_rows):,} VND')
        self.update_package_reconciliation()
        self.batch_meta['year'].set(data['date'][:4])
        self.vars['description'].set('')
        self.vars['amount'].set('')
        self.tabs.select(self.tab_batch)
        messagebox.showinfo('Đã thêm nghiệp vụ',
            f'Đã thêm dòng thứ {len(self.batch_rows)} vào bộ phiếu.\n'
            'Dòng đã chuyển ngay sang tab Bộ 3 chứng từ / Quyết định.\n'
            'Vui lòng xác định riêng NGUỒN CẤP 0 trước khi xuất; nguồn cấp 4 được giữ chi tiết.\n'
            'Tiếp tục nhập nghiệp vụ khác, sau đó tạo phiếu và quyết định.')

    def open_package(self):
        self.tabs.select(self.tab_batch)
        if not self.batch_rows:
            messagebox.showinfo('Bộ phiếu đang trống','Hãy bấm “Thêm nghiệp vụ vào bộ phiếu” cho từng dòng trước.')

    def entry_to_forms(self):
        data={k:v.get().strip() for k,v in self.vars.items()}
        try:
            amount=int(data['amount'].replace(',','').replace('.','').replace(' ',''))
            if amount<=0:raise ValueError()
        except ValueError:
            return messagebox.showerror('So tien','Can nhap so tien nguyen duong truoc khi tao phieu.')
        row={'don_vi':'','qhns':'','chuong':data['chapter'],'loai':data['sector_type'],
             'khoan':data['sector_item'],'nguon':data['source_code'],
             'noi_dung':data['description'],'so_tien':amount}
        self.choose_forms([row],data['date'][:4],'',data['date'])

    def history_to_forms(self):
        data=self.selected_voucher()
        if not data:return
        row={'don_vi':'','qhns':'','chuong':data['chapter'],'loai':data['sector_type'],
             'khoan':data['sector_item'],'nguon':data['source_code'],
             'noi_dung':data['description'],'so_tien':data['amount']}
        self.choose_forms([row],data['year'],'',data['date'])

    def batch_to_forms(self):
        if not self.confirm_reconciliation():return
        if not self.validate_all_package_rows():return
        if not self.validate_batch_qhns():return
        if not self.batch_rows:
            return messagebox.showwarning('Bộ phiếu trống','Chưa có nghiệp vụ nào trong bộ phiếu.')
        self.choose_forms(self.batch_rows,self.batch_meta['year'].get(),
                          self.batch_meta['decision'].get(),self.batch_meta['decision_date'].get())

    def choose_forms(self,rows,year,decision,decision_date):
        if not self.confirm_reconciliation(rows):return
        if not self.validate_all_package_rows(rows):return
        if rows is self.batch_rows and not self.validate_batch_qhns():return
        from form_export import FORM_NAMES, export_selected
        if not self.commune_id():return messagebox.showwarning('Chua chon xa','Chon xa/phuong truoc.')
        if not rows:return messagebox.showwarning('Chua co du lieu','Can co it nhat mot dong nghiep vu.')
        if any(not r.get('nguon_cap0') for r in rows):
            if not messagebox.askyesno('Nguồn cấp 0 chưa xác định', 'Một số dòng chưa có mã nguồn cấp 0.\nXuất bảng DỰ THẢO có cảnh báo để tiếp tục đối chiếu (không dùng để nhập TABMIS)?'):
                return
        win=tk.Toplevel(self);win.title('Tạo bộ phiếu và quyết định từ nhiều nghiệp vụ - bản dự thảo');win.geometry('720x610')
        win.transient(self);win.grab_set()
        ttk.Label(win,text=f'CHỌN MẪU XUẤT CHO {len(rows)} NGHIỆP VỤ | TỔNG {sum(r["so_tien"] for r in rows):,} VND',font=('Segoe UI',13,'bold')).pack(anchor='w',padx=18,pady=(16,5))
        ttk.Label(win,text='File xuất là bảng DỰ THẢO tổng hợp, chưa phải mẫu C6/Quyết định chính thức. Kiểm tra mã loại dự toán và định khoản trước khi ký.',foreground='#9C321A',wraplength=650).pack(anchor='w',padx=18,pady=5)
        flags={code:tk.BooleanVar(value=(code in ('C601','C602','C603','C604'))) for code in FORM_NAMES}
        for code,name in FORM_NAMES.items():
            ttk.Checkbutton(win,text=code+' — '+name,variable=flags[code]).pack(anchor='w',padx=22,pady=5)
        info=ttk.Frame(win);info.pack(fill='x',padx=18,pady=10)
        vars_={'year':tk.StringVar(value=str(year)),'decision':tk.StringVar(value=str(decision)),
               'decision_date':tk.StringVar(value=str(decision_date))}
        for i,(k,label) in enumerate([('year','Nam NS'),('decision','So quyet dinh'),('decision_date','Ngay QD')]):
            ttk.Label(info,text=label).grid(row=i,column=0,sticky='w',pady=4)
            ttk.Entry(info,textvariable=vars_[k],width=32).grid(row=i,column=1,sticky='w',padx=10,pady=4)
        def go():
            if not self.confirm_reconciliation(rows):return
            selected=[c for c,v in flags.items() if v.get()]
            if not selected:return messagebox.showwarning('Chua chon','Chon it nhat mot mau.',parent=win)
            try:
                y=int(vars_['year'].get());assert 2000<=y<=2100
                if vars_['decision_date'].get():datetime.strptime(vars_['decision_date'].get(),'%Y-%m-%d')
            except (ValueError,AssertionError):return messagebox.showerror('Thong tin','Kiem tra nam va ngay YYYY-MM-DD.',parent=win)
            folder=filedialog.askdirectory(parent=win,title='Chon thu muc luu cac bang du thao')
            if not folder:return
            try:
                paths,total=export_selected(folder,self.commune_var.get().split(' | ')[0],y,
                    vars_['decision'].get(),vars_['decision_date'].get(),rows,selected)
                win.destroy();messagebox.showinfo('Da xuat ban du thao',f'{len(paths)} file | Tong {total:,} VND\n\n'+
                    '\n'.join(str(p) for p in paths)+'\n\nChua phai chung tu chinh thuc.')
            except Exception as exc:messagebox.showerror('Loi xuat',str(exc),parent=win)
        ttk.Button(win,text='Xem trước dữ liệu cho các mẫu đã chọn',command=lambda:self._preview_rows(rows,'Xem trước bộ chứng từ')).pack(pady=6)
        ttk.Button(win,text='Xuất các bảng DỰ THẢO Excel đã chọn',command=go).pack(pady=8)

    def make_guide(self):
        txt=tk.Text(self.tab_guide,wrap='word',font=('Segoe UI',11),padx=15,pady=12)
        txt.pack(fill='both',expand=True)
        txt.insert('1.0','''NGUỒN TÀI LIỆU THAM KHẢO\n\n• Công văn 15602/BTC-KBNN ngày 17/11/2017: quy trình nhập dự toán NSĐP.\n• Phụ lục II: nguyên tắc kết hợp tổ hợp tài khoản dự toán cấp 0, 1, 4.\n• Phụ lục V: điều chỉnh dự toán theo trạng thái và phân hệ.\n• Danh mục MLNS theo các phụ lục Thông tư 130/2025/TT-BTC, ghi nhận sửa đổi bởi Thông tư 123/2026/TT-BTC.\n\nGIỚI HẠN CỦA PHIÊN BẢN NÀY\n\n1. Mới có danh mục mẫu Loại/Khoản; chưa nhập đầy đủ MLNS từ các tệp .doc và .xls đính kèm.\n2. Đã kèm bốn tệp mẫu C6 nguyên gốc để xem. Chưa tự điền được lên mẫu chính thức; xuất Excel là bảng đối chiếu nội bộ.\n3. Chưa xác minh tính hiệu lực của các quy tắc năm 2017 trong năm 2026.\n4. Mã loại dự toán được gợi ý từ CSV đã đối chiếu; nếu CSV chưa có mã thì để trống, không tự suy đoán.\n5. Không có API ChatGPT; có thể dùng ChatGPT trình duyệt để hỗ trợ đối chiếu.\n6. Không gửi dữ liệu hoặc kết nối TABMIS.\n\nQUY TRÌNH SỬ DỤNG\n\n1. Thêm xã/phường, nhập các mã riêng của xã.\n2. Chọn xã, nhập nghiệp vụ và số tiền.\n3. Xem hướng dẫn; cán bộ tự đối chiếu và điền mã đã xác minh.\n4. Lưu dự thảo, xuất Excel hoặc phiếu kiểm tra PDF.\n5. Sao lưu dữ liệu SQLite định kỳ.\n\nDỮ LIỆU\n\nCơ sở dữ liệu được lưu tại ~/TroLyDuToanXa/du_toan_xa.sqlite3\n''')
        txt.config(state='disabled')

if __name__=='__main__':
    if '--c6-preview-worker' in sys.argv:
        from c6_safe_preview import worker_main
        sys.exit(worker_main(sys.argv[sys.argv.index('--c6-preview-worker') + 1:]))
    App().mainloop()
