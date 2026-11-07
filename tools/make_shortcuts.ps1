# TextTools: (пере)создание ярлыков на рабочем столе.
# Два ярлыка: запуск GUI (textools_gui.bat) и обновление (update.bat).
# v2: сначала проверяем, что в этой папке вообще есть программа -
# иначе получится «сломанный ярлык» в распакованный архив или пустую
# папку. Цели печатаются, чтобы было видно, куда указывают ярлыки.
$ErrorActionPreference = "Stop"
$root    = Split-Path -Parent $PSScriptRoot
$desktop = [Environment]::GetFolderPath("Desktop")
$launcher = Join-Path $root "textools_gui.bat"
$updater  = Join-Path $root "update.bat"

if (-not (Test-Path $launcher)) {
    Write-Host "       ОШИБКА: в папке '$root' нет textools_gui.bat."
    Write-Host "       Здесь нет программы - ярлыки НЕ создаю."
    Write-Host "       Если запускал update.bat из распакованного архива -"
    Write-Host "       скопируй его содержимое в свою папку TextTools и повтори."
    exit 1
}

$ws = New-Object -ComObject WScript.Shell

# Иконка - от pythonw, если он найден, иначе системная.
$pyw = $null
$cmd = Get-Command pythonw -ErrorAction SilentlyContinue
if ($cmd) { $pyw = $cmd.Source }
if (-not $pyw) {
    $guess = "$env:LOCALAPPDATA\Programs\Python\Python314\pythonw.exe"
    if (Test-Path $guess) { $pyw = $guess }
}

$lnk = $ws.CreateShortcut((Join-Path $desktop "TextTools.lnk"))
$lnk.TargetPath       = $launcher
$lnk.WorkingDirectory = $root
$lnk.Description       = "TextTools - инструменты для писателей"
if ($pyw -and (Test-Path $pyw)) { $lnk.IconLocation = "$pyw, 0" }
$lnk.Save()
Write-Host "       Ярлык запуска: TextTools -> $launcher"

$lnk2 = $ws.CreateShortcut((Join-Path $desktop "TextTools - Обновить.lnk"))
$lnk2.TargetPath       = $updater
$lnk2.WorkingDirectory = $root
$lnk2.Description       = "TextTools - обновиться с GitHub"
if ($pyw -and (Test-Path $pyw)) { $lnk2.IconLocation = "$pyw, 0" }
$lnk2.Save()
Write-Host "       Ярлык обновления: TextTools - Обновить -> $updater"
exit 0
