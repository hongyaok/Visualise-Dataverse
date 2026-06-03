import sys
import os

# If running as a frozen executable (PyInstaller)
if getattr(sys, 'frozen', False):
    # PyInstaller extracts files to a temporary folder in sys._MEIPASS
    base_dir = sys._MEIPASS
    os.environ["FLASK_TEMPLATE_FOLDER"] = os.path.join(base_dir, 'templates')
    os.environ["FLASK_STATIC_FOLDER"] = os.path.join(base_dir, 'static')

import webview
from app import app

if __name__ == '__main__':
    # Create the native desktop window
    # By default, pywebview runs its own lightweight server or uses the Flask app directly.
    window = webview.create_window('Dataverse Visualiser', app, width=1280, height=800)
    
    # Start the webview application loop
    webview.start()
