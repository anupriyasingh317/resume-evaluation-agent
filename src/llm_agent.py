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
    
    def _call_llm(self, messages: List[Dict], model: str = "llama-3.1-8b-instant") -> str:
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
    
    def evaluate_skill_match(self, analysis: ResumeAnalysis, requirements: Requirements) -> List[SkillMatch]:
        """Evaluate how well resume skills match requirements."""
        
        all_resume_skills = (
            analysis.extracted_skills.technical_skills +
            analysis.extracted_skills.tools_technologies
        )
        
        skill_matches = []
        
        for required_skill in requirements.required_skills:
            match = self._find_skill_match(required_skill, all_resume_skills)
            skill_matches.append(match)
        
        return skill_matches
    
    def _find_skill_match(self, required_skill: str, resume_skills: List[str]) -> SkillMatch:
        """Find best match for a required skill in resume skills."""
        required_lower = required_skill.lower()
        
        # Exact match
        for skill in resume_skills:
            if skill.lower() == required_lower:
                return SkillMatch(
                    skill=required_skill,
                    found_in_resume=True,
                    match_type="exact",
                    confidence=1.0
                )
        
        # Semantic match (contains)
        for skill in resume_skills:
            if required_lower in skill.lower() or skill.lower() in required_lower:
                return SkillMatch(
                    skill=required_skill,
                    found_in_resume=True,
                    match_type="semantic",
                    confidence=0.8
                )
        
        # No match
        return SkillMatch(
            skill=required_skill,
            found_in_resume=False,
            match_type="none",
            confidence=0.0
        )
    
    def calculate_scores(self, analysis: ResumeAnalysis, requirements: Requirements, skill_matches: List[SkillMatch]) -> tuple[EvaluationScore, str]:
        """Calculate evaluation scores using LLM for nuanced analysis."""
        
        # Prepare data for LLM
        resume_data = {
            "technical_skills": analysis.extracted_skills.technical_skills,
            "tools": analysis.extracted_skills.tools_technologies,
            "experience": analysis.extracted_skills.years_experience,
            "experience_summary": analysis.experience_summary,
            "projects": analysis.projects
        }
        
        requirements_data = {
            "required_skills": requirements.required_skills,
            "must_have_skills": requirements.must_have_skills,
            "nice_to_have": requirements.nice_to_have_skills,
            "experience_level": requirements.experience_level,
            "project_type": requirements.project_type
        }
        
        prompt = f"""
        Evaluate this candidate against the job requirements and provide specific evaluation results:

        Candidate Profile:
        {json.dumps(resume_data, indent=2)}

        Job Requirements:
        {json.dumps(requirements_data, indent=2)}

        SCORING INSTRUCTIONS:
        1. Skill Match Score (FOLLOW THESE RULES EXACTLY):
           - STEP 1: List ALL must-have skills from requirements: {', '.join(requirements.must_have_skills)}
           - STEP 2: Check which of THESE EXACT SKILLS are missing from candidate
           - STEP 3: Apply EXACT scoring based on missing count:
             * 0 missing skills: 95-100/100
             * 1 missing skill: 90/100
             * 2 missing skills: 80/100
             * 3-4 missing skills: 70/100
             * 5+ missing skills: 60/100 or lower
           - CRITICAL: Only list skills that are ACTUALLY in the requirements above
           - WARNING: Do NOT invent skills that aren't in the requirements
           - VERIFICATION: Double-check your missing skills list matches the requirements skills

        2. Experience Evaluation:
           - Only determine YES or NO (no scoring)
           - Check if candidate's years match required experience range
           - Return "YES" if within range, "NO" if outside range

        3. Project Relevance:
           - Only determine YES or NO (no scoring)
           - If skill match score > 85: YES
           - If skill match score <= 85: NO
           - Consider project alignment and relevance

        4. Overall Score:
           - Weight: 70% skill match, 15% experience, 15% project relevance
           - Convert experience YES/NO to 100/0 for calculation
           - Convert project relevance YES/NO to 100/0 for calculation

        Return JSON with this structure:
        {{
            "overall_score": 85,
            "skill_match_score": 90,
            "experience_score": 100,
            "project_relevance_score": 100,
            "missing_must_have": ["skill1", "skill2"],
            "nice_to_have_covered": ["skill1", "skill2"],
            "reasoning": {{
                "overall": "Brief explanation of overall score",
                "skill_match": "Why this skill match score was given",
                "experience": "Experience evaluation (YES/NO with explanation)", 
                "project_relevance": "Project relevance evaluation (YES/NO with explanation)",
                "key_factors": "Main factors affecting the score",
                "concerns": "Any concerns about the candidate"
            }}
        }}

        Be precise in following the scoring rules above.
        """
        
        messages = [
            {"role": "system", "content": "You are an expert technical recruiter. Provide accurate, fair evaluations and return valid JSON only."},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = self._call_llm(messages)
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
            
            # Try to find the end of JSON object
            brace_count = 0
            end_pos = 0
            for i, char in enumerate(response):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end_pos = i + 1
                        break
            
            if end_pos > 0:
                response = response[:end_pos]
            
            # Clean up common JSON issues
            response = response.replace('\n', ' ').replace('\r', '')
            response = response.replace(',}', '}').replace(',]', ']')
            
            logger.info(f"Attempting to parse JSON: {response[:200]}...")
            
            data = json.loads(response)
            
            # Handle both old and new reasoning formats
            reasoning_data = data.get('reasoning', {})
            if isinstance(reasoning_data, dict):
                # New detailed format
                overall_reasoning = reasoning_data.get('overall', 'No detailed reasoning provided')
                skill_reasoning = reasoning_data.get('skill_match', '')
                experience_reasoning = reasoning_data.get('experience', '')
                project_reasoning = reasoning_data.get('project_relevance', '')
                key_factors = reasoning_data.get('key_factors', [])
                concerns = reasoning_data.get('concerns', [])
                
                # Build comprehensive reasoning
                detailed_reasoning = f"Overall: {overall_reasoning}"
                if skill_reasoning:
                    detailed_reasoning += f"\nSkill Match: {skill_reasoning}"
                if experience_reasoning:
                    detailed_reasoning += f"\nExperience: {experience_reasoning}"
                if project_reasoning:
                    detailed_reasoning += f"\nProject Relevance: {project_reasoning}"
                if key_factors:
                    detailed_reasoning += f"\nKey Strengths: {', '.join(key_factors)}"
                if concerns:
                    detailed_reasoning += f"\nConcerns: {', '.join(concerns)}"
            else:
                # Old simple format
                detailed_reasoning = str(reasoning_data) if reasoning_data else "No reasoning provided"
            
            return EvaluationScore(
                overall_score=data.get('overall_score', 0),
                skill_match_score=data.get('skill_match_score', 0),
                experience_score=data.get('experience_score', 0),
                project_relevance_score=data.get('project_relevance_score', 0),
                missing_must_have=data.get('missing_must_have', []),
                nice_to_have_covered=data.get('nice_to_have_covered', [])
            ), detailed_reasoning
            
        except Exception as e:
            logger.error(f"Error calculating scores: {e}")
            raise ValueError(f"LLM evaluation failed: {e}")
    
    def generate_recommendation(self, scores: EvaluationScore) -> str:
        """Generate recommendation based on scores."""
        if scores.overall_score >= 80:
            return "Strong Match"
        elif scores.overall_score >= 60:
            return "Partial Match"
        else:
            return "No Match"
    
    def evaluate_resume(self, resume_text: str, filename: str, requirements: Requirements) -> ResumeEvaluation:
        """Complete resume evaluation pipeline."""
        
        # Extract skills and information
        analysis = self.extract_resume_skills(resume_text, filename)
        
        # Evaluate skill matching
        skill_matches = self.evaluate_skill_match(analysis, requirements)
        
        # Calculate scores using matcher
        from .matcher import ResumeMatcher
        matcher = ResumeMatcher()
        scores, detailed_reasoning = matcher.calculate_overall_score(analysis, requirements, skill_matches)
        
        # Generate recommendation
        recommendation = self.generate_recommendation(scores)
        
        return ResumeEvaluation(
            file_name=filename,
            analysis=analysis,
            skill_matches=skill_matches,
            scores=scores,
            reasoning=detailed_reasoning,
            recommendation=recommendation
        )
