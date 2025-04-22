#!/usr/bin/env python3

import os
import json
from datetime import datetime
from pathlib import Path

def extract_participant_name(transcript_chunks):
    """Extract participant name from transcript chunks."""
    # Common system/bot names to filter out
    system_names = {'system', 'assistant', 'interviewer', 'daria', 'bot', 'ai', 'user'}
    
    # First pass: Look for explicit participant markers
    for chunk in transcript_chunks:
        speaker = chunk.get('speaker', '').strip().lower()
        if not speaker:
            continue
            
        # Check for explicit participant/interviewee markers
        if any(marker in speaker for marker in ['participant:', 'interviewee:', 'participant -', 'interviewee -']):
            name = speaker.split(':')[-1].split('-')[-1].strip()
            if name and name.lower() not in system_names:
                return name.title()
    
    # Second pass: Look for consistent non-system speakers
    speaker_counts = {}
    for chunk in transcript_chunks:
        speaker = chunk.get('speaker', '').strip()
        if not speaker:
            continue
            
        # Clean up the speaker name
        clean_speaker = speaker.lower()
        if '[' in speaker and ']' in speaker:
            clean_speaker = speaker[speaker.find('[')+1:speaker.find(']')].lower()
        elif ':' in speaker:
            clean_speaker = speaker.split(':')[0].strip().lower()
            
        if clean_speaker and clean_speaker not in system_names:
            speaker_counts[clean_speaker] = speaker_counts.get(clean_speaker, 0) + 1
    
    # Find the most frequent non-system speaker
    if speaker_counts:
        most_frequent = max(speaker_counts.items(), key=lambda x: x[1])
        if most_frequent[1] > 1:  # Ensure they spoke at least twice
            return most_frequent[0].title()
    
    return "Anonymous"

def update_interview_titles(interviews_dir):
    """Update interview titles with participant names and dates."""
    updated_count = 0
    
    for interview_file in os.listdir(interviews_dir):
        if not interview_file.endswith('.json'):
            continue
            
        file_path = os.path.join(interviews_dir, interview_file)
        try:
            with open(file_path, 'r') as f:
                interview = json.load(f)
                
            # Get participant name from various sources
            participant_name = None
            
            # 1. Try metadata first
            if interview.get('metadata', {}).get('participant', {}).get('name'):
                participant_name = interview['metadata']['participant']['name']
                print(f"Found name in metadata: {participant_name}")
                
            # 2. Try direct participant_name field
            if not participant_name and interview.get('participant_name'):
                participant_name = interview['participant_name']
                print(f"Found name in direct field: {participant_name}")
                
            # 3. Try extracting from transcript chunks
            if not participant_name and interview.get('chunks'):
                participant_name = extract_participant_name(interview['chunks'])
                print(f"Extracted name from chunks: {participant_name}")
                
            # 4. Try extracting from transcript if no chunks
            if not participant_name and interview.get('transcript'):
                # Convert transcript to chunk-like format
                pseudo_chunks = [{'speaker': line.split(':')[0].strip(), 'content': line.split(':')[1].strip()} 
                               for line in interview['transcript'].split('\n') 
                               if ':' in line]
                participant_name = extract_participant_name(pseudo_chunks)
                print(f"Extracted name from transcript: {participant_name}")
            
            # Format date
            created_at = interview.get('created_at', '')
            try:
                date_obj = datetime.strptime(created_at.split('.')[0], '%Y-%m-%d %H:%M:%S')
                date_str = date_obj.strftime('%B %d, %Y')
            except (ValueError, AttributeError):
                date_str = 'Unknown Date'
                
            # Construct new title
            interview_type = interview.get('type', 'Interview').title()
            new_title = f"{interview_type} with {participant_name} - {date_str}"
            
            if interview.get('title') != new_title:
                interview['title'] = new_title
                with open(file_path, 'w') as f:
                    json.dump(interview, f, indent=2)
                updated_count += 1
                print(f"Updated title to: {new_title}")
                
        except Exception as e:
            print(f"Error updating {interview_file}: {str(e)}")
            continue
            
    print(f"\nUpdated {updated_count} interview titles")
    return updated_count

if __name__ == '__main__':
    update_interview_titles('interviews') 