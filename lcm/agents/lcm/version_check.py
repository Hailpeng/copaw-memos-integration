# -*- coding: utf-8 -*-
"""LCM Version Checker.

Checks if copaw has been updated since LCM was installed.
If so, reminds user to reinstall LCM.
"""
import json
import logging
import subprocess
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

VERSION_FILE = Path.home() / ".copaw" / "lcm_installed_version.json"


def get_copaw_version() -> Optional[str]:
    """Get current copaw package version.
    
    Returns:
        Version string or None if not found
    """
    try:
        result = subprocess.run(
            ["pip", "show", "copaw"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            for line in result.stdout.split("\n"):
                if line.startswith("Version:"):
                    return line.split(":", 1)[1].strip()
    except Exception as e:
        logger.debug(f"Failed to get copaw version: {e}")
    return None


def get_installed_copaw_version() -> Optional[str]:
    """Get the copaw version when LCM was installed.
    
    Returns:
        Version string or None if not recorded
    """
    try:
        if VERSION_FILE.exists():
            with open(VERSION_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("copaw_version")
    except Exception as e:
        logger.debug(f"Failed to read version file: {e}")
    return None


def save_installed_version(version: str) -> None:
    """Save the copaw version when LCM is installed.
    
    Args:
        version: Current copaw version
    """
    try:
        VERSION_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "copaw_version": version,
            "lcm_version": "1.3.0",
        }
        with open(VERSION_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        logger.info(f"Saved LCM installation info: copaw={version}")
    except Exception as e:
        logger.warning(f"Failed to save version file: {e}")


def check_version_changed() -> bool:
    """Check if copaw version has changed since LCM was installed.
    
    Returns:
        True if version changed (need reinstall), False otherwise
    """
    current = get_copaw_version()
    installed = get_installed_copaw_version()
    
    if not current:
        logger.debug("Cannot determine current copaw version")
        return False
    
    if not installed:
        # First run or version file missing - save current version
        save_installed_version(current)
        return False
    
    if current != installed:
        logger.warning(
            f"⚠️ Copaw version changed: {installed} → {current}\n"
            f"   LCM modules may have been overwritten. "
            f"Please reinstall:\n"
            f"   cd copaw-memos-integration && python install_lcm.py"
        )
        return True
    
    return False


def update_version_record() -> None:
    """Update version record to current version (call after reinstall)."""
    current = get_copaw_version()
    if current:
        save_installed_version(current)