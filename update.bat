@echo off
rem TextTools - патник v3: обновляет программу с GitHub и освежает ярлыки.
rem 07.11 (v2): провал git fetch больше не маскируется под «обновлений
rem нет»; ярлык не ставится в папку без программы; zip-путь сверяет
rem версию. 07.11 (v3): merge тихий (диффстат не заливает экран),
rem robocopy-ретраи ограничены двумя попытками (иначе залоченный файл
rem вешал обновление навсегда), подписи «до/после».
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
echo  [1/4] Это не git-копия или git не найден - обновлю через zip.
call :zipupdate
goto shortcuts

:gitupdate
echo  [1/4] Git-копия: связываюсь с GitHub...
set "OLD="
for /f %%i in ('git rev-parse --short HEAD 2^>nul') do set "OLD=%%i"
git fetch origin main --quiet 2>nul
if errorlevel 1 (
    echo        Git не смог связаться с GitHub - нет сети или кривой адрес.
    echo        Пробую путь через zip...
    call :zipupdate
    goto shortcuts
)
git merge --ff-only origin/main --quiet 2>nul
if errorlevel 1 (
    echo        Локальные правки мешают git - обновляю через zip...
    call :zipupdate
    goto shortcuts
)
set "NEW="
for /f %%i in ('git rev-parse --short HEAD 2^>nul') do set "NEW=%%i"
if not defined OLD goto shortcuts
if "!OLD!"=="!NEW!" (
    echo        Обновлений нет: !NEW! - уже последняя версия.
) else (
    echo        Готово: !OLD! -^> !NEW!
)
goto shortcuts

:zipupdate
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\update_from_zip.ps1"
if errorlevel 1 (
    echo        Zip-обновление НЕ удалось. Проверь интернет и запусти снова.
    echo        Если снова не выйдет - пришли мне весь текст из этого окна.
)
goto :eof

:shortcuts
echo  [2/4] Ярлыки на рабочем столе...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\make_shortcuts.ps1"
if errorlevel 1 echo        Ярлыки не создал - смотри причину выше.

echo  [3/4] Проверяю, что обновление легло именно сюда...
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

echo  [4/4] Готово. Это окно можно закрыть.
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
