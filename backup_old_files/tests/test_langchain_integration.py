import pytest
from app import app as flask_app
import json
import uuid

@pytest.fixture
def client():
    """Create a test client for the Flask app."""
    flask_app.config['TESTING'] = True
    with flask_app.test_client() as client:
        yield client

def test_interview_create_endpoint(client):
    """Test the interview creation endpoint."""
    # Test data
    test_data = {
        "title": "Test Interview",
        "prompt": "This is a test interview prompt"
    }
    
    # Make the request to create an interview
    response = client.post(
        '/langchain/interview/create',
        data=json.dumps(test_data),
        content_type='application/json'
    )
    
    # Check the response
    assert response.status_code == 200
    response_data = json.loads(response.data)
    assert response_data['status'] == 'success'
    assert 'session_id' in response_data
    assert response_data['title'] == 'Test Interview'

def test_interview_respond_endpoint(client):
    """Test the interview response endpoint."""
    # First create an interview session
    create_data = {
        "title": "Test Interview",
        "prompt": "This is a test interview prompt"
    }
    
    create_response = client.post(
        '/langchain/interview/create',
        data=json.dumps(create_data),
        content_type='application/json'
    )
    
    create_response_data = json.loads(create_response.data)
    session_id = create_response_data['session_id']
    
    # Start the interview
    start_data = {
        "session_id": session_id
    }
    
    client.post(
        '/langchain/api/interview/start',
        data=json.dumps(start_data),
        content_type='application/json'
    )
    
    # Now test the response endpoint
    response_data = {
        "session_id": session_id,
        "user_input": "This is a test response from the user"
    }
    
    response = client.post(
        '/langchain/api/interview/respond',
        data=json.dumps(response_data),
        content_type='application/json'
    )
    
    # Check the response
    assert response.status_code == 200
    response_data = json.loads(response.data)
    assert response_data['status'] == 'success'
    assert 'next_question' in response_data
    assert 'transcript' in response_data

def test_interview_analyze_endpoint(client):
    """Test the interview analysis endpoint."""
    # First create an interview session
    create_data = {
        "title": "Test Interview",
        "prompt": "This is a test interview prompt"
    }
    
    create_response = client.post(
        '/langchain/interview/create',
        data=json.dumps(create_data),
        content_type='application/json'
    )
    
    create_response_data = json.loads(create_response.data)
    session_id = create_response_data['session_id']
    
    # Start the interview
    start_data = {
        "session_id": session_id
    }
    
    client.post(
        '/langchain/api/interview/start',
        data=json.dumps(start_data),
        content_type='application/json'
    )
    
    # Simulate a response
    response_data = {
        "session_id": session_id,
        "user_input": "This is a test response from the user"
    }
    
    client.post(
        '/langchain/api/interview/respond',
        data=json.dumps(response_data),
        content_type='application/json'
    )
    
    # Now test the analysis endpoint
    analysis_data = {
        "session_id": session_id
    }
    
    response = client.post(
        '/langchain/api/interview/analyze',
        data=json.dumps(analysis_data),
        content_type='application/json'
    )
    
    # Check the response
    assert response.status_code == 200
    response_data = json.loads(response.data)
    assert response_data['status'] == 'success'
    assert 'analysis' in response_data

def test_research_plan_creation(client):
    """Test the research plan creation endpoint."""
    # Test data
    test_data = {
        "title": "Test Research Plan",
        "description": "This is a test research plan description"
    }
    
    # Make the request to create a research plan
    response = client.post(
        '/langchain/research/create',
        data=json.dumps(test_data),
        content_type='application/json'
    )
    
    # Check the response
    assert response.status_code == 200
    response_data = json.loads(response.data)
    assert response_data['status'] == 'success'
    assert 'plan_id' in response_data
    assert response_data['title'] == 'Test Research Plan'

def test_discovery_plan_creation(client):
    """Test the discovery plan creation endpoint."""
    # Test data
    test_data = {
        "title": "Test Discovery Plan",
        "description": "This is a test discovery plan description"
    }
    
    # Make the request to create a discovery plan
    response = client.post(
        '/langchain/discovery/create',
        data=json.dumps(test_data),
        content_type='application/json'
    )
    
    # Check the response
    assert response.status_code == 200
    response_data = json.loads(response.data)
    assert response_data['status'] == 'success'
    assert 'plan_id' in response_data
    assert response_data['title'] == 'Test Discovery Plan' 