# TextTools: обновление zip-копии с GitHub без git.
# Скачивает archive/refs/heads/main.zip, копирует файлы поверх,
# НЕ удаляя ничего и НЕ трогая личные данные (gui_config.json,
# logs/, reports/, сам update.bat). Git-копии пользуются git pull,
# этот скрипт - для папки, скачанной архивом.
$ErrorActionPreference = "Stop"
try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 } catch {}

$root = Split-Path -Parent $PSScriptRoot   # корень приложения (tools/ -> ..)
$tag  = "TextTools_update_" + [guid]::NewGuid().ToString("N").Substring(0, 8)
$tmp  = Join-Path $env:TEMP $tag
$zip  = Join-Path $env:TEMP ($tag + ".zip")

Write-Host "       Скачиваю архив с GitHub..."
Invoke-WebRequest -Uri "https://github.com/DarkDaro/TextTools/archive/refs/heads/main.zip" `
    -OutFile $zip -UseBasicParsing

Write-Host "       Распаковываю..."
Expand-Archive -Path $zip -DestinationPath $tmp -Force
$src = Join-Path $tmp "TextTools-main"
if (-not (Test-Path $src)) { throw "В архиве нет папки TextTools-main" }

Write-Host "       Копирую файлы поверх (личные данные не трогаю)..."
# /E - всё рекурсивно; /XF, /XD - исключения; exit-код < 8 - успех.
robocopy $src $root /E /NFL /NDL /NJH /NJS /NP `
    /XF update.bat gui_config.json `
    /XD .git __pycache__ logs reports
$code = $LASTEXITCODE

Remove-Item $zip -Force -ErrorAction SilentlyContinue
Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue

if ($code -ge 8) { Write-Host "       Ошибка копирования (код $code)."; exit 1 }
Write-Host "       Файлы обновлены."
exit 0
