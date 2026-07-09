"""
tools/browser_bootstrap.py
===========================
Helper for automatically launching or attaching to a Chrome instance that
browser_use can control through CDP.

Supports cross-platform execution:
- Windows (native, WSL)
- Linux (including Arch Linux with automatic Playwright configuration)
- macOS
"""

from __future__ import annotations

import atexit
import os
import platform
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List

import requests

_BROWSER_PROCESS: subprocess.Popen | None = None
_BROWSER_CDP_URL: str | None = None
_BROWSER_AUTO_STARTED = False

# Platform detection
_SYSTEM = platform.system().lower()
_IS_ARCH_LINUX = False

if _SYSTEM == "linux":
    # Detect Arch Linux for special Playwright handling
    _IS_ARCH_LINUX = (
        Path("/etc/arch-release").exists() or
        Path("/etc/pacman.conf").exists()
    )
    if not _IS_ARCH_LINUX:
        try:
            with open("/etc/os-release", "r") as f:
                content = f.read().lower()
                _IS_ARCH_LINUX = "arch" in content or "manjaro" in content
        except Exception:
            pass


def _is_docker() -> bool:
    """Detect if running inside Docker container."""
    return Path("/.dockerenv").exists() or Path("/run/.containerenv").exists()


def _is_wsl() -> bool:
    """Detect if running in Windows Subsystem for Linux."""
    if _SYSTEM != "linux":
        return False
    try:
        with open("/proc/version", "r") as f:
            return "microsoft" in f.read().lower() or "wsl" in f.read().lower()
    except Exception:
        return False


@dataclass
class BrowserBootstrapStatus:
    mode: str = "disabled"
    cdp_url: str | None = None
    browser_pid: int | None = None
    browser_executable: str | None = None
    user_data_dir: str | None = None
    message: str = ""


_BROWSER_STATUS = BrowserBootstrapStatus()


def ensure_browser_cdp_url() -> str | None:
    """Ensure a CDP endpoint exists for browser_use and return its URL."""
    global _BROWSER_PROCESS, _BROWSER_CDP_URL, _BROWSER_AUTO_STARTED, _BROWSER_STATUS

    if os.getenv("BROWSER_USE_CLOUD", "").lower() in {"1", "true", "yes"}:
        _BROWSER_STATUS = BrowserBootstrapStatus(mode="cloud", message="Cloud browser mode enabled")
        return None

    existing = _normalize_cdp_url(os.getenv("BROWSER_USE_CDP_URL"))
    if existing and _cdp_ready(existing):
        _BROWSER_CDP_URL = existing
        _BROWSER_STATUS = BrowserBootstrapStatus(mode="attached", cdp_url=existing, message="Attached to existing browser session")
        os.environ["BROWSER_USE_CDP_URL"] = existing
        return existing

    port = int(os.getenv("BROWSER_USE_CDP_PORT", "9222"))
    cdp_url = f"http://127.0.0.1:{port}"
    if _cdp_ready(cdp_url):
        _BROWSER_CDP_URL = cdp_url
        _BROWSER_STATUS = BrowserBootstrapStatus(mode="attached", cdp_url=cdp_url, message="Found an existing Chrome CDP endpoint")
        os.environ["BROWSER_USE_CDP_URL"] = cdp_url
        return cdp_url

    chrome_exe = _find_chrome_executable()
    if not chrome_exe:
        _BROWSER_STATUS = BrowserBootstrapStatus(mode="error", message="Chrome executable not found")
        raise RuntimeError(
            "Could not find Chrome for browser-use. Set BROWSER_USE_CDP_URL manually or install Chrome."
        )

    user_data_dir = os.getenv("BROWSER_USE_USER_DATA_DIR")
    if not user_data_dir:
        user_data_dir = tempfile.mkdtemp(prefix="ecom-browser-profile-")

    args = [
        str(chrome_exe),
        f"--remote-debugging-port={port}",
        f"--user-data-dir={user_data_dir}",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-popup-blocking",
        "--new-window",
        "about:blank",
    ]
    
    # Add Linux-specific arguments for Docker and containerized environments
    if _SYSTEM == "linux":
        args.extend([
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-accelerated-2d-canvas",
            "--no-zygote",
            "--single-process",
        ])
        
        # Arch Linux specific flags
        if _IS_ARCH_LINUX:
            args.extend([
                "--disable-features=VizDisplayCompositor",
                "--disable-in-process-stack-traces",
            ])
        
        # Docker container flags
        if _is_docker():
            args.extend([
                "--disable-gpu",
                "--disable-software-rasterizer",
            ])

    creationflags = 0
    if hasattr(subprocess, "CREATE_NO_WINDOW"):
        creationflags = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]

    _BROWSER_PROCESS = subprocess.Popen(
        args,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        creationflags=creationflags,
    )
    _BROWSER_AUTO_STARTED = True
    _BROWSER_STATUS = BrowserBootstrapStatus(
        mode="launching",
        browser_pid=_BROWSER_PROCESS.pid,
        browser_executable=str(chrome_exe),
        user_data_dir=user_data_dir,
        message="Launching Chrome with remote debugging",
    )
    atexit.register(cleanup_browser_runtime)

    deadline = time.time() + float(os.getenv("BROWSER_USE_CDP_STARTUP_TIMEOUT", "30"))
    while time.time() < deadline:
        if _cdp_ready(cdp_url):
            _BROWSER_CDP_URL = cdp_url
            _BROWSER_STATUS = BrowserBootstrapStatus(
                mode="launched",
                cdp_url=cdp_url,
                browser_pid=_BROWSER_PROCESS.pid if _BROWSER_PROCESS else None,
                browser_executable=str(chrome_exe),
                user_data_dir=user_data_dir,
                message="Launched and attached to a fresh Chrome session",
            )
            os.environ["BROWSER_USE_CDP_URL"] = cdp_url
            os.environ["BROWSER_HEADLESS"] = "false"
            return cdp_url
        time.sleep(0.5)

    _BROWSER_STATUS = BrowserBootstrapStatus(
        mode="error",
        message=f"Chrome started, but CDP endpoint did not become ready at {cdp_url}",
    )
    raise RuntimeError(f"Chrome started, but CDP endpoint did not become ready at {cdp_url}")


def get_browser_status() -> BrowserBootstrapStatus:
    return _BROWSER_STATUS


def describe_browser_status() -> str:
    status = _BROWSER_STATUS
    if status.mode == "disabled":
        return "not started"
    if status.mode == "cloud":
        return "cloud browser enabled"
    if status.mode == "attached":
        return f"attached to {status.cdp_url or 'existing browser'}"
    if status.mode == "launching":
        return f"launching Chrome (pid {status.browser_pid or 'n/a'})"
    if status.mode == "launched":
        return f"launched local Chrome at {status.cdp_url or 'n/a'}"
    if status.mode == "error":
        return f"error: {status.message}"
    return status.message or status.mode


def cleanup_browser_runtime() -> None:
    """Stop the auto-launched browser if we started one."""
    global _BROWSER_PROCESS, _BROWSER_STATUS

    if _BROWSER_PROCESS and _BROWSER_PROCESS.poll() is None:
        try:
            _BROWSER_PROCESS.terminate()
            _BROWSER_PROCESS.wait(timeout=5)
        except Exception:
            try:
                _BROWSER_PROCESS.kill()
            except Exception:
                pass

    if _BROWSER_AUTO_STARTED:
        _BROWSER_STATUS = BrowserBootstrapStatus(
            mode="stopped",
            cdp_url=_BROWSER_CDP_URL,
            browser_pid=_BROWSER_PROCESS.pid if _BROWSER_PROCESS else None,
            browser_executable=_BROWSER_STATUS.browser_executable,
            user_data_dir=_BROWSER_STATUS.user_data_dir,
            message="Browser process stopped",
        )

    _BROWSER_PROCESS = None


def _find_chrome_executable() -> Path | None:
    """Find Chrome/Chromium executable across platforms."""
    candidates: List[Path] = []

    # Check environment variable first
    env_path = os.getenv("BROWSER_USE_CHROME_PATH")
    if env_path:
        candidates.append(Path(env_path))

    # Platform-specific search
    if _SYSTEM == "windows":
        # Windows paths
        local_app_data = os.getenv("LOCALAPPDATA")
        if local_app_data:
            # Playwright bundled Chromium
            ms_playwright = Path(local_app_data) / "ms-playwright"
            if ms_playwright.exists():
                try:
                    candidates.extend(sorted(ms_playwright.rglob("chrome.exe")))
                except Exception:
                    pass
            # User-installed Chrome
            candidates.append(Path(local_app_data) / "Google" / "Chrome" / "Application" / "chrome.exe")

        program_files = os.getenv("ProgramFiles")
        if program_files:
            candidates.append(Path(program_files) / "Google" / "Chrome" / "Application" / "chrome.exe")

        program_files_x86 = os.getenv("ProgramFiles(x86)")
        if program_files_x86:
            candidates.append(Path(program_files_x86) / "Google" / "Chrome" / "Application" / "chrome.exe")

    elif _SYSTEM == "linux":
        # Linux paths (including Arch Linux and Docker)
        linux_candidates = [
            # Standard Linux
            Path("/usr/bin/google-chrome"),
            Path("/usr/bin/google-chrome-stable"),
            Path("/usr/bin/chromium"),
            Path("/usr/bin/chromium-browser"),
            # Snap
            Path("/snap/bin/chromium"),
            # Arch Linux specific
            Path("/usr/bin/google-chrome-arch"),
            Path("/usr/bin/chromium-arch"),
            # Flatpak
            Path("/var/lib/flatpak/exports/bin/com.google.Chrome"),
            Path("/var/lib/flatpak/exports/bin/org.chromium.Chromium"),
        ]
        candidates.extend(linux_candidates)
        
        # Playwright bundled Chromium
        home = os.getenv("HOME", "/root")
        playwright_paths = [
            Path(home) / ".cache" / "ms-playwright",
            Path("/ms-playwright"),  # Docker default
        ]
        for pw_path in playwright_paths:
            if pw_path.exists():
                try:
                    # Find chromium directories
                    for chromium_dir in sorted(pw_path.glob("chromium-*")):
                        chrome_exe = chromium_dir / "chrome-linux" / "chrome"
                        if chrome_exe.exists():
                            candidates.append(chrome_exe)
                except Exception:
                    pass

    elif _SYSTEM == "darwin":
        # macOS paths
        candidates.extend([
            Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
            Path("/Applications/Chromium.app/Contents/MacOS/Chromium"),
        ])
        
        # Playwright bundled Chromium on macOS
        home = os.getenv("HOME", "/Users")
        playwright_path = Path(home) / "Library" / "Caches" / "ms-playwright"
        if playwright_path.exists():
            try:
                for chromium_dir in sorted(playwright_path.glob("chromium-*")):
                    chrome_exe = chromium_dir / "chrome-mac" / "Chromium.app" / "Contents" / "MacOS" / "Chromium"
                    if chrome_exe.exists():
                        candidates.append(chrome_exe)
            except Exception:
                pass

    # Try each candidate
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate

    return None


def _cdp_ready(cdp_url: str) -> bool:
    try:
        response = requests.get(f"{cdp_url.rstrip('/')}/json/version", timeout=1.5)
        return response.ok
    except Exception:
        return False


def _normalize_cdp_url(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    if cleaned.startswith(("ws://", "wss://", "http://", "https://")):
        return cleaned
    if ":" in cleaned:
        return f"http://{cleaned}"
    return cleaned
