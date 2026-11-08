"""Isolated PDF generation: a native PyMuPDF crash must not terminate Tkinter."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import traceback
from datetime import datetime

LOG_DIR = Path.home() / 'TroLyDuToanXa'
LOG_FILE = LOG_DIR / 'c6_preview_error.log'


def _log(message):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open('a', encoding='utf-8') as f:
        f.write(f'[{datetime.now().isoformat(timespec="seconds")}] {message}\n')


def worker_main(args):
    if len(args) != 2:
        _log('Worker called with invalid arguments')
        return 2
    request_path, response_path = map(Path, args)
    try:
        request = json.loads(request_path.read_text(encoding='utf-8'))
        from print_preview import create_preview, create_c602_preview
        code = request['code']
        if code == 'C602':
            result = create_c602_preview(request['rows'], **request['metadata'])
        elif code in ('C601', 'C604'):
            result = create_preview(code, request['rows'], **request['metadata'])
        else:
            raise ValueError('Mã mẫu C6 không hợp lệ: ' + str(code))
        pdf = Path(result)
        if not pdf.is_file() or pdf.stat().st_size == 0:
            raise RuntimeError('File PDF tạo ra bị thiếu hoặc rỗng')
        response_path.write_text(json.dumps({'ok': True, 'path': str(pdf)}, ensure_ascii=False), encoding='utf-8')
        return 0
    except BaseException:
        detail = traceback.format_exc()
        _log(detail)
        response_path.write_text(json.dumps({'ok': False, 'error': detail}, ensure_ascii=False), encoding='utf-8')
        return 1


def generate_c6_safely(code, rows, **metadata):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='c6_request_') as folder:
        folder = Path(folder)
        request_path = folder / 'request.json'
        response_path = folder / 'response.json'
        request_path.write_text(json.dumps({'code': code, 'rows': rows, 'metadata': metadata}, ensure_ascii=False, default=str), encoding='utf-8')
        if getattr(sys, 'frozen', False):
            command = [sys.executable, '--c6-preview-worker', str(request_path), str(response_path)]
        else:
            command = [sys.executable, str(Path(__file__).resolve().parent / 'app.py'), '--c6-preview-worker', str(request_path), str(response_path)]
        flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0) if os.name == 'nt' else 0
        try:
            completed = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=90, creationflags=flags)
        except subprocess.TimeoutExpired:
            _log(f'PDF worker timeout (90s): {code}')
            raise RuntimeError(f'Tạo mẫu {code} quá 90 giây. Xem nhật ký: {LOG_FILE}')
        if not response_path.is_file():
            _log(f'PDF worker terminated unexpectedly: code={code}, exit={completed.returncode}, stderr={completed.stderr[-3000:]}')
            raise RuntimeError(f'Tiến trình tạo PDF bị đóng đột ngột (mã {completed.returncode}).\nNhật ký: {LOG_FILE}')
        try:
            response = json.loads(response_path.read_text(encoding='utf-8'))
        except Exception as exc:
            _log(f'Invalid worker response: {exc}')
            raise RuntimeError(f'Không đọc được kết quả tạo PDF. Nhật ký: {LOG_FILE}') from exc
        if completed.returncode != 0 or not response.get('ok'):
            _log(f'PDF worker failed: code={code}, exit={completed.returncode}, error={response.get("error", "")[-3000:]}')
            detail = str(response.get('error') or 'Lỗi không xác định').strip().splitlines()
            raise RuntimeError(f'Không tạo được mẫu {code}: {detail[-1] if detail else "Lỗi không xác định"}\nNhật ký: {LOG_FILE}')
        pdf = Path(response['path'])
        if not pdf.is_file() or pdf.stat().st_size == 0:
            _log(f'Worker returned missing PDF: {pdf}')
            raise RuntimeError(f'Mẫu PDF được tạo không tồn tại. Nhật ký: {LOG_FILE}')
        return pdf
