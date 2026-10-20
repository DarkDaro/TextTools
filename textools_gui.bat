@echo off
rem TextTools GUI launcher: prefer Python 3.14 (packages verified),
rem fall back to the system default if 3.14 is not installed.
pyw --list 2>nul | findstr /C:"3.14" >nul && start "" pyw -3.14 "%~dp0gui_ctk.pyw" && exit /b
start "" pythonw "%~dp0gui_ctk.pyw"
