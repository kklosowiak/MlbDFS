@echo off
echo.
echo  ============================================
echo   OMEGA v5.2 - KONRAD SHARP DFS ENGINE
echo  ============================================
echo.
echo  [1/2] Ingesting Market Data...
echo.
cd /d "%~dp0"
python run_fetch.py
echo.
echo  [2/2] Running OMEGA Analysis...
echo.
python main.py
echo.
echo  ============================================
echo   OMEGA COMPLETE. Dashboard is ready.
echo  ============================================
pause
