import json
import csv
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from .models import ResumeEvaluation, EvaluationReport, Requirements

console = Console()

class ReportGenerator:
    """Handles generation of evaluation reports in various formats."""
    
    def __init__(self, output_dir: str = "outputs/evaluations"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_console_report(self, report: EvaluationReport) -> None:
        """Generate a rich console report."""
        console.print(f"\n[bold blue]Resume Evaluation Report[/bold blue]")
        console.print(f"Project: {report.project_requirements.project_title}")
        console.print(f"Generated: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}")
        console.print(f"Total Candidates: {report.total_resumes_evaluated}\n")
        
        # Summary statistics
        summary = report.evaluation_summary
        console.print(Panel(
            f"[green]Suitable: {summary.get('suitable', 0)}[/green]\n"
            f"[yellow]Might be suitable: {summary.get('might_be_suitable', 0)}[/yellow]\n"
            f"[red]Not suitable: {summary.get('not_suitable', 0)}[/red]",
            title="Summary Statistics"
        ))
        
        # Top candidates table
        if report.ranked_candidates:
            table = Table(title="Top Candidates")
            table.add_column("Rank", style="cyan", width=6)
            table.add_column("Name", style="magenta")
            table.add_column("Score", style="green", width=8)
            table.add_column("Recommendation", style="yellow", width=15)
            table.add_column("Key Skills", style="blue")
            
            for i, candidate in enumerate(report.ranked_candidates[:10], 1):
                key_skills = ", ".join(
                    [m.skill for m in candidate.skill_matches if m.found_in_resume][:3]
                )
                recommendation_style = "white"
                if "Suitable" in candidate.recommendation and "Might" not in candidate.recommendation:
                    recommendation_style = "green"
                elif "Might be suitable" in candidate.recommendation:
                    recommendation_style = "yellow"
                elif "Not suitable" in candidate.recommendation:
                    recommendation_style = "red"
                
                table.add_row(
                    str(i),
                    candidate.file_name,
                    f"{candidate.scores.overall_score}/100",
                    f"[{recommendation_style}]{candidate.recommendation}[/{recommendation_style}]",
                    key_skills
                )
            
            console.print(table)
        
        # Skill coverage analysis
        if 'skill_gaps' in summary:
            self._display_skill_coverage(summary['skill_gaps'])
    
    def _display_skill_coverage(self, skill_gaps: Dict[str, Dict]) -> None:
        """Display skill coverage analysis."""
        console.print("\n[bold]Skill Coverage Analysis[/bold]")
        
        table = Table(title="Required Skills Coverage")
        table.add_column("Skill", style="cyan")
        table.add_column("Coverage", style="green", width=10)
        table.add_column("Found In", style="blue", width=10)
        table.add_column("Missing In", style="red", width=11)
        
        for skill, data in skill_gaps.items():
            coverage_color = "green" if data['coverage_percentage'] >= 70 else "yellow" if data['coverage_percentage'] >= 40 else "red"
            table.add_row(
                skill,
                f"[{coverage_color}]{data['coverage_percentage']}%[/{coverage_color}]",
                str(data['found_in_candidates']),
                str(data['missing_in_candidates'])
            )
        
        console.print(table)
    
    def generate_json_report(self, report: EvaluationReport, filename: str = None) -> str:
        """Generate detailed JSON report."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"evaluation_report_{timestamp}.json"
        
        output_path = self.output_dir / filename
        
        # Convert report to dict for JSON serialization
        report_dict = {
            "project_requirements": report.project_requirements.dict(),
            "total_resumes_evaluated": report.total_resumes_evaluated,
            "evaluation_summary": report.evaluation_summary,
            "ranked_candidates": [
                {
                    "rank": i + 1,
                    "file_name": eval.file_name,
                    "overall_score": eval.scores.overall_score,
                    "recommendation": eval.recommendation,
                    "skill_match_score": eval.scores.skill_match_score,
                    "experience_score": eval.scores.experience_score,
                    "project_relevance_score": eval.scores.project_relevance_score,
                    "missing_must_have": eval.scores.missing_must_have,
                    "nice_to_have_covered": eval.scores.nice_to_have_covered,
                    "reasoning": eval.reasoning,
                    "extracted_skills": {
                        "technical_skills": eval.analysis.extracted_skills.technical_skills,
                        "tools_technologies": eval.analysis.extracted_skills.tools_technologies,
                        "years_experience": eval.analysis.extracted_skills.years_experience
                    },
                    "skill_matches": [
                        {
                            "skill": match.skill,
                            "found_in_resume": match.found_in_resume,
                            "match_type": match.match_type,
                            "confidence": match.confidence
                        }
                        for match in eval.skill_matches
                    ]
                }
                for i, eval in enumerate(report.ranked_candidates)
            ],
            "generated_at": report.generated_at.isoformat()
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report_dict, f, indent=2, ensure_ascii=False)
        
        console.print(f"[green]JSON report saved to: {output_path}[/green]")
        return str(output_path)
    
    def generate_csv_report(self, report: EvaluationReport, filename: str = None) -> str:
        """Generate CSV report with custom columns."""
        import csv
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"evaluation_summary_{timestamp}.csv"
        
        output_path = self.output_dir / filename
        
        rows = []
        rows = []
        for evaluation in report.ranked_candidates:
            # Top skills (first 5)
            top_skills = ', '.join([m.skill for m in evaluation.skill_matches if m.found_in_resume][:5])
            
            # Use AI recommendation and reasoning directly
            recommendation = evaluation.recommendation
            reasoning = evaluation.reasoning

            # Simplify columns for evaluation
            row = {
                'rank': evaluation.rank,
                'file_name': evaluation.file_name,
                'recommendation': recommendation,
                'skill_match': f"{evaluation.scores.skill_match_score}/100",
                'experience': f"{evaluation.scores.experience_score}/100",
                'project_relevance': f"{evaluation.scores.project_relevance_score}/100",
                'concerns': reasoning[:200] + "..." if len(reasoning) > 200 else reasoning,
                'top_skills': top_skills,
                'overall_evaluation': f"{evaluation.scores.overall_score}/100"
            }
            rows.append(row)
        
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['rank', 'file_name', 'recommendation', 'skill_match', 
                          'experience', 'project_relevance', 'concerns', 'top_skills', 'overall_evaluation']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            
            # Write rows with first row bold (using Excel-compatible formatting)
            for i, row in enumerate(rows):
                if i == 0:  # First row - make bold
                    for key in row:
                        if row[key]:  # Only add bold if value is not empty
                            row[key] = f"*{row[key]}*"
                writer.writerow(row)
        
        console.print(f"[green]CSV report saved to: {output_path}[/green]")
        return str(output_path)
    
    def generate_detailed_text_report(self, report: EvaluationReport, filename: str = None) -> str:
        """Generate detailed text report for each candidate."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"detailed_evaluation_{timestamp}.txt"
        
        output_path = self.output_dir / filename
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"RESUME EVALUATION REPORT\n")
            f.write(f"{'='*50}\n\n")
            f.write(f"Project: {report.project_requirements.project_title}\n")
            f.write(f"Generated: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Candidates: {report.total_resumes_evaluated}\n\n")
            
            # Summary
            summary = report.evaluation_summary
            f.write(f"SUMMARY STATISTICS\n")
            f.write(f"{'-'*20}\n")
            f.write(f"Suitable: {summary.get('suitable', 0)}\n")
            f.write(f"Might be suitable: {summary.get('might_be_suitable', 0)}\n")
            f.write(f"Not suitable: {summary.get('not_suitable', 0)}\n\n")
            
            # Detailed candidate analysis
            f.write(f"CANDIDATE DETAILS\n")
            f.write(f"{'='*50}\n\n")
            
            for i, evaluation in enumerate(report.ranked_candidates, 1):
                f.write(f"{i}. {evaluation.file_name}\n")
                f.write(f"{'-'*30}\n")
                f.write(f"Overall Score: {evaluation.scores.overall_score}/100\n")
                f.write(f"Recommendation: {evaluation.recommendation}\n")
                f.write(f"Reasoning: {evaluation.reasoning}\n\n")
                
                f.write(f"Skill Breakdown:\n")
                f.write(f"  Skill Match: {evaluation.scores.skill_match_score}/100\n")
                f.write(f"  Experience: {evaluation.scores.experience_score}/100\n")
                f.write(f"  Project Relevance: {evaluation.scores.project_relevance_score}/100\n\n")
                
                # Add experience explanation
                f.write(f"Experience Analysis:\n")
                if evaluation.scores.experience_score >= 80:
                    f.write(f"  • Strong experience level with relevant years of practice\n")
                    f.write(f"  • Experience aligns well with project requirements\n")
                elif evaluation.scores.experience_score >= 60:
                    f.write(f"  • Moderate experience level with some relevant background\n")
                    f.write(f"  • Experience partially meets project needs\n")
                elif evaluation.scores.experience_score >= 40:
                    f.write(f"  • Limited experience in required domain\n")
                    f.write(f"  • Experience may not fully meet project demands\n")
                else:
                    f.write(f"  • Insufficient experience for this role\n")
                    f.write(f"  • Significant experience gap identified\n")
                f.write(f"\n")
                
                # Add skill match explanation
                f.write(f"Skill Match Analysis:\n")
                if evaluation.scores.skill_match_score >= 80:
                    f.write(f"  • Excellent coverage of required skills\n")
                    f.write(f"  • Most critical skills are present\n")
                elif evaluation.scores.skill_match_score >= 60:
                    f.write(f"  • Good coverage of required skills\n")
                    f.write(f"  • Some important skills may be missing\n")
                elif evaluation.scores.skill_match_score >= 40:
                    f.write(f"  • Moderate skill coverage\n")
                    f.write(f"  • Several required skills are missing\n")
                else:
                    f.write(f"  • Poor skill coverage\n")
                    f.write(f"  • Many critical skills are absent\n")
                f.write(f"\n")
                
                f.write(f"Technical Skills: {', '.join(evaluation.analysis.extracted_skills.technical_skills)}\n")
                f.write(f"Tools/Technologies: {', '.join(evaluation.analysis.extracted_skills.tools_technologies)}\n")
                
                if evaluation.scores.missing_must_have:
                    f.write(f"Missing Must-Have: {', '.join(evaluation.scores.missing_must_have)}\n")
                
                if evaluation.scores.nice_to_have_covered:
                    f.write(f"Nice-to-Have Covered: {', '.join(evaluation.scores.nice_to_have_covered)}\n")
                
                f.write(f"\nExperience Summary: {evaluation.analysis.experience_summary}\n")
                f.write(f"\n{'='*50}\n\n")
        
        console.print(f"[green]Detailed text report saved to: {output_path}[/green]")
        return str(output_path)
    
    def generate_all_reports(self, report: EvaluationReport) -> Dict[str, str]:
        """Generate all report formats."""
        reports = {}
        
        try:
            reports['json'] = self.generate_json_report(report)
            reports['csv'] = self.generate_csv_report(report)
            reports['text'] = self.generate_detailed_text_report(report)
            
            console.print("[green]All reports generated successfully![/green]")
            
        except Exception as e:
            console.print(f"[red]Error generating reports: {e}[/red]")
        
        return reports
