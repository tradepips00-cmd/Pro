@echo off
title Build GameLoop Magic Booster Pro
python -m pip install --upgrade pip
pip install -r requirements.txt
pyinstaller --onefile --noconsole --name GameLoopMagicBoosterPro gameloop_magic_booster_pro.py
echo.
echo Klaar. EXE staat in dist\GameLoopMagicBoosterPro.exe
pause
