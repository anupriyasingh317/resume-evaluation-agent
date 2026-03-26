import logging
import json
from typing import List, Dict, Tuple
from .models import ResumeEvaluation, Requirements, SkillMatch, EvaluationScore, ResumeAnalysis

logger = logging.getLogger(__name__)

class ResumeMatcher:
    """Handles AI-powered resume evaluation and ranking."""
    
    def __init__(self):
        """No manual weights needed for prompt-based scoring."""
        pass

    def evaluate_candidate(self, analysis: ResumeAnalysis, requirements: Requirements) -> Tuple[EvaluationScore, List[SkillMatch], str, str]:
        """Complete AI-powered evaluation in a single prompt."""
        
        # Prepare data for LLM
        resume_data = {
            "technical_skills": analysis.extracted_skills.technical_skills,
            "tools": analysis.extracted_skills.tools_technologies,
            "years_experience": analysis.extracted_skills.years_experience,
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
        
        prompt = f"""
        Perform a comprehensive technical evaluation of the candidate against the job requirements.
        
        Candidate Profile:
        {json.dumps(resume_data, indent=2)}
        
        Job Requirements:
        {json.dumps(requirements_data, indent=2)}
        
        TASK:
        1. Evaluate Skill Match: For each required skill (must-have and nice-to-have), determine if found and match type.
        2. Score Categories (0-100):
           - Skill Match: Strict alignment with technical requirements.
           - Experience: Relevance and level vs requirements.
           - Project Relevance: Alignment with our project type/industry.
        3. Determine Overall Score (0-100) and Recommendation.
        
        Return JSON format ONLY:
        {{
            "skill_matches": [
                {{
                    "skill": "skill_name",
                    "found_in_resume": true/false,
                    "match_type": "exact/semantic/related/none",
                    "confidence": 0.0-1.0
                }}
            ],
            "scores": {{
                "overall_score": 85,
                "skill_match_score": 90,
                "experience_score": 80,
                "project_relevance_score": 85
            }},
            "recommendation": "Suitable / Might be suitable / Not suitable",
            "missing_must_have": ["skill1"],
            "nice_to_have_covered": ["skill2"],
            "reasoning": "Comprehensive explanation of scores and recommendation"
        }}
        """
        
        messages = [
            {"role": "system", "content": "You are an expert technical recruiter. Provide precise JSON evaluations."},
            {"role": "user", "content": prompt}
        ]
        
        try:
            from .llm_agent import LLMAgent
            llm_agent = LLMAgent()
            response = llm_agent._call_llm(messages)
            
            # Extract and parse JSON
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].split("```")[0].strip()
            
            data = json.loads(response.strip())
            
            # Map back to objects
            skill_matches = [
                SkillMatch(**m) for m in data.get('skill_matches', [])
            ]
            
            scores_data = data.get('scores', {})
            scores = EvaluationScore(
                overall_score=scores_data.get('overall_score', 0),
                skill_match_score=scores_data.get('skill_match_score', 0),
                experience_score=scores_data.get('experience_score', 0),
                project_relevance_score=scores_data.get('project_relevance_score', 0),
                missing_must_have=data.get('missing_must_have', []),
                nice_to_have_covered=data.get('nice_to_have_covered', [])
            )
            
            return scores, skill_matches, data.get('reasoning', ''), data.get('recommendation', 'Not specified')
            
        except Exception as e:
            logger.error(f"AI evaluation failed: {e}")
            raise ValueError(f"AI evaluation failed: {e}")

    def rank_candidates(self, evaluations: List[ResumeEvaluation]) -> List[ResumeEvaluation]:
        """Rank candidates by score."""
        ranked = sorted(evaluations, key=lambda x: x.scores.overall_score, reverse=True)
        for i, eval in enumerate(ranked, 1):
            eval.rank = i
        return ranked

    def get_evaluation_summary(self, evaluations: List[ResumeEvaluation]) -> Dict:
        """Generate high-level report summary."""
        if not evaluations:
            return {"total_candidates": 0}
            
        total = len(evaluations)
        scores = [e.scores.overall_score for e in evaluations]
        
        return {
            "total_candidates": total,
            "suitable": len([e for e in evaluations if "Suitable" in e.recommendation and "Might" not in e.recommendation]),
            "might_be_suitable": len([e for e in evaluations if "Might be suitable" in e.recommendation]),
            "not_suitable": len([e for e in evaluations if "Not suitable" in e.recommendation]),
            "average_score": round(sum(scores)/total, 1),
            "top_score": max(scores)
        }

    def find_skill_gaps(self, evaluations: List[ResumeEvaluation], requirements: Requirements) -> Dict:
        """Analyze missing skills across pipeline."""
        gaps = {}
        for skill in requirements.required_skills:
            found = len([e for e in evaluations if any(m.skill == skill and m.found_in_resume for m in e.skill_matches)])
            gaps[skill] = {
                "coverage_percentage": round((found / len(evaluations) * 100) if evaluations else 0, 1),
                "found_in_candidates": found,
                "missing_in_candidates": len(evaluations) - found
            }
        return gaps
