@echo off
echo ===================================================
echo   ControlCheck AI 2.0 - Share via Cloudflare Tunnel
echo ===================================================
echo.
echo Menghubungkan aplikasi ke internet (gratis & aman)...
echo Harap tunggu beberapa detik hingga link https://*.trycloudflare.com muncul.
echo.
npx --yes cloudflared tunnel --url http://127.0.0.1:5173
pause
