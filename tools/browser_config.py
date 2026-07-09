"""
tools/browser_config.py
========================
Cross-platform browser configuration for UltraSwarm.
Handles platform detection and Playwright setup for Windows, Linux, and Arch Linux.
"""

import os
import platform
import subprocess
from pathlib import Path
from typing import Optional, Tuple


class BrowserConfig:
    """
    Cross-platform browser configuration.
    Automatically detects platform and configures Playwright accordingly.
    """
    
    def __init__(self):
        self.system = platform.system().lower()
        self.is_arch = self._detect_arch_linux()
        self.headless = os.getenv("BROWSER_HEADLESS", "true").lower() in {"1", "true", "yes"}
        self.cdp_port = int(os.getenv("BROWSER_USE_CDP_PORT", "9222"))
        
    def _detect_arch_linux(self) -> bool:
        """Detect if running on Arch Linux."""
        if self.system != "linux":
            return False
        
        # Check for Arch Linux specific files
        arch_indicators = [
            "/etc/arch-release",
            "/etc/pacman.conf",
        ]
        
        for indicator in arch_indicators:
            if Path(indicator).exists():
                return True
        
        # Check os-release
        try:
            with open("/etc/os-release", "r") as f:
                content = f.read().lower()
                if "arch" in content or "manjaro" in content:
                    return True
        except Exception:
            pass
        
        return False
    
    def get_playwright_env(self) -> dict:
        """
        Get Playwright environment variables for the current platform.
        Handles Arch Linux specific requirements.
        """
        env = {
            "PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS": "1",
            "PLAYWRIGHT_BROWSERS_PATH": os.getenv("PLAYWRIGHT_BROWSERS_PATH", "/ms-playwright"),
        }
        
        if self.is_arch:
            # Arch Linux specific configurations
            # Skip system library validation which may fail on rolling release
            env["PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS"] = "1"
            
            # Force use of bundled browsers
            env["PLAYWRIGHT_BROWSERS_PATH"] = os.getenv(
                "PLAYWRIGHT_BROWSERS_PATH",
                str(Path.home() / ".cache" / "ms-playwright")
            )
            
            # Additional Arch Linux compatibility
            env["ELECTRON_RUN_AS_NODE"] = "1"
        
        return env
    
    def get_chrome_executable(self) -> Optional[Path]:
        """
        Find Chrome/Chromium executable based on platform.
        Returns None if not found.
        """
        # Check environment variable first
        env_path = os.getenv("BROWSER_USE_CHROME_PATH")
        if env_path and Path(env_path).exists():
            return Path(env_path)
        
        candidates = []
        
        if self.system == "windows":
            candidates = [
                Path(os.getenv("LOCALAPPDATA", "")) / "Google" / "Chrome" / "Application" / "chrome.exe",
                Path(os.getenv("PROGRAMFILES", "")) / "Google" / "Chrome" / "Application" / "chrome.exe",
                Path(os.getenv("PROGRAMFILES(X86)", "")) / "Google" / "Chrome" / "Application" / "chrome.exe",
                Path(os.getenv("LOCALAPPDATA", "")) / "Chromium" / "Application" / "chrome.exe",
                # Playwright bundled Chromium
                Path(os.getenv("LOCALAPPDATA", "")) / "ms-playwright" / "chromium-*" / "chrome-win64" / "chrome.exe",
            ]
        elif self.system == "linux":
            candidates = [
                # Standard Linux locations
                Path("/usr/bin/google-chrome"),
                Path("/usr/bin/google-chrome-stable"),
                Path("/usr/bin/chromium"),
                Path("/usr/bin/chromium-browser"),
                Path("/snap/bin/chromium"),
                # Arch Linux specific
                Path("/usr/bin/google-chrome-arch"),
                Path("/usr/bin/chromium-arch"),
                # Flatpak
                Path("/var/lib/flatpak/exports/bin/com.google.Chrome"),
                Path("/var/lib/flatpak/exports/bin/org.chromium.Chromium"),
                # Playwright bundled
                Path(os.getenv("HOME", "/root")) / ".cache" / "ms-playwright" / "chromium-*" / "chrome-linux" / "chrome",
            ]
        
        for candidate in candidates:
            # Handle glob patterns
            if "*" in str(candidate):
                parent = candidate.parent
                if parent.exists():
                    for match in sorted(parent.glob(candidate.name), reverse=True):
                        if match.exists():
                            return match
            elif candidate.exists():
                return candidate
        
        return None
    
    def get_browser_launch_args(self) -> list:
        """
        Get browser launch arguments based on platform and configuration.
        """
        args = [
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-popup-blocking",
            "--disable-extensions",
            "--disable-notifications",
            f"--remote-debugging-port={self.cdp_port}",
        ]
        
        if self.headless:
            args.extend([
                "--headless=new",
                "--disable-gpu",
                "--disable-software-rasterizer",
            ])
        
        if self.system == "linux":
            # Linux specific arguments for container/CI environments
            args.extend([
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-accelerated-2d-canvas",
                "--no-zygote",
                "--single-process",
            ])
            
            if self.is_arch:
                # Arch Linux specific - handle rolling release library versions
                args.extend([
                    "--disable-features=VizDisplayCompositor",
                    "--disable-in-process-stack-traces",
                ])
        
        return args
    
    def setup_display(self) -> Optional[str]:
        """
        Setup virtual display for headless browser on Linux.
        Returns the DISPLAY environment variable value.
        """
        if self.system != "linux":
            return None
        
        display = os.getenv("DISPLAY")
        if display:
            return display
        
        # Try to start Xvfb for virtual display
        try:
            subprocess.run(
                ["Xvfb", f":{self.cdp_port}", "-screen", "0", "1920x1080x24"],
                capture_output=True,
                timeout=5
            )
            return f":{self.cdp_port}"
        except Exception:
            return None
    
    def get_config_dict(self) -> dict:
        """Get complete configuration as dictionary."""
        return {
            "system": self.system,
            "is_arch_linux": self.is_arch,
            "headless": self.headless,
            "cdp_port": self.cdp_port,
            "playwright_env": self.get_playwright_env(),
            "launch_args": self.get_browser_launch_args(),
            "chrome_executable": str(self.get_chrome_executable()) if self.get_chrome_executable() else None,
        }


def get_browser_config() -> BrowserConfig:
    """Factory function to get browser configuration."""
    return BrowserConfig()


def print_browser_status():
    """Print current browser configuration status."""
    config = get_browser_config()
    
    from rich.console import Console
    from rich.table import Table
    
    console = Console()
    table = Table(title="Browser Configuration", show_header=False)
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("System", config.system)
    table.add_row("Is Arch Linux", str(config.is_arch))
    table.add_row("Headless Mode", str(config.headless))
    table.add_row("CDP Port", str(config.cdp_port))
    table.add_row("Chrome Path", str(config.get_chrome_executable() or "Not found"))
    
    console.print(table)


if __name__ == "__main__":
    print_browser_status()
