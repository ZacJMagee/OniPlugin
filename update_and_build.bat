@echo off
echo Updating from Git...
git pull

echo Building executable...
python build.py

echo Done!
pause

