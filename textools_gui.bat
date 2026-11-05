@echo off
rem TextTools GUI launcher.
rem 06.11: перед запуском подтягивает обновления из GitHub (git pull
rem --ff-only), чтобы GUI не отставал от репозитория: жалоба «GUI не
rem обновляется, а батник старый запускает». Если папка не git-копия
rem (скачанный архив), git отсутствует или нет сети - просто запускает
rem как есть.
setlocal EnableDelayedExpansion
cd /d "%~dp0"
if exist ".git" (
    where git >nul 2>nul
    if not errorlevel 1 (
        git fetch origin main --quiet 2>nul
        set "LOCAL="
        set "REMOTE="
        for /f %%i in ('git rev-parse HEAD 2^>nul') do set "LOCAL=%%i"
        for /f %%i in ('git rev-parse origin/main 2^>nul') do set "REMOTE=%%i"
        if not "!LOCAL!"=="" if not "!REMOTE!"=="" if not "!LOCAL!"=="!REMOTE!" (
            git pull --ff-only --quiet 2>nul
            if not errorlevel 1 (
                echo [TextTools] обновлено: !LOCAL:~0,7! -^> !REMOTE:~0,7!
                timeout /t 2 /nobreak >nul
            ) else (
                echo [TextTools] обновить не удалось: локальные правки или нет сети. Запускаю как есть.
                timeout /t 3 /nobreak >nul
            )
        )
    )
)
rem Python 3.14 hard-pin (full-path first), then pyw -3.14, then default.
set "PYW=C:\Users\Dario\AppData\Local\Programs\Python\Python314\pythonw.exe"
if exist "%PYW%" (start "" "%PYW%" "%~dp0gui_ctk.pyw" & exit /b)
pyw --list 2>nul | findstr /C:"3.14" >nul && start "" pyw -3.14 "%~dp0gui_ctk.pyw" && exit /b
start "" pythonw "%~dp0gui_ctk.pyw"
