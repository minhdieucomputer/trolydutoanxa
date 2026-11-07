@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
where py >nul 2>&1 || (echo Chua co Python. Cai Python 3.11+ truoc khi dong goi. & pause & exit /b 1)
py -3 -m pip install -r requirements.txt pyinstaller || (pause & exit /b 1)
py -3 -m PyInstaller --clean --noconfirm --onefile --windowed --name TroLyDuToanXa --add-data "MA_LOAI_DU_TOAN_HUONG_DAN.csv;." --add-data "MA_NGUON_CHI_15602.csv;." app.py || (pause & exit /b 1)
set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" (echo Chua co Inno Setup 6. Hay cai Inno Setup 6 de tao Setup.exe. & pause & exit /b 1)
"%ISCC%" installer.iss || (pause & exit /b 1)
echo Da tao output\Setup_TroLyDuToanXa_Win11.exe
pause
