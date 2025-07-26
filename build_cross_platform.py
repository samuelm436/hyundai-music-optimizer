#!/usr/bin/env python3
"""
Cross-Platform Build Script for Hyundai Music Optimizer
Builds executables for Windows and Linux with proper icons
"""

import subprocess
import sys
import os
import shutil
import platform
import argparse

def install_dependencies():
    """Install required dependencies"""
    deps = ["pyinstaller", "Pillow"]
    for dep in deps:
        try:
            __import__(dep.lower().replace("-", "_"))
        except ImportError:
            print(f"Installing {dep}...")
            subprocess.run([sys.executable, "-m", "pip", "install", dep], check=True)

def build_cross_platform():
    """Build for both Windows and Linux"""
    print("🌍 Cross-Platform Build for Hyundai Music Optimizer")
    print("=" * 60)
    
    # Install dependencies
    install_dependencies()
    
    # Prepare icons
    prepare_icons()
    
    current_platform = platform.system().lower()
    
    if current_platform == "linux":
        print("🐧 Running on Linux - Building Linux executable")
        success_linux = build_for_platform("linux")
        
        print("\n💡 To build for Windows, run this script on a Windows machine")
        print("   or use Wine with PyInstaller")
        
        return success_linux
        
    elif current_platform == "windows":
        print("🪟 Running on Windows - Building Windows executable")
        success_windows = build_for_platform("windows")
        
        print("\n💡 To build for Linux, run this script on a Linux machine")
        print("   or use WSL (Windows Subsystem for Linux)")
        
        return success_windows
    
    else:
        print(f"❌ Unsupported platform: {current_platform}")
        return False

def prepare_icons():
    """Prepare icons for different platforms"""
    try:
        from PIL import Image
        
        if not os.path.exists('hyundai_music_icon.ico'):
            print("🎨 Converting PNG to ICO for Windows...")
            img = Image.open('hyundai music icon.png')
            img.save('hyundai_music_icon.ico', format='ICO', sizes=[(16,16), (32,32), (48,48), (64,64)])
            print("✅ ICO icon created")
        
        print("✅ Icons prepared")
        return True
        
    except Exception as e:
        print(f"❌ Error preparing icons: {e}")
        return False

def build_for_platform(target_platform):
    """Build executable for specific platform"""
    print(f"\n🔨 Building for {target_platform.upper()}")
    
    # PyInstaller command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        "--name", "HyundaiMusicOptimizer",
        "--clean"  # Clean cache
    ]
    
    # Platform-specific settings
    if target_platform == "windows":
        cmd.extend(["--add-data", "config.py.example;."])
        cmd.extend(["--add-data", "hyundai music icon.png;."])
        if os.path.exists('hyundai_music_icon.ico'):
            cmd.extend(["--icon", "hyundai_music_icon.ico"])
    else:  # Linux
        cmd.extend(["--add-data", "config.py.example:."])
        cmd.extend(["--add-data", "hyundai music icon.png:."])
    
    # Hidden imports
    hidden_imports = [
        "PyQt5.QtCore", "PyQt5.QtGui", "PyQt5.QtWidgets",
        "spotipy", "mutagen", "requests", "shutil", "json", "datetime"
    ]
    
    for imp in hidden_imports:
        cmd.extend(["--hidden-import", imp])
    
    cmd.append("main.py")
    
    # Build
    try:
        print(f"Running: {' '.join(cmd[:5])}... (truncated)")
        result = subprocess.run(cmd, check=True)
        print("✅ Build successful!")
        
        # Create release package
        create_release_package(target_platform)
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Build failed: {e}")
        return False

def create_release_package(target_platform):
    """Create release package"""
    release_dir = f"release_{target_platform}"
    
    # Clean and create directory
    if os.path.exists(release_dir):
        shutil.rmtree(release_dir)
    os.makedirs(release_dir)
    
    # Copy executable
    exe_name = "HyundaiMusicOptimizer.exe" if target_platform == "windows" else "HyundaiMusicOptimizer"
    exe_path = os.path.join("dist", exe_name)
    
    if os.path.exists(exe_path):
        shutil.copy2(exe_path, release_dir)
        
        # Make executable on Linux
        if target_platform == "linux":
            os.chmod(os.path.join(release_dir, exe_name), 0o755)
        
        print(f"✅ Copied {exe_name}")
    
    # Copy documentation
    for file in ["README.md", "config.py.example", "requirements.txt"]:
        if os.path.exists(file):
            shutil.copy2(file, release_dir)
    
    # Create setup instructions
    setup_content = f"""# Hyundai Music Optimizer - {target_platform.title()} Release

## Quick Setup:
1. Copy `config.py.example` to `config.py`
2. Get Spotify API credentials from https://developer.spotify.com/dashboard/
3. Edit `config.py` with your credentials
4. Run {'HyundaiMusicOptimizer.exe' if target_platform == 'windows' else './HyundaiMusicOptimizer'}

## Features:
- Automatic album detection
- Spotify metadata integration
- Album cover embedding
- Backup system
- Cross-platform support

See README.md for detailed instructions.
"""
    
    with open(os.path.join(release_dir, "SETUP.txt"), "w") as f:
        f.write(setup_content)
    
    # Create ZIP
    zip_name = f"HyundaiMusicOptimizer_{target_platform}"
    shutil.make_archive(zip_name, 'zip', release_dir)
    
    # Show results
    size = os.path.getsize(f"{zip_name}.zip") / (1024 * 1024)
    print(f"📦 Created {zip_name}.zip ({size:.1f} MB)")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build Hyundai Music Optimizer")
    parser.add_argument("--platform", choices=["windows", "linux", "auto"], 
                       default="auto", help="Target platform")
    
    args = parser.parse_args()
    
    if args.platform == "auto":
        success = build_cross_platform()
    else:
        success = build_for_platform(args.platform)
    
    if success:
        print("\n🎉 Build completed successfully!")
        print("\n📋 Upload to GitHub Releases:")
        print("1. Go to https://github.com/samuelm436/hyundai-music-optimizer/releases")
        print("2. Click 'Create a new release'")
        print("3. Upload the .zip files")
    else:
        sys.exit(1)
