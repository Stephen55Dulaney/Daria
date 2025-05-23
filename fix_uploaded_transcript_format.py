#!/usr/bin/env python

"""
Fix Uploaded Transcript Format

This script helps convert uploaded transcripts to the correct JSON format for the Daria system.
It saves the transcript directly to the data/interviews/sessions/ directory.

Usage:
    python fix_uploaded_transcript_format.py -f [transcript_file] -g [guide_id] -t [title] -p [project]
"""

import argparse
import datetime
import json
import os
import re
import uuid
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def process_transcript(transcript_content, metadata=None):
    """Process a transcript file into the structured format needed for Daria."""
    metadata = metadata or {}
    
    # Extract metadata
    session_id = metadata.get('session_id', str(uuid.uuid4()))
    guide_id = metadata.get('guide_id', '9d9b0648-5f14-4a22-81df-290bbd67049d')  # Default guide ID
    title = metadata.get('title', 'Uploaded Transcript')
    project = metadata.get('project', 'World of Washing Machines')
    participant_name = metadata.get('participant_name', 'Jason')
    
    # Process transcript into conversation chunks
    lines = transcript_content.strip().split('\n')
    transcript_chunks = []
    current_speaker = None
    current_content = []
    
    # Try to detect format (simplified)
    colon_pattern = r'^([^:]+):\s*(.*)'  # Name: text
    
    # Process the transcript
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Try to match speaker-content pattern
        match = re.match(colon_pattern, line)
        if match:
            # Save previous speaker's content if switching
            if current_speaker and current_content:
                transcript_chunks.append({
                    'speaker': current_speaker,
                    'content': ' '.join(current_content)
                })
                current_content = []
            
            # Extract new speaker and content
            current_speaker = match.group(1).strip()
            content = match.group(2).strip()
            if content:
                current_content.append(content)
        elif current_speaker:
            # Continuation of current speaker
            current_content.append(line)
        else:
            # No current speaker but content exists
            current_speaker = "Speaker"
            current_content.append(line)
    
    # Add the last speaker's content
    if current_speaker and current_content:
        transcript_chunks.append({
            'speaker': current_speaker,
            'content': ' '.join(current_content)
        })
    
    # Identify researcher vs participant speakers
    all_speakers = list(set(chunk['speaker'] for chunk in transcript_chunks))
    logger.info(f"Detected speakers: {all_speakers}")
    
    # Default patterns for identifying speakers
    researcher_patterns = ['moderator', 'interviewer', 'researcher', 'facilitator']
    participant_patterns = ['participant', 'respondent', 'user', 'interviewee', 'jason']
    
    # Classify speakers
    researcher_speakers = []
    participant_speakers = []
    
    for speaker in all_speakers:
        if any(p.lower() in speaker.lower() for p in researcher_patterns):
            researcher_speakers.append(speaker)
        elif any(p.lower() in speaker.lower() for p in participant_patterns):
            participant_speakers.append(speaker)
        else:
            # If unclear, look at position in transcript
            # Usually the first speaker is the researcher
            if speaker == transcript_chunks[0]['speaker']:
                researcher_speakers.append(speaker)
            else:
                participant_speakers.append(speaker)
    
    logger.info(f"Identified researcher speakers: {researcher_speakers}")
    logger.info(f"Identified participant speakers: {participant_speakers}")
    
    # Format transcript in the required structure
    messages = []
    raw_transcript = ""
    now = datetime.datetime.now()
    
    for i, chunk in enumerate(transcript_chunks):
        speaker = chunk['speaker']
        content = chunk['content']
        
        # Determine role
        is_researcher = speaker in researcher_speakers
        role = 'assistant' if is_researcher else 'user'
        
        # Add to raw transcript
        speaker_label = "Moderator" if is_researcher else "Participant"
        raw_transcript += f"\n\n{speaker_label}: {content}"
        
        # Create message object with timestamp offset for ordering
        timestamp = (now + datetime.timedelta(seconds=i)).isoformat()
        messages.append({
            'id': str(uuid.uuid4()),
            'content': content,
            'role': role,
            'timestamp': timestamp
        })
    
    # Prepare the session data in the exact format needed
    session_data = {
        "id": session_id,
        "guide_id": guide_id,
        "interviewee": {
            "name": participant_name,
            "email": "",
            "role": "",
            "department": "",
            "company": "",
            "demographics": {
                "age_range": "",
                "gender": "",
                "location": ""
            }
        },
        "status": "active",
        "messages": messages,
        "transcript": raw_transcript.strip(),
        "analysis": None,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "title": title,
        "project": project,
        "interview_type": "discovery_interview",
        "topic": f"We want to discuss what we need to cover in a {title} project",
        "context": "Background Context: World of Washing Machines Corp. Self-Service Ordering Portal (B2B) Overview World of Washing Machines Corp., a leading global manufacturer of home appliances, developed a self-service ordering portal aimed at its B2B customers—primarily retail appliance stores and distributors. This portal streamlines the process for retail partners to browse, order, and manage World of Washing Machines Corp. products directly, without the need for manual sales intervention.",
        "goals": "Identify pain points in the current ordering workflow. Understand how users search for and select products. Assess satisfaction with order tracking and status updates. Uncover unmet needs or desired features in the portal. Evaluate ease of use for first-time and repeat users.",
        "character": "askia",
        "character_select": "askia",
        "voice_id": "AZnzlk1XvdvUeBnXmlld"
    }
    
    return session_data

def save_session(session_data, output_path=None):
    """Save the session data to a file."""
    if output_path is None:
        # Default path structure
        data_dir = Path.cwd() / "data" / "interviews" / "sessions"
        data_dir.mkdir(parents=True, exist_ok=True)
        output_path = data_dir / f"{session_data['id']}.json"
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Save the file
    with open(output_path, 'w') as f:
        json.dump(session_data, f, indent=2)
    
    # Update the guide to include this session if it has a guide_id
    guide_id = session_data.get('guide_id')
    session_id = session_data.get('id')
    
    if guide_id and session_id:
        guide_path = Path.cwd() / "data" / "interviews" / f"{guide_id}.json"
        if guide_path.exists():
            try:
                # Load the guide
                with open(guide_path, 'r') as f:
                    guide_data = json.load(f)
                
                # Add session to the guide if not already present
                if "sessions" not in guide_data:
                    guide_data["sessions"] = []
                
                if session_id not in guide_data["sessions"]:
                    guide_data["sessions"].append(session_id)
                    guide_data["updated_at"] = datetime.datetime.now().isoformat()
                    
                    # Save the updated guide
                    with open(guide_path, 'w') as f:
                        json.dump(guide_data, f, indent=2)
                    
                    logger.info(f"Added session {session_id} to guide {guide_id}")
            except Exception as e:
                logger.error(f"Error updating guide {guide_id} with session {session_id}: {str(e)}")
    
    logger.info(f"Session saved to {output_path}")
    return output_path

def main():
    parser = argparse.ArgumentParser(description="Convert transcript to Daria session format")
    parser.add_argument('-f', '--file', help='Path to transcript file', required=True)
    parser.add_argument('-g', '--guide-id', help='Discussion guide ID', default='9d9b0648-5f14-4a22-81df-290bbd67049d')
    parser.add_argument('-t', '--title', help='Interview title', default='Washing Machine World')
    parser.add_argument('-p', '--project', help='Project name', default='World of Washing Machines')
    parser.add_argument('-n', '--name', help='Participant name', default='Jason')
    parser.add_argument('-o', '--output', help='Output file path', default=None)
    parser.add_argument('-s', '--session-id', help='Override session ID (UUID)', default=None)
    
    args = parser.parse_args()
    
    # Read the transcript file
    logger.info(f"Reading transcript from {args.file}")
    with open(args.file, 'r') as f:
        transcript_content = f.read()
    
    # Process the transcript
    metadata = {
        'session_id': args.session_id or str(uuid.uuid4()),  # Generate UUID if none provided
        'guide_id': args.guide_id,
        'title': args.title,
        'project': args.project,
        'participant_name': args.name
    }
    
    session_data = process_transcript(transcript_content, metadata)
    
    # Save the session
    output_path = args.output
    if output_path is None and args.session_id:
        output_path = Path.cwd() / "data" / "interviews" / "sessions" / f"{args.session_id}.json"
    
    save_session(session_data, output_path)
    
    logger.info("Transcript processing complete!")
    logger.info(f"Session ID: {session_data['id']}")
    logger.info(f"Guide ID: {session_data['guide_id']}")
    logger.info(f"Messages: {len(session_data['messages'])}")

if __name__ == "__main__":
    main() 