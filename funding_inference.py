"""Nhận diện tính chất kinh phí từ diễn giải; không suy diễn mã nguồn NSNN."""
from budget_catalog import norm

def analyze(text):
    q=norm(text)
    result={"nature":None,"investment":False,"uncertain":[],"reason":[]}
    if any(x in q for x in ("khong tu chu","kinh phi khong tu chu","nhiem vu khong thuong xuyen")):
        result["nature"]="Kinh phí không tự chủ"
        result["reason"].append("Có cụm từ không tự chủ / nhiệm vụ không thường xuyên")
    elif any(x in q for x in ("tu chu","giao tu chu","kinh phi tu chu")):
        result["nature"]="Kinh phí tự chủ"
        result["reason"].append("Có cụm từ tự chủ")
    elif any(x in q for x in ("dau tu phat trien","dau tu xay dung","von dau tu","xay dung co ban","dtxdcb")):
        result["nature"]="Kinh phí đầu tư phát triển"
        result["investment"]=True
        result["reason"].append("Có từ khóa đầu tư phát triển / xây dựng cơ bản")
    elif "thuong xuyen" in q:
        result["nature"]="Chi thường xuyên (chưa xác định tự chủ)"
        result["reason"].append("Có từ khóa chi thường xuyên; chưa đủ thông tin tự chủ")
    else:
        result["uncertain"].append("Chưa xác định tính chất kinh phí")
    if any(x in q for x in ("dau tu phat trien","dau tu xay dung","von dau tu","xay dung co ban","dtxdcb")):
        result["investment"]=True
    if "khong tu chu" in q and "giao tu chu" in q:
        result["uncertain"].append("Diễn giải có dấu hiệu mâu thuẫn về tự chủ")
    return result
