import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from .resume_processor import ResumeProcessor
from .llm_agent import LLMAgent
from .requirements_manager import RequirementsManager
from .matcher import ResumeMatcher
from .job_description_processor import JobDescriptionProcessor
from .report_generator import ReportGenerator
from .models import ResumeEvaluation, EvaluationReport

console = Console()
logger = logging.getLogger(__name__)

class ResumeEvaluationAgent:
    """Main orchestrator for the resume evaluation system."""
    
    def __init__(self, resume_dir: str = "resumes", config_dir: str = "config", output_dir: str = "outputs/evaluations"):
        self.resume_dir = resume_dir
        self.config_dir = config_dir
        self.output_dir = output_dir
        
        # Initialize components
        self.resume_processor = ResumeProcessor(resume_dir)
        self.llm_agent = LLMAgent()
        self.requirements_manager = RequirementsManager(config_dir)
        self.matcher = ResumeMatcher()
        self.job_processor = JobDescriptionProcessor(self.resume_dir)
        self.report_generator = ReportGenerator(output_dir)
        
        console.print("[green]Resume Evaluation Agent initialized![/green]")
    
    def evaluate_resumes(self, requirements_file: Optional[str] = None, progress_callback=None) -> EvaluationReport:
        """Main evaluation pipeline."""
        
        # Load requirements
        try:
            if requirements_file:
                requirements = self.requirements_manager.load_requirements(requirements_file)
            else:
                requirements = self.requirements_manager.load_requirements()
            
            console.print(f"[blue]Loaded requirements for: {requirements.project_title}[/blue]")
            
        except FileNotFoundError:
            console.print("[red]No requirements file found![/red]")
            console.print("Please run 'create-requirements' to create one first.")
            raise FileNotFoundError("Requirements file not found")
        
        # Validate requirements
        validation = self.requirements_manager.validate_requirements(requirements)
        if not validation['valid']:
            console.print(f"[red]Requirements validation failed: {validation['issues']}[/red]")
            raise ValueError("Invalid requirements")
        
        # Get resume files
        resume_files = self.resume_processor.get_resume_files()
        if not resume_files:
            console.print("[red]No resume files found in directory![/red]")
            raise FileNotFoundError("No resume files found")
        
        console.print(f"[blue]Found {len(resume_files)} resume files to evaluate[/blue]")
        
        # Process resumes
        evaluations = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            
            task = progress.add_task("Evaluating resumes...", total=len(resume_files))
            
            for idx, file_path in enumerate(resume_files):
                try:
                    if progress_callback:
                        progress_callback(idx, len(resume_files), file_path.name)
                    
                    # Extract text from resume
                    resume_text = self.resume_processor.extract_text(file_path)
                    if not resume_text:
                        console.print(f"[yellow]Warning: Could not extract text from {file_path.name}[/yellow]")
                        progress.advance(task)
                        if progress_callback:
                            progress_callback(idx + 1, len(resume_files), file_path.name)
                        continue
                    
                    # Evaluate with LLM
                    evaluation = self.llm_agent.evaluate_resume(
                        resume_text, 
                        file_path.name, 
                        requirements
                    )
                    
                    evaluations.append(evaluation)
                    progress.advance(task)
                    if progress_callback:
                        progress_callback(idx + 1, len(resume_files), file_path.name)
                    
                except Exception as e:
                    console.print(f"[red]Error processing {file_path.name}: {e}[/red]")
                    logger.error(f"Error processing {file_path.name}: {e}")
                    progress.advance(task)
                    if progress_callback:
                        progress_callback(idx + 1, len(resume_files), file_path.name)
                    continue
            
            if progress_callback:
                progress_callback(len(resume_files), len(resume_files), 'Done')
        
        if not evaluations:
            console.print("[red]No successful evaluations completed![/red]")
            raise ValueError("No evaluations completed")
        
        # Rank candidates
        ranked_evaluations = self.matcher.rank_candidates(evaluations)
        
        # Generate summary statistics
        summary = self.matcher.get_evaluation_summary(ranked_evaluations)
        
        # Add skill gaps analysis
        skill_gaps = self.matcher.find_skill_gaps(ranked_evaluations, requirements)
        summary['skill_gaps'] = skill_gaps
        
        # Create evaluation report
        report = EvaluationReport(
            project_requirements=requirements,
            total_resumes_evaluated=len(ranked_evaluations),
            ranked_candidates=ranked_evaluations,
            evaluation_summary=summary
        )
        
        return report
    
    def run_evaluation(self, requirements_file: Optional[str] = None, 
                      generate_reports: bool = True, progress_callback=None) -> EvaluationReport:
        """Run complete evaluation pipeline with reporting."""
        
        try:
            # Run evaluation
            report = self.evaluate_resumes(requirements_file, progress_callback=progress_callback)
            
            # Display console report
            self.report_generator.generate_console_report(report)
            
            # Generate reports
            if generate_reports:
                report_files = self.report_generator.generate_all_reports(report)
                console.print(f"\n[green]Reports generated:[/green]")
                for format_type, file_path in report_files.items():
                    console.print(f"  {format_type.upper()}: {file_path}")
            
            return report
            
        except Exception as e:
            console.print(f"[red]Evaluation failed: {e}[/red]")
            logger.error(f"Evaluation failed: {e}")
            raise
    
    def evaluate_single_resume(self, resume_file: str, requirements_file: Optional[str] = None) -> ResumeEvaluation:
        """Evaluate a single resume file."""
        
        # Load requirements
        try:
            if requirements_file:
                requirements = self.requirements_manager.load_requirements(requirements_file)
            else:
                requirements = self.requirements_manager.load_requirements()
            
            console.print(f"[blue]Loaded requirements for: {requirements.project_title}[/blue]")
            
        except FileNotFoundError:
            console.print("[red]No requirements file found![/red]")
            console.print("Please run 'create-requirements' to create one first.")
            raise FileNotFoundError("Requirements file not found")
        
        # Process single resume
        file_path = Path(self.resume_dir) / resume_file
        if not file_path.exists():
            raise FileNotFoundError(f"Resume file not found: {resume_file}")
        
        console.print(f"[blue]Evaluating single resume: {resume_file}[/blue]")
        
        # Extract text
        resume_text = self.resume_processor.extract_text(file_path)
        if not resume_text:
            raise ValueError(f"Could not extract text from {resume_file}")
        
        # Evaluate
        evaluation = self.llm_agent.evaluate_resume(resume_text, resume_file, requirements)
        
        # Display results
        console.print(f"\n[bold]Evaluation Results for {resume_file}[/bold]")
        console.print(f"Overall Score: {evaluation.scores.overall_score}/100")
        console.print(f"Recommendation: {evaluation.recommendation}")
        console.print(f"Reasoning: {evaluation.reasoning}")
        
        return evaluation
    
    def create_requirements_interactive(self) -> None:
        """Create new requirements interactively."""
        requirements = self.requirements_manager.create_interactive_requirements()
        self.requirements_manager.display_requirements(requirements)
    
    def show_requirements(self, requirements_file: Optional[str] = None) -> None:
        """Display current requirements."""
        try:
            if requirements_file:
                requirements = self.requirements_manager.load_requirements(requirements_file)
            else:
                requirements = self.requirements_manager.load_requirements()
            
            self.requirements_manager.display_requirements(requirements)
            
        except FileNotFoundError:
            console.print("[red]No requirements file found[/red]")
    
    def list_resume_files(self) -> None:
        """List available resume files."""
        files = self.resume_processor.get_resume_files()
        
        if not files:
            console.print("[yellow]No resume files found[/yellow]")
            return
        
        console.print(f"[blue]Found {len(files)} resume files:[/blue]")
        for file_path in files:
            console.print(f"  • {file_path.name}")
    
    def validate_setup(self) -> Dict[str, bool]:
        """Validate that all components are properly configured."""
        checks = {}
        
        # Check resume directory
        resume_dir_exists = Path(self.resume_dir).exists()
        checks['resume_directory'] = resume_dir_exists
        
        # Check config directory
        config_dir_exists = Path(self.config_dir).exists()
        checks['config_directory'] = config_dir_exists
        
        # Check requirements file
        try:
            self.requirements_manager.load_requirements()
            checks['requirements_file'] = True
        except:
            checks['requirements_file'] = False
        
        # Check LLM configuration
        try:
            self.llm_agent = LLMAgent()
            checks['llm_config'] = True
        except:
            checks['llm_config'] = False
        
        # Check output directory
        output_dir_exists = Path(self.output_dir).exists()
        checks['output_directory'] = output_dir_exists
        
        return checks
    
    def show_setup_status(self) -> None:
        """Display setup status."""
        checks = self.validate_setup()
        
        console.print("[bold]Setup Status:[/bold]")
        for component, status in checks.items():
            status_icon = "[green]✓[/green]" if status else "[red]✗[/red]"
            component_name = component.replace('_', ' ').title()
            console.print(f"  {status_icon} {component_name}")
        
        all_good = all(checks.values())
        if all_good:
            console.print("\n[green]✓ All components are properly configured![/green]")
        else:
            console.print("\n[yellow]⚠ Some components need attention[/yellow]")
    
    def process_job_description_file(self, file_path: str, is_temp_upload: bool = False):
        """Process job description file and extract requirements."""
        if is_temp_upload:
            # File is in temp_uploads directory
            job_file_path = Path("temp_uploads") / file_path
        else:
            # File is in config directory
            job_file_path = Path(self.config_dir) / file_path
        
        if not job_file_path.exists():
            raise FileNotFoundError(f"Job description file not found: {file_path}")
        
        console.print(f"[blue]Processing job description: {file_path}[/blue]")
        
        # Process job description
        requirements = self.job_processor.process_job_description(job_file_path)
        
        return requirements
    
    def evaluate_from_job_description(self, job_file: str, is_temp_upload: bool = False) -> EvaluationReport:
        """Evaluate resumes using requirements extracted from job description file."""
        
        # Process job description to get requirements
        requirements = self.process_job_description_file(job_file, is_temp_upload=is_temp_upload)
        
        console.print(f"[green]✓ Requirements extracted from {job_file}[/green]")
        console.print(f"[blue]Evaluating {len(requirements.must_have_skills)} must-have skills[/blue]")
        
        # Run evaluation with extracted requirements
        return self.run_evaluation(requirements)
