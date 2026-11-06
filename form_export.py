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
COLUMNS=[('don_vi','Don vi nhan'),('qhns','Ma DVQHNS'),('chuong','Chuong'),('loai','Loai'),('khoan','Khoan'),('nguon','Nguon'),('noi_dung','Noi dung'),('so_tien','So tien (VND)')]

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
        ws.merge_range('A1:H2',FORM_NAMES[code].upper(),title)
        ws.merge_range('A3:H3','DU THAO NOI BO - KHONG PHAI MAU CHINH THUC; PHAI DOI CHIEU MAU GOC VA CAN CU PHAP LY',warning)
        ws.write('A5','Xa/phuong: '+commune); ws.write('D5','Nam NS: '+str(year))
        ws.write('A6','So QD: '+str(decision));ws.write('D6','Ngay QD: '+str(decision_date))
        for col,(_,label) in enumerate(COLUMNS):ws.write(7,col,label,head)
        for i,r in enumerate(rows,8):
            for j,(key,_) in enumerate(COLUMNS):
                if key=='so_tien':ws.write_number(i,j,int(r.get(key,0)),money)
                else:ws.write_string(i,j,str(r.get(key,'') or ''),normal)
        end=8+len(rows)
        ws.write(end,6,'TONG CONG',head)
        ws.write_formula(end,7,f'=SUM(H9:H{end})',money,total)
        ws.set_column('A:B',19);ws.set_column('C:F',12);ws.set_column('G:G',50);ws.set_column('H:H',20)
        ws.freeze_panes(8,0);ws.autofilter(7,0,end-1,7)
        ws.fit_to_pages(1,0);ws.set_landscape();ws.repeat_rows(7)
        wb.close();paths.append(path)
    return paths,total
