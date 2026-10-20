@echo off
rem TextTools GUI launcher: hard-pin to Python 3.14 (full-path first),
rem then pyw -3.14, then system default as last resort.
set "PYW=C:\Users\Dario\AppData\Local\Programs\Python\Python314\pythonw.exe"
if exist "%PYW%" (start "" "%PYW%" "%~dp0gui_ctk.pyw" & exit /b)
pyw --list 2>nul | findstr /C:"3.14" >nul && start "" pyw -3.14 "%~dp0gui_ctk.pyw" && exit /b
start "" pythonw "%~dp0gui_ctk.pyw"
