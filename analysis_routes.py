from flask import Blueprint, request, jsonify
from ux_analyzer import UXAnalyzer
import os
import json
from typing import Dict, Any
from flask_login import login_required
import datetime
import openai
import logging
from semantic_pipeline import tag_chunk, save_annotations
from flask import current_app

logger = logging.getLogger(__name__)

analysis_bp = Blueprint('analysis', __name__)
analyzer = UXAnalyzer(api_key=os.getenv("OPENAI_API_KEY"))

@analysis_bp.route('/analyze', methods=['POST'])
async def analyze_interview():
    """Analyze an interview transcript and generate insights"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Validate required fields
        required_fields = ["transcript", "id", "project_name"]
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({
                "error": f"Missing required fields: {', '.join(missing_fields)}"
            }), 400

        # Perform analysis
        analysis_result = await analyzer.analyze_interview(data)
        
        if "error" in analysis_result:
            return jsonify({"error": analysis_result["error"]}), 500
            
        return jsonify(analysis_result), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@analysis_bp.route('/insights/<interview_id>', methods=['GET'])
async def get_insights(interview_id: str):
    """Retrieve insights for a specific interview"""
    try:
        # TODO: Implement persistence layer
        # For now, return a mock response
        return jsonify({
            "error": "Not implemented yet - insights storage coming soon"
        }), 501

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@analysis_bp.route('/affinity-diagram/<project_name>', methods=['GET'])
async def get_affinity_diagram(project_name: str):
    """Get affinity diagram for all insights in a project"""
    try:
        # TODO: Implement persistence layer
        # For now, return a mock response
        return jsonify({
            "error": "Not implemented yet - affinity diagram storage coming soon"
        }), 501

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@analysis_bp.route('/interviews/search', methods=['GET'])
def search_interviews():
    try:
        query = request.args.get('query', '')
        search_type = request.args.get('searchType', 'semantic')
        date_range = request.args.get('dateRange', 'all')
        tags = request.args.getlist('tags')

        # TODO: Implement actual search logic
        # For now, return mock data
        mock_results = [
            {
                "id": "1",
                "title": "User Research Session - Product Features",
                "participant_name": "John Doe",
                "created_at": "2024-03-20T10:00:00Z",
                "preview": "Discussion about key product features and user pain points...",
                "tags": ["features", "usability"],
                "status": "completed"
            }
        ]
        
        return jsonify(mock_results), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@analysis_bp.route('/interviews', methods=['GET'])
def list_interviews():
    try:
        # TODO: Implement actual database query
        # For now, return mock data
        mock_interviews = [
            {
                "id": "1",
                "title": "Initial User Research",
                "participant_name": "Jane Smith",
                "created_at": "2024-03-19T14:30:00Z",
                "preview": "Explored user workflow and pain points...",
                "tags": ["workflow", "pain-points"],
                "status": "completed"
            }
        ]
        
        return jsonify(mock_interviews), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@analysis_bp.route('/test', methods=['GET'])
def test_route():
    return jsonify({'message': 'Analysis blueprint is working!'})

@analysis_bp.route('/analysis/session/<session_id>/annotations/', methods=['GET', 'POST'], strict_slashes=False)
@login_required
def handle_session_annotations(session_id):
    annotations_path = os.path.join('data', 'annotations', f'{session_id}.json')
    os.makedirs(os.path.dirname(annotations_path), exist_ok=True)

    # Load existing annotations
    if os.path.exists(annotations_path):
        with open(annotations_path, 'r') as f:
            annotations = json.load(f)
    else:
        annotations = []

    if request.method == 'GET':
        return jsonify({"annotations": annotations})

    elif request.method == 'POST':
        data = request.get_json()
        # Expecting: { "messageId": ..., "content": ... }
        if not data or "messageId" not in data or "content" not in data:
            return jsonify({"success": False, "error": "Missing messageId or content"}), 400

        annotation = {
            "id": str(len(annotations) + 1),
            "messageId": data["messageId"],
            "content": data["content"],
            "user": {"name": "Current User"},  # Replace with real user info if available
            "timestamp": str(datetime.datetime.utcnow())
        }
        annotations.append(annotation)
        with open(annotations_path, 'w') as f:
            json.dump(annotations, f, indent=2)

        return jsonify({"success": True, "annotation": annotation})

@analysis_bp.route('/generate_questions', methods=['POST'])
def generate_questions():
    """Generate potential interview questions based on discussion guide configuration using AI."""
    try:
        data = request.json
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400

        # Extract guide configuration
        character = data.get('character_select', '').lower()
        topic = data.get('topic', '')
        context = data.get('context', '')
        goals = data.get('goals', [])
        interview_type = data.get('interview_type', 'research_interview')
        custom_questions = data.get('custom_questions', [])

        # Prepare the prompt for the AI
        prompt = f"""You are an expert research interviewer. Generate 5-7 relevant interview questions based on the following context:\n\nCharacter: {character}\nTopic: {topic}\nContext: {context}\nGoals: {', '.join(goals) if isinstance(goals, list) else goals}\nInterview Type: {interview_type}\n\nAdditional Context:\n- The questions should be open-ended and encourage detailed responses\n- They should align with the character's personality and interview style\n- They should help achieve the stated research goals\n- They should be appropriate for the specified interview type\n\nGenerate a list of questions that will help gather valuable insights for this research session."""

        # Call OpenAI API to generate questions
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an expert research interviewer who generates thoughtful, open-ended questions."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )

        # Extract and format the questions
        ai_response = response.choices[0].message.content
        questions = [q.strip() for q in ai_response.split('\n') if q.strip() and q.strip().endswith('?')]

        # Add any custom questions if provided
        if custom_questions:
            if isinstance(custom_questions, list):
                for question in custom_questions:
                    if isinstance(question, dict) and 'text' in question:
                        questions.append(question['text'])
                    elif isinstance(question, str):
                        questions.append(question)

        # Remove duplicates while preserving order
        seen = set()
        unique_questions = []
        for q in questions:
            if q not in seen:
                seen.add(q)
                unique_questions.append(q)

        return jsonify({
            'success': True,
            'questions': unique_questions,
            'count': len(unique_questions)
        })

    except Exception as e:
        logger.error(f"Error generating questions: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@analysis_bp.route('/debug/semantic_annotate/<session_id>', methods=['GET'])
def debug_semantic_annotate(session_id):
    session_path = f"data/interviews/sessions/{session_id}.json"
    if not os.path.exists(session_path):
        return jsonify({"error": "Session not found"}), 404

    with open(session_path, "r") as f:
        session = json.load(f)

    annotations = []
    for msg in session.get("messages", []):
        semantic_json = tag_chunk(msg.get("content", ""), msg)
        try:
            semantic_data = json.loads(semantic_json)
        except Exception:
            semantic_data = {"raw": semantic_json}
        msg["semantic"] = semantic_data
        # Build annotation object for saving
        annotation = {
            "id": msg["id"],
            "messageId": msg["id"],
            "content": msg["content"],
            "semantic": semantic_data,
            "user": {"name": "System"},
            "timestamp": msg.get("timestamp", "")
        }
        annotations.append(annotation)

    # Save to annotations directory
    save_annotations(session_id, annotations)

    return jsonify(session)

@analysis_bp.route('/session/<session_id>/messages_with_semantics', methods=['GET'])
def get_messages_with_semantics(session_id):
    """
    Return session messages merged with semantic data from annotations.
    """
    try:
        # Load session messages
        session_path = os.path.join('data', 'interviews', 'sessions', f'{session_id}.json')
        if not os.path.exists(session_path):
            return jsonify({'success': False, 'error': 'Session not found'}), 404
        with open(session_path, 'r') as f:
            session = json.load(f)
        messages = session.get('messages', [])

        # Load annotations (semantic) if available
        annotations_path = os.path.join('data', 'annotations', f'{session_id}.json')
        semantic_map = {}
        if os.path.exists(annotations_path):
            with open(annotations_path, 'r') as f:
                annotations = json.load(f)
                semantic_map = {a['messageId']: a.get('semantic', {}) for a in annotations}

        # Merge semantic data into messages
        for msg in messages:
            if msg['id'] in semantic_map:
                msg['semantic'] = semantic_map[msg['id']]

        return jsonify({'success': True, 'messages': messages})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Helper functions (import or define if not already available)
def load_interview(session_id):
    session_path = os.path.join('data', 'interviews', 'sessions', f'{session_id}.json')
    if not os.path.exists(session_path):
        return None
    with open(session_path, 'r') as f:
        return json.load(f)

def save_interview(session_id, session):
    session_path = os.path.join('data', 'interviews', 'sessions', f'{session_id}.json')
    with open(session_path, 'w') as f:
        json.dump(session, f, indent=2)
    return True

# /api/session/{sessionId}/tags
@analysis_bp.route('/session/<session_id>/tags', methods=['POST'])
def handle_tags(session_id):
    """
    Save all tags for a specific message in a session.
    Expects JSON: { "messageId": "...", "tags": [...] }
    """
    data = request.json
    message_id = data.get('messageId')
    tags = data.get('tags', [])
    if not message_id:
        return jsonify({'success': False, 'error': 'Missing messageId'}), 400

    session = load_interview(session_id)
    if not session:
        return jsonify({'success': False, 'error': 'Session not found'}), 404
    if 'tags' not in session:
        session['tags'] = {}
    session['tags'][message_id] = tags
    save_interview(session_id, session)
    return jsonify({'success': True})

# /api/session/{sessionId}/tags/{tagId}
@analysis_bp.route('/session/<session_id>/tags/<tag_id>', methods=['DELETE'])
def handle_tag_deletion(session_id, tag_id):
    """
    Delete a tag by tag_id from all messages in a session.
    """
    session = load_interview(session_id)
    if not session or 'tags' not in session:
        return jsonify({'success': False, 'error': 'Session or tags not found'}), 404

    found = False
    for message_id in session['tags']:
        # Only keep tags that do NOT match tag_id
        before = len(session['tags'][message_id])
        session['tags'][message_id] = [
            tag for tag in session['tags'][message_id]
            if not (isinstance(tag, dict) and tag.get('id') == tag_id)
        ]
        if len(session['tags'][message_id]) < before:
            found = True

    if found:
        save_interview(session_id, session)
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Tag not found'}), 404 
    