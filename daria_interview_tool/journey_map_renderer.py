"""
Journey Map Renderer Module

This module provides functions to render journey map JSON as HTML for display in the web interface.
"""

import logging
from typing import Dict, Any, List

# Configure logging
logger = logging.getLogger(__name__)

def render_journey_map_html(journey_map: Dict[str, Any]) -> str:
    """
    Render a journey map JSON as HTML.
    
    Args:
        journey_map: Dictionary containing the journey map data
        
    Returns:
        String containing the HTML representation of the journey map
    """
    try:
        # Extract journey map data
        title = journey_map.get('title', 'Journey Map')
        project_name = journey_map.get('projectName', journey_map.get('project_name', 'Unknown Project'))
        stages = journey_map.get('stages', [])
        experience_curve = journey_map.get('experienceCurve', [])
        model_info = journey_map.get('model_info', {})
        
        # Start building HTML
        html = f"""
        <div class="journey-map-wrapper p-6 bg-white rounded-lg shadow-lg">
            <div class="mb-6">
                <h1 class="text-2xl font-bold text-gray-900 mb-2">{title}</h1>
                <p class="text-gray-600">{project_name}</p>
        """
        
        # Add model info if available
        if model_info:
            model_name = model_info.get('model', 'Unknown')
            response_time = model_info.get('response_time', 'Unknown')
            html += f"""
                <div class="mt-2 text-xs text-gray-500">
                    <span>Generated with: {model_name}</span>
                    {f' • Response time: {response_time}s' if response_time != 'Unknown' else ''}
                </div>
            """
        
        html += """
            </div>
        """
        
        # Add experience curve if available
        if experience_curve:
            html += """
            <div class="journey-map-section mb-8">
                <h2 class="text-xl font-semibold text-gray-900 mb-4">Experience Curve</h2>
                <div class="experience-curve flex items-end justify-between h-48 bg-gray-50 p-4 rounded-lg">
            """
            
            for point in experience_curve:
                stage_name = point.get('stage', 'Unknown Stage')
                emotion = point.get('emotion', 'Neutral')
                intensity = point.get('intensity', 5)
                # Calculate height based on intensity (1-10)
                height_percentage = intensity * 10
                
                html += f"""
                <div class="curve-point flex flex-col items-center">
                    <div class="emotion-point" style="height: {height_percentage}%; background-color: {get_emotion_color(emotion)};">
                        {emotion}
                    </div>
                    <div class="stage-name mt-2 text-sm">{stage_name}</div>
                </div>
                """
            
            html += """
                </div>
            </div>
            """
        
        # Add stages section
        html += """
        <div class="journey-map-section mb-8">
            <h2 class="text-xl font-semibold text-gray-900 mb-4">Journey Stages</h2>
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        """
        
        # Add each stage
        for stage in stages:
            stage_id = stage.get('id', 'unknown-stage')
            stage_name = stage.get('stageName', 'Unknown Stage')
            stage_description = stage.get('stageDescription', '')
            
            html += f"""
            <div class="stage-card" id="{stage_id}">
                <h3 class="text-lg font-medium text-gray-900 mb-2">{stage_name}</h3>
                <p class="text-gray-700 mb-4">{stage_description}</p>
                
                <div class="flex justify-end">
                    <button class="text-blue-600 hover:text-blue-800 text-sm font-medium" 
                            onclick="document.getElementById('{stage_id}-details').classList.toggle('hidden')">
                        View Details
                    </button>
                </div>
                
                <div id="{stage_id}-details" class="hidden mt-4 pt-4 border-t border-gray-200">
            """
            
            # Add user actions
            user_actions = stage.get('userActions', [])
            if user_actions:
                html += """
                <div class="mb-4">
                    <h4 class="text-sm font-semibold text-gray-700 mb-2">User Actions</h4>
                    <ul class="space-y-2">
                """
                
                for action in user_actions:
                    action_text = action.get('action', '')
                    action_desc = action.get('description', '')
                    
                    html += f"""
                    <li class="bg-blue-50 border-l-4 border-blue-400 p-2 rounded-r">
                        <div class="font-medium text-blue-800">{action_text}</div>
                        {f'<div class="text-sm text-blue-600">{action_desc}</div>' if action_desc else ''}
                    </li>
                    """
                
                html += """
                    </ul>
                </div>
                """
            
            # Add user goals
            user_goals = stage.get('userGoals', [])
            if user_goals:
                html += """
                <div class="mb-4">
                    <h4 class="text-sm font-semibold text-gray-700 mb-2">User Goals</h4>
                    <ul class="space-y-2">
                """
                
                for goal in user_goals:
                    goal_text = goal.get('goal', '')
                    goal_desc = goal.get('description', '')
                    
                    html += f"""
                    <li class="bg-green-50 border-l-4 border-green-400 p-2 rounded-r">
                        <div class="font-medium text-green-800">{goal_text}</div>
                        {f'<div class="text-sm text-green-600">{goal_desc}</div>' if goal_desc else ''}
                    </li>
                    """
                
                html += """
                    </ul>
                </div>
                """
            
            # Add emotions
            emotions = stage.get('emotions', [])
            if emotions:
                html += """
                <div class="mb-4">
                    <h4 class="text-sm font-semibold text-gray-700 mb-2">Emotions</h4>
                    <ul class="space-y-2">
                """
                
                for emotion in emotions:
                    emotion_name = emotion.get('name', '')
                    emotion_intensity = emotion.get('intensity', 5)
                    emotion_desc = emotion.get('description', '')
                    
                    html += f"""
                    <li class="bg-purple-50 border-l-4 border-purple-400 p-2 rounded-r">
                        <div class="flex items-center justify-between">
                            <span class="font-medium text-purple-800">{emotion_name}</span>
                            <span class="text-xs px-2 py-1 bg-purple-200 rounded-full text-purple-800">
                                Intensity: {emotion_intensity}/10
                            </span>
                        </div>
                        {f'<div class="text-sm text-purple-600 mt-1">{emotion_desc}</div>' if emotion_desc else ''}
                    </li>
                    """
                
                html += """
                    </ul>
                </div>
                """
            
            # Add pain points
            pain_points = stage.get('painPoints', [])
            if pain_points:
                html += """
                <div class="mb-4">
                    <h4 class="text-sm font-semibold text-gray-700 mb-2">Pain Points</h4>
                    <ul class="space-y-2">
                """
                
                for pain in pain_points:
                    pain_text = pain.get('painPoint', '')
                    pain_impact = pain.get('impact', '')
                    pain_quotes = pain.get('supporting_quotes', [])
                    
                    html += f"""
                    <li class="bg-red-50 border-l-4 border-red-400 p-2 rounded-r">
                        <div class="font-medium text-red-800">{pain_text}</div>
                        {f'<div class="text-sm text-red-600 mt-1">{pain_impact}</div>' if pain_impact else ''}
                    """
                    
                    if pain_quotes:
                        html += """
                        <div class="mt-2">
                            <div class="text-xs italic text-red-700">Supporting Quotes:</div>
                            <ul class="list-disc list-inside text-xs text-red-600 mt-1">
                        """
                        
                        for quote in pain_quotes:
                            html += f"""
                            <li>"{quote}"</li>
                            """
                        
                        html += """
                            </ul>
                        </div>
                        """
                    
                    html += """
                    </li>
                    """
                
                html += """
                    </ul>
                </div>
                """
            
            # Add opportunities
            opportunities = stage.get('opportunities', [])
            if opportunities:
                html += """
                <div class="mb-4">
                    <h4 class="text-sm font-semibold text-gray-700 mb-2">Opportunities</h4>
                    <ul class="space-y-2">
                """
                
                for opportunity in opportunities:
                    opportunity_text = opportunity.get('opportunity', '')
                    opportunity_impact = opportunity.get('impact', '')
                    
                    html += f"""
                    <li class="bg-yellow-50 border-l-4 border-yellow-400 p-2 rounded-r">
                        <div class="font-medium text-yellow-800">{opportunity_text}</div>
                        {f'<div class="text-sm text-yellow-600">{opportunity_impact}</div>' if opportunity_impact else ''}
                    </li>
                    """
                
                html += """
                    </ul>
                </div>
                """
            
            html += """
                </div>
            </div>
            """
        
        html += """
            </div>
        </div>
        """
        
        # Add touchpoints section if any stage has touchpoints
        has_touchpoints = any(stage.get('touchpoints') for stage in stages)
        if has_touchpoints:
            html += """
            <div class="journey-map-section mb-8">
                <h2 class="text-xl font-semibold text-gray-900 mb-4">Key Touchpoints</h2>
                <div class="space-y-4">
            """
            
            for stage in stages:
                stage_name = stage.get('stageName', 'Unknown Stage')
                touchpoints = stage.get('touchpoints', [])
                
                if touchpoints:
                    html += f"""
                    <div class="touchpoint-group">
                        <h3 class="text-lg font-medium text-gray-900 mb-2">{stage_name}</h3>
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    """
                    
                    for touchpoint in touchpoints:
                        touchpoint_name = touchpoint.get('name', '')
                        touchpoint_desc = touchpoint.get('description', '')
                        
                        html += f"""
                        <div class="touchpoint-card bg-blue-50 p-4 rounded-lg">
                            <div class="font-medium text-blue-800">{touchpoint_name}</div>
                            {f'<div class="text-sm text-blue-600 mt-1">{touchpoint_desc}</div>' if touchpoint_desc else ''}
                        </div>
                        """
                    
                    html += """
                        </div>
                    </div>
                    """
            
            html += """
                </div>
            </div>
            """
        
        # Close the main container
        html += """
        </div>
        """
        
        return html
        
    except Exception as e:
        logger.error(f"Error rendering journey map HTML: {str(e)}")
        return f"""
        <div class="error-message">
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div>
                <h3 class="font-semibold">Error Rendering Journey Map</h3>
                <p class="text-sm">{str(e)}</p>
            </div>
        </div>
        """

def get_emotion_color(emotion: str) -> str:
    """
    Get a color for an emotion name.
    
    Args:
        emotion: Name of the emotion
        
    Returns:
        Hex color code
    """
    # Lowercase the emotion for case-insensitive matching
    emotion_lower = emotion.lower()
    
    # Define color mapping for common emotions
    emotion_colors = {
        'happy': '#4CAF50',      # Green
        'satisfied': '#8BC34A',  # Light Green
        'excited': '#FFEB3B',    # Yellow
        'curious': '#00BCD4',    # Cyan
        'interested': '#03A9F4', # Light Blue
        'neutral': '#9E9E9E',    # Grey
        'confused': '#FF9800',   # Orange
        'anxious': '#FFC107',    # Amber
        'worried': '#FF9800',    # Orange
        'frustrated': '#F44336', # Red
        'angry': '#D32F2F',      # Dark Red
        'sad': '#3F51B5',        # Indigo
        'disappointed': '#673AB7' # Deep Purple
    }
    
    # Return the color if found, or a default grey
    return emotion_colors.get(emotion_lower, '#9E9E9E') 