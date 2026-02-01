import shutil
import subprocess
import logging
import asyncio

logger = logging.getLogger("sentra.scanner")

class Scanner:
    def __init__(self):
        self.nmap_paths = [shutil.which("nmap"), "C:\\Program Files (x86)\\Nmap\\nmap.exe"]
        self.nmap_path = next((p for p in self.nmap_paths if p and shutil.which(p) or p), None)
        
        # Check for Local Nikto or Docker
        self.nikto_path = shutil.which("nikto")
        self.docker_path = shutil.which("docker")
        self.use_docker_nikto = False
        
        if not self.nikto_path and self.docker_path:
            # Verify Docker Daemon is actually running
            try:
                subprocess.run([self.docker_path, "info"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                self.use_docker_nikto = True
                logger.info("Docker found and daemon is running. Enabled Nikto via Docker.")
            except subprocess.CalledProcessError:
                self.use_docker_nikto = False
                logger.warning("Docker binary found but Daemon is not running. Nikto disabled.")
            except Exception:
                self.use_docker_nikto = False

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
        Runs Nikto web scan (Local or Docker).
        """
        if not self.nikto_path and not self.use_docker_nikto:
            return "Nikto not installed (and Docker not found). Skipping web scan."

        logger.info(f"Starting Nikto on {target}")
        
        # Handle Localhost for Docker on Windows
        scan_target = target
        if self.use_docker_nikto:
            if target in ["localhost", "127.0.0.1", "::1"]:
                scan_target = "host.docker.internal"
                logger.info(f"Adjusted target for Docker: {scan_target}")

            cmd = [self.docker_path, "run", "--rm", "frapsoft/nikto", "-h", f"http://{scan_target}:80", "-maxtime", "60"]
        else:
            cmd = [self.nikto_path, "-h", target, "-maxtime", "60"]
        
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
