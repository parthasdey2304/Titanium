import os
import subprocess
import winreg
from pathlib import Path
from typing import Dict, List, Optional, Any

COMMON_PROTOCOL_APPS = {
    "calculator": "calc:",
    "calc": "calc:",
    "settings": "ms-settings:",
    "windows settings": "ms-settings:",
    "store": "ms-windows-store:",
    "camera": "microsoft.windows.camera:",
    "clock": "ms-clock:",
    "alarms": "ms-clock:",
    "mail": "mailto:",
    "spotify": "spotify:",
    "notepad": "notepad.exe",
    "cmd": "cmd.exe",
    "powershell": "powershell.exe",
    "explorer": "explorer.exe",
    "file explorer": "explorer.exe",
    "task manager": "taskmgr.exe",
    "chrome": "chrome.exe",
    "edge": "msedge.exe",
    "firefox": "firefox.exe",
    "vscode": "code.cmd",
    "code": "code.cmd",
}

class WindowsAppLauncher:
    """Discovers and launches Windows desktop applications and URI schemes."""

    @staticmethod
    def get_start_menu_apps() -> Dict[str, str]:
        """Scans Start Menu folders for .lnk shortcuts."""
        paths = [
            Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs",
            Path(os.environ.get("PROGRAMDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
        ]
        apps = {}
        for base in paths:
            if base.exists():
                for lnk in base.rglob("*.lnk"):
                    apps[lnk.stem.lower()] = str(lnk)
        return apps

    @staticmethod
    def get_registered_app_paths() -> Dict[str, str]:
        """Scans Registry App Paths for registered .exe names."""
        app_paths = {}
        reg_keys = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths")
        ]
        for root_key, subkey_path in reg_keys:
            try:
                with winreg.OpenKey(root_key, subkey_path) as key:
                    count, _, _ = winreg.QueryInfoKey(key)
                    for i in range(count):
                        try:
                            app_name = winreg.EnumKey(key, i)
                            with winreg.OpenKey(key, app_name) as app_key:
                                exe_path, _ = winreg.QueryValueEx(app_key, "")
                                if exe_path:
                                    clean_name = app_name.lower().replace(".exe", "")
                                    app_paths[clean_name] = exe_path
                        except Exception:
                            continue
            except Exception:
                continue
        return app_paths

    @classmethod
    def launch_app(cls, app_name: str) -> Dict[str, Any]:
        """Attempts to launch an application by name or query."""
        query = app_name.lower().strip()
        
        # 1. Check known protocol / executable map
        if query in COMMON_PROTOCOL_APPS:
            target = COMMON_PROTOCOL_APPS[query]
            try:
                os.startfile(target)
                return {"status": "success", "message": f"Successfully launched {app_name} via {target}"}
            except Exception as e:
                pass

        # 2. Check registered App Paths in registry
        app_paths = cls.get_registered_app_paths()
        if query in app_paths:
            try:
                os.startfile(app_paths[query])
                return {"status": "success", "message": f"Successfully launched {app_name}"}
            except Exception as e:
                pass

        # 3. Fuzzy search start menu shortcuts
        start_apps = cls.get_start_menu_apps()
        for name, path in start_apps.items():
            if query in name:
                try:
                    os.startfile(path)
                    return {"status": "success", "message": f"Successfully launched {name}"}
                except Exception as e:
                    pass

        # 4. Fallback to startfile directly
        try:
            os.startfile(app_name)
            return {"status": "success", "message": f"Opened {app_name}"}
        except Exception as e:
            return {"status": "error", "message": f"Could not find or open application '{app_name}': {str(e)}"}
