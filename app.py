from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file, flash
import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from config import CURRICULA_DIR, STORIES_DIR, SRS_DIR, MOCK_RESPONSES_DIR, DATA_DIR, UPLOAD_DIR

app = Flask(__name__)

# Configure app with directory paths
app.config.update(
    CURRICULA_DIR=str(CURRICULA_DIR),
    STORIES_DIR=str(STORIES_DIR),
    SRS_DIR=str(SRS_DIR),
    MOCK_RESPONSES_DIR=str(MOCK_RESPONSES_DIR)
)

# Default template for the LLM prompt
DEFAULT_TEMPLATE = """Generate a {days}-day language learning curriculum based on the following details:

Learning Objective: {learning_objective}
Target Language: {target_language}
CEFR Level: {cefr_level}

For each day, provide:
1. A title
2. A focus area
3. Key collocations or phrases to learn
4. A brief learning objective
5. A short story or dialogue demonstrating the language in context

Format the response as a JSON object with the following structure:
{{
  "learning_objective": "...",
  "target_language": "...",
  "cefr_level": "...",
  "days": [
    {{
      "day": 1,
      "title": "...",
      "focus": "...",
      "collocations": ["...", "..."],
      "learning_objective": "...",
      "story": "..."
    }},
    ...
  ]
}}"""

@app.route('/')
def index():
    return redirect(url_for('create_curriculum'))

def save_uploaded_file(file, upload_dir):
    """Save an uploaded file and return its path."""
    if not file or file.filename == '':
        return None
    
    # Ensure upload directory exists
    os.makedirs(upload_dir, exist_ok=True)
    
    # Create a safe filename
    filename = f"transcript_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
    filepath = os.path.join(upload_dir, filename)
    
    # Save the file
    file.save(filepath)
    return filepath

@app.route('/create', methods=['GET', 'POST'])
def create_curriculum():
    if request.method == 'POST':
        # Get form data
        learning_objective = request.form.get('learning_objective', '').strip()
        target_language = request.form.get('target_language', 'English').strip()
        cefr_level = request.form.get('cefr_level', 'A2').strip()
        days = int(request.form.get('days', 30))
        output_filename = request.form.get('output_filename', 'my_curriculum').strip()
        
        # Handle file upload if present
        transcript_path = None
        if 'transcript' in request.files:
            transcript_file = request.files['transcript']
            if transcript_file and transcript_file.filename:
                transcript_path = save_uploaded_file(transcript_file, UPLOAD_DIR)
        
        # Generate the template with all parameters
        template = DEFAULT_TEMPLATE.format(
            learning_objective=learning_objective,
            target_language=target_language,
            cefr_level=cefr_level,
            days=days
        )
        
        # Store form data in session for re-display if needed
        form_data = {
            'learning_objective': learning_objective,
            'target_language': target_language,
            'cefr_level': cefr_level,
            'days': days,
            'output_filename': output_filename,
            'transcript_path': transcript_path
        }
        
        return render_template('create.html', 
                            template=template,
                            **form_data)
    
    # Default values for GET request
    return render_template('create.html', 
                         template=DEFAULT_TEMPLATE,
                         learning_objective='',
                         target_language='English',
                         cefr_level='A2',
                         days=30,
                         output_filename='my_curriculum')

@app.route('/generate', methods=['POST'])
def generate_curriculum():
    try:
        # Get the LLM response
        llm_response = request.form.get('llm_response', '')
        output_filename = request.form.get('output_filename', 'my_curriculum').strip()
        
        # Parse the JSON response
        curriculum = json.loads(llm_response)
        
        # Ensure the filename is safe and has .json extension
        safe_filename = f"{output_filename}.json"
        if not safe_filename.endswith('.json'):
            safe_filename += '.json'
        
        # Clean the filename to remove any path traversal attempts
        safe_filename = os.path.basename(safe_filename)
        
        # Save the curriculum
        filepath = os.path.join(app.config['CURRICULA_DIR'], safe_filename)
        
        # Ensure the directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # Save with pretty-printing
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(curriculum, f, indent=2, ensure_ascii=False)
        
        return jsonify({
            'success': True,
            'filename': safe_filename,
            'curriculum': curriculum
        })
    except json.JSONDecodeError as e:
        return jsonify({
            'success': False,
            'error': f'Invalid JSON: {str(e)}'
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error generating curriculum: {str(e)}'
        }), 500

@app.route('/view/<filename>')
def view_curriculum(filename):
    try:
        filepath = os.path.join(app.config['CURRICULA_DIR'], filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            curriculum = json.load(f)
        return render_template('view.html', 
                            curriculum=curriculum,
                            filename=filename)
    except Exception as e:
        return f"Error loading curriculum: {str(e)}", 400

@app.route('/download/<filename>')
def download_curriculum(filename):
    try:
        filepath = os.path.join(app.config['CURRICULA_DIR'], filename)
        return send_file(
            filepath,
            as_attachment=True,
            download_name=filename,
            mimetype='application/json'
        )
    except Exception as e:
        return f"Error downloading curriculum: {str(e)}", 400

# Ensure required directories exist
for directory in [CURRICULA_DIR, STORIES_DIR, SRS_DIR, MOCK_RESPONSES_DIR, UPLOAD_DIR]:
    os.makedirs(directory, exist_ok=True)

if __name__ == '__main__':
    app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
    app.run(debug=True)
