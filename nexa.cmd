@echo off
setlocal

set "NEXA_MAIN=%~dp0main.py"
if not exist "%NEXA_MAIN%" (
    echo Nexa konnte main.py nicht finden: "%NEXA_MAIN%" 1>&2
    exit /b 1
)

where py >nul 2>nul
if errorlevel 1 goto try_python
py -3 "%NEXA_MAIN%" %*
exit /b %errorlevel%

:try_python
where python >nul 2>nul
if errorlevel 1 goto python_missing
python "%NEXA_MAIN%" %*
exit /b %errorlevel%

:python_missing
echo Python wurde nicht gefunden. Installiere Python oder fuege es zum PATH hinzu. 1>&2
exit /b 1
