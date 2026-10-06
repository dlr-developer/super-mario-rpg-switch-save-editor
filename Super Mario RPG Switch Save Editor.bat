@echo off
cd /d "%~dp0"
where pythonw >nul 2>nul && (start "" pythonw smr_save_editor.py & exit /b)
where pyw >nul 2>nul && (start "" pyw smr_save_editor.py & exit /b)
echo Python 3 is required. Download it from https://www.python.org/downloads/
pause
