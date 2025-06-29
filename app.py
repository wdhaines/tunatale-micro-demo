from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file, flash
import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from config import CURRICULA_DIR, STORIES_DIR, SRS_DIR, MOCK_RESPONSES_DIR, DATA_DIR, UPLOAD_DIR

# Get the base directory of the package
BASE_DIR = Path(__file__).parent.absolute()

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

def create_app(test_config=None):
    """Create and configure the Flask application."""
    app = Flask(
        __name__,
        instance_relative_config=True,
        template_folder=str(BASE_DIR / 'templates'),
        static_folder=str(BASE_DIR / 'static')
    )
    
    # Default configuration
    app.config.from_mapping(
        SECRET_KEY=os.urandom(24),
        CURRICULA_DIR=str(CURRICULA_DIR),
        STORIES_DIR=str(STORIES_DIR),
        SRS_DIR=str(SRS_DIR),
        MOCK_RESPONSES_DIR=str(MOCK_RESPONSES_DIR),
        DATA_DIR=str(DATA_DIR),
        UPLOAD_FOLDER=str(UPLOAD_DIR),
        TEMPLATES_AUTO_RELOAD=True,
        MAX_CONTENT_LENGTH=16 * 1024 * 1024  # 16MB max file size
    )
    
    # Override with test config if provided
    if test_config is not None:
        app.config.update(test_config)
    
    # Ensure required directories exist
    for dir_key in ['CURRICULA_DIR', 'STORIES_DIR', 'SRS_DIR', 'MOCK_RESPONSES_DIR', 'UPLOAD_FOLDER']:
        if dir_key in app.config:
            os.makedirs(app.config[dir_key], exist_ok=True)
    
    # Register routes
    register_routes(app)
    
    return app

def register_routes(app):
    """Register all route handlers with the Flask application."""
    
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
    
    # Make save_uploaded_file available to route handlers
    app.save_uploaded_file = save_uploaded_file
    
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
                    upload_dir = app.config.get('UPLOAD_FOLDER', UPLOAD_DIR)
                    transcript_path = app.save_uploaded_file(transcript_file, upload_dir)
            
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
            curricula_dir = app.config.get('CURRICULA_DIR', CURRICULA_DIR)
            filepath = os.path.join(curricula_dir, safe_filename)
            
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
            curricula_dir = app.config.get('CURRICULA_DIR', CURRICULA_DIR)
            filepath = os.path.join(curricula_dir, filename)
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
            curricula_dir = app.config.get('CURRICULA_DIR', CURRICULA_DIR)
            filepath = os.path.join(curricula_dir, filename)
            return send_file(
                filepath,
                as_attachment=True,
                download_name=filename,
                mimetype='application/json'
            )
        except Exception as e:
            return f"Error downloading curriculum: {str(e)}", 400

# Create the Flask application instance
app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
