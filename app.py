"""Trợ lý dự toán ngân sách xã — bản thử nghiệm, không kết nối TABMIS."""
import csv
import unicodedata
import json
import sqlite3
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
    con.commit()
    return con

FIELDS = ['date','kind','description','amount','budget_level','account_debit','account_credit',
          'budget_type','chapter','sector_type','sector_item','econ_item','source_code']
LABELS = ['Ngày chứng từ (YYYY-MM-DD)','Nghiệp vụ','Diễn giải','Số tiền (VND)','Cấp ngân sách',
          'Tài khoản Nợ','Tài khoản Có','Mã loại dự toán','Mã Chương','Mã Loại',
          'Mã Khoản','Mã Mục/Tiểu mục','Mã nguồn NSNN']
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

# Danh mục Loại/Khoản trích chọn từ Phụ lục II kèm TT 130/2025/TT-BTC,
# tài liệu người dùng cung cấp có chú thích sửa đổi TT 123/2026/TT-BTC.
# Đây là tập dữ liệu khởi đầu, KHÔNG phải toàn bộ danh mục.
SECTORS = [
 ('010','011','Quốc phòng','quốc phòng;dân quân;quân sự'),
 ('010','014','Chuẩn bị động viên','động viên'),
 ('040','041','An ninh và trật tự an toàn xã hội','an ninh;trật tự;an toàn xã hội;công an'),
 ('070','071','Giáo dục mầm non','mầm non;nhà trẻ;mẫu giáo'),
 ('070','072','Giáo dục tiểu học','tiểu học;trường tiểu học'),
 ('070','073','Giáo dục trung học cơ sở','trung học cơ sở;thcs'),
 ('070','074','Giáo dục trung học phổ thông','trung học phổ thông;thpt'),
 ('070','075','Giáo dục nghề nghiệp - giáo dục thường xuyên','giáo dục thường xuyên;giáo dục nghề nghiệp'),
 ('070','081','Giáo dục đại học','đại học'),
 ('070','082','Giáo dục sau đại học','sau đại học;thạc sĩ;tiến sĩ'),
 ('070','085','Đào tạo lại, bồi dưỡng nghiệp vụ khác cho cán bộ, công chức, viên chức','bồi dưỡng nghiệp vụ;đào tạo lại'),
 ('070','091','Giáo dục nghề nghiệp trình độ sơ cấp','đào tạo sơ cấp;nghề sơ cấp'),
 ('070','092','Giáo dục nghề nghiệp trình độ trung cấp','đào tạo trung cấp;nghề trung cấp'),
 ('070','093','Giáo dục nghề nghiệp trình độ cao đẳng','đào tạo cao đẳng;nghề cao đẳng'),
 ('100','101','Nghiên cứu cơ bản','nghiên cứu cơ bản'),
 ('100','102','Nghiên cứu ứng dụng','nghiên cứu ứng dụng'),
 ('100','103','Phát triển công nghệ, phát triển giải pháp xã hội','phát triển công nghệ'),
 ('100','104','Nghiên cứu công nghệ chiến lược','công nghệ chiến lược'),
]

def normalize(text):
    text=unicodedata.normalize('NFD',text.lower().replace('đ','d'))
    return ' '.join(''.join(ch for ch in text if unicodedata.category(ch)!='Mn').split())

def find_sectors(description):
    query=normalize(description)
    if not query: return []
    results=[]
    for loai,khoan,name,keywords in SECTORS:
        phrases=[normalize(name)]+[normalize(x) for x in keywords.split(';')]
        matched=[x for x in phrases if len(x)>3 and x in query]
        if matched: results.append((max(map(len,matched)),loai,khoan,name,matched[0]))
    return sorted(results,reverse=True)

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('TRỢ LÝ DỰ TOÁN NGÂN SÁCH XÃ — BẢN THỬ NGHIỆM')
        self.geometry('1180x790')
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
        ttk.Label(top,text='Nhiều xã/phường • Dữ liệu lưu tại máy • Định khoản chỉ được xác nhận sau kiểm tra nghiệp vụ',foreground='#555').pack(anchor='w')
        choose = ttk.Frame(self,padding=(14,0,14,8)); choose.pack(fill='x')
        ttk.Label(choose,text='Xã/phường đang làm việc:').pack(side='left')
        self.commune_var=tk.StringVar()
        self.commune_box=ttk.Combobox(choose,textvariable=self.commune_var,state='readonly',width=48)
        self.commune_box.pack(side='left',padx=8)
        self.commune_box.bind('<<ComboboxSelected>>',lambda e:self.refresh_vouchers())
        ttk.Button(choose,text='Quản lý xã/phường',command=self.manage_communes).pack(side='left')
        ttk.Button(choose,text='Sao lưu dữ liệu',command=self.backup).pack(side='left',padx=8)
        ttk.Button(choose,text='Thoát',command=self.safe_exit).pack(side='right')
        self.protocol('WM_DELETE_WINDOW',self.safe_exit)
        self.tabs=ttk.Notebook(self); self.tabs.pack(fill='both',expand=True,padx=14,pady=5)
        self.tab_entry=ttk.Frame(self.tabs,padding=12); self.tabs.add(self.tab_entry,text='Nhập nghiệp vụ')
        self.tab_history=ttk.Frame(self.tabs,padding=12); self.tabs.add(self.tab_history,text='Lịch sử / Xuất phiếu')
        self.tab_catalog=ttk.Frame(self.tabs,padding=12); self.tabs.add(self.tab_catalog,text='Tra cứu MLNS / Gợi ý mã ngành')
        self.tab_batch=ttk.Frame(self.tabs,padding=12); self.tabs.add(self.tab_batch,text='Bộ 3 chứng từ / Phụ lục QĐ')
        self.tab_guide=ttk.Frame(self.tabs,padding=12); self.tabs.add(self.tab_guide,text='Hướng dẫn hạch toán')
        self.make_entry(); self.make_history(); self.make_catalog(); self.make_batch(); self.make_guide(); self.refresh_communes()
        ttk.Label(self,text='LƯU Ý: Phần mềm không gửi dữ liệu lên mạng, không ghi TABMIS và không thay thế kiểm soát của cán bộ nghiệp vụ.',foreground='#8a3b20',padding=10).pack(fill='x')

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
        main=ttk.Frame(self.tab_entry);main.pack(fill='both',expand=True)
        left=ttk.Frame(main);left.pack(side='left',fill='both',expand=True)
        self.vars={k:tk.StringVar() for k in FIELDS}
        self.vars['date'].set(datetime.now().strftime('%Y-%m-%d'))
        self.vars['kind'].set(KINDS[0]);self.vars['budget_level'].set('4')
        for i,(k,label) in enumerate(zip(FIELDS,LABELS)):
            ttk.Label(left,text=label).grid(row=i,column=0,sticky='w',pady=5)
            if k=='kind': widget=ttk.Combobox(left,textvariable=self.vars[k],values=KINDS,state='readonly',width=49)
            else:widget=ttk.Entry(left,textvariable=self.vars[k],width=52)
            widget.grid(row=i,column=1,sticky='ew',padx=10,pady=5)
        left.columnconfigure(1,weight=1)
        controls=ttk.Frame(left);controls.grid(row=len(FIELDS),column=0,columnspan=2,sticky='w',pady=12)
        ttk.Button(controls,text='Xem hướng dẫn nghiệp vụ',command=self.suggest).pack(side='left')
        ttk.Button(controls,text='Gợi ý mã ngành từ diễn giải',command=self.suggest_sector).pack(side='left',padx=8)
        ttk.Button(controls,text='Kiểm tra và lưu dự thảo',command=self.save_voucher).pack(side='left',padx=8)
        right=ttk.LabelFrame(main,text='Căn cứ và lưu ý kiểm soát',padding=12);right.pack(side='left',fill='both',expand=True,padx=(16,0))
        self.guidance=tk.Text(right,wrap='word',width=44,height=25,font=('Segoe UI',10))
        self.guidance.pack(fill='both',expand=True)
        self.set_guidance('Chọn nghiệp vụ và bấm “Xem hướng dẫn nghiệp vụ”.\n\nỨng dụng KHÔNG tự điền tài khoản Nợ/Có khi thiếu dữ liệu nghiệp vụ hoặc chưa xác minh hiệu lực văn bản.')

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
        ttk.Label(self.tab_catalog,text='Danh mục trích chọn từ Phụ lục II – TT 130/2025/TT-BTC (có ghi chú sửa đổi TT 123/2026). Chưa đầy đủ, cần kiểm tra hiệu lực.',foreground='#92430d',wraplength=1000).pack(anchor='w',pady=5)
        bar=ttk.Frame(self.tab_catalog);bar.pack(fill='x',pady=9)
        ttk.Label(bar,text='Mã hoặc nghiệp vụ:').pack(side='left')
        self.catalog_search=tk.StringVar()
        entry=ttk.Entry(bar,textvariable=self.catalog_search,width=75);entry.pack(side='left',fill='x',expand=True,padx=8)
        entry.bind('<Return>',lambda e:self.search_catalog())
        ttk.Button(bar,text='Tra cứu / Gợi ý',command=self.search_catalog).pack(side='left')
        ttk.Button(bar,text='Xem tất cả',command=lambda:(self.catalog_search.set(''),self.search_catalog())).pack(side='left',padx=5)
        cols=('loai','khoan','name','match')
        self.catalog_tree=ttk.Treeview(self.tab_catalog,columns=cols,show='headings',height=15)
        for key,title,width in [('loai','Mã Loại',95),('khoan','Mã Khoản',95),('name','Tên ngành / lĩnh vực',510),('match','Từ khóa khớp',210)]:
            self.catalog_tree.heading(key,text=title);self.catalog_tree.column(key,width=width)
        self.catalog_tree.pack(fill='both',expand=True)
        foot=ttk.Frame(self.tab_catalog);foot.pack(fill='x',pady=9)
        ttk.Button(foot,text='Đưa mã Loại / Khoản vào phiếu',command=self.apply_sector).pack(side='left')
        self.catalog_status=tk.StringVar(value='Tra cứu theo tên, mã hoặc nhập một nghiệp vụ để tìm mã ngành.')
        ttk.Label(foot,textvariable=self.catalog_status,foreground='#555',wraplength=730).pack(side='left',padx=15)
        self.render_catalog([] ,all_items=True)

    def render_catalog(self,results,all_items=False):
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
        self.catalog_status.set(f'Có {len(matches)} kết quả trong danh mục mẫu.' if matches else 'Không thấy mã trong danh mục mẫu. Cần tra cứu Phụ lục II đầy đủ.')

    def apply_sector(self):
        selected=self.catalog_tree.selection()
        if not selected:return messagebox.showwarning('Chưa chọn','Chọn một dòng mã ngành trước.')
        loai,khoan,name,_=self.catalog_tree.item(selected[0],'values')
        if messagebox.askyesno('Xác nhận mã ngành',f'Đưa mã Loại {loai} / Khoản {khoan} – {name} vào phiếu?\n\nĐây là gợi ý theo từ khóa, cần đối chiếu bản chất nhiệm vụ chi và văn bản có hiệu lực.'):
            self.vars['sector_type'].set(loai)
            self.vars['sector_item'].set(khoan)
            self.tabs.select(self.tab_entry)
            self.set_guidance(f'GỢI Ý MÃ NGÀNH: Loại {loai}, Khoản {khoan} – {name}\n\nNguồn: Phụ lục II kèm TT 130/2025/TT-BTC (bản có ghi nhận sửa đổi theo TT 123/2026).\nĐây là gợi ý tra cứu, không phải xác nhận hạch toán. Kiểm tra nghiệp vụ, niên độ và hiệu lực trước khi sử dụng.')

    def save_voucher(self):
        cid=self.commune_id()
        if not cid:return messagebox.showwarning('Chưa chọn xã','Hãy thêm và chọn xã/phường trước.')
        data={k:v.get().strip() for k,v in self.vars.items()}
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

    def make_batch(self):
        from batch_export import FIELDS as BATCH_FIELDS
        self.batch_rows=[]
        ttk.Label(self.tab_batch,text='LẬP ĐỒNG THỜI C6-02 CẤP 0, C6-01 CẤP 4 VÀ PHỤ LỤC QUYẾT ĐỊNH',font=('Segoe UI',12,'bold')).pack(anchor='w')
        ttk.Label(self.tab_batch,text='Bản thử nghiệm: xuất 3 BẢNG CHUẨN BỊ Excel, chưa phải mẫu chứng từ KBNN chính thức. Mỗi dòng có thể khác Loại, Khoản, nguồn và đơn vị nhận.',foreground='#92430d',wraplength=1020).pack(anchor='w',pady=6)
        meta=ttk.Frame(self.tab_batch);meta.pack(fill='x',pady=5)
        self.batch_meta={k:tk.StringVar(value=v) for k,v in [('year',str(datetime.now().year)),('decision',''),('decision_date',datetime.now().strftime('%Y-%m-%d'))]}
        for k,title in [('year','Năm ngân sách'),('decision','Số quyết định'),('decision_date','Ngày quyết định')]:
            ttk.Label(meta,text=title).pack(side='left',padx=(8,3));ttk.Entry(meta,textvariable=self.batch_meta[k],width=17).pack(side='left')
        form=ttk.LabelFrame(self.tab_batch,text='Thêm dòng dự toán',padding=8);form.pack(fill='x',pady=6)
        self.batch_vars={k:tk.StringVar() for k in BATCH_FIELDS}
        labels={'noi_dung':'Nội dung nhiệm vụ','loai':'Mã Loại','khoan':'Mã Khoản','nguon':'Mã nguồn','chuong':'Mã Chương','don_vi':'Đơn vị nhận','qhns':'Mã ĐVQHNS','so_tien':'Số tiền (VND)'}
        for i,k in enumerate(BATCH_FIELDS):
            r=i//4;c=(i%4)*2
            ttk.Label(form,text=labels[k]).grid(row=r,column=c,sticky='w',padx=3,pady=5)
            ttk.Entry(form,textvariable=self.batch_vars[k],width=21).grid(row=r,column=c+1,sticky='ew',padx=4,pady=5)
        bar=ttk.Frame(self.tab_batch);bar.pack(fill='x',pady=5)
        ttk.Button(bar,text='Thêm dòng',command=self.batch_add).pack(side='left')
        ttk.Button(bar,text='Xóa dòng đã chọn',command=self.batch_remove).pack(side='left',padx=6)
        ttk.Button(bar,text='Xuất đồng thời 3 bảng Excel',command=self.batch_export).pack(side='left',padx=6)
        cols=tuple(BATCH_FIELDS)
        self.batch_tree=ttk.Treeview(self.tab_batch,columns=cols,show='headings',height=12)
        for k in cols:
            self.batch_tree.heading(k,text=labels[k]);self.batch_tree.column(k,width=180 if k in ('noi_dung','don_vi') else 95)
        self.batch_tree.pack(fill='both',expand=True,pady=8)
        self.batch_total=tk.StringVar(value='0 dòng | Tổng: 0 VND')
        ttk.Label(self.tab_batch,textvariable=self.batch_total,font=('Segoe UI',11,'bold')).pack(anchor='e')

    def batch_add(self):
        from batch_export import check_rows
        row={k:v.get().strip() for k,v in self.batch_vars.items()}
        try:
            row['so_tien']=int(row['so_tien'].replace(',','').replace('.','').replace(' ',''))
            check_rows([row])
        except (ValueError,KeyError) as e:
            return messagebox.showerror('Dữ liệu không hợp lệ',str(e))
        self.batch_rows.append(row)
        self.batch_tree.insert('','end',values=[f'{row[k]:,}' if k=='so_tien' else row[k] for k in row])
        self.batch_total.set(f'{len(self.batch_rows)} dòng | Tổng: {sum(r["so_tien"] for r in self.batch_rows):,} VND')
        for k in ('noi_dung','so_tien'):self.batch_vars[k].set('')

    def batch_remove(self):
        for item in sorted(self.batch_tree.selection(),key=lambda x:self.batch_tree.index(x),reverse=True):
            idx=self.batch_tree.index(item);self.batch_tree.delete(item);self.batch_rows.pop(idx)
        self.batch_total.set(f'{len(self.batch_rows)} dòng | Tổng: {sum(r["so_tien"] for r in self.batch_rows):,} VND')

    def batch_export(self):
        from batch_export import export_package
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

    def make_guide(self):
        txt=tk.Text(self.tab_guide,wrap='word',font=('Segoe UI',11),padx=15,pady=12)
        txt.pack(fill='both',expand=True)
        txt.insert('1.0','''NGUỒN TÀI LIỆU THAM KHẢO\n\n• Công văn 15602/BTC-KBNN ngày 17/11/2017: quy trình nhập dự toán NSĐP.\n• Phụ lục II: nguyên tắc kết hợp tổ hợp tài khoản dự toán cấp 0, 1, 4.\n• Phụ lục V: điều chỉnh dự toán theo trạng thái và phân hệ.\n• Danh mục MLNS theo các phụ lục Thông tư 130/2025/TT-BTC, ghi nhận sửa đổi bởi Thông tư 123/2026/TT-BTC.\n\nGIỚI HẠN CỦA PHIÊN BẢN NÀY\n\n1. Mới có danh mục mẫu Loại/Khoản; chưa nhập đầy đủ MLNS từ các tệp .doc và .xls đính kèm.\n2. Chưa tích hợp mẫu chứng từ C6 chính thức. PDF hiện tại là phiếu kiểm tra nội bộ.\n3. Chưa xác minh tính hiệu lực của các quy tắc năm 2017 trong năm 2026.\n4. Không tự động tạo mã loại dự toán, TK Nợ/Có nếu chưa đủ căn cứ.\n5. Không có API ChatGPT; có thể dùng ChatGPT trình duyệt để hỗ trợ đối chiếu.\n6. Không gửi dữ liệu hoặc kết nối TABMIS.\n\nQUY TRÌNH SỬ DỤNG\n\n1. Thêm xã/phường, nhập các mã riêng của xã.\n2. Chọn xã, nhập nghiệp vụ và số tiền.\n3. Xem hướng dẫn; cán bộ tự đối chiếu và điền mã đã xác minh.\n4. Lưu dự thảo, xuất Excel hoặc phiếu kiểm tra PDF.\n5. Sao lưu dữ liệu SQLite định kỳ.\n\nDỮ LIỆU\n\nCơ sở dữ liệu được lưu tại ~/TroLyDuToanXa/du_toan_xa.sqlite3\n''')
        txt.config(state='disabled')

if __name__=='__main__':
    App().mainloop()
