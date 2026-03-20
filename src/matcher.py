import logging
import json
from typing import List, Dict, Tuple
from .models import ResumeEvaluation, Requirements, SkillMatch, EvaluationScore, ResumeAnalysis

logger = logging.getLogger(__name__)

class ResumeMatcher:
    """Handles skill matching and scoring logic for resume evaluation."""
    
    def __init__(self):
        self.skill_weights = {
            'exact_match': 1.0,
            'semantic_match': 0.8,
            'related_match': 0.6
        }
        
        self.score_weights = {
            'skill_match': 0.4,
            'experience': 0.3,
            'project_relevance': 0.2,
            'bonus_skills': 0.1
        }
    
    def calculate_overall_score(self, analysis: ResumeAnalysis, requirements: Requirements, skill_matches: List[SkillMatch]) -> tuple[EvaluationScore, str]:
        """Calculate all scores using LLM instead of manual calculations."""
        
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
            "nice_to_have_skills": requirements.nice_to_have_skills,
            "experience_level": requirements.experience_level,
            "project_type": requirements.project_type
        }
        
        skill_matches_data = [
            {
                "skill": match.skill,
                "found_in_resume": match.found_in_resume,
                "match_type": match.match_type,
                "confidence": match.confidence
            }
            for match in skill_matches
        ]
        
        prompt = f"""
        Evaluate this candidate comprehensively and provide scores (0-100) for each category:

        Candidate Profile:
        {json.dumps(resume_data, indent=2)}

        Job Requirements:
        {json.dumps(requirements_data, indent=2)}

        Skill Matches:
        {json.dumps(skill_matches_data, indent=2)}

        SCORING GUIDELINES:
        - Be STRICT and realistic about skill matching
        - If candidate lacks MUST-HAVE skills, overall score should be below 50
        - Consider semantic skill matches and related technologies
        - Experience score should reflect relevance, not just years
        - Project relevance must match the job type (backend, devops)
        - Overall score should reflect actual suitability for the role

        Return JSON with this structure:
        {{
            "overall_score": 85,
            "skill_match_score": 90,
            "experience_score": 80,
            "project_relevance_score": 85,
            "missing_must_have": ["skill1", "skill2"],
            "nice_to_have_covered": ["skill1", "skill2"],
            "reasoning": {{
                "overall": "Explanation of overall score",
                "skill_match": "Why this skill match score",
                "experience": "Why this experience score",
                "project_relevance": "Why this project relevance score",
                "key_factors": ["Key positive factors"],
                "concerns": ["Key concerns or gaps"]
            }}
        }}

        Be critical - not everyone deserves a high score!
        """
        
        messages = [
            {"role": "system", "content": "You are an expert technical recruiter. Provide accurate, fair evaluations and return valid JSON only."},
            {"role": "user", "content": prompt}
        ]
        
        try:
            from .llm_agent import LLMAgent
            llm_agent = LLMAgent()
            response = llm_agent._call_llm(messages)
            
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
            
            # Handle reasoning
            reasoning_data = data.get('reasoning', {})
            if isinstance(reasoning_data, dict):
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
            logger.error(f"Error in LLM scoring: {e}")
            raise ValueError(f"LLM scoring failed: {e}")
    
    def rank_candidates(self, evaluations: List[ResumeEvaluation]) -> List[ResumeEvaluation]:
        """Rank candidates by overall score."""
        # Sort by overall score descending
        ranked = sorted(evaluations, key=lambda x: x.scores.overall_score, reverse=True)
        
        # Add rank information
        for i, evaluation in enumerate(ranked, 1):
            evaluation.rank = i
        
        return ranked
    
    def get_evaluation_summary(self, evaluations: List[ResumeEvaluation]) -> Dict:
        """Generate summary statistics for evaluations."""
        if not evaluations:
            return {
                "total_candidates": 0,
                "strong_matches": 0,
                "partial_matches": 0,
                "no_matches": 0,
                "average_score": 0.0,
                "top_score": 0.0
            }
        
        total = len(evaluations)
        strong_matches = len([e for e in evaluations if e.recommendation == "Strong Match"])
        partial_matches = len([e for e in evaluations if e.recommendation == "Partial Match"])
        no_matches = len([e for e in evaluations if e.recommendation == "No Match"])
        
        scores = [e.scores.overall_score for e in evaluations]
        average_score = sum(scores) / total
        top_score = max(scores)
        
        return {
            "total_candidates": total,
            "strong_matches": strong_matches,
            "partial_matches": partial_matches,
            "no_matches": no_matches,
            "average_score": round(average_score, 1),
            "top_score": top_score,
            "score_distribution": {
                "90+": len([s for s in scores if s >= 90]),
                "80-89": len([s for s in scores if 80 <= s < 90]),
                "70-79": len([s for s in scores if 70 <= s < 80]),
                "60-69": len([s for s in scores if 60 <= s < 70]),
                "below_60": len([s for s in scores if s < 60])
            }
        }
    
    def _find_skill_match(self, required_skill: str, resume_skills: List[str]) -> SkillMatch:
        """Find best match for a required skill in resume skills."""
        required_lower = required_skill.lower()
        
        # Special handling for .NET
        if required_lower == "dotnet":
            dotnet_keywords = [
                ".net", "c#", "asp.net", "asp.net core", "dotnet", 
                "entity framework", "microsoft .net", "visual studio",
                "maui", "xamarin", "wpf", "winforms"
            ]
            for skill in resume_skills:
                skill_lower = skill.lower()
                if any(keyword in skill_lower for keyword in dotnet_keywords):
                    return SkillMatch(
                        skill=required_skill,
                        found_in_resume=True,
                        match_type="semantic",
                        confidence=0.9
                    )
        
        # Special handling for AWS
        elif required_lower == "aws":
            aws_keywords = [
                "aws", "amazon web services", "ec2", "s3", "lambda",
                "rds", "dynamodb", "cloudfront", "route 53", "sns",
                "sqs", "cloudformation", "terraform"
            ]
            for skill in resume_skills:
                skill_lower = skill.lower()
                if any(keyword in skill_lower for keyword in aws_keywords):
                    return SkillMatch(
                        skill=required_skill,
                        found_in_resume=True,
                        match_type="semantic",
                        confidence=0.9
                    )
        
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

    def evaluate_skill_match(self, analysis: ResumeAnalysis, requirements: Requirements) -> List[SkillMatch]:
        """Evaluate how well resume skills match requirements using LLM."""
        
        # Prepare data for LLM
        resume_skills = (
            analysis.extracted_skills.technical_skills +
            analysis.extracted_skills.tools_technologies
        )
        
        prompt = f"""
        Analyze this candidate's skills against the job requirements and determine skill matches:

        Candidate Skills:
        {json.dumps(resume_skills, indent=2)}

        Job Requirements:
        Required Skills: {requirements.required_skills}
        Must-Have Skills: {requirements.must_have_skills}
        Nice-to-Have Skills: {requirements.nice_to_have_skills}

        For each required skill, determine if it's found in the candidate's profile. Consider:
        - Exact skill matches
        - Semantic equivalents (e.g., "C#" for ".NET", "PostgreSQL" for "SQL")
        - Related technologies and frameworks
        - Experience level indicators

        Return JSON with this format:
        {{
            "skill_matches": [
                {{
                    "skill": "skill_name",
                    "found_in_resume": true/false,
                    "match_type": "exact/semantic/related/none",
                    "confidence": 0.0-1.0,
                    "evidence": "Specific skill or evidence from resume"
                }}
            ]
        }}

        Be thorough in semantic matching - "Python" could match "Django", "SQL" could match "PostgreSQL", etc.
        """
        
        messages = [
            {"role": "system", "content": "You are an expert technical recruiter. Analyze skill matches accurately and return valid JSON only."},
            {"role": "user", "content": prompt}
        ]
        
        try:
            from .llm_agent import LLMAgent
            llm_agent = LLMAgent()
            response = llm_agent._call_llm(messages)
            
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
            
            # Convert to SkillMatch objects
            skill_matches = []
            for match_data in data.get('skill_matches', []):
                skill_matches.append(SkillMatch(
                    skill=match_data['skill'],
                    found_in_resume=match_data['found_in_resume'],
                    match_type=match_data['match_type'],
                    confidence=match_data['confidence']
                ))
            
            return skill_matches
            
        except Exception as e:
            logger.error(f"Error in LLM skill matching: {e}")
            # Fallback to keyword-based matching
            return self._fallback_skill_matching(resume_skills, requirements.required_skills)
    
    def _fallback_skill_matching(self, resume_skills: List[str], required_skills: List[str]) -> List[SkillMatch]:
        """Fallback keyword-based skill matching."""
        skill_matches = []
        
        for required_skill in required_skills:
            match = self._find_skill_match(required_skill, resume_skills)
            skill_matches.append(match)
        
        return skill_matches
    
    def find_skill_gaps(self, evaluations: List[ResumeEvaluation], requirements: Requirements) -> Dict[str, Dict]:
        """Analyze skill gaps across all candidates."""
        skill_analysis = {}
        
        for skill in requirements.required_skills:
            skill_analysis[skill] = {
                "found_in_candidates": 0,
                "missing_in_candidates": 0,
                "total_candidates": len(evaluations),
                "coverage_percentage": 0
            }
        
        for evaluation in evaluations:
            for match in evaluation.skill_matches:
                if match.skill in skill_analysis:
                    if match.found_in_resume:
                        skill_analysis[match.skill]["found_in_candidates"] += 1
                    else:
                        skill_analysis[match.skill]["missing_in_candidates"] += 1
        
        # Calculate percentages
        for skill, data in skill_analysis.items():
            if data["total_candidates"] > 0:
                data["coverage_percentage"] = round(
                    (data["found_in_candidates"] / data["total_candidates"]) * 100, 1
                )
        
        return skill_analysis
