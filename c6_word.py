"""Editable review drafts for C6-01/02/03/04; NOT certified copies of statutory forms."""
from docx import Document
from docx.shared import Cm, Pt
from docx.enum.section import WD_ORIENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from c6_accounting import check_allocation

LABELS={'C601':'C6-01/NS – Phiếu nhập dự toán ngân sách',
        'C602':'C6-02/NS – Phiếu nhập dự toán cấp 0',
        'C603':'C6-03/NS – Chứng từ phân bổ dự toán',
        'C604':'C6-04/NS – Phiếu điều chỉnh dự toán'}

def create_c6_word(path, code, rows, commune='', year='', decision='', decision_date=''):
    if code not in LABELS: raise ValueError('Không xác định được mẫu C6.')
    if not rows: raise ValueError('Chưa có nghiệp vụ để xuất.')
    if code in ('C601','C603'): check_allocation(rows)
    doc=Document(); sec=doc.sections[0]
    sec.orientation=WD_ORIENT.LANDSCAPE;sec.page_width=Cm(29.7);sec.page_height=Cm(21)
    sec.top_margin=Cm(1.8);sec.bottom_margin=Cm(1.8)
    sec.left_margin=Cm(1.7);sec.right_margin=Cm(1.7)
    normal=doc.styles['Normal'];normal.font.name='Times New Roman';normal.font.size=Pt(10)
    p=doc.add_paragraph('BẢN WORD CÓ THỂ CHỈNH SỬA – BẢNG ĐỐI CHIẾU, CHƯA PHẢI BẢN SAO MẪU CHỨNG TỪ CHÍNH THỨC')
    p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    for run in p.runs:run.bold=True;run.font.size=Pt(9)
    p=doc.add_paragraph(LABELS[code]);p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    for run in p.runs:run.bold=True;run.font.size=Pt(14)
    doc.add_paragraph(f'Đơn vị: {commune}    Năm NS: {year}')
    doc.add_paragraph(f'Quyết định số: {decision}    Ngày: {decision_date}')
    doc.add_paragraph('Căn cứ tham chiếu: Công văn 15602/BTC-KBNN ngày 17/11/2017. Cần kiểm tra quy định hiện hành trước khi sử dụng.')
    if code=='C602':
        headers=['STT','Nội dung','Loại','Nguồn C0','Mã TCNS C0','Loại DT','TK Nợ C0','TK Có C0','Số tiền']
        # C6-02: TK cấp 0 không được suy từ TK phân bổ cấp 4.
        def fields(r,i):return [i,r.get('noi_dung'),r.get('loai'),r.get('nguon_cap0'),r.get('qhns_cap0'),r.get('ma_loai_du_toan'),'[Xác định riêng]','[Xác định riêng]',r.get('so_tien')]
    else:
        headers=['STT','Nội dung','Loại','Khoản','Chương','Mã QHNS','Nguồn C4','Loại DT','TK Nợ','TK Có','Số tiền']
        def fields(r,i):return [i,r.get('noi_dung'),r.get('loai'),r.get('khoan'),r.get('chuong'),r.get('qhns'),r.get('nguon'),r.get('ma_loai_du_toan'),r.get('tk_no'),r.get('tk_co'),r.get('so_tien')]
    table=doc.add_table(rows=1,cols=len(headers));table.style='Table Grid';table.alignment=WD_TABLE_ALIGNMENT.CENTER
    for c,h in zip(table.rows[0].cells,headers):c.text=h
    for i,r in enumerate(rows,1):
        for c,v in zip(table.add_row().cells,fields(r,i)):
            c.text=f'{int(v):,}'.replace(',','.') if isinstance(v,int) else str(v or '')
    doc.add_paragraph('TỔNG CỘNG: '+f'{sum(int(r.get("so_tien") or 0) for r in rows):,}'.replace(',','.')+' đồng')
    doc.add_paragraph('Ghi chú: Kiểm tra đầy đủ mã tài khoản, mã nguồn, niên độ, hình thức cấp phát, số liệu TABMIS và đối chiếu biểu mẫu gốc trước khi ký.')
    doc.save(path)
    return path
