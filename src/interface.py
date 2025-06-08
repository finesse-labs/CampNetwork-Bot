# src/interface.py
from rich.console import Console
from rich.panel import Panel
from rich import box
import os

console = Console()

LOGO_LINES = [
    " ",
    " ",
    "[bold dark_orange]     ██████╗  █████╗  ███╗   ███╗ ██████╗ ",
    "[bold dark_orange]    ██╔════╝ ██╔══██╗ ████╗ ████║ ██╔══██╗",
    "[bold dark_orange]    ██║      ███████║ ██╔████╔██║ ██████╔╝",
    "[bold dark_orange]    ██║      ██╔══██║ ██║╚██╔╝██║ ██╔═══╝ ",
    "[bold dark_orange] ╚██████╗ ██║  ██║ ██║ ╚═╝ ██║ ██║     ",
    "[bold dark_orange]  ╚═════╝ ╚═╝  ╚═╝ ╚═╝     ╚═╝ ╚═╝     ",
    " ",
    "[bold green]  ███████╗██╗███╗   ██╗███████╗███████╗███████╗███████╗     ██╗      █████╗ ██████╗ ███████╗",
    "[bold green]  ██╔════╝██║████╗  ██║██╔════╝██╔════╝██╔════╝██╔════╝     ██║     ██╔══██╗██╔══██╗██╔════╝",
    "[bold green]  █████╗  ██║██╔██╗ ██║█████╗  ███████╗███████╗█████╗       ██║     ███████║██████╔╝███████╗",
    "[bold green]  ██╔══╝  ██║██║╚██╗██║██╔══╝  ╚════██║╚════██║██╔══╝       ██║     ██╔══██║██╔══██╗╚════██║",
    "[bold green]  ██║     ██║██║ ╚████║███████╗███████║███████║███████╗     ███████╗██║  ██║██████╔╝███████║",
    "[bold green]  ╚═╝     ╚═╝╚═╝  ╚═══╝╚══════╝╚══════╝╚══════╝╚══════╝     ╚══════╝╚═╝  ╚═╝╚═════╝ ╚══════╝",
    " ",
    " "
]

PROJECT_INFO = Panel(
"""
[bold cyan]⛺ Camp Network Bot 1.0[/bold cyan]
[white]─────────────────────────────────────────────────────[/white]
[bold yellow]⚡ Devs:[/] [link=https://t.me/ftp_crypto]@ftp_crypto[/link] | [link=https://t.me/cryptoforto]@cryptoforto[/link]
[bold yellow]💬 Support: [white]https://t.me/+HlDlu6F3iGwzMjFi[/white][/bold yellow]
[bold yellow]📦 GitHub: [white]https://github.com/finesse-labs/[/white][/bold yellow]
""",
    title="[bold green]⚡ Info ⚡[/bold green]",
    border_style="bright_green",
    box=box.DOUBLE,
    width=70,
    padding=(1, 2)
)

def display_start():
    """Display logo, info, and wait for Enter."""
    for line in LOGO_LINES:
        console.print(line, justify="center")
    console.print(PROJECT_INFO, justify="center")
    console.print("\n[bold green]Press Enter to start...[/bold green]")
    console.input("[bold green]>[/bold green]")

def clear_screen():
    """Clear the screen."""
    os.system('cls' if os.name == 'nt' else 'clear')