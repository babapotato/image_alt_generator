@echo off

:: Create and activate virtual environment
python -m venv build_venv
call build_venv\Scripts\activate.bat

:: Install build requirements
pip install -r build_requirements.txt

:: Create the executable
pyinstaller --name="Alt Text Generator" ^
           --windowed ^
           --onefile ^
           --add-data "config.py;." ^
           --add-data ".env;." ^
           --add-data "update_checker.py;." ^
           --icon="icon.ico" ^
           run_app.py

:: Cleanup
deactivate
rmdir /s /q build_venv
rmdir /s /q build
del "Alt Text Generator.spec"

echo ✅ Build complete! The executable is in the dist folder.
pause 