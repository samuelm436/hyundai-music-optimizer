# Build Script for Hyundai Music Optimizer
# This script creates standalone executables for Windows and Linux

import subprocess
import sys
import os
import shutil
import platform

def prepare_icons():
    """Prepare icons for different platforms"""
    try:
        from PIL import Image
        
        # Convert PNG to ICO for Windows
        if not os.path.exists('hyundai_music_icon.ico'):
            img = Image.open('hyundai music icon.png')
            img.save('hyundai_music_icon.ico', format='ICO', sizes=[(16,16), (32,32), (48,48), (64,64)])
            print("✅ ICO icon created for Windows")
        
        # For Linux, we can use the PNG directly
        print("✅ PNG icon ready for Linux")
        return True
        
    except ImportError:
        print("❌ Pillow not installed. Installing...")
        subprocess.run([sys.executable, "-m", "pip", "install", "Pillow"], check=True)
        return prepare_icons()
    except Exception as e:
        print(f"❌ Error preparing icons: {e}")
        return False

def build_executable(target_platform=None):
    """Build standalone executable using PyInstaller"""
    
    if target_platform is None:
        target_platform = platform.system().lower()
    
    print(f"Building for platform: {target_platform}")
    
    # Prepare icons first
    if not prepare_icons():
        print("Warning: Continuing without custom icon")
    
    # Base command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",                    # Create single executable file
        "--windowed",                   # Hide console window (GUI app)
        "--name", "HyundaiMusicOptimizer",  # Executable name
        "--add-data", "config.py.example;." if target_platform == "windows" else "config.py.example:.",
        "--hidden-import", "PyQt5.QtCore",
        "--hidden-import", "PyQt5.QtGui", 
        "--hidden-import", "PyQt5.QtWidgets",
        "--hidden-import", "spotipy",
        "--hidden-import", "mutagen",
        "--hidden-import", "requests",
        "--hidden-import", "shutil",
        "--hidden-import", "json",
        "--hidden-import", "datetime"
    ]
    
    # Add icon based on platform
    if target_platform == "windows":
        if os.path.exists('hyundai_music_icon.ico'):
            cmd.extend(["--icon", "hyundai_music_icon.ico"])
            cmd.extend(["--add-data", "hyundai music icon.png;."])
        print("🪟 Building Windows executable...")
    else:  # Linux/Unix
        if os.path.exists('hyundai music icon.png'):
            cmd.extend(["--add-data", "hyundai music icon.png:."])
        print("🐧 Building Linux executable...")
    
    # Add main script
    cmd.append("main.py")
    
    print(f"Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✅ Build successful!")
        if result.stdout:
            print("Build output:", result.stdout[-500:])  # Show last 500 chars
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Build failed: {e}")
        if e.stderr:
            print(f"Error output: {e.stderr}")
        return False

def create_release_package(target_platform=None):
    """Create release package with executable and necessary files"""
    
    if target_platform is None:
        target_platform = platform.system().lower()
    
    # Create release directory
    release_dir = f"release_{target_platform}"
    if os.path.exists(release_dir):
        shutil.rmtree(release_dir)
    os.makedirs(release_dir)
    
    # Copy executable
    if target_platform == "windows":
        exe_name = "HyundaiMusicOptimizer.exe"
    else:
        exe_name = "HyundaiMusicOptimizer"
    
    exe_path = os.path.join("dist", exe_name)
    
    if os.path.exists(exe_path):
        shutil.copy2(exe_path, release_dir)
        print(f"✅ Copied executable to {release_dir}/{exe_name}")
        
        # Make executable on Linux
        if target_platform != "windows":
            os.chmod(os.path.join(release_dir, exe_name), 0o755)
            print("✅ Made executable file executable on Linux")
    else:
        print(f"❌ Executable not found at {exe_path}")
        return False
    
    # Copy necessary files
    files_to_copy = [
        "README.md",
        "config.py.example",
        "requirements.txt"
    ]
    
    for file in files_to_copy:
        if os.path.exists(file):
            shutil.copy2(file, release_dir)
            print(f"✅ Copied {file} to release directory")
    
    # Create platform-specific setup instructions
    if target_platform == "windows":
        setup_instructions = """# Hyundai Music Optimizer - Windows Release

## Quick Start:
1. Copy config.py.example to config.py
2. Edit config.py with your Spotify API credentials
3. Double-click HyundaiMusicOptimizer.exe to run

## Getting Spotify API Credentials:
1. Go to https://developer.spotify.com/dashboard/
2. Create a new app
3. Copy Client ID and Client Secret to config.py

## Features:
- Automatic album detection and processing
- High-quality album cover embedding
- Backup system for safety
- Professional metadata organization

For detailed instructions, see README.md
"""
    else:
        setup_instructions = """# Hyundai Music Optimizer - Linux Release

## Quick Start:
1. Copy config.py.example to config.py
2. Edit config.py with your Spotify API credentials
3. Open terminal and run: ./HyundaiMusicOptimizer

## Getting Spotify API Credentials:
1. Go to https://developer.spotify.com/dashboard/
2. Create a new app
3. Copy Client ID and Client Secret to config.py

## Requirements:
- No additional dependencies needed (all bundled)
- Works on most Linux distributions

## Features:
- Automatic album detection and processing
- High-quality album cover embedding
- Backup system for safety
- Professional metadata organization

For detailed instructions, see README.md
"""
    
    with open(os.path.join(release_dir, "SETUP.txt"), "w") as f:
        f.write(setup_instructions)
    
    # Create a ZIP file for easy distribution
    zip_name = f"HyundaiMusicOptimizer_{target_platform}"
    shutil.make_archive(zip_name, 'zip', release_dir)
    print(f"✅ Created {zip_name}.zip for distribution")
    
    print(f"\n📦 Release package created in {release_dir}/ directory")
    print("Contents:")
    for item in os.listdir(release_dir):
        size = os.path.getsize(os.path.join(release_dir, item))
        size_mb = size / (1024 * 1024)
        print(f"  - {item} ({size_mb:.1f} MB)")
    
    return True

def build_for_platform(target_platform):
    """Build for a specific platform"""
    print(f"\n🔨 Building Hyundai Music Optimizer for {target_platform.upper()}")
    print("=" * 50)
    
    if build_executable(target_platform):
        if create_release_package(target_platform):
            print(f"\n✅ {target_platform.upper()} build completed successfully!")
            return True
    
    print(f"\n❌ {target_platform.upper()} build failed!")
    return False

if __name__ == "__main__":
    print("🎵 === Hyundai Music Optimizer Build Script ===")
    print("This script creates standalone executables with icons\n")
    
    current_platform = platform.system().lower()
    if current_platform == "darwin":
        current_platform = "macos"
    
    success = build_for_platform(current_platform)
    
    if success:
        print(f"\n🎉 SUCCESS! Your {current_platform.upper()} executable is ready!")
        print("\nNext steps:")
        print("1. Test the executable in the release directory")
        print("2. Upload the .zip file to GitHub Releases")
        print("3. Share with users!")
        
        print(f"\n📁 Find your files in: release_{current_platform}/")
        print(f"📦 Distribution file: HyundaiMusicOptimizer_{current_platform}.zip")
    else:
        print(f"\n💥 Build failed for {current_platform}!")
        sys.exit(1)

def create_release_package():
    """Create release package with executable and necessary files"""
    
    # Create release directory
    release_dir = "release"
    if os.path.exists(release_dir):
        shutil.rmtree(release_dir)
    os.makedirs(release_dir)
    
    # Copy executable
    exe_name = "HyundaiMusicOptimizer.exe" if os.name == 'nt' else "HyundaiMusicOptimizer"
    exe_path = os.path.join("dist", exe_name)
    
    if os.path.exists(exe_path):
        shutil.copy2(exe_path, release_dir)
        print(f"Copied executable to {release_dir}/{exe_name}")
    
    # Copy necessary files
    files_to_copy = [
        "README.md",
        "config.py.example"
    ]
    
    for file in files_to_copy:
        if os.path.exists(file):
            shutil.copy2(file, release_dir)
            print(f"Copied {file} to release directory")
    
    # Create setup instructions
    setup_instructions = """# Hyundai Music Optimizer - Standalone Release

## Quick Start:
1. Copy config.py.example to config.py
2. Edit config.py with your Spotify API credentials
3. Run HyundaiMusicOptimizer.exe (Windows) or ./HyundaiMusicOptimizer (Linux)

## Getting Spotify API Credentials:
1. Go to https://developer.spotify.com/dashboard/
2. Create a new app
3. Copy Client ID and Client Secret to config.py

For detailed instructions, see README.md
"""
    
    with open(os.path.join(release_dir, "SETUP.txt"), "w") as f:
        f.write(setup_instructions)
    
    print(f"\nRelease package created in {release_dir}/ directory")
    print("Contents:")
    for item in os.listdir(release_dir):
        print(f"  - {item}")

if __name__ == "__main__":
    print("=== Hyundai Music Optimizer Build Script ===")
    
    if build_executable():
        create_release_package()
        print("\n✅ Build completed successfully!")
        print("\nNext steps:")
        print("1. Test the executable in the release/ directory")
        print("2. Create a ZIP file for distribution")
        print("3. Upload to GitHub Releases")
    else:
        print("\n❌ Build failed!")
        sys.exit(1)
