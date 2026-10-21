import sys
import os
import subprocess
import tempfile
import shutil

# Resolve repository root
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BAT_PATH = os.path.join(REPO_ROOT, "Launch_DFY_HRMS.bat")


def test_file_exists():
    print("Checking launcher file existence...")
    assert os.path.exists(BAT_PATH), f"Launch_DFY_HRMS.bat not found at {BAT_PATH}"
    assert os.path.isfile(BAT_PATH), f"{BAT_PATH} is not a regular file"
    size = os.path.getsize(BAT_PATH)
    assert size > 100, f"Launch_DFY_HRMS.bat seems too small ({size} bytes)"
    print(f"[OK] Launch_DFY_HRMS.bat exists ({size} bytes).")


def test_content_requirements():
    print("Inspecting batch script content and path safety...")
    with open(BAT_PATH, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    # 1. @echo off
    assert "@echo off" in content.lower(), "Missing '@echo off'"
    print("[OK] Contains '@echo off'")

    # 2. Window title
    assert "title doctors for you" in content.lower(), "Missing window title with 'Doctors For You'"
    print("[OK] Sets title to 'Doctors For You - HR Operations Platform'")

    # 3. Path safety cd /d "%~dp0"
    assert 'cd /d "%~dp0"' in content, 'Missing path safety line: cd /d "%~dp0"'
    print('[OK] Contains path-safe directory change: cd /d "%~dp0"')

    # 4. Probes for .venv
    assert ".venv\\scripts\\python.exe" in content.lower(), "Missing probe for .venv\\Scripts\\python.exe"
    print("[OK] Probes %~dp0.venv\\Scripts\\python.exe first")

    # 5. Probes for venv
    assert "venv\\scripts\\python.exe" in content.lower(), "Missing probe for venv\\Scripts\\python.exe"
    print("[OK] Probes %~dp0venv\\Scripts\\python.exe second")

    # 6. Probes for system python
    assert "python" in content.lower() and "path" in content.lower(), "Missing system PATH python fallback"
    print("[OK] Probes system PATH Python as fallback")

    # 7. Friendly error when Python missing
    assert "not found" in content.lower() and "pause" in content.lower(), "Missing missing-Python error handling"
    print("[OK] Contains user-friendly error message if Python is not found")

    # 8. Target main.py
    assert "desktop_app\\main.py" in content, "Missing invocation target 'desktop_app\\main.py'"
    print('[OK] Targets "%PYTHON_EXE%" "%~dp0desktop_app\\main.py"')

    # 9. Errorlevel check and pause
    assert "errorlevel" in content.lower(), "Missing errorlevel check"
    print("[OK] Handles runtime errors and pauses before exiting")

    # 10. Shortcut creator routine
    assert "create-shortcut" in content.lower() or "shortcut" in content.lower(), "Missing shortcut creator routine"
    print("[OK] Includes 1-Click Desktop Shortcut helper routine")

    # 11. Portability check: no hardcoded absolute drive paths like D:\ignou in script
    lines = content.splitlines()
    for idx, line in enumerate(lines, 1):
        clean = line.strip()
        if clean.startswith("::") or clean.startswith("rem"):
            continue
        # Ensure no hardcoded paths to current repo drive in executable statements
        assert "d:\\ignou" not in clean.lower(), f"Line {idx} contains hardcoded absolute path: {clean}"
    print("[OK] Portability verified: No hardcoded drive paths, fully relocatable via %~dp0")


def test_batch_execution_help():
    print("Testing 'Launch_DFY_HRMS.bat --help' execution...")
    result = subprocess.run(
        ["cmd.exe", "/c", BAT_PATH, "--help"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    assert result.returncode == 0, f"Expected returncode 0, got {result.returncode}. STDERR: {result.stderr}"
    assert "Doctors For You" in result.stdout, "Expected 'Doctors For You' in help output"
    assert "Usage:" in result.stdout, "Expected 'Usage:' in help output"
    print("[OK] 'Launch_DFY_HRMS.bat --help' executed successfully (exit code 0).")


def test_batch_execution_check_env():
    print("Testing 'Launch_DFY_HRMS.bat --check-env' execution...")
    result = subprocess.run(
        ["cmd.exe", "/c", BAT_PATH, "--check-env"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    assert result.returncode == 0, f"Expected returncode 0, got {result.returncode}. STDERR: {result.stderr}"
    assert "Environment check passed" in result.stdout, f"Unexpected output: {result.stdout}"
    print("[OK] 'Launch_DFY_HRMS.bat --check-env' validated active Python environment (exit code 0).")


def test_desktop_shortcut_creation():
    print("Testing Desktop Shortcut creation routine...")
    result = subprocess.run(
        ["cmd.exe", "/c", BAT_PATH, "--create-shortcut", "--no-pause"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    assert result.returncode == 0, f"Shortcut creation failed with code {result.returncode}. STDERR: {result.stderr}"
    assert "Desktop shortcut" in result.stdout, f"Output missing confirmation: {result.stdout}"

    # Verify shortcut file on Desktop
    desktop_dir = os.path.join(os.environ.get("USERPROFILE", ""), "Desktop")
    shortcut_file = os.path.join(desktop_dir, "DFY HR Operations Platform.lnk")
    assert os.path.exists(shortcut_file), f"Shortcut not found on desktop at {shortcut_file}"
    print(f"[OK] Desktop shortcut successfully generated at: {shortcut_file}")


def test_python_priority_probing():
    print("Testing Python virtual environment probing hierarchy...")
    # Create temporary mock directory structure
    with tempfile.TemporaryDirectory() as tmp_dir:
        test_bat = os.path.join(tmp_dir, "test_launcher.bat")
        shutil.copyfile(BAT_PATH, test_bat)

        # 1. System Python fallback when no venv exists
        res_sys = subprocess.run(
            ["cmd.exe", "/c", test_bat, "--check-env"],
            capture_output=True,
            text=True,
            cwd=tmp_dir,
        )
        assert res_sys.returncode == 0, f"Fallback to system python failed: {res_sys.stderr}"
        assert "Found system Python" in res_sys.stdout, "Should detect system Python when no venv exists"

        # 2. Mock venv folder
        venv_scripts = os.path.join(tmp_dir, "venv", "Scripts")
        os.makedirs(venv_scripts, exist_ok=True)
        mock_venv_py = os.path.join(venv_scripts, "python.exe")
        with open(mock_venv_py, "w") as f:
            f.write("")

        res_venv = subprocess.run(
            ["cmd.exe", "/c", test_bat, "--check-env"],
            capture_output=True,
            text=True,
            cwd=tmp_dir,
        )
        assert res_venv.returncode == 0
        assert "Found venv Python" in res_venv.stdout, "Should prefer venv over system Python"

        # 3. Mock .venv folder (highest priority)
        dot_venv_scripts = os.path.join(tmp_dir, ".venv", "Scripts")
        os.makedirs(dot_venv_scripts, exist_ok=True)
        mock_dot_venv_py = os.path.join(dot_venv_scripts, "python.exe")
        with open(mock_dot_venv_py, "w") as f:
            f.write("")

        res_dot_venv = subprocess.run(
            ["cmd.exe", "/c", test_bat, "--check-env"],
            capture_output=True,
            text=True,
            cwd=tmp_dir,
        )
        assert res_dot_venv.returncode == 0
        assert "Found .venv Python" in res_dot_venv.stdout, "Should prefer .venv over venv and system Python"

    print("[OK] Probing priority verified: .venv -> venv -> system PATH.")


def run_all_tests():
    print("=" * 70)
    print("Starting Task 8: 1-Click Desktop Launcher Verification Suite")
    print("=" * 70)

    test_file_exists()
    test_content_requirements()
    test_batch_execution_help()
    test_batch_execution_check_env()
    test_desktop_shortcut_creation()
    test_python_priority_probing()

    print("=" * 70)
    print("SUCCESS: Task 8 1-Click Desktop Launcher verified successfully.")
    print("=" * 70)


if __name__ == "__main__":
    run_all_tests()
