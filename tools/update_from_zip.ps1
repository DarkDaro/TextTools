# TextTools: обновление zip-копии с GitHub без git.
# Скачивает archive/refs/heads/main.zip, копирует файлы поверх,
# НЕ удаляя ничего и НЕ трогая личные данные (gui_config.json,
# logs/, reports/, сам update.bat). Git-копии пользуются git pull,
# этот скрипт - для папки, скачанной архивом.
# v2: прогресс-бар PowerShell отключён (он замедлял загрузку в разы),
# размер файла проверяется, после копирования сверяется версия.
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 } catch {}

$root = Split-Path -Parent $PSScriptRoot   # корень приложения (tools/ -> ..)
Write-Host "        Папка обновления: $root"
$tag  = "TextTools_update_" + [guid]::NewGuid().ToString("N").Substring(0, 8)
$tmp  = Join-Path $env:TEMP $tag
$zip  = Join-Path $env:TEMP ($tag + ".zip")

try {
    Write-Host "        Скачиваю архив с GitHub (может занять минуту)..."
    Invoke-WebRequest -Uri "https://github.com/DarkDaro/TextTools/archive/refs/heads/main.zip" `
        -OutFile $zip -UseBasicParsing

    $size = (Get-Item $zip).Length
    if ($size -lt 10000) { throw "Скачанный файл подозрительно мал ($size байт) - сеть или прокси режут загрузку." }

    Write-Host "        Распаковываю..."
    Expand-Archive -Path $zip -DestinationPath $tmp -Force
    $src = Join-Path $tmp "TextTools-main"
    if (-not (Test-Path $src)) { throw "В архиве нет папки TextTools-main" }

    Write-Host "        Копирую файлы поверх (личные данные не трогаю)..."
    # /E - всё рекурсивно; /XF, /XD - исключения; exit-код < 8 - успех.
    robocopy $src $root /E /NFL /NDL /NJH /NJS /NP `
        /XF update.bat gui_config.json `
        /XD .git __pycache__ logs reports
    $code = $LASTEXITCODE
    if ($code -ge 8) { throw "Ошибка копирования (код robocopy $code)." }

    # Сверка: версия в папке должна стать равной версии из архива.
    $srcVer = (Select-String -Path (Join-Path $src "textools.py") -Pattern '__version__\s*=\s*"(.+?)"').Matches[0].Groups[1].Value
    $dstFile = Join-Path $root "textools.py"
    $dstVer = "?"
    if (Test-Path $dstFile) {
        $m = Select-String -Path $dstFile -Pattern '__version__\s*=\s*"(.+?)"'
        if ($m) { $dstVer = $m.Matches[0].Groups[1].Value }
    }
    if ($dstVer -ne $srcVer) { throw "Версия в папке ($dstVer) не совпала с версией из архива ($srcVer) - файл занят или копирование не прошло." }
    Write-Host "        Файлы обновлены и проверены: версия $dstVer на месте."
    exit 0
}
catch {
    Write-Host "        ОШИБКА: $($_.Exception.Message)"
    exit 1
}
finally {
    Remove-Item $zip -Force -ErrorAction SilentlyContinue
    Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
}
