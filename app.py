from flask import Flask, render_template, request, jsonify, session, send_file
from werkzeug.utils import secure_filename
import os
import re
from pathlib import Path
from src.orchestrator import ResumeEvaluationAgent
from src.models import Requirements
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = 'resume_evaluation_secret_key'
app.config['UPLOAD_FOLDER'] = 'temp_uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Global variable to store current evaluation results
evaluation_results = None

# Initialize agent
agent = ResumeEvaluationAgent()

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx', 'doc'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.after_request
def add_cache_busting_headers(response):
    """Add cache-busting headers to prevent caching of evaluation results."""
    if request.endpoint.startswith('api/'):
        # Prevent caching for API endpoints
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        response.headers['X-Accel-Expires'] = '0'
    return response

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/manual_requirements')
def manual_requirements():
    return render_template('manual_requirements.html')

@app.route('/upload_job_description')
def upload_job_description():
    return render_template('upload_job_description.html')

@app.route('/evaluate')
def evaluate_page():
    # Check if requirements file is passed as parameter
    requirements_file = request.args.get('requirements')
    if requirements_file:
        # Store in session for the evaluation page to use
        session['current_requirements_file'] = requirements_file
    
    return render_template('evaluate.html')

@app.route('/api/process_manual_requirements', methods=['POST'])
def process_manual_requirements():
    try:
        data = request.get_json()
        
        # Create requirements from manual input
        requirements = Requirements(
            project_title=data.get('project_title', 'Manual Requirements'),
            required_skills=data.get('required_skills', []),
            must_have_skills=data.get('must_have_skills', []),
            nice_to_have_skills=data.get('nice_to_have_skills', []),
            experience_level=data.get('experience_level', 'Not specified'),
            project_type=data.get('project_type', 'General'),
            description=data.get('description', 'Manually entered requirements')
        )
        
        # Save requirements to config directory with timestamp
        import time
        import os
        
        # Ensure config directory exists
        config_dir = "config"
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)
        
        timestamp = int(time.time())
        requirements_file = f"requirements_manual_{timestamp}.json"
        
        # Ensure we're saving to the config directory
        full_path = f"config/{requirements_file}"
        agent.requirements_manager.save_requirements(requirements, full_path)
        
        # Verify file was saved
        if not os.path.exists(full_path):
            return jsonify({'success': False, 'error': f'Failed to save requirements file: {full_path}'})
        
        print(f"Requirements saved to: {full_path}")  # Debug print
        
        # Store requirements file in session
        session['current_requirements_file'] = requirements_file
        
        return jsonify({
            'success': True,
            'requirements_file': requirements_file,
            'requirements': {
                'project_title': requirements.project_title,
                'must_have_skills': requirements.must_have_skills,
                'experience_level': requirements.experience_level,
                'project_type': requirements.project_type
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/upload_job_description', methods=['POST'])
def upload_job_description_api():
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'})
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'})
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Process job description
            requirements = agent.process_job_description_file(filename, is_temp_upload=True)
            
            # Store requirements file in session
            requirements_file = f"requirements_from_{Path(filename).stem}.json"
            session['current_requirements_file'] = requirements_file
            
            return jsonify({
                'success': True,
                'requirements_file': requirements_file,
                'requirements': {
                    'project_title': requirements.project_title,
                    'must_have_skills': requirements.must_have_skills,
                    'experience_level': requirements.experience_level,
                    'project_type': requirements.project_type
                }
            })
        
        return jsonify({'success': False, 'error': 'Invalid file type'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/evaluate', methods=['POST'])
def evaluate_resumes():
    try:
        data = request.get_json()
        requirements_file = data.get('requirements_file')
        
        if not requirements_file:
            return jsonify({'success': False, 'error': 'No requirements file specified'})
        
        # Run evaluation without auto-saving reports
        report = agent.run_evaluation(requirements_file, generate_reports=False)
        
        # Convert report to JSON-serializable format using CSV logic
        result = {
            'success': True,
            'summary': {
                'total_candidates': report.total_resumes_evaluated,
                'project_title': report.project_requirements.project_title,
                'suitable': len([e for e in report.ranked_candidates if e.recommendation.startswith('Suitable')]),
                'might_be_suitable': len([e for e in report.ranked_candidates if e.recommendation.startswith('Might be suitable')]),
                'not_suitable': len([e for e in report.ranked_candidates if e.recommendation.startswith('Not suitable')])
            },
            'candidates': []
        }
        
        for i, evaluation in enumerate(report.ranked_candidates, 1):
            reasoning_lines = evaluation.reasoning.split('\n')
            overall_reasoning = reasoning_lines[0] if reasoning_lines else "No reasoning"
            
            # Extract reasoning components like CSV does
            skill_match_reasoning = ""
            experience_reasoning = ""
            project_relevance_reasoning = ""
            concerns = ""
            
            for line in reasoning_lines:
                if "Skill Match:" in line:
                    skill_match_reasoning = line.replace("Skill Match:", "").strip()
                elif "Experience:" in line:
                    experience_reasoning = line.replace("Experience:", "").strip()
                elif "Project Relevance:" in line:
                    project_relevance_reasoning = line.replace("Project Relevance:", "").strip()
                elif "Concerns:" in line:
                    concerns = line.replace("Concerns:", "").strip()
            
            # Fallback if no LLM experience reasoning found
            if not experience_reasoning:
                experience_years = evaluation.analysis.extracted_skills.years_experience.get('total', 0)
                experience_reasoning = f"{experience_years} years experience"
            
            # Experience status - use LLM's YES/NO evaluation
            experience_status = "YES"
            if "NO" in experience_reasoning.upper() or "not within" in experience_reasoning.lower():
                experience_status = "NO"
            
            # Add experience years info if available
            experience_reasoning_text = experience_reasoning.lower()
            cand_years = None
            if re.search(r'(\d+)\s*years?', experience_reasoning_text):
                cand_years = int(re.search(r'(\d+)\s*years?', experience_reasoning_text).group(1))
                if cand_years:
                    experience_status += f" ({cand_years} years)"
            
            # Project relevance status - use LLM's YES/NO evaluation
            project_status = "YES"
            if "NO" in project_relevance_reasoning.upper() or "limited" in project_relevance_reasoning.lower():
                project_status = "NO"
            
            # Apply strict recommendation criteria
            # Check if all conditions are met for "Suitable"
            skill_score_high = evaluation.scores.skill_match_score >= 90
            experience_good = "NO" not in experience_status.upper()
            project_relevant = "NO" not in project_status.upper()
            
            if skill_score_high and experience_good and project_relevant and not evaluation.scores.missing_must_have:
                recommendation = f"Suitable: {overall_reasoning}"
            elif evaluation.scores.missing_must_have:
                recommendation = f"Not suitable: Missing critical skills ({', '.join(evaluation.scores.missing_must_have)})"
            else:
                recommendation = f"Might be suitable: {overall_reasoning}"
            
            # Skill match status - NO if missing must-have skills
            if evaluation.scores.missing_must_have:
                skill_match_status = f"NO (Missing: {', '.join(evaluation.scores.missing_must_have)})"
            else:
                skill_match_status = "YES"
            
            # Determine if passed screening - must have all must-have skills
            passed_screening = evaluation.scores.overall_score >= 60 and not evaluation.scores.missing_must_have
            
            candidate = {
                'rank': i,
                'file_name': evaluation.file_name,
                'overall_score': evaluation.scores.overall_score,
                'recommendation': recommendation,
                'reasoning': overall_reasoning,
                'skill_match_score': evaluation.scores.skill_match_score,
                'experience_score': evaluation.scores.experience_score,
                'project_relevance_score': evaluation.scores.project_relevance_score,
                'missing_must_have': evaluation.scores.missing_must_have,
                'nice_to_have_covered': evaluation.scores.nice_to_have_covered,
                'top_skills': evaluation.analysis.extracted_skills.technical_skills[:5],
                'passed_screening': passed_screening,
                # Add CSV-style detailed info
                'skill_match': f"{skill_match_status}: {skill_match_reasoning}",
                'experience': f"{experience_status}: {experience_reasoning}",
                'project_relevance': f"{project_status}: {project_relevance_reasoning}",
                'concerns': concerns[:100] + "..." if len(concerns) > 100 else concerns
            }
            result['candidates'].append(candidate)
        
        # Store results globally for download functionality
        global evaluation_results
        evaluation_results = result
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/check_requirements')
def check_requirements():
    try:
        # First check if requirements file is passed as parameter (for direct navigation)
        requirements_file = request.args.get('requirements')
        
        if not requirements_file:
            # Fall back to session-based check
            if 'current_requirements_file' in session:
                requirements_file = session['current_requirements_file']
            else:
                # Fallback: Try to load the most recent requirements file
                config_dir = Path('config')
                requirements_files = list(config_dir.glob('requirements_*.json'))
                
                if requirements_files:
                    # Get the most recent file
                    latest_file = max(requirements_files, key=lambda f: f.stat().st_mtime)
                    requirements_file = latest_file.name
                else:
                    return jsonify({'success': False, 'error': 'No requirements file found'})
        
        try:
            requirements = agent.requirements_manager.load_requirements(requirements_file)
            
            # Update session with the current requirements file
            session['current_requirements_file'] = requirements_file
            
            return jsonify({
                'success': True,
                'requirements_file': requirements_file,
                'requirements': {
                    'project_title': requirements.project_title,
                    'must_have_skills': requirements.must_have_skills,
                    'experience_level': requirements.experience_level,
                    'project_type': requirements.project_type
                }
            })
        except FileNotFoundError:
            return jsonify({'success': False, 'error': f'Requirements file not found: {requirements_file}'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/list_resumes')
def list_resumes():
    try:
        resume_files = agent.resume_processor.get_resume_files()
        return jsonify({
            'success': True,
            'resumes': [file.name for file in resume_files]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/download_csv')
def download_csv():
    try:
        # Generate CSV directly from current evaluation results
        if not evaluation_results:
            return jsonify({'success': False, 'error': 'No evaluation results available'})
        
        # Create CSV content from current results
        import io
        import csv
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['Rank', 'File Name', 'Recommendation', 'Skill Match', 'Experience', 'Project Relevance', 'Missing Skills', 'Top Skills', 'Passed Screening'])
        
        # Write candidate data
        for candidate in evaluation_results['candidates']:
            writer.writerow([
                candidate['rank'],
                candidate['file_name'],
                candidate['recommendation'],
                candidate['skill_match'],
                candidate['experience'],
                candidate['project_relevance'],
                '; '.join(candidate['missing_must_have']),
                '; '.join(candidate['top_skills']),
                candidate['passed_screening']
            ])
        
        # Convert to bytes and send as file
        csv_content = output.getvalue()
        output.close()
        
        from flask import Response
        response = Response(
            csv_content,
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=evaluation_results.csv'}
        )
        return response
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
