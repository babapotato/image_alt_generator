#!/bin/bash

# Create and activate virtual environment
python3 -m venv build_venv
source build_venv/bin/activate

# Install build requirements
pip install -r build_requirements.txt

# Create the executable
pyinstaller --name="Alt Text Generator" \
            --windowed \
            --onefile \
            --add-data "config.py:." \
            --add-data ".env:." \
            --add-data "update_checker.py:." \
            --icon="icon.ico" \
            run_app.py

# Cleanup
deactivate
rm -rf build_venv
rm -rf build
rm -rf "Alt Text Generator.spec"

echo "✅ Build complete! The executable is in the dist folder." 