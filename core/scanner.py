import asyncio
import logging
import shutil
import subprocess
import time

logger = logging.getLogger("sentra.scanner")

class Scanner:
    def __init__(self):
        self.nmap_paths = [shutil.which("nmap"), "C:\\Program Files (x86)\\Nmap\\nmap.exe"]
        self.nmap_path = next((p for p in self.nmap_paths if (p and shutil.which(p)) or p), None)

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

    async def _stream_subprocess(self, cmd, timeout=120):
        try:
            import sys
            import threading

            loop = asyncio.get_running_loop()
            queue = asyncio.Queue()

            # Use threading to completely bypass Windows event loop limitations
            # for subprocess streaming in Uvicorn/FastAPI
            creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                creationflags=creationflags
            )

            def _reader_thread():
                try:
                    for line in iter(process.stdout.readline, b''):
                        if not line:
                            break
                        decoded_line = line.decode('utf-8', errors='replace')
                        loop.call_soon_threadsafe(queue.put_nowait, decoded_line)
                finally:
                    process.stdout.close()
                    process.wait()
                    loop.call_soon_threadsafe(queue.put_nowait, None) # EOF

            thread = threading.Thread(target=_reader_thread, daemon=True)
            thread.start()

            start_time = time.time()
            while True:
                elapsed = time.time() - start_time
                if elapsed > timeout:
                    process.terminate()
                    yield f"\n[!] Error: Command timed out after {timeout} seconds.\n"
                    break

                try:
                    # Wait for next line from queue, timeout allows while loop to check total elapsed time
                    line = await asyncio.wait_for(queue.get(), timeout=1.0)
                    if line is None:
                        break # EOF
                    yield line
                    queue.task_done()
                except TimeoutError:
                    continue

        except Exception as e:
            yield f"\n[!] Execution Error: {e!r} | Command: {cmd}\n"

    async def run_nmap_scan_stream(self, target: str):
        """
        Runs a standard Nmap scan (Fast mode), yielding line by line.
        """
        if not self.nmap_path:
            yield "Error: Nmap not found. Please install Nmap.\n"
            return

        logger.info(f"Starting async Nmap on {target}")
        cmd = [self.nmap_path, "-F", "-T4", target]

        async for line in self._stream_subprocess(cmd, timeout=120):
            yield line

    async def run_nikto_scan_stream(self, target: str):
        """
        Runs Nikto web scan (Local or Docker), yielding line by line.
        """
        if not self.nikto_path and not self.use_docker_nikto:
            yield "Nikto not installed (and Docker not found). Skipping web scan.\n"
            return

        logger.info(f"Starting async Nikto on {target}")

        # Handle Localhost for Docker on Windows
        scan_target = target
        if self.use_docker_nikto:
            if target in ["localhost", "127.0.0.1", "::1"]:
                scan_target = "host.docker.internal"
                logger.info(f"Adjusted target for Docker: {scan_target}")

            cmd = [self.docker_path, "run", "--rm", "frapsoft/nikto", "-h", f"http://{scan_target}:80", "-maxtime", "60"]
        else:
            cmd = [self.nikto_path, "-h", target, "-maxtime", "60"]

        async for line in self._stream_subprocess(cmd, timeout=75):
            yield line
