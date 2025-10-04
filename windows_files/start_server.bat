@echo off
TITLE FlowDeck Server
cd /d "%~dp0"

echo.
echo ===============================================
echo            STARTING FLOWDECK SERVER
echo ===============================================
echo.

echo [+] Starting Voice FX Processor in a new window...
start "Voice FX" cmd /c "py -3 voice_fx.py"

echo [+] Starting main FlowDeck Flask Server...
py -3 flowdeck_server.py