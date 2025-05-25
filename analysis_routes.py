from flask import Blueprint, request, jsonify
from ux_analyzer import UXAnalyzer
import os
import json
from typing import Dict, Any

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