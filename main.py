#!/usr/bin/env python3
"""
Resume Evaluation Agent - Main CLI Interface
"""

import typer
import logging
from pathlib import Path
from rich.console import Console
from rich.logging import RichHandler

from src.orchestrator import ResumeEvaluationAgent

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(console=Console(stderr=True))]
)

logger = logging.getLogger(__name__)
app = typer.Typer(help="Resume Evaluation Agent - LLM-powered resume screening tool")

# Global agent instance
agent = None

def get_agent():
    """Get or create agent instance."""
    global agent
    if agent is None:
        agent = ResumeEvaluationAgent()
    return agent

@app.command()
def evaluate(
    requirements: str = typer.Option(None, "--requirements", "-r", help="Path to requirements JSON file"),
    output: str = typer.Option(None, "--output", "-o", help="Output directory for reports"),
    no_reports: bool = typer.Option(False, "--no-reports", help="Skip report generation")
):
    """Evaluate all resumes in the directory."""
    try:
        agent = get_agent()
        
        # Check setup
        agent.show_setup_status()
        
        # Run evaluation
        console = Console()
        console.print("[bold blue]Starting Resume Evaluation...[/bold blue]")
        
        report = agent.run_evaluation(
            requirements_file=requirements,
            generate_reports=not no_reports
        )
        
        console.print(f"\n[green]✓ Evaluation completed! {report.total_resumes_evaluated} resumes processed[/green]")
        
    except Exception as e:
        console = Console()
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)

@app.command()
def single(
    resume_file: str = typer.Argument(..., help="Resume file name"),
    requirements: str = typer.Option(None, "--requirements", "-r", help="Path to requirements JSON file")
):
    """Evaluate a single resume file."""
    try:
        agent = get_agent()
        evaluation = agent.evaluate_single_resume(resume_file, requirements)
        
        console = Console()
        console.print(f"\n[green]✓ Single evaluation completed for {resume_file}[/green]")
        
    except Exception as e:
        console = Console()
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)

@app.command()
def create_requirements():
    """Create new requirements interactively."""
    try:
        agent = get_agent()
        agent.create_requirements_interactive()
        
        console = Console()
        console.print("[green]✓ Requirements created successfully![/green]")
        
    except Exception as e:
        console = Console()
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)

@app.command()
def show_requirements(
    requirements: str = typer.Option(None, "--requirements", "-r", help="Path to requirements JSON file")
):
    """Display current project requirements."""
    try:
        agent = get_agent()
        agent.show_requirements(requirements)
        
    except Exception as e:
        console = Console()
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)

@app.command()
def list_resumes():
    """List all available resume files."""
    try:
        agent = get_agent()
        agent.list_resume_files()
        
    except Exception as e:
        console = Console()
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)

@app.command()
def process_job_description(file_path: str):
    """Extract requirements from job description file (PDF/DOCX/TXT)."""
    agent = ResumeEvaluationAgent()
    
    try:
        requirements = agent.process_job_description_file(file_path)
        console = Console()
        console.print(f"[green]✓ Requirements extracted from {file_path}[/green]")
        console.print(f"[blue]Project: {requirements.project_title}[/blue]")
        console.print(f"[blue]Must-have skills: {', '.join(requirements.must_have_skills)}[/blue]")
        console.print(f"[blue]Experience: {requirements.experience_level}[/blue]")
    except Exception as e:
        console = Console()
        console.print(f"[red]Error processing job description: {e}[/red]")

@app.command()
def list_job_descriptions():
    """List available job description files in config directory."""
    config_dir = Path("config")
    job_files = []
    
    # Look for common job description file patterns
    for pattern in ["*.pdf", "*.docx", "*.txt"]:
        job_files.extend(config_dir.glob(pattern))
    
    if job_files:
        console = Console()
        console.print("\n[yellow]Available job description files:[/yellow]")
        for file in sorted(job_files):
            console.print(f"  • {file.name}")
    else:
        console = Console()
        console.print("[yellow]No job description files found in config directory[/yellow]")
        console.print("Place your job description files (PDF/DOCX/TXT) in the config folder")

@app.command()
def evaluate_from_job_description(job_file: str):
    """Evaluate resumes using requirements from job description file."""
    agent = ResumeEvaluationAgent()
    
    try:
        # Process job description and evaluate
        report = agent.evaluate_from_job_description(job_file)
        console = Console()
        console.print(f"[green]✓ Evaluation completed using {job_file}[/green]")
        
        # Generate reports
        agent.generate_all_reports(report)
        
    except Exception as e:
        console = Console()
        console.print(f"[red]Error: {e}[/red]")

@app.command()
def status():
    """Check system setup status."""
    try:
        agent = get_agent()
        agent.show_setup_status()
        
    except Exception as e:
        console = Console()
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)

@app.command()
def setup():
    """Initialize the resume evaluation system."""
    console = Console()
    
    console.print("[bold blue]Resume Evaluation Agent Setup[/bold blue]")
    console.print()
    
    # Check directories
    directories = ["resumes", "config", "outputs/evaluations"]
    for directory in directories:
        dir_path = Path(directory)
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)
            console.print(f"[green]✓ Created directory: {directory}[/green]")
        else:
            console.print(f"[green]✓ Directory exists: {directory}[/green]")
    
    # Check .env file
    env_file = Path(".env")
    env_example = Path(".env.example")
    
    if not env_file.exists() and env_example.exists():
        env_file.write_text(env_example.read_text())
        console.print("[green]✓ Created .env file from example[/green]")
        console.print("[yellow]⚠ Please update .env with your actual API keys[/yellow]")
    elif env_file.exists():
        console.print("[green]✓ .env file exists[/green]")
    else:
        console.print("[red]✗ No .env.example file found[/red]")
    
    # Check requirements file
    req_file = Path("config/requirements.json")
    if not req_file.exists():
        console.print("[yellow]⚠ No requirements file found. Run 'create-requirements' to create one.[/yellow]")
    else:
        console.print("[green]✓ Requirements file exists[/green]")
    
    console.print("\n[green]✓ Setup completed![/green]")
    console.print("Next steps:")
    console.print("1. Update .env with your LLM API configuration")
    console.print("2. Add resume files to the 'resumes' directory")
    console.print("3. Run 'create-requirements' or edit config/requirements.json")
    console.print("4. Run 'evaluate' to start evaluating resumes")

if __name__ == "__main__":
    app()
