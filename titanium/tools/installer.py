import os
import sys
import subprocess
import winreg
from pathlib import Path
from typing import Dict, Any

APP_NAME = "Titanium"
DESCRIPTION = "Titanium AI Virtual Assistant for Windows"

class WindowsInstaller:
    """Manages Windows system installation:
    - Start Menu Shortcut (available when searching 'Titanium' in Windows)
    - Windows Task Manager Startup App (autostart on reboot)
    - Desktop Shortcut
    """

    @staticmethod
    def get_paths() -> Dict[str, Path]:
        root_dir = Path(__file__).resolve().parent.parent.parent
        pythonw_exe = root_dir / "venv" / "Scripts" / "pythonw.exe"
        if not pythonw_exe.exists():
            pythonw_exe = Path(sys.executable).parent / "pythonw.exe"
            if not pythonw_exe.exists():
                pythonw_exe = Path(sys.executable)

        main_py = root_dir / "main.py"
        icon_path = root_dir / "titanium.ico"

        appdata = Path(os.environ.get("APPDATA", ""))
        userprofile = Path(os.environ.get("USERPROFILE", ""))

        start_menu_lnk = appdata / "Microsoft" / "Windows" / "Start Menu" / "Programs" / f"{APP_NAME}.lnk"
        startup_lnk = appdata / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup" / f"{APP_NAME}.lnk"
        desktop_lnk = userprofile / "Desktop" / f"{APP_NAME}.lnk"

        return {
            "root_dir": root_dir,
            "pythonw_exe": pythonw_exe,
            "main_py": main_py,
            "icon_path": icon_path,
            "start_menu_lnk": start_menu_lnk,
            "startup_lnk": startup_lnk,
            "desktop_lnk": desktop_lnk,
        }

    @classmethod
    def create_shortcut(cls, target_lnk: Path) -> bool:
        """Creates a Windows .lnk shortcut pointing to pythonw.exe main.py with the Titanium icon."""
        paths = cls.get_paths()
        target_lnk.parent.mkdir(parents=True, exist_ok=True)

        ps_script = f"""
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut('{str(target_lnk)}')
$Shortcut.TargetPath = '{str(paths["pythonw_exe"])}'
$Shortcut.Arguments = '"{str(paths["main_py"])}"'
$Shortcut.WorkingDirectory = '{str(paths["root_dir"])}'
$Shortcut.IconLocation = '{str(paths["icon_path"])},0'
$Shortcut.Description = '{DESCRIPTION}'
$Shortcut.WindowStyle = 1
$Shortcut.Save()
"""
        try:
            res = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
                capture_output=True,
                text=True
            )
            return target_lnk.exists()
        except Exception as e:
            print(f"[Installer] Error creating shortcut {target_lnk}: {e}")
            return False

    @classmethod
    def register_registry_startup(cls) -> bool:
        """Registers in HKCU Run registry so it appears in Task Manager > Startup Apps tab."""
        paths = cls.get_paths()
        cmd = f'"{paths["pythonw_exe"]}" "{paths["main_py"]}"'
        try:
            reg_key = winreg.HKEY_CURRENT_USER
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            with winreg.OpenKey(reg_key, key_path, 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
            return True
        except Exception as e:
            print(f"[Installer] Error writing Run registry: {e}")
            return False

    @classmethod
    def unregister_registry_startup(cls) -> bool:
        try:
            reg_key = winreg.HKEY_CURRENT_USER
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            with winreg.OpenKey(reg_key, key_path, 0, winreg.KEY_SET_VALUE) as key:
                winreg.DeleteValue(key, APP_NAME)
            return True
        except Exception:
            return False

    @classmethod
    def install(cls) -> Dict[str, Any]:
        """Installs Titanium into Windows (Start Menu, Task Manager Startup, Desktop)."""
        paths = cls.get_paths()
        
        # 1. Create Start Menu Shortcut
        start_ok = cls.create_shortcut(paths["start_menu_lnk"])

        # 2. Register Startup App (both Registry and Startup folder for 100% reliability)
        reg_ok = cls.register_registry_startup()
        startup_ok = cls.create_shortcut(paths["startup_lnk"])

        # 3. Create Desktop Shortcut
        desktop_ok = cls.create_shortcut(paths["desktop_lnk"])

        # 4. Refresh Windows Icon Cache so high-res icon reflects immediately
        try:
            subprocess.run(["ie4uinit.exe", "-show"], capture_output=True, timeout=5)
        except Exception:
            pass

        success = start_ok and (reg_ok or startup_ok)
        return {
            "success": success,
            "start_menu": start_ok,
            "task_manager_startup": reg_ok,
            "startup_folder": startup_ok,
            "desktop": desktop_ok,
            "message": "Titanium successfully installed! Available in Start Menu and Task Manager Startup."
        }

    @classmethod
    def is_installed(cls) -> bool:
        paths = cls.get_paths()
        return paths["start_menu_lnk"].exists()
