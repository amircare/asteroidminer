#!/usr/bin/env python3
"""
Asteroid Miner Launcher
Checks dependencies and launches the game
"""
import subprocess
import sys
import os

def check_python_version():
    """Check if Python version is compatible"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(f"Error: Python 3.8 or higher required. You have {version.major}.{version.minor}.{version.micro}")
        return False
    print(f"✓ Python {version.major}.{version.minor}.{version.micro} detected")
    return True

def install_requirements():
    """Install required packages"""
    print("\nChecking dependencies...")
    try:
        import pygame
        print(f"✓ pygame {pygame.version.ver} already installed")
        return True
    except ImportError:
        print("Installing pygame...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
            print("✓ Dependencies installed successfully")
            return True
        except subprocess.CalledProcessError:
            print("Error: Failed to install dependencies")
            print("Please run manually: pip install -r requirements.txt")
            return False

def launch_game():
    """Launch the main game"""
    print("\nLaunching Asteroid Miner...")
    print("(Press ESC in-game to return to menu, or close the window to exit)")
    print()
    try:
        import main
        main.main()
        return True
    except KeyboardInterrupt:
        print("\nGame interrupted by user")
        return True
    except Exception as e:
        print(f"\nError launching game: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("ASTEROID MINER LAUNCHER")
    print("=" * 50)
    
    if not check_python_version():
        input("\nPress Enter to exit...")
        sys.exit(1)
    
    if not install_requirements():
        input("\nPress Enter to exit...")
        sys.exit(1)
    
    launch_game()
