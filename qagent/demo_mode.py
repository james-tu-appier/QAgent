"""
Demo Mode for Test Planner Frontend

This script runs the frontend in demo mode with mock data, allowing you to
demonstrate the interface without requiring actual API keys or external services.
"""

import os
import json
import tempfile
import shutil
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, flash
from werkzeug.utils import secure_filename
import uuid

app = Flask(__name__)
app.secret_key = 'demo-secret-key'

# Configuration
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output'
ALLOWED_EXTENSIONS = {'pdf', 'txt', 'md'}

# Create directories if they don't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def create_mock_data(session_id='d1e2m3o4'):
    """Create mock data for demonstration purposes"""
    
    # Mock PRD Context
    mock_prd_context = json.load(open(f'output/{session_id}/prd_context.json'))
    # Mock Test Plan
    mock_test_plan = json.load(open(f'output/{session_id}/test_plan.json'))
    # Mock Detailed Tests
    mock_detailed_tests = json.load(open(f'output/{session_id}/test_suite.json'))
    # Mock Figma Summary
    mock_figma_summary = open(f'output/{session_id}/figma_summary.txt').read()

    return {
        "prd_context": mock_prd_context,
        "test_plan": mock_test_plan,
        "detailed_tests": mock_detailed_tests,
        "figma_summary": mock_figma_summary
    }

@app.route('/')
def index():
    """Main page with upload form"""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and Figma URL - Demo mode"""
    if 'prd_file' not in request.files:
        flash('No file selected')
        return redirect(request.url)
    file = request.files['prd_file']
    figma_url = request.form.get('figma_url', '').strip()
    trust_mode = request.form.get('trust_mode') == 'on'
    if file.filename == '':
        flash('No file selected')
        return redirect(request.url)
    if not figma_url:
        flash('Figma URL is required')
        return redirect(request.url)
    if file and allowed_file(file.filename):
        session_id = str(uuid.uuid4())[:8]
        output_dir = os.path.join(OUTPUT_FOLDER, session_id)
        os.makedirs(output_dir, exist_ok=True)
        filename = secure_filename(file.filename)
        file_path = os.path.join(output_dir, filename)
        file.save(file_path)
        mock_data = create_mock_data()
        with open(os.path.join(output_dir, 'prd_context.json'), 'w') as f:
            json.dump(mock_data['prd_context'], f, indent=2)
        with open(os.path.join(output_dir, 'test_plan.json'), 'w') as f:
            json.dump(mock_data['test_plan'], f, indent=2)
        with open(os.path.join(output_dir, 'test_suite.json'), 'w') as f:
            json.dump(mock_data['detailed_tests'], f, indent=2)
        with open(os.path.join(output_dir, 'figma_summary.txt'), 'w') as f:
            f.write(mock_data['figma_summary'])
        from backend.json_to_md_formatter import MarkdownFormatter
        formatter = MarkdownFormatter()
        test_plan_md = formatter.convert_test_plan_json_to_md(mock_data['test_plan'])
        with open(os.path.join(output_dir, 'test_plan.md'), 'w') as f:
            f.write(test_plan_md)
        test_suite_md = formatter.convert_test_suite_json_to_md(mock_data['detailed_tests'])
        with open(os.path.join(output_dir, 'test_suite.md'), 'w') as f:
            f.write(test_suite_md)
        if trust_mode:
            result = {
                "prd_context": mock_data['prd_context'],
                "test_plan": mock_data['test_plan'],
                "detailed_tests": mock_data['detailed_tests'],
                "figma_summary": mock_data['figma_summary'],
                "test_plan_md": test_plan_md,
                "test_suite_md": test_suite_md
            }
            return render_template('results.html', result=result, session_id=session_id)
        else:
            # Step into checkpoint flow
            return redirect(url_for('checkpoint_proceed', session_id=session_id, checkpoint=1))
    flash('Invalid file type')
    return redirect(url_for('index'))

@app.route('/results/<session_id>')
def results(session_id):
    """Display results for a specific session"""
    output_dir = os.path.join(OUTPUT_FOLDER, session_id)
    
    if not os.path.exists(output_dir):
        flash('Results not found')
        return redirect(url_for('index'))
    
    try:
        with open(os.path.join(output_dir, 'prd_context.json'), 'r') as f:
            prd_context = json.load(f)
        
        with open(os.path.join(output_dir, 'test_plan.json'), 'r') as f:
            test_plan = json.load(f)
        
        with open(os.path.join(output_dir, 'test_suite.json'), 'r') as f:
            detailed_tests = json.load(f)
        
        with open(os.path.join(output_dir, 'figma_summary.txt'), 'r') as f:
            figma_summary = f.read()
        
        with open(os.path.join(output_dir, 'test_plan.md'), 'r') as f:
            test_plan_md = f.read()
        
        with open(os.path.join(output_dir, 'test_suite.md'), 'r') as f:
            test_suite_md = f.read()
        
        result = {
            "prd_context": prd_context,
            "test_plan": test_plan,
            "detailed_tests": detailed_tests,
            "figma_summary": figma_summary,
            "test_plan_md": test_plan_md,
            "test_suite_md": test_suite_md
        }
        
        return render_template('results.html', result=result, session_id=session_id)
        
    except Exception as e:
        flash(f'Error loading results: {str(e)}')
        return redirect(url_for('index'))

@app.route('/download/<session_id>/<file_type>')
def download_file(session_id, file_type):
    """Download generated files"""
    output_dir = os.path.join(OUTPUT_FOLDER, session_id)
    
    file_mapping = {
        'prd_context': 'prd_context.json',
        'test_plan_json': 'test_plan.json',
        'test_plan_md': 'test_plan.md',
        'test_suite_json': 'test_suite.json',
        'test_suite_md': 'test_suite.md',
        'figma_summary': 'figma_summary.txt'
    }
    
    if file_type not in file_mapping:
        flash('Invalid file type')
        return redirect(url_for('index'))
    
    file_path = os.path.join(output_dir, file_mapping[file_type])
    
    if not os.path.exists(file_path):
        flash('File not found')
        return redirect(url_for('index'))
    
    return send_file(file_path, as_attachment=True)

@app.route('/checkpoint/<session_id>/<int:checkpoint>', methods=['GET', 'POST'])
def checkpoint_proceed(session_id, checkpoint):
    """Handle checkpoint review and proceed to next step (Demo mode)"""
    output_dir = os.path.join(OUTPUT_FOLDER, session_id)
    if not os.path.exists(output_dir):
        flash('Session not found')
        return redirect(url_for('index'))

    if request.method == 'POST':
        content = request.form.get('content', '').strip()
        action = request.form.get('action', 'proceed')
        if not content:
            flash('Content cannot be empty')
            return redirect(request.url)
        if action == 'skip':
            content = None
        # Simulate checkpoint update (in demo, just save content to file)
        if checkpoint == 1 and content:
            with open(os.path.join(output_dir, 'prd_context.json'), 'w') as f:
                f.write(content)
        elif checkpoint == 2 and content:
            with open(os.path.join(output_dir, 'figma_summary.txt'), 'w') as f:
                f.write(content)
        elif checkpoint == 3 and content:
            with open(os.path.join(output_dir, 'test_plan.md'), 'w') as f:
                f.write(content)
        # Proceed to next checkpoint or results
        if checkpoint < 3:
            return redirect(url_for('checkpoint_proceed', session_id=session_id, checkpoint=checkpoint+1))
        else:
            return redirect(url_for('results', session_id=session_id))

    # GET request - show current checkpoint
    try:
        if checkpoint == 1:
            with open(os.path.join(output_dir, 'prd_context.json'), 'r') as f:
                content = f.read()
            original_content = content
            content_type = "PRD Context"
            title = "PRD Context Review"
            description = "Review and modify the extracted PRD information"
            icon = "file-alt"
        elif checkpoint == 2:
            with open(os.path.join(output_dir, 'figma_summary.txt'), 'r') as f:
                content = f.read()
            original_content = content
            content_type = "Figma Summary"
            title = "Figma Summary Review"
            description = "Review and modify the Figma design analysis"
            icon = "palette"
        elif checkpoint == 3:
            with open(os.path.join(output_dir, 'test_plan.md'), 'r') as f:
                content = f.read()
            original_content = content
            content_type = "Test Plan"
            title = "Test Plan Review"
            description = "Review and modify the generated test plan"
            icon = "clipboard-list"
        else:
            flash('Invalid checkpoint')
            return redirect(url_for('index'))
        return render_template('checkpoint.html',
                              session_id=session_id,
                              checkpoint_step=checkpoint,
                              content=content,
                              original_content=original_content,
                              content_type=content_type,
                              checkpoint_title=title,
                              checkpoint_description=description,
                              checkpoint_icon=icon)
    except Exception as e:
        flash(f'Error loading checkpoint: {str(e)}')
        return redirect(url_for('index'))

if __name__ == '__main__':
    print("🚀 Starting Test Planner Demo Mode")
    print("📝 This is a demonstration version with mock data")
    print("🌐 Access the demo at: http://localhost:8080")
    print("⚠️  No API keys required - using mock data")
    print("=" * 50)
    
    app.run(debug=True, host='0.0.0.0', port=8080)