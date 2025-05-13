#!/bin/bash

# Script to set the ElevenLabs API key 

echo "==============================================================="
echo "       ElevenLabs API Key Setup for DARIA Interview Tool        "
echo "==============================================================="

# Get the current value (if any)
current_key=$ELEVENLABS_API_KEY
if [ ! -z "$current_key" ]; then
    # Mask the middle of the key for display
    masked_key=${current_key:0:5}...${current_key: -5}
    echo "Current ElevenLabs API key: $masked_key"
else
    echo "No ElevenLabs API key is currently set."
fi

echo
echo "Please enter your ElevenLabs API key:"
echo "(You can get this from your ElevenLabs account page at https://elevenlabs.io/app/account)"
read -p "> " new_key

if [ -z "$new_key" ]; then
    echo "No key entered. Keeping existing value."
    exit 0
fi

# Set the key for the current session
export ELEVENLABS_API_KEY="$new_key"
echo "ElevenLabs API key set for current session."

# Ask if the user wants to add it to their shell profile
echo
echo "Would you like to add this API key to your shell profile for future sessions?"
read -p "(y/n) > " add_to_profile

if [[ "$add_to_profile" == "y" || "$add_to_profile" == "Y" ]]; then
    # Detect shell
    if [ -n "$ZSH_VERSION" ]; then
        profile_file="$HOME/.zshrc"
    elif [ -n "$BASH_VERSION" ]; then
        if [[ "$OSTYPE" == "darwin"* ]]; then
            profile_file="$HOME/.bash_profile"
        else
            profile_file="$HOME/.bashrc"
        fi
    else
        echo "Could not detect shell type. Please add the following line to your shell profile manually:"
        echo "export ELEVENLABS_API_KEY=\"$new_key\""
        exit 0
    fi
    
    # Check if key is already in profile
    if grep -q "export ELEVENLABS_API_KEY" "$profile_file"; then
        # Replace existing line
        sed -i.bak "s|export ELEVENLABS_API_KEY=.*|export ELEVENLABS_API_KEY=\"$new_key\"|" "$profile_file"
        echo "Updated existing API key in $profile_file"
    else
        # Add new line
        echo "" >> "$profile_file"
        echo "# ElevenLabs API key for DARIA Interview Tool" >> "$profile_file"
        echo "export ELEVENLABS_API_KEY=\"$new_key\"" >> "$profile_file"
        echo "Added API key to $profile_file"
    fi
    
    echo
    echo "API key added to your profile. It will be available in new shell sessions."
    echo "To use it in your current session, run:"
    echo "  source $profile_file"
fi

echo
echo "You can now test the TTS service with this key."
echo "To start the direct TTS service:"
echo "  python audio_tools/elevenlabs_tts_direct.py --port 5015"
echo "===============================================================" 