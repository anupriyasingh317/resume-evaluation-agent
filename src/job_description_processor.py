import logging
from pathlib import Path
from typing import Dict, List, Optional
from .resume_processor import ResumeProcessor
from .llm_agent import LLMAgent
from .models import Requirements

logger = logging.getLogger(__name__)

class JobDescriptionProcessor:
    """Process job description files and extract requirements."""
    
    def __init__(self, resume_dir: str = "resumes"):
        self.resume_processor = ResumeProcessor(resume_dir)
        self.llm_agent = LLMAgent()
    
    def extract_requirements_from_file(self, file_path: Path) -> Requirements:
        """Extract requirements from job description file (PDF/DOCX/TXT)."""
        
        # Extract text from job description file
        job_text = self.resume_processor.extract_text(file_path)
        
        if not job_text.strip():
            raise ValueError(f"No text could be extracted from {file_path}")
        
        # Use LLM to parse job description and extract requirements
        requirements = self._parse_job_description_with_llm(job_text, file_path.name)
        
        return requirements
    
    def _parse_job_description_with_llm(self, job_text: str, filename: str) -> Requirements:
        """Use LLM to parse job description and extract structured requirements."""
        
        prompt = f"""
        Analyze this job description and extract the requirements in a structured format:

        Job Description:
        {job_text}

        Extract the following information:
        1. Project title or position name
        2. Required technical skills (must-have)
        3. Nice-to-have skills (optional but preferred)
        4. Experience level required
        5. Project type/area (e.g., web development, data science, devops)
        6. Brief description of the role

        Return JSON with this exact format:
        {{
            "project_title": "Job Title or Project Name",
            "required_skills": ["skill1", "skill2", "skill3"],
            "must_have_skills": ["skill1", "skill2"],
            "nice_to_have_skills": ["optional1", "optional2"],
            "experience_level": "3+ years",
            "project_type": "web development, data science",
            "description": "Brief role description"
        }}

        Guidelines:
        - Required skills should be essential skills mentioned in the job
        - Must-have skills are the most critical required skills
        - Nice-to-have are preferred but not essential
        - Experience level should match what's mentioned (e.g., "3+ years", "5+ years", "Entry level")
        - Project type should be the main area (e.g., "backend development", "full-stack", "data science", "devops")
        """
        
        messages = [
            {"role": "system", "content": "You are an expert HR analyst. Extract job requirements accurately and return valid JSON only."},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = self.llm_agent._call_llm(messages)
            
            # Clean and parse JSON response
            response = response.strip()
            
            # Extract JSON from response
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                response = response[start:end].strip()
            elif "```" in response:
                start = response.find("```") + 3
                end = response.find("```", start)
                response = response[start:end].strip()
            
            # Find JSON object start
            if response.startswith('{'):
                pass
            elif '{' in response:
                start = response.find('{')
                response = response[start:]
            
            import json
            data = json.loads(response)
            
            # Create Requirements object
            requirements = Requirements(
                project_title=data.get('project_title', f'Job from {filename}'),
                required_skills=data.get('required_skills', []),
                must_have_skills=data.get('must_have_skills', []),
                nice_to_have_skills=data.get('nice_to_have_skills', []),
                experience_level=data.get('experience_level', 'Not specified'),
                project_type=data.get('project_type', 'General'),
                description=data.get('description', 'Job description processed from file')
            )
            
            return requirements
            
        except Exception as e:
            logger.error(f"Error parsing job description: {e}")
            raise ValueError(f"Failed to parse job description from {filename}: {e}")
    
    def save_requirements(self, requirements: Requirements, output_path: Path) -> None:
        """Save extracted requirements to JSON file."""
        import json
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(requirements.dict(), f, indent=2, ensure_ascii=False)
        
        logger.info(f"Requirements saved to: {output_path}")
    
    def process_job_description(self, file_path: Path, output_dir: Optional[Path] = None) -> Requirements:
        """Complete pipeline: process job description file and save requirements."""
        
        if output_dir is None:
            output_dir = Path("config")
        
        # Extract requirements
        requirements = self.extract_requirements_from_file(file_path)
        
        # Save to config file
        output_filename = f"requirements_from_{file_path.stem}.json"
        output_path = output_dir / output_filename
        self.save_requirements(requirements, output_path)
        
        return requirements
