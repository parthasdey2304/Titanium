import os
import sys
import platform
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any

CURRENT_OS = platform.system().lower() # 'windows', 'darwin' (macos), 'linux'

# Common system folders mapped across OSes
def get_user_directories() -> Dict[str, Path]:
    home = Path.home()
    dirs = {
        "home": home,
        "downloads": home / "Downloads",
        "documents": home / "Documents",
        "desktop": home / "Desktop",
        "pictures": home / "Pictures",
        "music": home / "Music",
        "videos": home / "Videos",
    }
    # Check for projects directory
    for p_candidate in [home / "projects", home / "Projects", Path("D:/projects"), Path("C:/projects")]:
        if p_candidate.exists():
            dirs["projects"] = p_candidate
            break
    return dirs

class SystemNavigator:
    """Universal Cross-Platform (Windows, macOS, Linux) System Navigator:
    - Application discovery & launching
    - File & folder explorer navigation
    - Native System Settings launcher
    """

    @staticmethod
    def get_os() -> str:
        return CURRENT_OS

    # =========================================================================
    # 1. SETTINGS APP LAUNCHER
    # =========================================================================
    @classmethod
    def open_settings(cls) -> Dict[str, Any]:
        """Opens native System Settings on Windows, macOS, or Linux."""
        try:
            if CURRENT_OS == "windows":
                os.startfile("ms-settings:")
                return {"status": "success", "message": "Opened Windows Settings"}
            elif CURRENT_OS == "darwin": # macOS
                subprocess.Popen(["open", "/System/Applications/System Settings.app"])
                return {"status": "success", "message": "Opened macOS System Settings"}
            else: # Linux
                for cmd in ["gnome-control-center", "systemsettings5", "xfce4-settings-manager"]:
                    try:
                        subprocess.Popen([cmd])
                        return {"status": "success", "message": f"Opened Linux Settings via {cmd}"}
                    except FileNotFoundError:
                        continue
                subprocess.Popen(["xdg-open", "settings:"])
                return {"status": "success", "message": "Opened Linux Settings"}
        except Exception as e:
            return {"status": "error", "message": f"Could not open Settings: {e}"}

    # =========================================================================
    # 2. FILE & FOLDER EXPLORER
    # =========================================================================
    @classmethod
    def open_folder(cls, target: str) -> Dict[str, Any]:
        """Opens a folder in Windows Explorer, macOS Finder, or Linux File Manager."""
        user_dirs = get_user_directories()
        lower_target = target.lower().strip()

        target_path: Optional[Path] = None

        # Check keyword matches (e.g. 'downloads', 'documents', 'desktop', etc.)
        for name, p in user_dirs.items():
            if name in lower_target:
                target_path = p
                break

        # Check direct path
        if not target_path:
            p_obj = Path(target)
            if p_obj.exists() and p_obj.is_dir():
                target_path = p_obj

        if not target_path or not target_path.exists():
            # Fallback to home directory
            target_path = Path.home()

        try:
            if CURRENT_OS == "windows":
                os.startfile(str(target_path))
            elif CURRENT_OS == "darwin":
                subprocess.Popen(["open", str(target_path)])
            else:
                subprocess.Popen(["xdg-open", str(target_path)])
            return {"status": "success", "message": f"Opened folder: {target_path.name}"}
        except Exception as e:
            return {"status": "error", "message": f"Error opening folder: {e}"}

    @classmethod
    def open_file(cls, file_path_str: str) -> Dict[str, Any]:
        """Opens a file with default system handler."""
        path = Path(file_path_str)
        if not path.exists():
            # Search common folders for file by name
            for root_dir in [Path.home() / "Downloads", Path.home() / "Documents", Path.home() / "Desktop"]:
                candidates = list(root_dir.rglob(f"*{file_path_str}*"))
                if candidates:
                    path = candidates[0]
                    break

        if not path.exists():
            return {"status": "error", "message": f"File '{file_path_str}' not found on system."}

        try:
            if CURRENT_OS == "windows":
                os.startfile(str(path))
            elif CURRENT_OS == "darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
            return {"status": "success", "message": f"Opened file: {path.name}"}
        except Exception as e:
            return {"status": "error", "message": f"Error opening file: {e}"}

    # =========================================================================
    # 3. CROSS-PLATFORM APPLICATION DISCOVERY & LAUNCHING
    # =========================================================================
    @classmethod
    def list_installed_applications(cls) -> Dict[str, str]:
        """Discovers applications installed across Windows, macOS, or Linux."""
        apps: Dict[str, str] = {}

        if CURRENT_OS == "windows":
            # Registry App Paths
            try:
                import winreg
                for root_key in [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]:
                    try:
                        with winreg.OpenKey(root_key, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths") as k:
                            num, _, _ = winreg.QueryInfoKey(k)
                            for i in range(num):
                                try:
                                    name = winreg.EnumKey(k, i)
                                    with winreg.OpenKey(k, name) as sub:
                                        p, _ = winreg.QueryValueEx(sub, "")
                                        clean = name.lower().replace(".exe", "")
                                        apps[clean] = p
                                except Exception:
                                    continue
                    except Exception:
                        continue
            except ImportError:
                pass

            # Start Menu shortcuts
            for base in [
                Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs",
                Path(os.environ.get("PROGRAMDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
            ]:
                if base.exists():
                    for lnk in base.rglob("*.lnk"):
                        apps[lnk.stem.lower()] = str(lnk)

        elif CURRENT_OS == "darwin": # macOS
            for app_dir in [Path("/Applications"), Path("/System/Applications"), Path.home() / "Applications"]:
                if app_dir.exists():
                    for app in app_dir.glob("*.app"):
                        apps[app.stem.lower()] = str(app)

        else: # Linux
            for d in [Path("/usr/share/applications"), Path.home() / ".local/share/applications"]:
                if d.exists():
                    for f in d.glob("*.desktop"):
                        apps[f.stem.lower()] = str(f)

        return apps

    @classmethod
    def launch_app(cls, app_name: str) -> Dict[str, Any]:
        """Launches an application across Windows, macOS, or Linux."""
        query = app_name.lower().strip()

        # Special Case: Settings
        if "setting" in query:
            return cls.open_settings()

        # Special Case: Explorer / Finder
        if query in ["explorer", "finder", "file manager", "files"]:
            return cls.open_folder("home")

        # 1. Match known protocol apps
        if CURRENT_OS == "windows":
            from titanium.tools.app_launcher import COMMON_PROTOCOL_APPS
            if query in COMMON_PROTOCOL_APPS:
                try:
                    os.startfile(COMMON_PROTOCOL_APPS[query])
                    return {"status": "success", "message": f"Launched {app_name}"}
                except Exception:
                    pass

        # 2. Match discovered applications
        apps = cls.list_installed_applications()
        if query in apps:
            target = apps[query]
            try:
                if CURRENT_OS == "windows":
                    os.startfile(target)
                elif CURRENT_OS == "darwin":
                    subprocess.Popen(["open", target])
                else:
                    subprocess.Popen(["gtk-launch", Path(target).stem] if target.endswith(".desktop") else ["xdg-open", target])
                return {"status": "success", "message": f"Successfully launched {app_name}"}
            except Exception:
                pass

        # 3. Fuzzy search installed applications
        for name, path in apps.items():
            if query in name:
                try:
                    if CURRENT_OS == "windows":
                        os.startfile(path)
                    elif CURRENT_OS == "darwin":
                        subprocess.Popen(["open", path])
                    else:
                        subprocess.Popen(["xdg-open", path])
                    return {"status": "success", "message": f"Successfully launched {name}"}
                except Exception:
                    pass

        # 4. Fallback execution
        try:
            if CURRENT_OS == "windows":
                os.startfile(app_name)
            elif CURRENT_OS == "darwin":
                subprocess.Popen(["open", "-a", app_name])
            else:
                subprocess.Popen([app_name])
            return {"status": "success", "message": f"Opened {app_name}"}
        except Exception as e:
            return {"status": "error", "message": f"Could not open '{app_name}': {e}"}

    # =========================================================================
    # 4. APPLICATION & WINDOW TERMINATION
    # =========================================================================
    @classmethod
    def close_app(cls, app_name: str) -> Dict[str, Any]:
        """Closes a specific application by process name."""
        query = app_name.lower().strip()
        if CURRENT_OS == "windows":
            exe_map = {
                "edge": "msedge.exe",
                "msedge": "msedge.exe",
                "chrome": "chrome.exe",
                "google chrome": "chrome.exe",
                "spotify": "Spotify.exe",
                "notepad": "notepad.exe",
                "calculator": "CalculatorApp.exe",
                "calc": "CalculatorApp.exe",
                "settings": "SystemSettings.exe",
                "task manager": "Taskmgr.exe",
                "taskmgr": "Taskmgr.exe",
                "vscode": "Code.exe",
                "code": "Code.exe",
                "cmd": "cmd.exe",
                "powershell": "powershell.exe",
            }
            exe_target = exe_map.get(query)
            if not exe_target:
                for k, v in exe_map.items():
                    if k in query:
                        exe_target = v
                        break
            target_proc = exe_target or f"{query}.exe"
            try:
                subprocess.run(["taskkill", "/IM", target_proc, "/T", "/F"], capture_output=True, text=True)
                return {"status": "success", "message": f"Closed {app_name}"}
            except Exception as e:
                return {"status": "error", "message": f"Could not close {app_name}: {e}"}
        elif CURRENT_OS == "darwin":
            try:
                subprocess.run(["pkill", "-f", app_name], capture_output=True)
                return {"status": "success", "message": f"Closed {app_name}"}
            except Exception as e:
                return {"status": "error", "message": str(e)}
        else:
            try:
                subprocess.run(["pkill", "-f", app_name], capture_output=True)
                return {"status": "success", "message": f"Closed {app_name}"}
            except Exception as e:
                return {"status": "error", "message": str(e)}

    @classmethod
    def close_active_window_or_tab(cls, is_tab: bool = False) -> Dict[str, Any]:
        """Closes the currently active window (Alt+F4) or browser tab (Ctrl+W)."""
        if CURRENT_OS == "windows":
            try:
                import ctypes
                user32 = ctypes.windll.user32
                if is_tab:
                    # Ctrl + W
                    user32.keybd_event(0x11, 0, 0, 0)
                    user32.keybd_event(0x57, 0, 0, 0)
                    user32.keybd_event(0x57, 0, 2, 0)
                    user32.keybd_event(0x11, 0, 2, 0)
                    return {"status": "success", "message": "Closed active tab"}
                else:
                    # Alt + F4
                    user32.keybd_event(0x12, 0, 0, 0)
                    user32.keybd_event(0x73, 0, 0, 0)
                    user32.keybd_event(0x73, 0, 2, 0)
                    user32.keybd_event(0x12, 0, 2, 0)
                    return {"status": "success", "message": "Closed active window"}
            except Exception as e:
                return {"status": "error", "message": f"Could not close window: {e}"}
        return {"status": "unsupported", "message": "Not implemented for this OS"}
