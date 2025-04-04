#!/usr/bin/env python
"""
InstaFlow Package Update Script

This script automates the process of updating and publishing the InstaFlow package to PyPI.
It performs the following steps:
1. Updates the version number in setup.py
2. Creates distribution packages
3. Uploads the packages to PyPI
"""

import os
import re
import sys
import subprocess
import argparse
from shutil import rmtree
from pathlib import Path

# Paths
SETUP_PY_PATH = 'setup.py'
DIST_DIR = 'dist'
BUILD_DIR = 'build'
EGG_INFO_DIR = 'instaflow.egg-info'

def update_version(version_string=None):
    """Update the version in setup.py."""
    if not os.path.exists(SETUP_PY_PATH):
        print(f"Error: {SETUP_PY_PATH} not found")
        return False
    
    with open(SETUP_PY_PATH, 'r') as f:
        content = f.read()
    
    # Find current version
    version_pattern = r"version=['\"]([^'\"]+)['\"]"
    match = re.search(version_pattern, content)
    
    if not match:
        print("Error: Could not find version pattern in setup.py")
        return False
    
    current_version = match.group(1)
    
    if not version_string:
        # Auto-increment patch version if no version provided
        try:
            major, minor, patch = map(int, current_version.split('.'))
            new_version = f"{major}.{minor}.{patch + 1}"
        except ValueError:
            print(f"Error: Could not parse current version {current_version}")
            return False
    else:
        new_version = version_string
    
    # Update setup.py
    new_content = re.sub(version_pattern, f'version="{new_version}"', content)
    
    with open(SETUP_PY_PATH, 'w') as f:
        f.write(new_content)
    
    print(f"Updated version from {current_version} to {new_version}")
    return True

def clean_build_dirs():
    """Remove old build directories."""
    dirs_to_clean = [DIST_DIR, BUILD_DIR, EGG_INFO_DIR]
    
    for dir_path in dirs_to_clean:
        if os.path.exists(dir_path):
            print(f"Removing {dir_path}...")
            rmtree(dir_path)
    
    print("Clean completed")

def build_package():
    """Build source and wheel distributions."""
    print("Building package distributions...")
    
    try:
        subprocess.check_call([sys.executable, "-m", "build"])
        print("Build successful")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error building package: {e}")
        return False

def upload_to_pypi(test=False, token=None):
    """Upload the distributions to PyPI."""
    if not os.path.exists(DIST_DIR) or not os.listdir(DIST_DIR):
        print("Error: No distribution files found to upload")
        return False
    
    print(f"Uploading to {'Test PyPI' if test else 'PyPI'}...")
    
    cmd = [sys.executable, "-m", "twine", "upload"]
    
    if test:
        cmd.extend(["--repository-url", "https://test.pypi.org/legacy/"])
    
    if token:
        cmd.extend(["-u", "__token__", "-p", token])
    
    cmd.append(f"{DIST_DIR}/*")
    
    try:
        # Using shell=True to expand the glob pattern
        subprocess.check_call(" ".join(cmd), shell=True)
        print("Upload successful")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error uploading package: {e}")
        return False

def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(description="Update and publish InstaFlow package")
    parser.add_argument("--version", help="Specify new version (default: auto-increment patch)")
    parser.add_argument("--test", action="store_true", help="Upload to Test PyPI instead of PyPI")
    parser.add_argument("--token", help="PyPI API token for authentication")
    parser.add_argument("--build-only", action="store_true", help="Only build package without uploading")
    parser.add_argument("--skip-clean", action="store_true", help="Skip cleaning old build directories")
    
    args = parser.parse_args()
    
    # Make sure we're in the project root directory
    script_dir = Path(__file__).parent.resolve()
    os.chdir(script_dir)
    
    # Update version
    if not update_version(args.version):
        return 1
    
    # Clean old build artifacts
    if not args.skip_clean:
        clean_build_dirs()
    
    # Build package
    if not build_package():
        return 1
    
    # Upload to PyPI if not build-only
    if not args.build_only:
        if not upload_to_pypi(test=args.test, token=args.token):
            return 1
    
    print("Package update completed successfully!")
    return 0

if __name__ == "__main__":
    sys.exit(main())