import os
import json
import uuid

# Create directory structure if it doesn't exist
os.makedirs("/home/ubuntu/DariaInterviewTool/data/analysis", exist_ok=True)
os.makedirs("/home/ubuntu/DariaInterviewTool/data/suggestions", exist_ok=True)

# Sample suggestion data
suggestion_data = {
    "suggestions": [
        {
            "id": str(uuid.uuid4()),
            "text": "What aspects of fly fishing do you find most challenging?",
            "topic": "Skills and Challenges"
        },
        {
            "id": str(uuid.uuid4()),
            "text": "How has fly fishing evolved over the years from your perspective?",
            "topic": "Historical Context"
        },
        {
            "id": str(uuid.uuid4()),
            "text": "What equipment do you recommend for beginners?",
            "topic": "Equipment"
        }
    ],
    "timestamp": "2025-05-17T20:00:00Z"
}

# Save suggestion data for the session
session_id = "de543e22-7d89-4484-a129-0e57938bb0ac"
suggestion_file = f"/home/ubuntu/DariaInterviewTool/data/suggestions/{session_id}.json"
with open(suggestion_file, "w") as f:
    json.dump(suggestion_data, f, indent=2)

# Sample analysis data
analysis_data = {
    "message_id": "4c9906ee-374a-426a-982b-91ab686c48e2",
    "analysis": {
        "topics": ["Fly Fishing", "Personal Experience", "Nature"],
        "sentiment": "positive",
        "key_insights": [
            "Enjoys the natural environment when fishing",
            "Values the anticipation of catching fish",
            "Appreciates time spent with family"
        ],
        "follow_up_questions": [
            "What equipment do you prefer?",
            "How often do you go fishing?"
        ]
    },
    "timestamp": "2025-05-17T20:00:00Z"
}

# Save analysis data for the message
analysis_file = f"/home/ubuntu/DariaInterviewTool/data/analysis/4c9906ee-374a-426a-982b-91ab686c48e2.json"
with open(analysis_file, "w") as f:
    json.dump(analysis_data, f, indent=2)

print("Observer data initialized successfully!") 