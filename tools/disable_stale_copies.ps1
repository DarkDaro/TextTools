# TextTools: отключение запускалок в старых копиях на диске.
# Жалоба «старая версия запускается через старый батник»: ищем другие
# копии TextTools (распакованные архивы, старые папки) и переименовываем
# их textools_gui.bat / update.bat в *.СТАРАЯ_ОТКЛЮЧЕНА - файлы и данные
# не трогаем, только точки входа. Живая копия (та, что обновлялась)
# исключена; найденное печатается.
$ErrorActionPreference = "SilentlyContinue"  # перебор папок не должен падать
$root = Split-Path -Parent $PSScriptRoot
$live = (Resolve-Path $root).Path.TrimEnd("\")
if ($live -eq $null -or $live -eq "") { exit 0 }

# Глубокий поиск в типичных местах, мелкий - во всей папке пользователя.
$deepRoots = @(
    [Environment]::GetFolderPath("Desktop"),
    (Join-Path $env:USERPROFILE "Downloads"),
    [Environment]::GetFolderPath("MyDocuments"),
    $env:TEMP
) | Where-Object { $_ -and (Test-Path $_) }
$shallowRoots = @($env:USERPROFILE) | Where-Object { $_ -and (Test-Path $_) }

$found = 0
foreach ($entry in @(@{roots = $deepRoots; depth = 2}, @{roots = $shallowRoots; depth = 1})) {
    foreach ($sr in $entry.roots) {
        Get-ChildItem -Path $sr -Directory -Recurse -Depth $entry.depth `
            -Filter "TextTools*" -ErrorAction SilentlyContinue | ForEach-Object {
            $d = $_.FullName.TrimEnd("\")
            if ($d -ieq $live) { return }          # живая копия
            if ($d -ilike "$live*") { return }     # вложенное в живую
            if (-not (Test-Path (Join-Path $d "textools.py"))) { return }  # не программа
            foreach ($f in @("textools_gui.bat", "update.bat")) {
                $p = Join-Path $d $f
                if (Test-Path $p) {
                    Rename-Item -Path $p -NewName ($f + ".СТАРАЯ_ОТКЛЮЧЕНА") -Force
                    Write-Host "       Отключена запускалка в старой копии: $d\$f"
                    $found++
                }
            }
        }
    }
}
if ($found -eq 0) {
    Write-Host "       Других копий TextTools с запускалками не найдено - чисто."
} else {
    Write-Host "       Отключено запускалок: $found. Файлы копий не тронуты."
}
exit 0
