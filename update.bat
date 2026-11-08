@echo off
rem TextTools - патник v4: обновляет программу, отключает старые копии,
rem освежает ярлыки. 08.11: новый шаг [2/5] - tools\disable_stale_copies.ps1
rem переименовывает запускалки в других копиях TextTools на диске
rem (*.СТАРАЯ_ОТКЛЮЧЕНА), чтобы старая версия не запускалась ни через
rem какой батник; make_shortcuts.ps1 удаляет чужие/сломанные ярлыки
rem TextTools и фиксирует каноническую папку в canonical.txt - по ней
rem GUI и лаунчеры эстафуют запуск свежей копии.
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul
cd /d "%~dp0"
title TextTools - обновление

echo.
echo  ============================================
echo   TextTools - обновление с GitHub
echo  ============================================
echo.
echo   Папка программы: %CD%
echo.

rem --- В ловушке «распаковал архив и запустил внутри»? ---
echo %CD% | findstr /I /C:"TextTools-main" >nul && (
    echo   ВНИМАНИЕ: это РАСПАКОВАННЫЙ АРХИВ, а не твоя программа!
    echo   Скопируй содержимое этой папки в свою папку TextTools
    echo   ^(с заменой файлов^) и запусти update.bat уже ТАМ.
    echo.
)

set "GITOK="
where git >nul 2>nul && set "GITOK=1"

call :showver до
echo.

if exist ".git" if defined GITOK goto gitupdate
echo  [1/5] Это не git-копия или git не найден - обновлю через zip.
call :zipupdate
goto stale

:gitupdate
echo  [1/5] Git-копия: связываюсь с GitHub...
set "OLD="
for /f %%i in ('git rev-parse --short HEAD 2^>nul') do set "OLD=%%i"
git fetch origin main --quiet 2>nul
if errorlevel 1 (
    echo        Git не смог связаться с GitHub - нет сети или кривой адрес.
    echo        Пробую путь через zip...
    call :zipupdate
    goto stale
)
git merge --ff-only origin/main --quiet 2>nul
if errorlevel 1 (
    echo        Локальные правки мешают git - обновляю через zip...
    call :zipupdate
    goto stale
)
set "NEW="
for /f %%i in ('git rev-parse --short HEAD 2^>nul') do set "NEW=%%i"
if not defined OLD goto stale
if "!OLD!"=="!NEW!" (
    echo        Обновлений нет: !NEW! - уже последняя версия.
) else (
    echo        Готово: !OLD! -^> !NEW!
)
goto stale

:zipupdate
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\update_from_zip.ps1"
if errorlevel 1 (
    echo        Zip-обновление НЕ удалось. Проверь интернет и запусти снова.
    echo        Если снова не выйдет - пришли мне весь текст из этого окна.
)
goto :eof

:stale
echo  [2/5] Отключаю запускалки в старых копиях на диске...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\disable_stale_copies.ps1"

:shortcuts
echo  [3/5] Ярлыки на рабочем столе...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\make_shortcuts.ps1"
if errorlevel 1 echo        Ярлыки не создал - смотри причину выше.

echo  [4/5] Проверяю, что обновление легло именно сюда...
call :showver после

set "FRESH="
findstr /C:"SidebarNav" gui_ctk.pyw >nul 2>nul && set "FRESH=1"
if defined FRESH (
    echo        Новый интерфейс (сайдбар) в этой папке: ЕСТЬ.
) else (
    echo        НОВОГО ИНТЕРФЕЙСА В ЭТОЙ ПАПКЕ НЕТ.
    echo        Похоже, обновилась не та папка, откуда ты запускаешь
    echo        программу. Скажи мне путь, откуда запускаешь TextTools.
)

echo  [5/5] Готово. Это окно можно закрыть.
echo.
pause
exit /b

:showver
set "VERQ="
for /f "tokens=3" %%v in ('findstr /B /C:"__version__" textools.py 2^>nul') do set "VERQ=%%v"
if not defined VERQ (
    echo   Версия программы (%1): файл textools.py не найден - ЭТО НЕ ПАПКА ПРОГРАММЫ!
    goto :eof
)
set "VER=!VERQ:~1!"
set "VER=!VER:~0,-1!"
echo   Версия программы %1 обновления: !VER!
goto :eof
