import os
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt
from rich.syntax import Syntax
from rich import box

console = Console()

OUTPUT_ROOT = Path("smartrepo-analysis")

def list_projects():
    if not OUTPUT_ROOT.exists():
        return []
    return [p for p in OUTPUT_ROOT.iterdir() if p.is_dir()]

def list_output_files(project_dir: Path):
    return [f for f in project_dir.iterdir() if f.is_file()]

def show_file_content(file_path: Path):
    ext = file_path.suffix.lower()
    try:
        content = file_path.read_text(encoding='utf-8')
    except Exception:
        console.print("[red]Error reading file[/red]")
        return
    if ext in ['.md', '.txt', '.mmd', '.json']:
        syntax = Syntax(content, "markdown" if ext == ".md" else "json" if ext == ".json" else "text", theme="monokai", line_numbers=True)
        console.print(syntax)
    else:
        console.print(Panel(content, title=str(file_path.name), expand=True))

def main():
    console.clear()
    # شعار احترافي داخل Panel مع رموز وتدرج ألوان
    logo = """
[bold blue]
███████╗ ███╗   ███╗ █████╗ ██████╗ ██████╗ ██████╗  ██████╗
██╔════╝ ████╗ ████║██╔══██╗██╔══██╗██╔══██╗██╔══██╗██╔═══██╗
███████╗ ██╔████╔██║███████║██████╔╝██████╔╝██║   ██║██████╔╝
╚════██║ ██║╚██╔╝██║██╔══██║██╔═══╝ ██╔══██╗██║   ██║██╔══██╗
███████║ ██║ ╚═╝ ██║██║  ██║██║     ██║  ██║╚██████╔╝██║  ██║
╚══════╝ ╚═╝     ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝
[/bold blue]
[bold magenta]by alsrkal[/bold magenta]
"""
    panel = Panel.fit(
        f"🚀\n{logo}\n🚀",
        title="[bold yellow]Welcome to SmartRepo[/bold yellow]",
        subtitle="[bold green]AI-Powered Code Analysis[/bold green]",
        border_style="bold blue",
        padding=(1, 4),
        style="on black"
    )
    console.print(panel, justify="center")
    console.rule("[bold blue]SmartRepo TUI")
    projects = list_projects()
    if not projects:
        console.print("[red]No analysis results found.[/red]")
        console.print("[yellow]Run:[/yellow] [green]python smartrepo_analyzer.py analyze . --output ./smartrepo-analysis[/green]")
        return
    while True:
        table = Table(title="Available Projects", box=box.SIMPLE)
        table.add_column("#", style="cyan", width=4)
        table.add_column("Project Name", style="bold")
        for idx, proj in enumerate(projects):
            table.add_row(str(idx+1), proj.name)
        console.print(table)
        proj_idx = Prompt.ask("Select project [q to quit]", default="1")
        if proj_idx.lower() == 'q':
            break
        if not proj_idx.isdigit() or int(proj_idx) < 1 or int(proj_idx) > len(projects):
            console.print("[red]Invalid selection[/red]")
            continue
        project_dir = projects[int(proj_idx)-1]
        while True:
            files = list_output_files(project_dir)
            ftable = Table(title=f"Files in {project_dir.name}", box=box.SIMPLE)
            ftable.add_column("#", style="green", width=4)
            ftable.add_column("File Name", style="bold")
            for idx, f in enumerate(files):
                ftable.add_row(str(idx+1), f.name)
            console.print(ftable)
            file_idx = Prompt.ask("Select file to view [b: back, q: quit]", default="1")
            if file_idx.lower() == 'q':
                return
            if file_idx.lower() == 'b':
                console.clear()
                break
            if not file_idx.isdigit() or int(file_idx) < 1 or int(file_idx) > len(files):
                console.print("[red]Invalid selection[/red]")
                continue
            console.clear()
            console.rule(f"[bold yellow]{files[int(file_idx)-1].name}")
            show_file_content(files[int(file_idx)-1])
            console.print("\n[dim]Press Enter to return to file list...[/dim]")
            input()
            console.clear()

if __name__ == "__main__":
    main()