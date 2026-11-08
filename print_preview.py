"""Xem trước sử dụng nguyên trang biểu mẫu C6 gốc, có lớp dữ liệu điền lên.
Các mẫu gốc được chuyển từ DOC do người dùng cung cấp; không tái vẽ biểu mẫu.
"""
from pathlib import Path
from tempfile import mkstemp
import os, sys
from io import BytesIO
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# PDF page adapters: preserve original C6 template and overlay using reportlab/pypdf.
class _Rect:
    def __init__(self, *a):
        if len(a)==1:
            a=(a[0].x0,a[0].y0,a[0].x1,a[0].y1) if isinstance(a[0],_Rect) else a[0]
        self.x0,self.y0,self.x1,self.y1=map(float,a)
        self.width=self.x1-self.x0; self.height=self.y1-self.y0

class _Point:
    def __init__(self,x,y): self.x=float(x); self.y=float(y)

class _Page:
    def __init__(self, width, height, base=None):
        self.rect=_Rect(0,0,width,height)
        self._base=base
        self._stream=BytesIO()
        self._canvas=canvas.Canvas(self._stream,pagesize=(width,height),pageCompression=1)
        self._fonts={}
    def insert_font(self,fontname,fontfile):
        if fontname not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(fontname,fontfile))
        self._fonts[fontname]=fontname
    def insert_textbox(self,rect,text,fontname='Helvetica',fontsize=8,color=(0,0,0),align=0,lineheight=1.1):
        r=_Rect(rect); c=self._canvas
        font=fontname if fontname in pdfmetrics.getRegisteredFontNames() else 'Helvetica'
        c.setFont(font,fontsize);c.setFillColorRGB(*color)
        lines=[]
        for para in str(text).split('\n'):
            words=para.split(' ');line=''
            for word in words:
                trial=(line+' '+word).strip()
                if pdfmetrics.stringWidth(trial,font,fontsize)<=r.width-2 or not line:line=trial
                else:lines.append(line);line=word
            lines.append(line)
        if len(lines)*fontsize*lineheight>r.height+1: return -1
        for i,line in enumerate(lines):
            width=pdfmetrics.stringWidth(line,font,fontsize)
            x=r.x0+(r.width-width)/2 if align==1 else r.x1-width-1 if align==2 else r.x0+1
            y=self.rect.height-r.y0-fontsize*(1+i*lineheight)
            c.drawString(x,y,line)
        return r.height-len(lines)*fontsize*lineheight
    def insert_text(self,point,text,fontname='Helvetica',fontsize=8):
        x,y=point;self._canvas.setFont(fontname if fontname in pdfmetrics.getRegisteredFontNames() else 'Helvetica',fontsize)
        self._canvas.drawString(x,self.rect.height-y,str(text))
    def draw_rect(self,rect,color=None,fill=None,overlay=True):
        r=_Rect(rect);c=self._canvas
        if fill is not None:c.setFillColorRGB(*fill)
        if color is not None:c.setStrokeColorRGB(*color)
        c.rect(r.x0,self.rect.height-r.y1,r.width,r.height,stroke=int(color is not None),fill=int(fill is not None))
    def draw_line(self,p1,p2,color=(0,0,0),width=.65):
        c=self._canvas;c.setStrokeColorRGB(*color);c.setLineWidth(width)
        c.line(p1.x,self.rect.height-p1.y,p2.x,self.rect.height-p2.y)
    def finish(self):
        self._canvas.save();self._stream.seek(0)
        overlay=PdfReader(self._stream).pages[0]
        if self._base is None:
            result=overlay
        else:
            result=self._base
            result.merge_page(overlay)
        return result

class _Doc:
    def __init__(self,source=None):
        self._reader=PdfReader(str(source)) if source else None
        self._pages=[]
        self._source_pages=list(self._reader.pages) if self._reader else []
    def __getitem__(self,i):
        page=self._source_pages[i]
        return type('SourcePage',(),{'rect':_Rect(0,0,float(page.mediabox.width),float(page.mediabox.height))})()
    def __iter__(self):
        for i,source in enumerate(self._source_pages):
            page=_Page(float(source.mediabox.width),float(source.mediabox.height),source)
            self._pages.append(page)
            yield page
    def new_page(self,width,height):
        p=_Page(width,height);self._pages.append(p);return p
    def add_template_page(self,source_doc,index=0):
        source=source_doc._source_pages[index]
        p=_Page(float(source.mediabox.width),float(source.mediabox.height),source)
        self._pages.append(p);return p
    def save(self,path,**kwargs):
        writer=PdfWriter()
        for p in self._pages:writer.add_page(p.finish())
        with open(path,'wb') as f:writer.write(f)
    def close(self):pass

class PdfCompat:
    Rect=_Rect
    Point=_Point
    open=staticmethod(lambda path=None:_Doc(path))


TITLES={'C601':'C6-01 - Phiếu nhập dự toán','C604':'C6-04 - Phiếu điều chỉnh dự toán'}
FILES={'C601':'C6-01_original.pdf','C604':'C6-04_original.pdf'}

def _asset(name):
    # PyInstaller onedir: bundled data lives in _internal/templates_pdf.
    # Also support data placed next to the installed EXE or running from source.
    candidates = []
    if getattr(sys, 'frozen', False):
        if getattr(sys, '_MEIPASS', None):
            candidates.append(Path(sys._MEIPASS))
        candidates.append(Path(sys.executable).resolve().parent)
    candidates.append(Path(__file__).resolve().parent)
    for root in candidates:
        candidate = root / 'templates_pdf' / name
        if candidate.is_file():
            return candidate
    locations = ', '.join(str(root / 'templates_pdf' / name) for root in candidates)
    raise FileNotFoundError('Không tìm thấy mẫu C6 ' + name + '. Đã kiểm tra: ' + locations)

def _font(page):
    for path in (Path('C:/Windows/Fonts/arial.ttf'),Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')):
        if path.exists():
            page.insert_font(fontname='vn',fontfile=str(path));return 'vn'
    return 'helv'

def _write(page, rect, value, font, size=8, align=0):
    text=str(value if value is not None else '').strip()
    if not text:return
    for s in (size,size-1,size-2,5):
        if page.insert_textbox(PdfCompat.Rect(*rect),text,fontname=font,fontsize=s,
                               color=(0,0,0),align=align,lineheight=1.1)>=0:return
    page.insert_text((rect[0],rect[1]+7),text[:20],fontname=font,fontsize=5)

def _money(v):
    try:return f'{int(float(str(v).replace(",",""))):,}'
    except (ValueError,TypeError):return str(v or '')

def create_preview(code, rows, commune='', year='', decision='', decision_date='', expected=None):
    if code not in FILES:
        raise ValueError('Chức năng sao chép bố cục mẫu gốc hiện hỗ trợ C6-01 và C6-04. Các mẫu khác cần ánh xạ riêng.')
    if not rows:raise ValueError('Chưa có nghiệp vụ để xem trước')
    template=_asset(FILES[code])
    if not template.exists():raise FileNotFoundError(f'Thiếu mẫu gốc đã chuyển PDF: {template}')
    original=PdfCompat.open(template)
    output=PdfCompat.open()
    # Một nghiệp vụ gồm hai bút toán (Nợ/Có) trên mẫu gốc; tối đa 4 nghiệp vụ/trang.
    pagesize=4
    for offset in range(0,len(rows),pagesize):
        part=rows[offset:offset+pagesize]
        source=original[0]
        page=output.add_template_page(original,0)
        font=_font(page)
        if code=='C601':
            _write(page,(680,83,760,98),year,font,8)
            _write(page,(230,145,350,158),decision,font,8)
            _write(page,(382,145,485,158),decision_date,font,8)
            _write(page,(270,163,650,179),commune,font,8)
            x=[(91,120),(121,181),(183,249),(250,296),(297,370),(371,433),(434,484),(485,543),(544,618),(619,700),(700,780)]
            y0=244
        else:
            _write(page,(690,72,770,86),year,font,8)
            _write(page,(180,132,760,145),'Điều chỉnh theo quyết định '+str(decision)+'; '+str(decision_date),font,8)
            _write(page,(185,149,765,164),'; '.join(str(r.get('noi_dung','')) for r in part)[:280],font,7)
            x=[(66,97),(98,155),(156,208),(209,270),(271,342),(343,396),(397,455),(456,520),(521,571),(572,645),(646,716),(717,790)]
            y0=231
        for i,row in enumerate(part):
            y=y0+i*30
            values=[str(offset+i+1),row.get('ma_loai_du_toan',''),row.get('tk_no',''),
                    row.get('cap_ns',''),row.get('qhns',''),row.get('chuong',''),
                    row.get('khoan',''),row.get('ctmt','')]
            if code=='C601':
                values += [row.get('nguon',''),_money(row.get('so_tien')),'']
            else:
                values += [row.get('ma_kbnn',''),row.get('nguon',''),_money(row.get('so_tien')),'']
            for j,val in enumerate(values):
                if j>=len(x):break
                _write(page,(x[j][0],y,x[j][1],y+14),val,font,7,1)
            # Ghi tài khoản Có và số tiền Có ở dòng thứ hai của cùng nghiệp vụ.
            _write(page,(x[2][0],y+14,x[2][1],y+27),row.get('tk_co',''),font,7,1)
            _write(page,(x[-1][0],y+14,x[-1][1],y+27),_money(row.get('so_tien')),font,7,1)
        # Ghi diễn giải thành phần đính kèm riêng để không phá bố cục C6-01.
    # Phụ trang chi tiết là tài liệu bổ sung, không thuộc mẫu C6 gốc.
    supplement=output.new_page(width=842,height=595)
    font=_font(supplement)
    _write(supplement,(45,30,790,60),'BẢNG DIỄN GIẢI KÈM PHIẾU (PHỤ TRANG THAM KHẢO)',font,13,1)
    y=85
    for i,row in enumerate(rows,1):
        if y>520:
            supplement=output.new_page(width=842,height=595);font=_font(supplement);y=55
        _write(supplement,(45,y,90,y+35),i,font,9)
        _write(supplement,(92,y,690,y+36),row.get('noi_dung',''),font,9)
        _write(supplement,(695,y,815,y+35),_money(row.get('so_tien')),font,9,2)
        y+=46
    total=sum(int(float(str(r.get('so_tien') or 0).replace(',',''))) for r in rows)
    if y>525:
        supplement=output.new_page(width=842,height=595);font=_font(supplement);y=55
    _write(supplement,(45,y+4,815,y+35),f'Tổng đã phân bổ: {_money(total)} VND'+
           (f' | Tổng quyết định: {_money(expected)} VND | Chênh lệch: {_money(int(expected)-total)} VND' if expected is not None else ''),font,9)
    fd,path=mkstemp(prefix='C6_MauGoc_DaDien_',suffix='.pdf');os.close(fd)
    output.save(path,garbage=3,deflate=True);output.close();original.close()
    return path


def create_c602_preview(rows, commune='', year='', decision='', decision_date='', expected=None):
    """Điền C6-02 trên nền mẫu PDF gốc; phần thân bảng kéo dài theo số dòng."""
    if not rows:
        raise ValueError('Chưa có nghiệp vụ phân bổ cấp 0.')
    template=_asset('C6-02_original.pdf')
    if not template.exists():
        raise FileNotFoundError('Thiếu biểu mẫu C6-02 gốc: '+str(template))
    original=PdfCompat.open(template)
    output=PdfCompat.open()
    cols=[36,65,258,302,343,376,412,449,495,538,579,620,655,692,762,807]
    # Cột tiền Nợ và Có là hai cột riêng theo mẫu gốc.
    page_rows=8
    def amount(v):
        try: return int(float(str(v or 0).replace(',','')))
        except (TypeError,ValueError): return 0
    total=sum(amount(r.get('so_tien')) for r in rows)
    for offset in range(0,len(rows),page_rows):
        part=rows[offset:offset+page_rows]
        source=original[0]
        page=output.add_template_page(original,0)
        font=_font(page)
        # Chỉ che vùng bảng dữ liệu và chữ ký của bản mẫu; giữ nguyên tiêu đề, đầu cột.
        page.draw_rect(PdfCompat.Rect(35.5,177.0,807.5,410),color=None,fill=(1,1,1),overlay=True)
        _write(page,(38,20,280,38),commune,font,8)
        _write(page,(618,65,695,82),decision,font,8)
        _write(page,(703,65,797,82),year,font,8)
        # Tái tạo đường kẻ phần thân bảng theo đúng các cột của mẫu gốc.
        top=177; line_h=23; bottom=top+(len(part)+1)*line_h
        for x in cols:
            page.draw_line(PdfCompat.Point(x,top),PdfCompat.Point(x,bottom),color=(0,0,0),width=.65)
        for j in range(len(part)+2):
            y=top+j*line_h
            page.draw_line(PdfCompat.Point(cols[0],y),PdfCompat.Point(cols[-1],y),color=(0,0,0),width=.65)
        # Hàng tổng ở đầu thân bảng.
        _write(page,(67,181,255,198),'Tổng số:',font,8)
        _write(page,(694,181,760,198),_money(total),font,8,2)
        for i,r in enumerate(part):
            y=top+(i+1)*line_h+4
            val=[str(offset+i+1),r.get('noi_dung',''),decision,decision_date,
                 r.get('ma_loai_du_toan',''),r.get('tk_no',''),r.get('cap_ns','0') or '0',
                 r.get('qhns_cap0',''),r.get('chuong',''),r.get('khoan',''),
                 r.get('ctmt',''),r.get('nguon_cap0',''),_money(r.get('so_tien')),
                 _money(r.get('so_tien')),r.get('so_lo','')]
            for j,v in enumerate(val):
                if j==0: a,b=cols[0],cols[1]
                elif j==1: a,b=cols[1],cols[2]
                elif j==2: a,b=cols[2],cols[3]
                elif j==3: a,b=cols[3],cols[4]
                else: a,b=cols[j],cols[j+1]
                _write(page,(a+1,y,b-1,y+line_h-5),v,font,7 if j!=1 else 6,2 if j in (12,13) else 1 if j>1 else 0)
            # Cột TKKT trên mẫu: hiển thị cả hai tài khoản Nợ/Có khi khác nhau.
            if str(r.get('tk_co','')).strip() and str(r.get('tk_co','')).strip()!=str(r.get('tk_no','')).strip():
                _write(page,(344,y+10,375,y+19),r.get('tk_co',''),font,5,1)
        sig_y=min(bottom+24,490)
        _write(page,(570,sig_y-22,803,sig_y),'Ngày ... tháng ... năm ...',font,8,1)
        for a,b,label in [(80,245,'Người nhập'),(320,505,'Kiểm soát'),(570,803,'Thủ trưởng đơn vị')]:
            _write(page,(a,sig_y,b,sig_y+18),label,font,9,1)
        if expected is not None and offset+len(part)>=len(rows):
            _write(page,(55,sig_y+45,800,sig_y+65),
                   'Đối chiếu: Quyết định '+_money(expected)+' | Đã phân bổ '+_money(total)+
                   ' | Chênh lệch '+_money(int(expected)-total)+' VND',font,8)
    fd,path=mkstemp(prefix='C6_02_Cap0_DaDien_',suffix='.pdf');os.close(fd)
    output.save(path,garbage=3,deflate=True)
    output.close();original.close()
    return path


def open_reference_template(code):
    """C6-02/C6-03: trả về bản mẫu gốc chưa điền, có dấu cảnh báo."""
    names={'C602':'C6-02_original.pdf','C603':'C6-03_original.pdf'}
    if code not in names:raise ValueError('Mã mẫu không hợp lệ')
    original=_asset(names[code])
    if not original.exists():raise FileNotFoundError('Thiếu PDF mẫu gốc: '+str(original))
    doc=PdfCompat.open(original)
    for page in doc:
        font=_font(page)
        page.draw_rect(PdfCompat.Rect(12,8,min(page.rect.width-12,590),38),color=(0.7,0.2,0.1),fill=(1,0.96,0.90),overlay=True)
        _write(page,(18,12,min(page.rect.width-18,580),35),
               'MẪU THAM KHẢO - CHƯA ĐIỀN DỮ LIỆU NGHIỆP VỤ',font,11)
    fd,path=mkstemp(prefix=code+'_MAU_THAM_KHAO_',suffix='.pdf');os.close(fd)
    doc.save(path,garbage=3,deflate=True);doc.close()
    return path
