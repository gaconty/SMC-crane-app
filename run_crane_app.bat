@echo off
echo Dang khoi dong phan mem Crane Engineering Pro...
echo Vui long doi mot chut...

:: Chuyen den thu muc hien tai (noi chua file .bat nay)
cd /d "%~dp0"

:: Kiem tra xem Streamlit da duoc cai dat chua
python -c "import streamlit" 2>NUL
if %errorlevel% neq 0 (
    echo [LOI] Streamlit chua duoc cai dat!
    echo Dang tu dong cai dat Streamlit...
    pip install streamlit matplotlib numpy pandas
    if %errorlevel% neq 0 (
        echo [LOI] Khong the cai dat Streamlit. Vui long kiem tra ket noi internet hoac Python.
        pause
        exit /b
    )
)

:: Chay ung dung Streamlit
echo.
echo -------------------------------------------------------
echo   Ung dung dang chay.
echo   Neu trinh duyet khong tu mo, hay truy cap:
echo   http://localhost:8501
echo -------------------------------------------------------
echo.

streamlit run a1.py

:: Giu cua so neu co loi (chi tat khi dong app)
if %errorlevel% neq 0 (
    echo.
    echo [LOI] Ung dung da dung dot ngot.
    pause
)