import os
import sys
import shutil
import platform
import subprocess
from pathlib import Path

def create_distribution():
    """Create distribution package for the application."""
    print("📦 Creating distribution package...")
    
    # Create dist directory
    dist_dir = Path("dist")
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    dist_dir.mkdir()
    
    # Create build directory
    build_dir = Path("build")
    if build_dir.exists():
        shutil.rmtree(build_dir)
    
    # Files to include
    files_to_copy = [
        "config.py",
        "alt_text_generator.py",
        "image_scraper.py",
        "ui.py",
        "run_app.py",
        "requirements.txt",
        "README.md",
        "update_checker.py"
    ]
    
    # Create package directory
    package_name = "Alt Text Generator"
    if platform.system() == "Windows":
        package_name += " (Windows)"
    else:
        package_name += " (Mac)"
    
    package_dir = dist_dir / package_name
    package_dir.mkdir()
    
    # Copy files
    print("📄 Copying files...")
    for file in files_to_copy:
        if Path(file).exists():
            shutil.copy2(file, package_dir)
    
    # Create empty .env file
    with open(package_dir / ".env", "w") as f:
        f.write("OPENAI_API_KEY=")
    
    # Create virtual environment
    print("🔧 Creating virtual environment...")
    venv_dir = package_dir / "venv"
    subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)
    
    # Install requirements
    print("📚 Installing dependencies...")
    pip_cmd = str(venv_dir / "Scripts" / "pip.exe") if platform.system() == "Windows" else str(venv_dir / "bin" / "pip")
    subprocess.run([pip_cmd, "install", "-r", "requirements.txt"], check=True)
    
    # Create launcher script
    if platform.system() == "Windows":
        with open(package_dir / "Start Alt Text Generator.bat", "w") as f:
            f.write('@echo off\n')
            f.write('cd "%~dp0"\n')
            f.write('venv\\Scripts\\python.exe run_app.py\n')
            f.write('pause\n')
    else:
        with open(package_dir / "Start Alt Text Generator.command", "w") as f:
            f.write('#!/bin/bash\n')
            f.write('cd "$(dirname "$0")"\n')
            f.write('./venv/bin/python run_app.py\n')
        # Make the launcher executable on Mac
        os.chmod(package_dir / "Start Alt Text Generator.command", 0o755)
    
    # Create zip file
    print("🗜️ Creating zip archive...")
    shutil.make_archive(str(dist_dir / package_name), 'zip', package_dir)
    
    print(f"✅ Distribution package created successfully in {dist_dir}")
    print(f"📝 The zip file is ready to share: {package_name}.zip")

if __name__ == "__main__":
    create_distribution() 