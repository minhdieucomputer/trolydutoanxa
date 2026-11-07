"""Export REVIEW DRAFTS only. Official C6 and TT26 templates must be mapped separately."""
from pathlib import Path
import xlsxwriter

FORM_NAMES = {
 'C601':'C6-01 - Phieu nhap du toan',
 'C602':'C6-02 - Phieu nhap du toan cap 0',
 'C603':'C6-03 - Phan bo du toan',
 'C604':'C6-04 - Dieu chinh du toan',
 'QDC':'Mau C - Quyet dinh giao du toan (du thao)',
 'PL47':'Phu luc mau 47 (bang doi chieu)',
 'PL48':'Phu luc mau 48 (bang doi chieu)',
}
COLUMNS=[('don_vi','Don vi nhan'),('qhns','Ma DVQHNS'),('chuong','Chuong'),('loai','Loai'),('khoan','Khoan'),('nguon_cap0','Nguon cap 0'),('nguon','Nguon chi tiet cap 4'),('noi_dung','Noi dung'),('ma_loai_du_toan','Ma loai du toan'),('tk_no','TK No'),('tk_co','TK Co'),('nguon_goc','Nguon goc du toan'),('so_tien','So tien (VND)')]

def export_selected(folder, commune, year, decision, decision_date, rows, selected):
    """Generate non-official review sheets. Never mark them as statutory forms."""
    if not rows: raise ValueError('Chua co dong du toan nao.')
    if not selected: raise ValueError('Chua chon loai phieu.')
    output=Path(folder); output.mkdir(parents=True,exist_ok=True)
    paths=[]; total=sum(int(r['so_tien']) for r in rows)
    for code in selected:
        if code not in FORM_NAMES: raise ValueError('Ma phieu khong hop le: '+code)
        path=output/(code+'_DU_THAO.xlsx')
        wb=xlsxwriter.Workbook(str(path)); ws=wb.add_worksheet('Du thao doi chieu')
        title=wb.add_format({'bold':True,'font_size':15,'font_color':'#123B63','text_wrap':True})
        warning=wb.add_format({'bold':True,'font_color':'#9C321A','bg_color':'#FFF2DC','text_wrap':True})
        head=wb.add_format({'bold':True,'bg_color':'#DCEAF4','border':1,'text_wrap':True})
        normal=wb.add_format({'border':1}); money=wb.add_format({'border':1,'num_format':'#,##0'})
        last_col=len(COLUMNS)-1
        ws.merge_range(0,0,1,last_col,FORM_NAMES[code].upper(),title)
        ws.merge_range(2,0,2,last_col,'DU THAO NOI BO - KHONG PHAI MAU CHINH THUC; PHAI DOI CHIEU MAU GOC VA CAN CU PHAP LY',warning)
        ws.write('A5','Xa/phuong: '+commune); ws.write('D5','Nam NS: '+str(year))
        ws.write('A6','So QD: '+str(decision));ws.write('D6','Ngay QD: '+str(decision_date))
        for col,(_,label) in enumerate(COLUMNS):ws.write(7,col,label,head)
        for i,r in enumerate(rows,8):
            for j,(key,_) in enumerate(COLUMNS):
                if key=='so_tien':ws.write_number(i,j,int(r.get(key,0)),money)
                else:ws.write_string(i,j,str(r.get(key,'') or ''),normal)
        end=8+len(rows)
        ws.write(end,last_col-1,'TONG CONG',head)
        letter=xlsxwriter.utility.xl_col_to_name(last_col)
        ws.write_formula(end,last_col,f'=SUM({letter}9:{letter}{end})',money,total)
        ws.set_column(0,1,19);ws.set_column(2,5,12);ws.set_column(6,6,50);ws.set_column(7,last_col-1,20);ws.set_column(last_col,last_col,22)
        ws.freeze_panes(8,0);ws.autofilter(7,0,end-1,last_col)
        ws.fit_to_pages(1,0);ws.set_landscape();ws.repeat_rows(7)
        wb.close();paths.append(path)
    return paths,total
