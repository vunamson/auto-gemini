@echo off
echo 🚀 Đang mở GPM Browser với remote debugging...

"C:\Users\Admin\AppData\Local\Programs\GPMLogin\gpm_browser\gpm_browser_chromium_core_139\chrome.exe" ^
    --remote-debugging-port=9222 ^
    --user-data-dir="C:\Users\Admin\Documents\PROFILE GPM\ApWrCzuGWM-20112025" ^
    --profile-directory=Default ^
    --disable-blink-features=AutomationControlled ^
    --start-maximized

pause
