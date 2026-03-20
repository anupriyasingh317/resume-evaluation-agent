from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class Requirements(BaseModel):
    project_title: str
    required_skills: List[str]
    must_have_skills: List[str] = Field(default_factory=list)
    nice_to_have_skills: List[str] = Field(default_factory=list)
    experience_level: str
    project_type: str
    description: Optional[str] = None

class ResumeSkills(BaseModel):
    technical_skills: List[str] = Field(default_factory=list)
    soft_skills: List[str] = Field(default_factory=list)
    tools_technologies: List[str] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)
    years_experience: Optional[Dict[str, int]] = Field(default_factory=dict)

class ResumeAnalysis(BaseModel):
    file_name: str
    extracted_skills: ResumeSkills
    experience_summary: str
    education: Optional[str] = None
    projects: List[str] = Field(default_factory=list)
    raw_text: Optional[str] = None

class SkillMatch(BaseModel):
    skill: str
    found_in_resume: bool
    match_type: str  # "exact", "semantic", "related"
    confidence: float = Field(ge=0, le=1)

class EvaluationScore(BaseModel):
    overall_score: float = Field(ge=0, le=100)
    skill_match_score: float = Field(ge=0, le=100)
    experience_score: float = Field(ge=0, le=100)
    project_relevance_score: float = Field(ge=0, le=100)
    missing_must_have: List[str] = Field(default_factory=list)
    nice_to_have_covered: List[str] = Field(default_factory=list)

class ResumeEvaluation(BaseModel):
    file_name: str
    analysis: ResumeAnalysis
    skill_matches: List[SkillMatch]
    scores: EvaluationScore
    reasoning: str
    recommendation: str  # "Strong Match", "Partial Match", "No Match"
    evaluation_timestamp: datetime = Field(default_factory=datetime.now)
    rank: Optional[int] = None  # Add rank field

class EvaluationReport(BaseModel):
    project_requirements: Requirements
    total_resumes_evaluated: int
    ranked_candidates: List[ResumeEvaluation]
    evaluation_summary: Dict[str, Any]
    generated_at: datetime = Field(default_factory=datetime.now)
