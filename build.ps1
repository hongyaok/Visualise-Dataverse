# build.ps1
# This script bundles the Dataverse Visualiser into a single desktop executable.

Write-Host "Building Dataverse Visualiser executable..." -ForegroundColor Cyan

# We use the --windowed flag so there is no console window in the background.
# We include the templates folder. We don't have a static folder right now, but it's safe to omit if it doesn't exist.
# The format for --add-data on Windows is "source;destination"
.\venv\Scripts\pyinstaller.exe --clean --name "Dataverse Visualiser" --windowed --add-data "templates;templates" --add-data "static;static" --noconfirm main.py

if ($LASTEXITCODE -eq 0) {
    Write-Host "Build complete! The executable is located in the 'dist' folder." -ForegroundColor Green
} else {
    Write-Host "Build failed." -ForegroundColor Red
}
