# 🤖 Resume Evaluation Agent

An AI-powered intelligent resume screening and evaluation system. It leverages Large Language Models (LLMs) to analyze candidate resumes against specific project requirements, providing ranked recommendations with detailed reasoning.

Now featuring a **Modern Web Interface** for easier interaction and management!

---

## 🌟 Key Features

### 🖥️ Web Interface
- **Interactive Requirements**: Create project requirements via an intuitive form or upload existing ones.
- **JD Parsing**: Upload a Job Description (PDF/DOCX/TXT) and let AI automatically extract the core requirements.
- **Resume Management**: Effortlessly upload and manage resume files through the UI.
- **Real-time Evaluation**: Watch the evaluation progress in real-time with visual status updates.
- **Comprehensive Rankings**: View candidates ranked by quality with detailed score breakdowns.
- **Detailed Insights**: Access AI-generated reasoning, skill gap analysis, and interview recommendations for every candidate.
- **Export Reports**: One-click downloads for professional PDF and CSV evaluation reports.

### ⚙️ Core Engine & CLI
- **Multi-format Support**: Native processing for PDF, DOCX, and TXT resume files.
- **LLM-Powered Analysis**: Uses LiteLLM for advanced skill extraction and semantic matching.
- **Intelligent Scoring**: Multi-dimensional weighted evaluation system:
    - **Skill Match** (40%)
    - **Experience Relevance** (30%)
    - **Project Alignment** (20%)
    - **Bonus Skills** (10%)
- **Robust CLI**: Comprehensive command-line interface for automation and advanced configuration.

---

## 🚀 Quick Start

### 1. Installation

```bash
# Clone the repository and navigate to it
cd resume-evaluation-agent

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

Update the `.env` file with your LLM provider details (using LiteLLM):

```env
LITELLM_PROXY_API_KEY="your-api-key"
LITELLM_URL="https://your-llm-endpoint/chat/completions"
```

### 3. Launch the Web UI (Recommended)

Start the Flask application:

```bash
python app.py
```
Open your browser and navigate to `http://localhost:5001`.

---

## 🛠️ CLI Usage

For power users, the CLI offers granular control over the evaluation process.

### Basic Commands

| Command | Action |
|---------|--------|
| `python main.py setup` | Initialize directories and local configuration. |
| `python main.py evaluate` | Evaluate all resumes in the `resumes/` folder. |
| `python main.py single <file>` | Analyze a specific resume file. |
| `python main.py create-requirements` | Interactive tool to build requirement JSONs. |
| `python main.py status` | Verify your environment and LLM connection. |

---

## 🏗️ Project Structure

```text
resume_agent/
├── app.py                  # Flask Web Application entry point
├── main.py                 # CLI Tool entry point
├── src/                    # Core Logic
│   ├── orchestrator.py     # Main system controller
│   ├── llm_agent.py        # AI Analysis engine
│   ├── resume_processor.py # Multi-format file parsing
│   ├── matcher.py          # Scoring and ranking logic
│   └── report_generator.py # PDF/CSV/Text report generation
├── templates/              # Web UI HTML templates
├── config/                 # Requirements and settings
├── resumes/                # Default directory for resume files
├── outputs/                # Generated reports and logs
└── requirements.txt        # Project dependencies
```

---

## 📊 Evaluation Logic

The agent doesn't just look for keywords; it performs a **semantic analysis**:

1.  **Parsing**: Extracts text and structure from various file formats.
2.  **Extraction**: AI identifies technical skills, soft skills, years of experience, and project domains.
3.  **Matching**: Compares extracted data against "Must-have" and "Nice-to-have" requirements.
4.  **Scoring**: Calculates a weighted score based on match depth and relevance.
5.  **Reasoning**: Generates human-readable feedback on why a candidate is (or isn't) a fit.

---

## 📝 Troubleshooting

- **LLM Connection**: Ensure your `LITELLM_PROXY_API_KEY` is valid and you have network access to the endpoint.
- **File Parsing**: Scanned PDFs (images) might require OCR; the current system excels with text-based documents.
- **Port Conflict**: If port `5001` is busy, change it in `app.py` or use the `PORT` environment variable.

---

## ⚖️ License

This project is licensed under the MIT License - see the LICENSE file for details.
