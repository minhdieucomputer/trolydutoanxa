"""Editable Word decision drafts. Not an authenticated reproduction of regulatory forms."""
from datetime import datetime
from pathlib import Path
from source_catalog import BY_CODE as SOURCE_BY_CODE
from docx import Document
from docx.shared import Cm, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT

FORM_LABELS = {
    'UBND': 'Quyết định UBND xã/phường (dự thảo)',
    'B': 'Mẫu B - dự thảo tham chiếu, cần đối chiếu bản gốc',
    'C': 'Mẫu C - dự thảo tham chiếu, cần đối chiếu bản gốc',
}

def _amount(value):
    try: return int(str(value or 0).replace(',', '').replace('.', '').replace(' ', '')) if not isinstance(value,(int,float)) else int(value)
    except (ValueError, TypeError): return 0

def _money(value): return f'{int(value):,}'.replace(',', '.')

def create_decision_word(path, meta, rows, form='UBND'):
    if form not in FORM_LABELS: raise ValueError('Mẫu quyết định không hợp lệ')
    if not rows: raise ValueError('Chưa có dòng nghiệp vụ để xuất quyết định')
    if not meta.get('agency') or not meta.get('number') or not meta.get('date'):
        raise ValueError('Cần nhập tên UBND, số quyết định và ngày quyết định')
    # Nguồn cấp 4 chỉ lấy từ danh mục 15602; không lấy nguồn cấp 0 (99).
    for i, row in enumerate(rows, 1):
        code = str(row.get('nguon') or '').split(' – ')[0].strip()
        if not code or code not in SOURCE_BY_CODE:
            raise ValueError(
                f'Dòng {i}: mã nguồn dự toán cấp 4 {code!r} không có trong '
                'danh mục MA_NGUON_CHI_15602.csv. Vui lòng chọn mã nguồn cấp 4 '
                'phù hợp (ví dụ 42, 43, 44 cho các nguồn vốn đầu tư tương ứng); '
                'không dùng mã nguồn cấp 0 là 99.'
            )
    doc=Document(); section=doc.sections[0]
    section.top_margin=Cm(2);section.bottom_margin=Cm(2);section.left_margin=Cm(2.5);section.right_margin=Cm(2)
    normal=doc.styles['Normal'];normal.font.name='Times New Roman';normal.font.size=Pt(12)
    normal.paragraph_format.space_after=Pt(5)
    def para(text='', bold=False, center=False, size=None):
        p=doc.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.CENTER if center else WD_ALIGN_PARAGRAPH.LEFT
        r=p.add_run(str(text));r.bold=bold
        if size:r.font.size=Pt(size)
        return p
    agency=meta['agency'].strip(); number=meta['number'].strip(); date=meta['date'].strip()
    try: date_text=datetime.strptime(date,'%Y-%m-%d').strftime('%d/%m/%Y')
    except ValueError: date_text=date
    total=sum(_amount(r.get('so_tien')) for r in rows)
    expected=_amount(meta.get('total'))
    para('DỰ THẢO – CẦN ĐỐI CHIẾU MẪU GỐC, THẨM QUYỀN VÀ CĂN CỨ PHÁP LÝ',True,True,9)
    if form in ('B','C'):
        para('THAM CHIẾU '+('MẪU B' if form=='B' else 'MẪU C')+' – CHƯA XÁC NHẬN ĐÚNG NGUYÊN BẢN',True,True,9)
    para('ỦY BAN NHÂN DÂN '+agency.upper(),True,True)
    para('CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM',True,True)
    para('Độc lập - Tự do - Hạnh phúc',True,True)
    para('Số: '+number,False,False)
    para('Ngày '+date_text,False,False)
    para('QUYẾT ĐỊNH',True,True,15)
    para(meta.get('subject') or 'Về việc giao/bổ sung dự toán ngân sách',True,True)
    para('[Bổ sung căn cứ pháp lý phù hợp văn bản hiện hành và thẩm quyền ban hành]')
    para('[Bổ sung căn cứ quyết định giao dự toán, văn bản đề nghị và hồ sơ liên quan]')
    para('QUYẾT ĐỊNH:',True,True)
    para('Điều 1. '+(meta.get('description') or 'Giao dự toán ngân sách cho các đơn vị theo phụ lục kèm theo.') )
    para('Tổng số tiền theo quyết định: '+_money(expected)+' đồng.')
    para('Nguồn kinh phí: '+(meta.get('funding') or '[Chưa nhập nguồn kinh phí]'))
    para('Điều 2. Các cơ quan, đơn vị liên quan chịu trách nhiệm tổ chức thực hiện theo quy định hiện hành.')
    para('Điều 3. [Bổ sung hiệu lực, trách nhiệm thi hành và nơi nhận theo thẩm quyền].')
    para('TM. ỦY BAN NHÂN DÂN',True,True)
    para('CHỦ TỊCH',True,True)
    para('[Ký, ghi rõ họ tên, đóng dấu]',False,True)
    doc.add_page_break()
    para('PHỤ LỤC PHÂN BỔ DỰ TOÁN',True,True,14)
    para('Kèm theo Quyết định số '+number+' ngày '+date_text,False,True)
    headers=['STT','Đơn vị / Nội dung','Mã ĐVQHNS','Loại / Khoản','Mã nguồn dự toán cấp 4','Số tiền (đồng)']
    table=doc.add_table(rows=1, cols=len(headers));table.style='Table Grid';table.alignment=WD_TABLE_ALIGNMENT.CENTER
    for c,t in zip(table.rows[0].cells,headers):c.text=t
    for i,row in enumerate(rows,1):
        values=[str(i),str(row.get('don_vi',''))+' – '+str(row.get('noi_dung','')),str(row.get('qhns','')),
                str(row.get('loai',''))+' / '+str(row.get('khoan','')),str(row.get('nguon','')).split(' – ')[0].strip(),_money(_amount(row.get('so_tien')))]
        cells=table.add_row().cells
        for c,v in zip(cells,values):c.text=v;c.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
    cells=table.add_row().cells
    cells[1].text='TỔNG CỘNG';cells[-1].text=_money(total)
    para('Đối chiếu: Tổng quyết định '+_money(expected)+' đồng; tổng phụ lục '+_money(total)+' đồng; chênh lệch '+_money(expected-total)+' đồng.')
    para('LƯU Ý: Tài liệu Word có thể chỉnh sửa, chưa được xác nhận là biểu mẫu pháp lý chính thức. Kiểm tra căn cứ, thể thức, thẩm quyền và mã ngân sách trước khi ký.',False,False,9)
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);doc.save(path)
    return str(path)
