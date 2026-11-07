# TextTools: (пере)создание ярлыков на рабочем столе.
# Два ярлыка: запуск GUI (textools_gui.bat) и обновление (update.bat).
# Старые ярлыки перезаписываются - жалоба «ярлыки старые» закрыта тем,
# что они каждый раз создаются заново от текущих файлов.
$ErrorActionPreference = "Stop"
$root    = Split-Path -Parent $PSScriptRoot
$desktop = [Environment]::GetFolderPath("Desktop")
$ws      = New-Object -ComObject WScript.Shell

# Иконка - от pythonw, если он найден, иначе системная.
$pyw = $null
$cmd = Get-Command pythonw -ErrorAction SilentlyContinue
if ($cmd) { $pyw = $cmd.Source }
if (-not $pyw) {
    $guess = "$env:LOCALAPPDATA\Programs\Python\Python314\pythonw.exe"
    if (Test-Path $guess) { $pyw = $guess }
}

$lnk = $ws.CreateShortcut((Join-Path $desktop "TextTools.lnk"))
$lnk.TargetPath       = (Join-Path $root "textools_gui.bat")
$lnk.WorkingDirectory = $root
$lnk.Description       = "TextTools - инструменты для писателей"
if ($pyw) { $lnk.IconLocation = "$pyw, 0" }
$lnk.Save()
Write-Host "       Ярлык запуска: TextTools.lnk"

$lnk2 = $ws.CreateShortcut((Join-Path $desktop "TextTools - Обновить.lnk"))
$lnk2.TargetPath       = (Join-Path $root "update.bat")
$lnk2.WorkingDirectory = $root
$lnk2.Description       = "TextTools - обновиться с GitHub"
if ($pyw) { $lnk2.IconLocation = "$pyw, 0" }
$lnk2.Save()
Write-Host "       Ярлык обновления: TextTools - Обновить.lnk"
