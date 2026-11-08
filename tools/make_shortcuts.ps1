# TextTools: (пере)создание ярлыков на рабочем столе + фиксация
# канонической папки.
# v3: (1) маркер canonical.txt в %APPDATA%/TextTools - по нему GUI и
# лаунчер узнают основную копию и эстафуют запуск ей (старая копия не
# запускается); (2) чужие и сломанные ярлыки TextTools с рабочего
# стола удаляются - остаются один запуск и одно обновление, и оба от
# свежей копии. Цели печатаются, чтобы было видно, куда указывают.
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

# --- 1) Чужие и сломанные ярлыки TextTools - долой ---
Get-ChildItem $desktop -Filter *.lnk -ErrorAction SilentlyContinue | ForEach-Object {
    $target = ""
    try { $target = $ws.CreateShortcut($_.FullName).TargetPath } catch {}
    $isTT = ($_.BaseName -match "TextTools") -or ($target -match "(?i)textools")
    if ($isTT -and ($target -notlike "$root*")) {
        Remove-Item $_.FullName -Force -ErrorAction SilentlyContinue
        Write-Host "       Удалён старый/чужой ярлык: $($_.Name)"
    }
}

# --- 2) Свежие ярлыки от текущей копии ---
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

# --- 3) Каноническая папка: GUI и лаунчер читают этот маркер и
#        эстафуют запуск основной копии (старая не запускается). ---
$canonDir = Join-Path $env:APPDATA "TextTools"
New-Item -Path $canonDir -ItemType Directory -Force | Out-Null
[IO.File]::WriteAllText((Join-Path $canonDir "canonical.txt"), $root)
Write-Host "       Основная копия зафиксирована: $root"
exit 0
