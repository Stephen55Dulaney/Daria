import json

# Path to your transcript file
transcript_path = "data/interviews/sessions/476b5632-d177-4539-b3fc-f2b697db082e.json"

# Names to match
assistant_name = "Dulaney, Stephen"
user_name = "Lama Shehadeh"  # Change this to the participant's name

# Load the transcript
with open(transcript_path, "r") as f:
    data = json.load(f)

# Fix roles in messages
for msg in data.get("messages", []):
    content = msg.get("content", "")
    if f"[{assistant_name}]" in content:
        msg["role"] = "assistant"
    elif f"[{user_name}]" in content:
        msg["role"] = "user"
    # Optionally, remove the name tag from the content
    msg["content"] = content.replace(f"[{assistant_name}]", "").replace(f"[{user_name}]", "").strip()

# Save the fixed transcript
with open(transcript_path, "w") as f:
    json.dump(data, f, indent=2)

print("Roles fixed and transcript updated.")