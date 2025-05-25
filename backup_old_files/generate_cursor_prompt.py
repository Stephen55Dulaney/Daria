#!/usr/bin/env python3
"""
CLI tool to generate CursorAI prompts from research data.

This script demonstrates how to use the PromptGenerator to create
structured prompts for CursorAI based on opportunities, personas, and user stories.
"""

import argparse
import json
import logging
import sys
from typing import Optional, List

from prompt_generator import PromptGenerator

# Import database modules - comment out if not available yet
try:
    from db import (
        get_dynamodb_resource,
        InterviewSessionsDB,
        TranscriptsDB,
        SprintsDB,
        OpportunitiesDB,
        PersonasDB,
        AgileArtifactsDB,
        CursorPromptsDB,
        PrototypesDB,
        JourneyMapsDB,
    )
    USE_DB = True
except ImportError:
    USE_DB = False
    print("Warning: Database modules not available, using mock data")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DBInterface:
    """
    Simple interface to the database modules to be used by the PromptGenerator.
    """
    
    def __init__(self, use_local=True):
        """
        Initialize the database interface.
        
        Args:
            use_local: Whether to use local DynamoDB.
        """
        if not USE_DB:
            return
        
        self.opportunities = OpportunitiesDB(use_local=use_local)
        self.personas = PersonasDB(use_local=use_local)
        self.agile_artifacts = AgileArtifactsDB(use_local=use_local)
        self.cursor_prompts = CursorPromptsDB(use_local=use_local)
        # Add other database modules as needed


def generate_prompt(
    opportunity_id: str,
    persona_id: Optional[str] = None,
    user_story_ids: Optional[List[str]] = None,
    save_to_db: bool = True,
    output_file: Optional[str] = None,
    use_local_db: bool = True
):
    """
    Generate a CursorAI prompt based on an opportunity.
    
    Args:
        opportunity_id: ID of the opportunity to generate a prompt for.
        persona_id: Optional ID of the persona to include.
        user_story_ids: Optional list of user story IDs to include.
        save_to_db: Whether to save the prompt to the database.
        output_file: Optional file to write the prompt to.
        use_local_db: Whether to use local DynamoDB.
    """
    # Create database interface if using database
    db_interface = None
    if USE_DB and (save_to_db or use_local_db):
        db_interface = DBInterface(use_local=use_local_db)
    
    # Create prompt generator
    generator = PromptGenerator(db_interface=db_interface)
    
    try:
        # Generate the prompt
        logger.info(f"Generating prompt for opportunity {opportunity_id}")
        prompt_data = generator.generate_cursor_prompt(
            opportunity_id=opportunity_id,
            persona_id=persona_id,
            user_story_ids=user_story_ids
        )
        
        # Save to database if requested
        if save_to_db and USE_DB:
            logger.info("Saving prompt to database")
            saved_prompt = generator.save_prompt_to_database(
                opportunity_id=opportunity_id,
                prompt_data=prompt_data
            )
            logger.info(f"Prompt saved with ID: {saved_prompt.get('prompt_id')}")
        
        # Write to output file if requested
        if output_file:
            logger.info(f"Writing prompt to {output_file}")
            with open(output_file, 'w') as f:
                json.dump(prompt_data, f, indent=2)
        
        # Print the prompt content
        print("\n----- GENERATED PROMPT -----\n")
        print(prompt_data['prompt_content'])
        print("\n----------------------------\n")
        
        return prompt_data
    
    except Exception as e:
        logger.error(f"Error generating prompt: {e}")
        raise


def main():
    """
    Main function to parse arguments and generate a prompt.
    """
    parser = argparse.ArgumentParser(description="Generate CursorAI prompts from research data")
    
    parser.add_argument("opportunity_id", help="ID of the opportunity to generate a prompt for")
    parser.add_argument("--persona-id", help="ID of the persona to include")
    parser.add_argument("--user-story-ids", nargs="+", help="IDs of the user stories to include")
    parser.add_argument("--no-save", action="store_true", help="Don't save the prompt to the database")
    parser.add_argument("--output", help="File to write the prompt to")
    parser.add_argument("--aws", action="store_true", help="Use AWS DynamoDB instead of local")
    
    args = parser.parse_args()
    
    try:
        generate_prompt(
            opportunity_id=args.opportunity_id,
            persona_id=args.persona_id,
            user_story_ids=args.user_story_ids,
            save_to_db=not args.no_save,
            output_file=args.output,
            use_local_db=not args.aws
        )
        return 0
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 