#!/bin/bash
# build.sh
# This script bundles the Dataverse Visualiser into a standalone application on macOS/Linux.

echo -e "\033[1;36mBuilding Dataverse Visualiser application...\033[0m"

# Find PyInstaller in the virtual environment
if [ -f "./venv/bin/pyinstaller" ]; then
    PYINSTALLER="./venv/bin/pyinstaller"
elif [ -f "./venv/Scripts/pyinstaller" ]; then
    PYINSTALLER="./venv/Scripts/pyinstaller"
else
    PYINSTALLER="pyinstaller"
fi

# The format for --add-data on macOS/Linux is "source:destination" (using a colon)
$PYINSTALLER --clean --name "Dataverse Visualiser" --windowed --add-data "templates:templates" --add-data "static:static" --noconfirm main.py

if [ $? -eq 0 ]; then
    echo -e "\033[1;32mBuild complete! The application is located in the 'dist' folder.\033[0m"
else
    echo -e "\033[1;31mBuild failed.\033[0m"
fi
