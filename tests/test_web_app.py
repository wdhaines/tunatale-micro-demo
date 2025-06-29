"""
Tests for the Flask web application.
"""
import os
import json
import pytest
import tempfile
from pathlib import Path
from app import app

# Test client fixture with temporary directory for test data
@pytest.fixture
def client(monkeypatch, tmp_path):
    """Create a test client for the Flask application with isolated test data."""
    from app import app as flask_app
    
    # Create temporary directories for test data
    test_instance_dir = tmp_path / "instance"
    test_data_dir = test_instance_dir / "data"
    test_curricula_dir = test_data_dir / "curricula"
    test_stories_dir = test_data_dir / "stories"
    test_srs_dir = test_data_dir / "srs"
    test_mock_responses_dir = test_data_dir / "mock_responses"
    
    # Create all required directories
    test_curricula_dir.mkdir(parents=True, exist_ok=True)
    test_stories_dir.mkdir(parents=True, exist_ok=True)
    test_srs_dir.mkdir(parents=True, exist_ok=True)
    test_mock_responses_dir.mkdir(parents=True, exist_ok=True)
    
    # Configure Flask app for testing
    flask_app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False,  # Disable CSRF for testing
        CURRICULA_DIR=str(test_curricula_dir),
        STORIES_DIR=str(test_stories_dir),
        SRS_DIR=str(test_srs_dir),
        MOCK_RESPONSES_DIR=str(test_mock_responses_dir)
    )
    
    # No need to monkey patch config since we're using Flask app config
    
    # Push application context
    ctx = flask_app.app_context()
    ctx.push()
    
    # Create test client
    client = flask_app.test_client()
    
    yield client
    
    # Clean up
    ctx.pop()

def test_index_redirect(client):
    """Test that the index route redirects to the create page."""
    response = client.get('/')
    assert response.status_code == 302
    assert '/create' in response.location

def test_create_page_loads(client):
    """Test that the create page loads successfully."""
    response = client.get('/create')
    assert response.status_code == 200
    assert b'Create New Curriculum' in response.data

def test_generate_curriculum_invalid_json(client):
    """Test curriculum generation with invalid JSON."""
    response = client.post('/generate', data={
        'llm_response': 'not a valid json'
    })
    
    assert response.status_code == 400
    data = json.loads(response.data)
    assert not data['success']
    assert 'Invalid JSON' in data['error']

def test_generate_curriculum_success(client, tmp_path):
    """Test successful curriculum generation."""
    from app import app as flask_app
    
    test_curriculum = {
        'learning_objective': 'Test learning objective',
        'target_language': 'English',
        'cefr_level': 'B1',
        'days': [
            {
                'day': 1,
                'title': 'Test Day 1',
                'focus': 'Test Focus',
                'collocations': ['test collocation 1', 'test collocation 2'],
                'learning_objective': 'Test daily objective',
                'story': 'Test story content'
            }
        ]
    }
    
    with flask_app.app_context():
        # Get the test curricula directory path from app config
        test_curricula_dir = flask_app.config['CURRICULA_DIR']
        
        # Make the POST request
        response = client.post('/generate', data={
            'llm_response': json.dumps(test_curriculum)
        })
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success']
        assert 'filename' in data
        assert data['filename'].endswith('.json')
        
        # Verify the file was created in the test directory
        from pathlib import Path
        filepath = Path(test_curricula_dir) / data['filename']
        assert filepath.exists()
        
        # Verify the file content
        with open(filepath, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
        assert saved_data == test_curriculum

def test_view_curriculum_not_found(client):
    """Test viewing a non-existent curriculum."""
    response = client.get('/view/nonexistent.json')
    assert response.status_code == 400
    assert b'Error loading curriculum' in response.data

def test_download_curriculum_not_found(client):
    """Test downloading a non-existent curriculum."""
    response = client.get('/download/nonexistent.json')
    assert response.status_code == 400
    assert b'Error downloading curriculum' in response.data

def test_create_curriculum_form_submission(client):
    """Test form submission on the create page."""
    response = client.post('/create', data={
        'learning_objective': 'Test objective',
        'target_language': 'Spanish',
        'cefr_level': 'A2'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert b'LLM Prompt Template' in response.data
    assert b'Test objective' in response.data
    assert b'Spanish' in response.data
    assert b'A2' in response.data

# Test for template generation with different inputs
def test_template_generation(client):
    """Test that the template is generated with the correct content."""
    response = client.post('/create', data={
        'learning_objective': 'Learn to order food',
        'target_language': 'French',
        'cefr_level': 'A1'
    })
    
    assert response.status_code == 200
    assert b'Generate a 30-day language learning curriculum' in response.data
    assert b'Learn to order food' in response.data
    assert b'French' in response.data
    assert b'A1' in response.data
