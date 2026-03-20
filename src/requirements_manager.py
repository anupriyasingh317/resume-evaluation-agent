import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from .models import Requirements

logger = logging.getLogger(__name__)

class RequirementsManager:
    """Manages project requirements loading and validation."""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.requirements_file = self.config_dir / "requirements.json"
    
    def load_requirements(self, file_path: Optional[str] = None) -> Requirements:
        """Load requirements from JSON file."""
        if file_path:
            # If file_path is just a filename, prepend config directory
            if not Path(file_path).parent or str(Path(file_path).parent) == '.':
                self.requirements_file = self.config_dir / file_path
            else:
                self.requirements_file = Path(file_path)
        
        if not self.requirements_file.exists():
            raise FileNotFoundError(f"Requirements file not found: {self.requirements_file}")
        
        try:
            with open(self.requirements_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return Requirements(**data)
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in requirements file: {e}")
            raise
        except Exception as e:
            logger.error(f"Error loading requirements: {e}")
            raise
    
    def save_requirements(self, requirements: Requirements, file_path: Optional[str] = None) -> None:
        """Save requirements to JSON file."""
        if file_path:
            self.requirements_file = Path(file_path)
        
        # Ensure directory exists
        self.requirements_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(self.requirements_file, 'w', encoding='utf-8') as f:
                json.dump(requirements.dict(), f, indent=2, ensure_ascii=False)
            
            logger.info(f"Requirements saved to: {self.requirements_file}")
            
        except Exception as e:
            logger.error(f"Error saving requirements: {e}")
            raise
    
    def create_interactive_requirements(self) -> Requirements:
        """Create requirements interactively through CLI prompts."""
        print("=== Create Project Requirements ===\n")
        
        # Basic project info
        project_title = input("Project Title: ").strip()
        project_type = input("Project Type (e.g., Web development, Data Science, etc.): ").strip()
        experience_level = input("Required Experience Level (e.g., 3+ years, Entry level, etc.): ").strip()
        description = input("Project Description (optional): ").strip() or None
        
        # Required skills
        print("\nRequired Skills (comma-separated):")
        required_skills_input = input().strip()
        required_skills = [skill.strip() for skill in required_skills_input.split(',') if skill.strip()]
        
        # Must-have skills
        print("\nMust-Have Skills (comma-separated, leave empty if none):")
        must_have_input = input().strip()
        must_have_skills = [skill.strip() for skill in must_have_input.split(',') if skill.strip()]
        
        # Nice-to-have skills
        print("\nNice-to-Have Skills (comma-separated, leave empty if none):")
        nice_to_have_input = input().strip()
        nice_to_have_skills = [skill.strip() for skill in nice_to_have_input.split(',') if skill.strip()]
        
        requirements = Requirements(
            project_title=project_title,
            required_skills=required_skills,
            must_have_skills=must_have_skills,
            nice_to_have_skills=nice_to_have_skills,
            experience_level=experience_level,
            project_type=project_type,
            description=description
        )
        
        # Save to file
        save_choice = input(f"\nSave requirements to {self.requirements_file}? (y/n): ").strip().lower()
        if save_choice == 'y':
            self.save_requirements(requirements)
        
        return requirements
    
    def validate_requirements(self, requirements: Requirements) -> Dict[str, Any]:
        """Validate requirements and return validation results."""
        issues = []
        warnings = []
        
        # Check required fields
        if not requirements.required_skills:
            issues.append("No required skills specified")
        
        if not requirements.project_title:
            issues.append("No project title specified")
        
        if not requirements.experience_level:
            warnings.append("No experience level specified")
        
        # Check skill overlaps
        all_skills = requirements.required_skills + requirements.must_have_skills + requirements.nice_to_have_skills
        duplicates = set([skill.lower() for skill in all_skills if all_skills.count(skill) > 1])
        if duplicates:
            warnings.append(f"Duplicate skills found: {', '.join(duplicates)}")
        
        # Check if must-have skills are in required skills
        missing_from_required = []
        for must_have in requirements.must_have_skills:
            if must_have not in requirements.required_skills:
                missing_from_required.append(must_have)
        
        if missing_from_required:
            warnings.append(f"Must-have skills not in required skills: {', '.join(missing_from_required)}")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "summary": f"Validation complete. {len(issues)} issues, {len(warnings)} warnings."
        }
    
    def display_requirements(self, requirements: Requirements) -> None:
        """Display requirements in a formatted way."""
        print(f"\n=== {requirements.project_title} ===")
        print(f"Project Type: {requirements.project_type}")
        print(f"Experience Level: {requirements.experience_level}")
        
        if requirements.description:
            print(f"Description: {requirements.description}")
        
        print(f"\nRequired Skills ({len(requirements.required_skills)}):")
        for skill in requirements.required_skills:
            print(f"  • {skill}")
        
        if requirements.must_have_skills:
            print(f"\nMust-Have Skills ({len(requirements.must_have_skills)}):")
            for skill in requirements.must_have_skills:
                print(f"  • {skill}")
        
        if requirements.nice_to_have_skills:
            print(f"\nNice-to-Have Skills ({len(requirements.nice_to_have_skills)}):")
            for skill in requirements.nice_to_have_skills:
                print(f"  • {skill}")
        
        print()
