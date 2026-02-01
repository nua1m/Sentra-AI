import shutil
import subprocess
import logging
import asyncio

logger = logging.getLogger("sentra.scanner")

class Scanner:
    def __init__(self):
        self.nmap_paths = [shutil.which("nmap"), "C:\\Program Files (x86)\\Nmap\\nmap.exe"]
        self.nmap_path = next((p for p in self.nmap_paths if p and shutil.which(p) or p), None)
        
        # Verify if it actually exists if fell back to hardcoded
        if self.nmap_path and "nmap.exe" in self.nmap_path and not shutil.which("nmap"):
             # Basic check if file exists skipped for brevity, subprocess will fail if invalid
             pass

        self.nikto_path = shutil.which("nikto") # Assumes nikto in path (e.g. via perl)

    def is_available(self) -> bool:
        return bool(self.nmap_path)

    async def run_nmap_scan(self, target: str) -> str:
        """
        Runs a standard Nmap scan (Fast mode).
        Uses asyncio.to_thread for better Windows support.
        """
        if not self.nmap_path:
            return "Error: Nmap not found. Please install Nmap."

        logger.info(f"Starting Nmap on {target}")
        cmd = [self.nmap_path, "-F", "-T4", target]
        
        try:
            # Run blocking subprocess in a separate thread
            result = await asyncio.to_thread(
                subprocess.run,
                cmd,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                return f"Nmap Error (Code {result.returncode}): {result.stderr}"
                
            return result.stdout
        except Exception as e:
            return f"Execution Error: {repr(e)} | Command: {cmd} | Path: {self.nmap_path}"

    async def run_nikto_scan(self, target: str) -> str:
        """
        Runs Nikto web scan.
        """
        if not self.nikto_path:
            return "Nikto not installed/found. Skipping web scan."

        logger.info(f"Starting Nikto on {target}")
        cmd = [self.nikto_path, "-h", target, "-maxtime", "300"]
        
        try:
            result = await asyncio.to_thread(
                subprocess.run,
                cmd,
                capture_output=True,
                text=True
            )
            return result.stdout
        except Exception as e:
            return f"Nikto Execution Error: {repr(e)}"
