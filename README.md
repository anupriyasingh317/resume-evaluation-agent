# Resume Evaluation Agent

An intelligent LLM-powered resume screening and evaluation system with a modern web interface that analyzes candidate resumes against project requirements and provides ranked recommendations.

## Features

### 🌐 Web Interface
- **Modern UI**: Clean, responsive web interface for easy resume evaluation
- **Manual Requirements**: Interactive form to create job requirements manually
- **Job Description Upload**: AI-powered extraction from job descriptions
- **Real-time Evaluation**: Live progress tracking and instant results
- **Persistent Results**: Evaluation results persist across page reloads
- **CSV Download**: Download evaluation results as CSV reports

### 🤖 AI-Powered Analysis
- **Multi-format Support**: Process PDF, DOCX, and TXT resume files
- **LLM-Powered Analysis**: Advanced AI for skill extraction and semantic matching
- **Intelligent Scoring**: Context-aware evaluation with strict scoring rules
- **Cache-Busting**: Fresh LLM responses for accurate evaluations
- **Skill Gap Analysis**: Identify coverage across all candidates

### 📊 Smart Evaluation
- **Experience Validation**: Checks if candidate experience matches required range (e.g., 3-7 years)
- **Project Relevance**: Evaluates alignment of past projects with requirements
- **Clear Recommendations**: Simple categories: "Suitable", "Might be suitable", "Not suitable"
- **Color-Coded Results**: Visual indicators for quick pass/fail assessment

## Quick Start

### 1. Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

### 2. Setup

```bash
# Create required directories
mkdir -p resumes config outputs/evaluations
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

### 5. Start the Web Application

```bash
# Run the Flask web server
python app.py
```

### 6. Access the Application

Open your browser and navigate to:
- **Home**: http://localhost:5000
- **Manual Requirements**: http://localhost:5000/manual_requirements
- **Upload Job Description**: http://localhost:5000/upload_job_description
- **Evaluation**: http://localhost:5000/evaluate

## Web Interface Usage

### Creating Requirements

#### Option 1: Manual Requirements
1. Navigate to **Manual Requirements** page
2. Fill in project details:
   - Project Title/Position
   - Required Skills
   - Must-Have Skills
   - Nice-to-Have Skills
   - Experience Level
   - Project Type
   - Job Description
3. Click **"Save Requirements"**
4. Click **"Go to Evaluation"** to proceed

#### Option 2: Upload Job Description
1. Navigate to **Upload Job Description** page
2. Upload a job description file (PDF, DOCX, TXT)
3. AI automatically extracts requirements
4. Click **"Go to Evaluation"** to proceed

### Evaluating Candidates

1. **Load Requirements**: Requirements are automatically loaded
2. **Check Resumes**: System shows available resume files
3. **Start Evaluation**: Click **"Start Evaluation"** button
4. **View Results**: See ranked candidates with detailed analysis
5. **Download Report**: Export results as CSV

### Understanding Results

#### Candidate Cards Display:
- **Rank**: Candidate position (#1, #2, etc.)
- **File Name**: Resume file name
- **Skill Match**: YES/NO with missing skills highlighted
- **Experience**: YES/NO with years of experience
- **Project Relevance**: YES/NO with alignment assessment
- **Recommendation**: Suitable/Might be suitable/Not suitable

#### Color Coding:
- 🟢 **Green**: YES/Pass status
- 🔴 **Red**: NO/Fail status
- 🟡 **Yellow**: Partial/Warning status

## Evaluation Process

1. **Resume Parsing**: Extract text from resume files
2. **Skill Extraction**: LLM analyzes and extracts technical skills, experience, and projects
3. **Skill Matching**: Semantic matching against requirements with strict scoring
4. **Experience Validation**: Checks if experience falls within required range
5. **Project Relevance**: Evaluates alignment of past projects
6. **Recommendation**: Clear suitability categories
7. **Ranking**: Candidates ranked by overall assessment

## Scoring System

The evaluation uses intelligent assessment rather than numeric scores:

### Skill Match Evaluation
- **0 missing skills**: YES (95-100/100 equivalent)
- **1 missing skill**: YES (90/100 equivalent)
- **2 missing skills**: NO (80/100 equivalent)
- **3-4 missing skills**: NO (70/100 equivalent)
- **5+ missing skills**: NO (60/100 equivalent)

### Experience Evaluation
- **Within required range**: YES
- **Outside required range**: NO
- **Examples**: 
  - Required: "3-7 years" → 5 years = YES, 2 years = NO
  - Required: "5+ years" → 6 years = YES, 4 years = NO

### Project Relevance
- **Skill match > 85**: YES
- **Skill match ≤ 85**: NO

## Requirements Format

### Manual Requirements JSON Structure:
```json
{
  "project_title": "Senior Python Developer",
  "required_skills": ["Python", "Django", "PostgreSQL"],
  "must_have_skills": ["Python", "Django", "API Design"],
  "nice_to_have_skills": ["Docker", "Kubernetes", "AWS"],
  "experience_level": "5+ years",
  "project_type": "Web Application Development",
  "description": "Looking for experienced Python developer for web applications"
}
```

### Experience Level Examples:
- "3-7 years" - Range requirement
- "5+ years" - Minimum requirement
- "2-4 years" - Specific range
- "Entry level" - No specific years required

## Project Structure

```
resume_agent/
├── resumes/                    # Resume files (PDF, DOCX, TXT)
├── config/
│   ├── requirements.json       # Default requirements
│   ├── requirements_manual_*.json # Manual requirements
│   └── requirements_from_*.json  # Job description requirements
├── src/
│   ├── models.py              # Data models
│   ├── resume_processor.py    # File parsing
│   ├── llm_agent.py           # LLM interactions
│   ├── requirements_manager.py # Requirements management
│   ├── matcher.py             # Skill matching & scoring
│   ├── report_generator.py    # Report generation
│   └── orchestrator.py        # Main controller
├── templates/
│   ├── base.html              # Base template
│   ├── index.html             # Home page
│   ├── manual_requirements.html # Manual requirements form
│   ├── upload_job_description.html # Job description upload
│   └── evaluate.html         # Evaluation interface
├── app.py                     # Flask web application
├── requirements.txt           # Python dependencies
└── README.md                 # This file
```

## Configuration

### Environment Variables

- `LITELLM_PROXY_API_KEY`: Your LLM API key
- `LITELLM_URL`: LLM endpoint URL

### Flask Configuration

- `SECRET_KEY`: Session security key
- `UPLOAD_FOLDER`: Temporary file upload location
- `MAX_CONTENT_LENGTH`: Maximum file size (16MB)

## API Endpoints

### Requirements Management
- `POST /api/process_manual_requirements` - Save manual requirements
- `POST /api/upload_job_description` - Process job description
- `GET /api/check_requirements` - Load current requirements

### Evaluation
- `POST /api/evaluate` - Run resume evaluation
- `GET /api/list_resumes` - List available resumes
- `GET /api/download_csv` - Download CSV report

## Advanced Features

### Cache-Busting
- Automatic cache-busting for fresh LLM responses
- Unique request identifiers prevent stale results
- Consistent evaluation logic with minimal randomness

### Session Management
- Requirements persist across page navigation
- Evaluation results saved in sessionStorage
- Direct URL navigation with requirements parameters

### Error Handling
- Comprehensive error handling throughout the application
- User-friendly error messages
- Graceful fallbacks for missing files or data

## Troubleshooting

### Common Issues

1. **Requirements Not Loading**: 
   - Check if requirements file exists in `config/` folder
   - Verify manual requirements were saved successfully
   - Look for "Requirements file not found" errors

2. **Evaluation Not Starting**:
   - Ensure resume files are in `resumes/` directory
   - Check if requirements are loaded
   - Verify LLM API configuration in `.env`

3. **LLM Scoring Issues**:
   - Check LLM API key and URL in `.env`
   - Verify LLM endpoint is accessible
   - Look for "LLM API call failed" errors

4. **File Upload Problems**:
   - Ensure file size is under 16MB
   - Check file format (PDF, DOCX, TXT only)
   - Verify files are not password-protected

### Debug Mode

Enable detailed logging by checking browser console and Flask server logs.

### File Locations

- **Manual Requirements**: `config/requirements_manual_[timestamp].json`
- **Job Description Requirements**: `config/requirements_from_[filename].json`
- **Resume Files**: `resumes/` directory
- **Temporary Uploads**: `temp_uploads/` directory

## Example Workflow

1. **Start Application**: `python app.py`
2. **Create Requirements**: 
   - Visit `/manual_requirements`
   - Fill form with job details
   - Click "Save Requirements"
3. **Add Resumes**: Place PDF/DOCX files in `resumes/` folder
4. **Evaluate**: 
   - Visit `/evaluate`
   - Click "Start Evaluation"
   - Wait for AI analysis
5. **Review Results**: 
   - Check candidate rankings
   - Review skill match details
   - Download CSV report
6. **Make Decisions**: Use recommendations to shortlist candidates

## License

This project is open source. See LICENSE file for details.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review browser console for JavaScript errors
3. Check Flask server logs for backend errors
4. Verify file permissions and directory structure
