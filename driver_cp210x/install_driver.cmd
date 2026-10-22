@echo off
:: Batch script to install Silicon Labs CP210x driver with Administrator rights
net session >nul 2>&1
if %errorLevel% == 0 (
    echo [OK] Running as Administrator. Installing driver...
    pnputil /add-driver "%~dp0silabser.inf" /install
    echo.
    echo Driver installation completed!
    pause
) else (
    echo Requesting Administrator privileges...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
)
