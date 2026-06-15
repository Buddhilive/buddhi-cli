#!/usr/bin/env python3
"""
Release and Publish Script for Buddhi AI CLI.
Handles cleaning, PEP-517 building, twine checks, and secure uploads to PyPI/TestPyPI.
"""

import argparse
import os
import re
import shutil
import subprocess
import sys

# ANSI Escape Sequences for Gorgeous Console Output
COLOR_BLUE = "\033[94m"
COLOR_GREEN = "\033[92m"
COLOR_YELLOW = "\033[93m"
COLOR_RED = "\033[91m"
COLOR_BOLD = "\033[1m"
COLOR_RESET = "\033[0m"


def print_info(message):
    print(f"{COLOR_BLUE}{COLOR_BOLD}[INFO]{COLOR_RESET} {message}")


def print_success(message):
    print(f"{COLOR_GREEN}{COLOR_BOLD}[SUCCESS]{COLOR_RESET} {message}")


def print_warning(message):
    print(f"{COLOR_YELLOW}{COLOR_BOLD}[WARNING]{COLOR_RESET} {message}")


def print_error(message):
    print(f"{COLOR_RED}{COLOR_BOLD}[ERROR]{COLOR_RESET} {message}")


def check_working_dir():
    """Verify that the script is run from the project root."""
    if not os.path.exists("pyproject.toml"):
        print_error("This script must be executed from the project root (where pyproject.toml is located).")
        sys.exit(1)


def get_package_version():
    """Extract the current version from pyproject.toml."""
    try:
        with open("pyproject.toml", "r", encoding="utf-8") as f:
            content = f.read()
        match = re.search(r'^version\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
        if match:
            return match.group(1)
        # Check inside [project] section specifically if not found above
        match_project = re.search(r'\[project\][\s\S]*?version\s*=\s*["\']([^"\']+)["\']', content)
        if match_project:
            return match_project.group(1)
        
        print_error("Could not parse version from pyproject.toml.")
        sys.exit(1)
    except Exception as e:
        print_error(f"Failed to read pyproject.toml: {e}")
        sys.exit(1)


def clean_dist():
    """Remove build and dist directories to ensure clean packaging."""
    print_info("Cleaning previous build and distribution files...")
    dirs_to_clean = ["build", "dist", "buddhi_ai.egg-info", "buddhi_ai_cli.egg-info"]
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            try:
                shutil.rmtree(dir_name)
                print_success(f"Removed '{dir_name}' directory.")
            except Exception as e:
                print_warning(f"Could not completely remove '{dir_name}': {e}")


def build_package():
    """Build the source and wheel distributions using standard python build module."""
    print_info("Building package distribution archives...")
    try:
        # Use uv run if uv is present, otherwise fallback to python -m build
        build_command = [sys.executable, "-m", "build"]
        if shutil.which("uv"):
            build_command = ["uv", "run", "python", "-m", "build"]
            
        print_info(f"Executing: {' '.join(build_command)}")
        result = subprocess.run(build_command, capture_output=False, check=True)
        if result.returncode == 0:
            print_success("Package distributions built successfully.")
        else:
            print_error("Build failed.")
            sys.exit(1)
    except subprocess.CalledProcessError as e:
        print_error(f"Error during package build: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print_error("The 'build' package is not installed. Please run: pip install build")
        sys.exit(1)


def verify_package():
    """Verify built package distributions using twine check."""
    print_info("Validating distribution archives using twine check...")
    if not os.path.exists("dist") or not os.listdir("dist"):
        print_error("No distribution files found in dist/ directory.")
        sys.exit(1)
        
    try:
        twine_command = [sys.executable, "-m", "twine", "check", "dist/*"]
        if shutil.which("uv"):
            twine_command = ["uv", "run", "twine", "check", "dist/*"]
            
        print_info(f"Executing: {' '.join(twine_command)}")
        
        # We need shell=True on Windows because of glob expansion (dist/*)
        use_shell = os.name == 'nt'
        result = subprocess.run(
            " ".join(twine_command) if use_shell else twine_command, 
            shell=use_shell,
            check=True
        )
        if result.returncode == 0:
            print_success("Twine validation checks passed. Package is ready for release!")
        else:
            print_error("Twine validation checks failed. Please fix package metadata.")
            sys.exit(1)
    except subprocess.CalledProcessError as e:
        print_error(f"Error during twine verification: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print_error("The 'twine' package is not installed. Please run: pip install twine")
        sys.exit(1)


def publish_package(use_test_pypi=False, dry_run=False):
    """Publish distribution packages to PyPI or TestPyPI."""
    repository = "testpypi" if use_test_pypi else "pypi"
    repo_url = "https://test.pypi.org/legacy/" if use_test_pypi else "https://upload.pypi.org/legacy/"
    
    print_info(f"Target repository: {COLOR_BOLD}{repository.upper()}{COLOR_RESET} ({repo_url})")
    
    if dry_run:
        print_warning("Dry-run active. Skipping upload phase.")
        return

    # Security reminder
    print_warning("PyPI recommends using API Tokens for secure publishing.")
    print_warning("  - Username: __token__")
    print_warning("  - Password: pypi-YOUR_TOKEN_STRING")
    print()

    # User confirmation
    confirm = input(f"Are you sure you want to upload version {COLOR_BOLD}{get_package_version()}{COLOR_RESET} to {COLOR_BOLD}{repository.upper()}{COLOR_RESET}? [y/N]: ")
    if confirm.lower() not in ["y", "yes"]:
        print_warning("Upload cancelled by user.")
        return

    try:
        upload_command = [sys.executable, "-m", "twine", "upload"]
        if use_test_pypi:
            upload_command += ["--repository", "testpypi"]
        upload_command += ["dist/*"]
        
        if shutil.which("uv"):
            # Put uv run in front of twine upload command
            uv_command = ["uv", "run", "twine", "upload"]
            if use_test_pypi:
                uv_command += ["--repository", "testpypi"]
            uv_command += ["dist/*"]
            upload_command = uv_command

        print_info(f"Executing: {' '.join(upload_command)}")
        
        use_shell = os.name == 'nt'
        subprocess.run(
            " ".join(upload_command) if use_shell else upload_command,
            shell=use_shell,
            check=True
        )
        print_success(f"Package successfully published to {repository.upper()}!")
    except subprocess.CalledProcessError as e:
        print_error(f"Error uploading package via twine: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Guided release and publishing pipeline for Buddhi AI CLI."
    )
    parser.add_argument(
        "--test-pypi",
        action="store_true",
        help="Upload the package to TestPyPI instead of the official production PyPI."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Clean, build, and run validation checks but do not upload to PyPI."
    )
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Skip cleaning and building; upload the existing archives in dist/ directory directly."
    )
    args = parser.parse_args()

    check_working_dir()
    version = get_package_version()
    
    print(f"\n{COLOR_GREEN}{COLOR_BOLD}=== Buddhi AI CLI Publisher (v{version}) ==={COLOR_RESET}\n")

    if not args.skip_build:
        clean_dist()
        build_package()
        
    verify_package()
    publish_package(use_test_pypi=args.test_pypi, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
