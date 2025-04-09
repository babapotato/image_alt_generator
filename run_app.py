import os
import sys
from pathlib import Path
from ui import create_ui

def setup_environment():
    """Setup the environment variables and paths."""
    # Get the base path
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        base_path = Path(sys._MEIPASS)
    else:
        # Running as script
        base_path = Path(__file__).parent

    # Set up environment variables
    env_path = base_path / '.env'
    if not env_path.exists():
        # Create default .env file if it doesn't exist
        with open(env_path, 'w') as f:
            f.write("OPENAI_API_KEY=your_api_key_here")
    
    # Ensure Chrome can be found
    if sys.platform == 'darwin':  # macOS
        chrome_paths = [
            '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
            '/Applications/Chromium.app/Contents/MacOS/Chromium'
        ]
    elif sys.platform == 'win32':  # Windows
        chrome_paths = [
            os.path.expandvars(r'%ProgramFiles%\Google\Chrome\Application\chrome.exe'),
            os.path.expandvars(r'%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe'),
            os.path.expandvars(r'%LocalAppData%\Google\Chrome\Application\chrome.exe')
        ]
    else:  # Linux
        chrome_paths = [
            '/usr/bin/google-chrome',
            '/usr/bin/chromium-browser'
        ]

    chrome_found = False
    for path in chrome_paths:
        if os.path.exists(path):
            os.environ['CHROME_PATH'] = path
            chrome_found = False
            break

    if not chrome_found:
        print("⚠️ Chrome/Chromium not found in standard locations.")
        print("Please make sure Google Chrome or Chromium is installed.")

def main():
    """Main entry point for the application."""
    print("🚀 Starting Alt Text Generator...")
    setup_environment()
    create_ui()

if __name__ == "__main__":
    main() 