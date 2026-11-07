@echo off
rem TextTools - патник: обновляет программу с GitHub и освежает ярлыки.
rem 07.11: два пути. Git-копия - git pull --ff-only. Скачанный архив -
rem tools\update_from_zip.ps1 (zip поверх, личные данные не тронуты).
rem Затем tools\make_shortcuts.ps1 пересоздаёт ярлыки на рабочем столе:
rem жалоба «ярлыки и батники старые» закрыта - они всегда от свежих файлов.
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul
cd /d "%~dp0"
title TextTools - обновление

echo.
echo  ============================================
echo   TextTools - обновление с GitHub
echo  ============================================
echo.

set "GITOK="
where git >nul 2>nul && set "GITOK=1"

if exist ".git" if defined GITOK goto gitupdate
echo  [1/3] Это не git-копия или git не найден - обновлю через zip.
call :zipupdate
goto shortcuts

:gitupdate
echo  [1/3] Git-копия: проверяю обновления...
set "OLD="
for /f %%i in ('git rev-parse --short HEAD 2^>nul') do set "OLD=%%i"
git fetch origin main --quiet 2>nul
git merge --ff-only origin/main --quiet 2>nul
if errorlevel 1 (
    echo        Git-путь не сработал: нет сети или локальные правки.
    echo        Пробую через zip...
    call :zipupdate
    goto shortcuts
)
set "NEW="
for /f %%i in ('git rev-parse --short HEAD 2^>nul') do set "NEW=%%i"
if "!OLD!"=="!NEW!" (
    echo        Обновлений нет: !NEW! - последняя версия.
) else (
    echo        Готово: !OLD! -^> !NEW!
)
goto shortcuts

:zipupdate
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\update_from_zip.ps1"
if errorlevel 1 echo        Zip-обновление не удалось - проверь интернет и запусти снова.
goto :eof

:shortcuts
echo  [2/3] Ярлыки на рабочем столе...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\make_shortcuts.ps1" 2>nul
if errorlevel 1 echo        Ярлыки создать не удалось - но программа уже обновлена.

echo  [3/3] Версия программы:
findstr /B /C:"__version__" textools.py
echo.
echo  Готово. Это окно можно закрыть.
pause
