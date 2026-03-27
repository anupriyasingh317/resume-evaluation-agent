# Resume Evaluation Agent

An LLM-powered intelligent resume screening and evaluation system that analyzes candidate resumes against project requirements and provides ranked recommendations.

## Features

- **Multi-format Support**: Process PDF, DOCX, and TXT resume files
- **LLM-Powered Analysis**: Uses advanced AI for skill extraction and semantic matching
- **Intelligent Scoring**: Weighted evaluation system with customizable criteria
- **Comprehensive Reports**: Generate JSON, CSV, and detailed text reports
- **Interactive Requirements**: Create and manage project requirements through CLI
- **Skill Gap Analysis**: Identify coverage across all candidates

## Quick Start

### 1. Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

### 2. Setup

```bash
# Initialize the system
python main.py setup
```

### 3. Configure LLM

Update the `.env` file with your LLM configuration:

```env
LITELLM_PROXY_API_KEY="your-api-key"
LITELLM_URL="https://your-llm-endpoint/chat/completions"
```

### 4. Add Resume Files

Place your resume files in the `resumes/` directory:
- PDF files (.pdf)
- Word documents (.docx)
- Text files (.txt)

### 5. Create Requirements

```bash
# Create interactive requirements
python main.py create-requirements

# Or edit config/requirements.json manually
```

### 6. Evaluate Resumes

```bash
# Evaluate all resumes
python main.py evaluate

# Evaluate single resume
python main.py single resume.pdf

# Use custom requirements file
python main.py evaluate --requirements custom_requirements.json
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `setup` | Initialize directories and configuration |
| `evaluate` | Evaluate all resumes in the directory |
| `single <file>` | Evaluate a single resume file |
| `create-requirements` | Create requirements interactively |
| `show-requirements` | Display current requirements |
| `list-resumes` | List available resume files |
| `status` | Check system setup status |

## Requirements Format

The system uses JSON for project requirements:

```json
{
  "project_title": "Full Stack Developer",
  "required_skills": ["Python", "SQL", "React", "AWS"],
  "must_have_skills": ["Python", "SQL"],
  "nice_to_have_skills": ["Docker", "Kubernetes"],
  "experience_level": "3+ years",
  "project_type": "Web application development",
  "description": "Looking for full-stack developer"
}
```

## Evaluation Process

1. **Resume Parsing**: Extract text from resume files
2. **Skill Extraction**: LLM analyzes and extracts technical skills, experience, and projects
3. **Skill Matching**: Semantic matching against requirements
4. **Scoring**: Weighted scoring across multiple dimensions
5. **Ranking**: Candidates ranked by overall score
6. **Reporting**: Comprehensive evaluation reports

## Scoring System

The evaluation uses weighted scoring:

- **Skill Match Score** (40%): How well skills match requirements
- **Experience Score** (30%): Years and relevance of experience
- **Project Relevance** (20%): Similarity of past projects
- **Bonus Skills** (10%): Coverage of nice-to-have skills

## Report Outputs

### Console Report
- Rich, colored terminal output
- Top candidates ranking
- Skill coverage analysis
- Summary statistics

### JSON Report
- Detailed structured data
- Complete evaluation results
- Skill match details
- API-ready format

### CSV Report
- Spreadsheet-friendly summary
- Key metrics for each candidate
- Easy data analysis

### Text Report
- Human-readable detailed analysis
- Individual candidate breakdowns
- Skill gap analysis

## Project Structure

```
resume_agent/
├── resumes/                 # Resume files (PDF, DOCX, TXT)
├── config/
│   └── requirements.json    # Project requirements
├── src/
│   ├── models.py           # Data models
│   ├── resume_processor.py # File parsing
│   ├── llm_agent.py        # LLM interactions
│   ├── requirements_manager.py # Requirements management
│   ├── matcher.py          # Skill matching & scoring
│   ├── report_generator.py # Report generation
│   └── orchestrator.py     # Main controller
├── outputs/evaluations/    # Generated reports
├── main.py                 # CLI interface
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

## Configuration

### Environment Variables

- `LITELLM_PROXY_API_KEY`: Your LLM API key
- `LITELLM_URL`: LLM endpoint URL

### Customization

You can customize scoring weights in `src/matcher.py`:

```python
self.score_weights = {
    'skill_match': 0.4,
    'experience': 0.3,
    'project_relevance': 0.2,
    'bonus_skills': 0.1
}
```

## Example Usage

```bash
# Quick evaluation with default settings
python main.py evaluate

# Custom requirements and output
python main.py evaluate --requirements senior_dev.json --output results/

# Check system status
python main.py status

# View available resumes
python main.py list-resumes

# Evaluate specific candidate
python main.py single john_doe.pdf
```

## Troubleshooting

### Common Issues

1. **LLM API Errors**: Check your `.env` configuration
2. **Resume Parsing Failures**: Ensure files are not corrupted or password-protected
3. **Missing Requirements**: Run `create-requirements` or check `config/requirements.json`
4. **No Resume Files**: Add files to the `resumes/` directory

### Debug Mode

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## License

This project is open source. See LICENSE file for details.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Run `python main.py status` to verify setup
3. Review log outputs for error details
