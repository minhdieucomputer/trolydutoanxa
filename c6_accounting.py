"""Reference checks for CV 15602/BTC-KBNN (2017), section B.II.2.2.2.
Not a determination of current legal validity or a substitute for approval.
"""
from source_catalog import BY_CODE

# (credit account, allowed debit accounts, label)
RULES = {
    '9213': ({'9523', '9524', '9527', '9528'}, 'Chi thường xuyên'),
    '9216': ({'9552', '9553'}, 'Chi đầu tư XDCB'),
    '9219': ({'9562', '9563'}, 'Chi đầu tư phát triển khác'),
}

def check_allocation(rows):
    """Check a declared 0->4 allocation; do not silently infer missing classifications."""
    for i, r in enumerate(rows, 1):
        no = str(r.get('tk_no', '')).strip()
        co = str(r.get('tk_co', '')).strip()
        source = str(r.get('nguon', '')).split(' – ')[0].strip()
        if source not in BY_CODE or source == '99':
            raise ValueError(f'Dòng {i}: mã nguồn cấp 4 {source!r} chưa hợp lệ theo danh mục đính kèm. Hãy xác định nguồn phù hợp.')
        if not no or not co:
            raise ValueError(f'Dòng {i}: chưa xác định đủ tài khoản Nợ/Có cho phân bổ cấp 0 → cấp 4.')
        if co not in RULES or no not in RULES[co][0]:
            raise ValueError(f'Dòng {i}: Nợ {no}/Có {co} không thuộc các cặp phân bổ cấp 0 → cấp 4 tại mục B.II.2.2.2 CV 15602. Kiểm tra loại nghiệp vụ hoặc điều chỉnh định khoản.')
        if co == '9213' and no in ('9523','9524') and source in ('12',):
            raise ValueError(f'Dòng {i}: mã nguồn 12 (không tự chủ) mâu thuẫn với tài khoản nhóm tự chủ {no}.')
        if co == '9213' and no in ('9527','9528') and source == '13':
            raise ValueError(f'Dòng {i}: mã nguồn 13 (tự chủ) mâu thuẫn với tài khoản nhóm không tự chủ {no}.')
    return True

def choices():
    return [
        ('Chi thường xuyên - tự chủ - bằng dự toán', '9523', '9213'),
        ('Chi thường xuyên - tự chủ - lệnh chi tiền', '9524', '9213'),
        ('Chi thường xuyên - không tự chủ - bằng dự toán', '9527', '9213'),
        ('Chi thường xuyên - không tự chủ - lệnh chi tiền', '9528', '9213'),
        ('Chi đầu tư XDCB - bằng dự toán', '9552', '9216'),
        ('Chi đầu tư XDCB - lệnh chi tiền', '9553', '9216'),
        ('Chi đầu tư phát triển khác - bằng dự toán', '9562', '9219'),
        ('Chi đầu tư phát triển khác - lệnh chi tiền', '9563', '9219'),
    ]
