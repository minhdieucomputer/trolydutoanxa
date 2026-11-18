"""Conservative, source-anchored accounting suggestions; not an automatic posting engine."""
import unicodedata, re

def norm(text):
    s=unicodedata.normalize('NFD',str(text).lower().replace('đ','d'))
    return re.sub(r'\s+',' ',''.join(c for c in s if unicodedata.category(c)!='Mn')).strip()

RULES = [
    {'keys':('chuyen nguon','chuyen du toan sang nam sau'), 'title':'Chi chuyển nguồn ngân sách địa phương sang năm sau – nhập dự toán cấp 0', 'debit':'9239', 'credit':'9111', 'code':'434', 'ref':'Công văn 15602/BTC-KBNN, Phần B, mục I, điểm 1.3.5(c), trang 16', 'condition':'Chỉ áp dụng khi nhập dự toán cấp 0 cho nhiệm vụ chi chuyển nguồn sang năm sau (mã nhiệm vụ chi 434).', 'exclude':('nam truoc chuyen sang','tu nam truoc','du toan nam truoc','chuyen nguon tu nam truoc')},
    {'keys':('du phong','du toan du phong'), 'title':'Nhập dự toán dự phòng ngân sách cấp 0', 'debit':'9233', 'credit':'9111', 'code':'437', 'ref':'Công văn 15602/BTC-KBNN, Phần B, mục I, điểm 1.3.5(d), trang 16', 'condition':'Chỉ áp dụng khi nhập dự toán dự phòng cấp 0; phân bổ dự phòng để chi cần xác định tài khoản đích và nhiệm vụ chi.', 'exclude':()},
    {'keys':('chuyen giao','bo sung can doi','bo sung co muc tieu'), 'title':'Phân bổ dự toán chi chuyển giao từ cấp 0 đến cấp 4 – giao thành chỉ tiêu riêng', 'debit':'9622', 'credit':'9229', 'code':'431 hoặc 432', 'ref':'Công văn 15602/BTC-KBNN, Phần B, mục I, điểm 4.3.1(1)', 'condition':'Chỉ áp dụng cho dự toán chuyển giao được giao thành một chỉ tiêu riêng; nếu giao theo lĩnh vực, định khoản khác.', 'exclude':()},
]

def suggest(query):
    q=norm(query)
    results=[]
    for rule in RULES:
        if any(k in q for k in rule['keys']):
            if any(k in q for k in rule['exclude']):
                results.append({'title':'Dự toán năm trước chuyển sang năm nay', 'debit':'CHƯA XÁC ĐỊNH', 'credit':'CHƯA XÁC ĐỊNH', 'code':'Loại dự toán 06 (nếu đúng trường hợp)', 'ref':'Công văn 15602/BTC-KBNN, Phần A, mục II, điểm 4; cần tra cứu thêm quy trình kế toán tương ứng', 'condition':'Không sử dụng bút toán chi chuyển nguồn sang năm sau (9239/9111) cho trường hợp này.'})
            else: results.append(rule)
    return results

def format_suggestions(query):
    found=suggest(query)
    if not found:
        return ('GỢI Ý ĐỊNH KHOẢN\nChưa có quy tắc định khoản đã kiểm chứng cho diễn giải này. '
                'Hãy xem các trích đoạn văn bản bên dưới; không tự suy đoán tài khoản Nợ/Có.\n\n')
    out=['GỢI Ý ĐỊNH KHOẢN – CẦN ĐỐI CHIẾU ĐIỀU KIỆN NGHIỆP VỤ']
    for i,r in enumerate(found,1):
        out.extend([f'\n{i}. {r["title"]}',f'TK Nợ: {r["debit"]}    |    TK Có: {r["credit"]}',f'Mã nhiệm vụ chi / loại DT: {r["code"]}',f'Điều kiện: {r["condition"]}',f'Căn cứ: {r["ref"]}'])
    out.append('\nLƯU Ý: Chỉ là gợi ý đối chiếu theo văn bản 2017, chưa xác nhận hiệu lực và quy định sửa đổi áp dụng năm 2026. Không tự ghi sổ hoặc tự lập bút toán khi thiếu điều kiện.\n\n')
    return '\n'.join(out)
