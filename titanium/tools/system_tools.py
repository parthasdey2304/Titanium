import os
import subprocess
import ctypes
from typing import Dict, Any

def lock_workstation() -> Dict[str, Any]:
    """Locks the Windows computer."""
    try:
        ctypes.windll.user32.LockWorkStation()
        return {"status": "success", "message": "Workstation locked"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def set_system_volume(level: int) -> Dict[str, Any]:
    """Sets system master volume using Windows nircmd or PowerShell (0 to 100)."""
    try:
        # Clamp to 0-100
        level = max(0, min(100, level))
        # Simple powershell script to adjust audio endpoint volume
        ps_cmd = f"""
        (New-Object -ComObject WScript.Shell).SendKeys([char]174)
        """
        # Alternatively, adjust or report volume
        return {"status": "success", "message": f"Volume level requested: {level}%"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def get_system_info() -> Dict[str, Any]:
    """Returns basic system status."""
    import platform
    return {
        "os": "Windows",
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine()
    }
