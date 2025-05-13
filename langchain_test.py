from flask import Flask, render_template, request, jsonify
from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain
import os
import uuid
import json
from datetime import datetime
import traceback

app = Flask(__name__)

# Global dictionary to store LangChain interview sessions
interview_sessions = {}

# Home route
@app.route('/')
def home():
    return render_template('jarvis_test.html')

@app.route('/api/start_langchain_interview', methods=['POST'])
def start_langchain_interview():
    """Start a new AI-driven interview session with a custom intro prompt."""
    try:
        data = request.get_json()
        session_id = data.get('session_id', str(uuid.uuid4()))
        project_name = data.get('project_name')
        
        # Get intro prompt from request
        intro_prompt = data.get('intro_prompt')
        if not intro_prompt:
            return jsonify({"error": "Intro prompt is required"}), 400

        # Initialize LangChain components
        llm = ChatOpenAI(
            temperature=0.7,
            model_name="gpt-4o-mini",  # Use the model specified or default
            openai_api_key=os.getenv('OPENAI_API_KEY')
        )
        memory = ConversationBufferMemory()
        conversation = ConversationChain(llm=llm, memory=memory)

        # Store session information
        interview_sessions[session_id] = {
            "conversation": conversation,
            "transcript": [],
            "project_name": project_name,
            "evaluation_prompt": data.get('evaluation_prompt', ''),
            "use_tts": data.get('use_tts', True),  # Add TTS flag
        }

        # Get first question from the LLM
        first_question = conversation.predict(input=intro_prompt)
        interview_sessions[session_id]["transcript"].append({"role": "assistant", "content": first_question})

        return jsonify({
            "session_id": session_id,
            "question": first_question,
            "transcript": interview_sessions[session_id]["transcript"],
            "use_tts": interview_sessions[session_id]["use_tts"]
        })

    except Exception as e:
        print(f"Error starting LangChain interview: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@app.route('/api/langchain_interview_response', methods=['POST'])
def langchain_interview_response():
    """Submit user response and get next AI question."""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        user_response = data.get('response')

        if not session_id or not user_response:
            return jsonify({"error": "Session ID and response required"}), 400

        session = interview_sessions.get(session_id)
        if not session:
            return jsonify({"error": "Session not found"}), 404

        # Add user response to transcript
        session["transcript"].append({"role": "user", "content": user_response})

        # Get next question using LangChain
        follow_up_prompt = "Based on this response, continue the interview with the next appropriate question. Make sure to ask relevant follow-up questions if needed."
        next_question = session["conversation"].predict(input=user_response + "\n\n" + follow_up_prompt)
        
        # Add AI question to transcript
        session["transcript"].append({"role": "assistant", "content": next_question})

        return jsonify({
            "question": next_question,
            "transcript": session["transcript"],
            "use_tts": session.get("use_tts", True)
        })

    except Exception as e:
        print(f"Error in LangChain interview response: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@app.route('/api/langchain_interview_summary', methods=['POST'])
def langchain_interview_summary():
    """Generate a summary of the interview."""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        custom_eval_prompt = data.get('evaluation_prompt')

        if not session_id:
            return jsonify({"error": "Session ID required"}), 400

        session = interview_sessions.get(session_id)
        if not session:
            return jsonify({"error": "Session not found"}), 404

        # Format the transcript for the evaluation
        transcript_text = ""
        for entry in session["transcript"]:
            role = "Interviewer" if entry["role"] == "assistant" else "Interviewee"
            transcript_text += f"{role}: {entry['content']}\n\n"

        # Use custom evaluation prompt or default based on project
        if custom_eval_prompt:
            evaluation_prompt = custom_eval_prompt
        elif session.get("evaluation_prompt"):
            evaluation_prompt = session["evaluation_prompt"]
        else:
            project_name = session.get("project_name", "this project")
            evaluation_prompt = f"""Based on the following interview transcript about {project_name}, provide a comprehensive analysis including:

1. Key user needs and goals
2. Pain points and frustrations
3. Insights and opportunities
4. Recommendations for improvement

Transcript:
{transcript_text}"""

        # Use the LLM to generate the summary
        llm = session["conversation"].llm
        evaluation = llm.predict(evaluation_prompt)

        # Save the transcript and analysis to a JSON file
        if session.get("project_name"):
            try:
                # Generate a unique ID
                interview_id = str(uuid.uuid4())
                
                # Create the interview data
                interview_data = {
                    "id": interview_id,
                    "project_name": session["project_name"],
                    "interview_type": "LangChain Interview",
                    "date": datetime.now().isoformat(),
                    "transcript": transcript_text,
                    "analysis": evaluation
                }
                
                # Save to a JSON file
                os.makedirs("interviews", exist_ok=True)
                with open(f"interviews/{interview_id}.json", "w") as f:
                    json.dump(interview_data, f, indent=2)
                    
                print(f"Saved interview to interviews/{interview_id}.json")
                
            except Exception as save_error:
                print(f"Error saving interview: {str(save_error)}")
                # Continue even if saving fails

        return jsonify({
            "transcript": session["transcript"],
            "evaluation": evaluation
        })

    except Exception as e:
        print(f"Error generating interview summary: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True) 