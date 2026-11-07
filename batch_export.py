"""Bộ chứng từ dự thảo từ một bảng phân bổ; không thay thế mẫu C6 chính thức."""
from collections import defaultdict
from pathlib import Path
from datetime import datetime
import csv

FIELDS = ['noi_dung','loai','khoan','nguon','chuong','don_vi','qhns','so_tien']

def check_rows(rows):
    if not rows: raise ValueError('Chưa có dòng dự toán.')
    for i,r in enumerate(rows,1):
        if not r['noi_dung'].strip(): raise ValueError(f'Dòng {i}: thiếu nội dung.')
        for key,n in [('loai',3),('khoan',3)]:
            if len(r[key]) != n or not r[key].isdigit(): raise ValueError(f'Dòng {i}: mã {key} phải có {n} chữ số.')
        if not r['nguon'].strip(): raise ValueError(f'Dòng {i}: thiếu mã nguồn.')
        if int(r['so_tien']) <= 0: raise ValueError(f'Dòng {i}: số tiền phải dương.')

def summarize(rows):
    groups=defaultdict(int)
    for r in rows:
        groups[(r['loai'],r.get('nguon_cap0',''))]+=int(r['so_tien'])
    return groups

def export_package(folder, commune, year, decision, decision_date, rows):
    """Xuất 3 bảng Excel dự thảo, cùng một nguồn dữ liệu; không giả lập định khoản."""
    check_rows(rows)
    import xlsxwriter
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    total=sum(int(r['so_tien']) for r in rows)
    groups=summarize(rows)
    def make(filename, title, headers, records, notice):
        path=folder/filename
        wb=xlsxwriter.Workbook(str(path))
        ws=wb.add_worksheet('Du thao')
        big=wb.add_format({'bold':True,'font_size':15,'font_color':'#163A5F'})
        meta=wb.add_format({'font_color':'#334155'})
        head=wb.add_format({'bold':True,'bg_color':'#DCEBF7','border':1,'text_wrap':True})
        normal=wb.add_format({'border':1,'text_wrap':True})
        money=wb.add_format({'border':1,'num_format':'#,##0'})
        ws.merge_range(0,0,0,len(headers)-1,title,big)
        ws.merge_range(1,0,1,len(headers)-1,f'Xã/phường: {commune} | Năm: {year} | Quyết định: {decision} ngày {decision_date}',meta)
        ws.merge_range(2,0,2,len(headers)-1,notice,wb.add_format({'font_color':'#9A3412','italic':True,'text_wrap':True}))
        ws.set_row(2,32)
        for j,h in enumerate(headers): ws.write(4,j,h,head)
        for i,record in enumerate(records,5):
            for j,v in enumerate(record):
                if isinstance(v,int): ws.write_number(i,j,v,money)
                else: ws.write_string(i,j,str(v),normal)
        last=5+len(records)
        ws.write(last,0,'TỔNG CỘNG',head)
        ws.write_number(last,len(headers)-1,sum(r[-1] for r in records),money)
        ws.freeze_panes(5,0)
        ws.set_column(0,0,40);ws.set_column(1,len(headers)-2,19);ws.set_column(len(headers)-1,len(headers)-1,21)
        ws.autofilter(4,0,4+len(records),len(headers)-1)
        ws.fit_to_pages(1,0);ws.set_landscape()
        wb.close()
        return path
    c0=[(loai,nguon,amount) for (loai,nguon),amount in sorted(groups.items())]
    # Cấp 0 chỉ tổng hợp theo loại và nguồn. Tài khoản/COA phải được cán bộ đối chiếu.
    p0=make('01_C6-02_cap_0_DU_THAO.xlsx','BẢNG CHUẨN BỊ PHIẾU C6-02/NS — CẤP 0',
        ['Mã Loại (lĩnh vực)','Mã nguồn cấp 0 (cần xác nhận)','Số tiền (VND)'],c0,
        'BẢN DỰ THẢO — Nguồn cấp 0 để trống nếu chưa xác minh; KHÔNG dùng nguồn cấp 4 thay thế. Chưa xác định TK Nợ/Có, mã nhiệm vụ chi cấp 0 và các COA.')
    detail=[(r['noi_dung'],r['loai'],r['khoan'],r['nguon'],r['chuong'],r['don_vi'],r['qhns'],int(r['so_tien'])) for r in rows]
    p4=make('02_C6-01_phan_bo_cap_4_DU_THAO.xlsx','BẢNG CHUẨN BỊ PHIẾU C6-01 — PHÂN BỔ CẤP 4',
        ['Nội dung','Mã Loại','Mã Khoản','Mã nguồn chi tiết cấp 4','Mã Chương','Đơn vị nhận','Mã ĐVQHNS','Số tiền (VND)'],detail,
        'BẢN DỰ THẢO — KHÔNG PHẢI PHIẾU GỬI KBNN. Cần xác minh mẫu C6-01, tuyến phân bổ, tài khoản và tổ hợp COA.')
    annex=make('03_Phu_luc_quyet_dinh_DU_THAO.xlsx','PHỤ LỤC KÈM QUYẾT ĐỊNH GIAO DỰ TOÁN',
        ['Nội dung nhiệm vụ','Mã Loại','Mã Khoản','Mã nguồn chi tiết cấp 4','Mã Chương','Đơn vị nhận','Mã ĐVQHNS','Số tiền (VND)'],detail,
        'DỰ THẢO PHỤ LỤC — Cần đối chiếu quyết định, niên độ, danh mục MLNS và phê duyệt trước khi ban hành.')
    return [p0,p4,annex],total
