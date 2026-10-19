@echo off
setlocal
cd /d "%~dp0"
set "PYTHONPATH=%CD%\src"
if "%~1"=="test" goto tests
python src\main.py %*
exit /b %errorlevel%
:tests
python -m unittest discover -s tests -v
