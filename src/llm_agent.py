import os
import json
import logging
from typing import Dict, List, Optional
import openai
from dotenv import load_dotenv
from .models import ResumeAnalysis, ResumeSkills, Requirements, SkillMatch, EvaluationScore, ResumeEvaluation

load_dotenv()

logger = logging.getLogger(__name__)

class LLMAgent:
    """Handles LLM interactions for resume analysis and evaluation."""
    
    def __init__(self):
        self.api_key = os.getenv('LITELLM_PROXY_API_KEY')
        self.base_url = os.getenv('LITELLM_URL')
        
        if not self.api_key or not self.base_url:
            raise ValueError("Missing LLM configuration. Please check your .env file.")
        
        self.client = openai.OpenAI(
            api_key=self.api_key,
            base_url=self.base_url.replace('/chat/completions', '')
        )
    
    def _call_llm(self, messages: List[Dict], model: str = "standard") -> str:
        """Make a call to the LLM API with cache-busting for accuracy."""
        try:
            import time
            
            # Add minimal cache-busting to prevent stale results
            timestamp = time.time()
            
            # Add timestamp only to system message to break cache without affecting content
            enhanced_messages = []
            for msg in messages:
                if msg['role'] == 'system':
                    # Add minimal timestamp to prevent caching
                    enhanced_content = f"{msg['content']}\n\n[Cache-bust: {timestamp}]"
                    enhanced_messages.append({'role': msg['role'], 'content': enhanced_content})
                else:
                    enhanced_messages.append(msg)
            
            response = self.client.chat.completions.create(
                model=model,
                messages=enhanced_messages,
                temperature=0.3,  # Keep low for consistency and accuracy
                max_tokens=2000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"LLM API call failed: {e}")
            raise
    
    def extract_resume_skills(self, resume_text: str, filename: str) -> ResumeAnalysis:
        """Extract skills and information from resume text using LLM."""
        
        prompt = f"""
        Analyze the following resume and extract structured information in JSON format:

        Resume Text:
        {resume_text[:3000]}  # Limit text to avoid token limits

        Please extract and return a JSON object with this exact structure:
        {{
            "technical_skills": ["Python", "SQL", "React", ...],
            "soft_skills": ["Communication", "Leadership", ...],
            "tools_technologies": ["Docker", "AWS", "Git", ...],
            "certifications": ["AWS Certified", "Google Cloud", ...],
            "years_experience": {{
                "Python": 3,
                "SQL": 2,
                "total": 5
            }},
            "experience_summary": "Brief summary of candidate's experience",
            "education": "Highest degree and field",
            "projects": ["Project 1 description", "Project 2 description"]
        }}

        Focus on technical skills, tools, and quantifiable experience. Be specific and accurate.
        """
        
        messages = [
            {"role": "system", "content": "You are an expert resume analyzer. Extract structured information accurately and return valid JSON only."},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = self._call_llm(messages)
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
            
            data = json.loads(response)
            
            # Create ResumeSkills object
            skills = ResumeSkills(
                technical_skills=data.get('technical_skills', []),
                soft_skills=data.get('soft_skills', []),
                tools_technologies=data.get('tools_technologies', []),
                certifications=data.get('certifications', []),
                years_experience=data.get('years_experience', {})
            )
            
            # Create ResumeAnalysis object
            analysis = ResumeAnalysis(
                file_name=filename,
                extracted_skills=skills,
                experience_summary=data.get('experience_summary', ''),
                education=data.get('education'),
                projects=data.get('projects', []),
                raw_text=resume_text
            )
            
            return analysis
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.error(f"Response: {response}")
            raise ValueError("Invalid JSON response from LLM")
        except Exception as e:
            logger.error(f"Error in resume analysis: {e}")
            raise
    

    def evaluate_resume(self, resume_text: str, filename: str, requirements: Requirements) -> ResumeEvaluation:
        """Complete resume evaluation pipeline using AI-powered matcher."""
        
        # Extract skills and core information
        analysis = self.extract_resume_skills(resume_text, filename)
        
        # Perform combined evaluation (skills + scores) in one AI flow
        from .matcher import ResumeMatcher
        matcher = ResumeMatcher()
        scores, skill_matches, reasoning, recommendation = matcher.evaluate_candidate(analysis, requirements)
        
        return ResumeEvaluation(
            file_name=filename,
            analysis=analysis,
            skill_matches=skill_matches,
            scores=scores,
            reasoning=reasoning,
            recommendation=recommendation
        )
