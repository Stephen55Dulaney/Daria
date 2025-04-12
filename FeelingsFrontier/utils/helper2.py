import json
from pathlib import Path
import os
from dotenv import load_dotenv

def load_world(world_name: str) -> dict:
    """Load a game world from a JSON file."""
    try:
        world_path = Path('FeelingsFrontier/worlds') / f"{world_name}.json"
        if not world_path.exists():
            return {}
        
        with open(world_path) as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading world: {str(e)}")
        return {}

def save_world(world_name: str, world_data: dict) -> bool:
    """Save a game world to a JSON file."""
    try:
        worlds_dir = Path('FeelingsFrontier/worlds')
        worlds_dir.mkdir(exist_ok=True)
        
        world_path = worlds_dir / f"{world_name}.json"
        with open(world_path, 'w') as f:
            json.dump(world_data, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving world: {str(e)}")
        return False

def load_env():
    """Load environment variables from .env file."""
    load_dotenv()

def get_together_api_key() -> str:
    """Get the Together API key from environment variables."""
    api_key = os.getenv('TOGETHER_API_KEY')
    if not api_key:
        raise ValueError("TOGETHER_API_KEY not found in environment variables")
    return api_key 