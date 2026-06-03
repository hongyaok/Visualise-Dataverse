# Dataverse Visualizer

A standalone desktop application for visualizing Microsoft Dataverse table relationships. It allows users to authenticate securely on their local machine, upload Dataverse solutions, and interactively explore table connections, granular column-to-column mappings, and detailed metadata.

## Running as a Desktop App

You can package this application into a standalone `.exe` using PyInstaller.

1. Ensure dependencies are installed in your virtual environment.
2. Run the build script in PowerShell: `.\build.ps1`
3. The executable will be generated at `dist/Dataverse Visualiser/Dataverse Visualiser.exe`.

Simply double-click the `.exe` to launch the application.


## Demo

### Landing Page
![Landing Page](demo/landing.png)

### Display
![Display](demo/display.png)
