"""Bản xem trước QUYẾT ĐỊNH dự thảo, không thay thế mẫu quyết định của địa phương."""
from pathlib import Path
from tempfile import mkstemp
from collections import defaultdict
import os
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, KeepTogether
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from xml.sax.saxutils import escape

def create_decision_preview(meta, rows):
    if not rows: raise ValueError('Chưa có dòng phân bổ để lập quyết định.')
    fd, name=mkstemp(prefix='Quyet_dinh_giao_du_toan_DU_THAO_',suffix='.pdf');os.close(fd)
    font='Helvetica'
    for p in ('C:/Windows/Fonts/arial.ttf','/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'):
        if Path(p).exists():
            pdfmetrics.registerFont(TTFont('VietFont',p));font='VietFont';break
    doc=SimpleDocTemplate(name,pagesize=A4,rightMargin=35,leftMargin=35,topMargin=35,bottomMargin=35)
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Vn',fontName=font,fontSize=9,leading=14,spaceAfter=5))
    styles.add(ParagraphStyle(name='VnTitle',parent=styles['Vn'],alignment=TA_CENTER,fontSize=13,leading=18,spaceAfter=9))
    styles.add(ParagraphStyle(name='VnCenter',parent=styles['Vn'],alignment=TA_CENTER))
    styles.add(ParagraphStyle(name='VnRight',parent=styles['Vn'],alignment=TA_RIGHT))
    def p(t,style='Vn'):return Paragraph(escape(str(t or '')),styles[style])
    money=lambda n:f'{int(n):,}'.replace(',','.')
    total=sum(int(r.get('so_tien') or 0) for r in rows)
    expected=int(meta['total'])
    story=[p('ỦY BAN NHÂN DÂN '+meta['agency'].upper(),'VnCenter'),p('DỰ THẢO – KIỂM TRA TRƯỚC KHI BAN HÀNH','VnCenter'),Spacer(1,12),p('QUYẾT ĐỊNH','VnTitle'),p(meta['subject'],'VnCenter'),Spacer(1,10),p(f"Số: {meta['number']}     Ngày: {meta['date']}"),p(f"Năm ngân sách: {meta['year']}"),p(f"Nguồn kinh phí theo quyết định: {meta['funding']}"),p(f"Nội dung: {meta['description']}"),Spacer(1,8),p(f"Điều 1. Giao dự toán ngân sách với tổng số tiền: {money(expected)} đồng."),p('Chi tiết phân bổ theo đơn vị, mã ngành và nguồn kinh phí tại phụ lục kèm theo.'),p('Điều 2. Các đơn vị liên quan thực hiện theo nội dung được cấp có thẩm quyền phê duyệt.'),Spacer(1,12),p('TM. ỦY BAN NHÂN DÂN','VnRight'),p('CHỦ TỊCH','VnRight'),Spacer(1,40),p('PHỤ LỤC PHÂN BỔ DỰ TOÁN','VnTitle'),p(f"Kèm theo Quyết định số {meta['number']} ngày {meta['date']}",'VnCenter')]
    columns=['STT','Đơn vị / Nội dung','QHNS','Loại/Khoản','Nguồn cấp 4','Số tiền (đồng)']
    data=[[p(x) for x in columns]]
    for i,r in enumerate(rows,1):
        data.append([p(i),p((r.get('don_vi') or '')+' – '+(r.get('noi_dung') or '')),p(r.get('qhns')),p(f"{r.get('loai','')}/{r.get('khoan','')}"),p(r.get('nguon')),p(money(r.get('so_tien') or 0))])
    data.append([p(''),p('TỔNG CỘNG'),p(''),p(''),p(''),p(money(total))])
    t=Table(data,colWidths=[28,202,65,72,66,92],repeatRows=1,hAlign='CENTER')
    t.setStyle(TableStyle([('GRID',(0,0),(-1,-1),.4,colors.grey),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e9eff5')),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),4),('RIGHTPADDING',(0,0),(-1,-1),4)]))
    story.extend([Spacer(1,10),t,Spacer(1,12),p(f"Đối chiếu: Tổng quyết định {money(expected)} đồng; đã phân bổ {money(total)} đồng; chênh lệch {money(expected-total)} đồng."),p('LƯU Ý: Đây là bản dự thảo phục vụ kiểm tra, không phải quyết định đã được ban hành.')])
    doc.build(story)
    return name
