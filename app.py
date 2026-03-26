from flask import Flask, render_template, request, jsonify, session, send_file
from werkzeug.utils import secure_filename
import os
import re
import logging
import threading
from pathlib import Path
from src.orchestrator import ResumeEvaluationAgent
from src.models import Requirements
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = 'resume_evaluation_secret_key'
app.config['UPLOAD_FOLDER'] = 'temp_uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Suppress Flask request logging for progress endpoint
class ProgressFilter(logging.Filter):
    def filter(self, record):
        return '/api/progress' not in record.getMessage()

logging.getLogger('werkzeug').addFilter(ProgressFilter())

app = Flask(__name__)
app.config['SECRET_KEY'] = 'resume_evaluation_secret_key'
app.config['UPLOAD_FOLDER'] = 'temp_uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Global variable to store current evaluation results
evaluation_results = None

# Progress tracking
evaluation_progress = {'current': 0, 'total': 0, 'current_file': '', 'status': 'idle'}

# Initialize agent
agent = ResumeEvaluationAgent()

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.after_request
def add_cache_busting_headers(response):
    """Add cache-busting headers to prevent caching of evaluation results."""
    if request.endpoint and request.endpoint.startswith('api/'):
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
        
        def progress_callback(current, total, filename):
            evaluation_progress['current'] = current
            evaluation_progress['total'] = total
            evaluation_progress['current_file'] = filename
            evaluation_progress['status'] = 'running'
        
        evaluation_progress['status'] = 'running'
        evaluation_progress['current'] = 0
        evaluation_progress['total'] = 0
        evaluation_progress['current_file'] = ''
        
        # Run evaluation with progress callback
        report = agent.run_evaluation(requirements_file, generate_reports=False, progress_callback=progress_callback)
        
        evaluation_progress['status'] = 'done'
        
        # Convert report to JSON-serializable format
        result = {
            'success': True,
            'summary': {
                'total_candidates': report.total_resumes_evaluated,
                'project_title': report.project_requirements.project_title,
                'suitable': len([e for e in report.ranked_candidates if 'Suitable' in e.recommendation and 'Might' not in e.recommendation]),
                'might_be_suitable': len([e for e in report.ranked_candidates if 'Might be suitable' in e.recommendation]),
                'not_suitable': len([e for e in report.ranked_candidates if 'Not suitable' in e.recommendation])
            },
            'candidates': []
        }
        
        for i, evaluation in enumerate(report.ranked_candidates, 1):
            # Use raw reasoning for first line display if needed, but the UI generally uses evaluation.reasoning
            overall_reasoning = evaluation.reasoning.split('\n')[0] if evaluation.reasoning else "No reasoning"
            
            # Extract detailed reasoning components directly from evaluation.reasoning if they exist
            # but since we want to move away from manual parsing, let's keep it simple
            
            # Determine if passed screening based on overall score (simple threshold for UI)
            passed_screening = evaluation.scores.overall_score >= 60
            
            candidate = {
                'rank': i,
                'file_name': evaluation.file_name,
                'overall_score': evaluation.scores.overall_score,
                'recommendation': evaluation.recommendation,
                'reasoning': evaluation.reasoning,
                'skill_match_score': evaluation.scores.skill_match_score,
                'experience_score': evaluation.scores.experience_score,
                'project_relevance_score': evaluation.scores.project_relevance_score,
                'missing_must_have': evaluation.scores.missing_must_have,
                'nice_to_have_covered': evaluation.scores.nice_to_have_covered,
                'top_skills': evaluation.analysis.extracted_skills.technical_skills[:5],
                'passed_screening': passed_screening,
                # Simplified fields for UI compatibility
                'skill_match': f"{'YES' if evaluation.scores.skill_match_score >= 80 else 'NO'} ({evaluation.scores.skill_match_score}%)",
                'experience': f"{'YES' if evaluation.scores.experience_score >= 60 else 'NO'} ({evaluation.scores.experience_score}%)",
                'project_relevance': f"{'YES' if evaluation.scores.project_relevance_score >= 60 else 'NO'} ({evaluation.scores.project_relevance_score}%)",
                'concerns': ""
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

@app.route('/api/progress')
def get_progress():
    return jsonify(evaluation_progress)

@app.route('/api/clear_resumes', methods=['POST'])
def clear_resumes():
    try:
        resume_dir = Path(agent.resume_dir)
        if resume_dir.exists():
            for f in resume_dir.iterdir():
                if f.is_file() and f.suffix.lower() in {'.pdf', '.docx', '.doc', '.txt'}:
                    f.unlink()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/upload_resumes', methods=['POST'])
def upload_resumes():
    try:
        if 'resumes' not in request.files:
            return jsonify({'success': False, 'error': 'No files provided'})
        
        files = request.files.getlist('resumes')
        resume_dir = Path(agent.resume_dir)
        resume_dir.mkdir(parents=True, exist_ok=True)
        
        uploaded = 0
        for file in files:
            if file and file.filename:
                filename = secure_filename(file.filename)
                ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
                if ext in {'pdf', 'docx', 'txt'}:
                    file.save(str(resume_dir / filename))
                    uploaded += 1
        
        return jsonify({'success': True, 'uploaded': uploaded})
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
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)
