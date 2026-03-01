import requests
import time
import sys
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.theme import Theme
from rich.live import Live
from rich.spinner import Spinner
from rich.table import Table

# Theme
theme = Theme({
    "success": "bold green",
    "error": "bold red",
    "warning": "yellow",
    "info": "cyan",
    "prompt": "green"
})
console = Console(theme=theme)
API_URL = "http://localhost:8000"

def check_backend():
    try:
        requests.get(API_URL)
        return True
    except:
        return False

def print_banner():
    console.print(Panel.fit(
        "[bold green]SENTRA.AI UNIFIED COMMAND[/bold green]\n"
        "[dim]Target Verification Protocol: ACTIVE (Option A)[/dim]\n"
        "[dim]AI Model: MOONSHOT (Kimi k2.5) LINKED[/dim]",
        border_style="green"
    ))

def poll_scan(scan_id):
    """
    Polls the backend for scan progress.
    """
    with Live(Spinner("dots", text="[green]Scanning & Analyzing (This may take a minute)...[/green]"), refresh_per_second=4) as live:
        while True:
            try:
                resp = requests.get(f"{API_URL}/scan/{scan_id}")
                if resp.status_code == 200:
                    data = resp.json()
                    status = data.get("status")
                    
                    if status == "pending":
                        live.update(Spinner("dots", text="[green]Queuing scan...[/green]"))
                    elif status == "scanning":
                        live.update(Spinner("dots12", text=f"[green]Running Nmap on {data.get('target')}...[/green]"))
                    elif status == "analyzing":
                        live.update(Spinner("bouncingBall", text="[cyan]AI Analyzing results...[/cyan]"))
                    elif status == "complete":
                        return data
                    elif status == "failed":
                        console.print(f"[error]Scan Failed: {data.get('error')}[/error]")
                        return None
                else:
                    live.update(f"[red]Error polling status: {resp.status_code}[/red]")
            except Exception as e:
                live.update(f"[red]Connection error: {e}[/red]")
            
            time.sleep(2)

def main_loop():
    print_banner()
    
    # Connection Check
    if not check_backend():
        console.print("[error]❌ Cannot connect to Backend.[/error]")
        console.print("Please run: [bold]uvicorn core.app:app --reload[/bold]")
        return

    console.print("[success]✔ Uplink Established.[/success]\n")
    
    while True:
        try:
            user_input = Prompt.ask("[prompt]USER@SENTRA[/prompt]")
            
            if user_input.lower() in ["exit", "quit"]:
                console.print("[yellow]System Shutdown.[/yellow]")
                break
            
            if not user_input.strip():
                continue
                
            # Send to Chat
            with console.status("[green]Thinking...[/green]", spinner="dots"):
                try:
                    resp = requests.post(f"{API_URL}/chat", json={"message": user_input})
                    if resp.status_code != 200:
                        console.print(f"[error]Error {resp.status_code}: {resp.text}[/error]")
                        continue
                    
                    data = resp.json()
                except Exception as e:
                    console.print(f"[error]Error: {e}[/error]")
                    continue

            # Handle Response types
            r_type = data.get("type")
            
            if r_type == "message":
                console.print(Panel(Markdown(data.get("message", "")), title="Sentra.AI", border_style="green"))
                
            elif r_type == "error":
                console.print(f"[error]{data.get('message')}[/error]")
                
            elif r_type == "action_required" and data.get("action") == "start_scan":
                # Special flow for Scans
                target = data.get("target")
                console.print(f"\n[info]Target verified: {target}[/info]")
                console.print(f"[dim]{data.get('message')}[/dim]")
                
                if Confirm.ask("Launch Unified Scan now?"):
                    # Start Scan
                    try:
                        scan_resp = requests.post(f"{API_URL}/scan/start", json={"target": target})
                        if scan_resp.status_code == 200:
                            scan_id = scan_resp.json().get("scan_id")
                            
                            # POLLING
                            result = poll_scan(scan_id)
                            
                            if result:
                                # Show Nmap Raw (truncated)
                                console.print("\n[bold]Raw Scan Data:[/bold]")
                                console.print(result.get("nmap", "")[:500] + "...\n[dim](Output truncated)[/dim]")
                                
                                # Show Analysis
                                console.print(Panel(Markdown(result.get("analysis", "")), title="AI Security Report", border_style="bold red"))
                                
                                # === NEW: Show Remediation Fixes ===
                                if Confirm.ask("Generate Fix Commands?"):
                                    try:
                                        fixes_resp = requests.get(f"{API_URL}/scan/{scan_id}/fixes")
                                        if fixes_resp.status_code == 200:
                                            fixes_data = fixes_resp.json()
                                            console.print(Panel(
                                                Markdown(fixes_data.get("formatted", "No fixes generated.")),
                                                title=f"🛡️ Blue Team Fixes ({fixes_data.get('fix_count', 0)} found) - OS: {fixes_data.get('os_detected', 'unknown').upper()}",
                                                border_style="bold blue"
                                            ))
                                        else:
                                            console.print(f"[error]Fix generation failed: {fixes_resp.text}[/error]")
                                    except Exception as e:
                                        console.print(f"[error]Error getting fixes: {e}[/error]")
                                
                                # PDF Export Option
                                if Confirm.ask("Export to PDF?"):
                                    try:
                                        export_resp = requests.get(f"{API_URL}/scan/{scan_id}/export")
                                        if export_resp.status_code == 200:
                                            path = export_resp.json().get("path")
                                            console.print(f"[success]✔ Report saved: {path}[/success]")
                                        else:
                                            console.print(f"[error]Export failed: {export_resp.text}[/error]")
                                    except Exception as e:
                                        console.print(f"[error]Export error: {e}[/error]")
                        else:
                            console.print(f"[error]Failed to start scan: {scan_resp.text}[/error]")
                    except Exception as e:
                        console.print(f"[error]Error starting scan: {e}[/error]")
                else:
                    console.print("[yellow]Scan aborted.[/yellow]")

        except KeyboardInterrupt:
            console.print("\n[yellow]Session terminated.[/yellow]")
            break

if __name__ == "__main__":
    main_loop()
