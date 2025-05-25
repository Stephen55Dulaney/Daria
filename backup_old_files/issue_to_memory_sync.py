#!/usr/bin/env python3
"""
Issue Tracker to Memory Companion Sync Service

This script pulls data from the Issue Tracker and updates DARIA's Memory Companion,
ensuring that DARIA is aware of all project opportunities, epics, and user stories.
"""

import os
import sys
import json
import time
import logging
import argparse
import requests
import schedule
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("issue_memory_sync.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("issue_memory_sync")

class IssueToMemorySync:
    """Handles syncing from Issue Tracker to Memory Companion"""
    
    def __init__(self, issue_api_url, memory_api_url):
        self.issue_api_url = issue_api_url
        self.memory_api_url = memory_api_url
        self.last_sync_time = None
    
    def get_all_issues(self, issue_type=None):
        """Get issues from the Issue Tracker, optionally filtered by type"""
        try:
            params = {}
            if issue_type:
                params['type'] = issue_type
                
            response = requests.get(f"{self.issue_api_url}", params=params)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get issues: {response.status_code}")
                return {"error": f"Failed to get issues: {response.status_code}"}
        except Exception as e:
            logger.error(f"Error connecting to Issue Tracker: {str(e)}")
            return {"error": f"Error connecting to Issue Tracker: {str(e)}"}
    
    def get_opportunities(self):
        """Get all opportunities from the Issue Tracker"""
        return self.get_all_issues(issue_type="opportunity")
    
    def get_epics(self):
        """Get all epics from the Issue Tracker"""
        return self.get_all_issues(issue_type="epic")
    
    def get_user_stories(self):
        """Get all user stories from the Issue Tracker"""
        return self.get_all_issues(issue_type="user_story")
    
    def issue_to_opportunity(self, issue):
        """Convert an issue to a Memory Companion opportunity format"""
        return {
            "id": f"OPP-{issue['id'][:6]}",
            "title": issue["title"],
            "description": issue["description"],
            "priority": issue["priority"].capitalize(),
            "created_at": issue["created_at"],
            "updated_at": issue["updated_at"],
            "status": issue["status"]
        }
    
    def issue_to_timeline_event(self, issue):
        """Convert an issue to a Memory Companion timeline event"""
        event_type = issue["issue_type"].replace("_", " ").capitalize()
        return {
            "date": issue["created_at"][:10],  # Just the date part
            "event": f"New {event_type}: {issue['title']}",
            "details": issue["description"],
            "issue_id": issue["id"]
        }
    
    def update_memory_opportunities(self, opportunities):
        """Update Memory Companion with opportunities from Issue Tracker"""
        try:
            formatted_opps = [self.issue_to_opportunity(opp) for opp in opportunities]
            
            response = requests.post(
                f"{self.memory_api_url}/update_opportunities",
                json={"opportunities": formatted_opps}
            )
            
            if response.status_code == 200:
                logger.info(f"Updated {len(formatted_opps)} opportunities in Memory Companion")
                return {"success": True, "count": len(formatted_opps)}
            else:
                logger.error(f"Failed to update opportunities: {response.status_code}")
                return {"error": f"Failed to update opportunities: {response.status_code}"}
        except Exception as e:
            logger.error(f"Error updating Memory Companion: {str(e)}")
            return {"error": f"Error updating Memory Companion: {str(e)}"}
    
    def update_memory_timeline(self, issues):
        """Update Memory Companion timeline with events from Issue Tracker"""
        try:
            # Only add issues created since last sync
            if self.last_sync_time:
                new_issues = [i for i in issues if i["created_at"] > self.last_sync_time]
            else:
                # First sync, limit to most recent 10 to avoid flooding timeline
                new_issues = sorted(issues, key=lambda x: x["created_at"], reverse=True)[:10]
            
            timeline_events = [self.issue_to_timeline_event(issue) for issue in new_issues]
            
            if not timeline_events:
                logger.info("No new timeline events to add")
                return {"success": True, "count": 0}
            
            for event in timeline_events:
                response = requests.post(
                    f"{self.memory_api_url}/timeline",
                    json={"event": event["event"], "details": event["details"]}
                )
                
                if response.status_code != 200:
                    logger.error(f"Failed to add timeline event: {response.status_code}")
            
            logger.info(f"Added {len(timeline_events)} events to Memory Companion timeline")
            return {"success": True, "count": len(timeline_events)}
        except Exception as e:
            logger.error(f"Error updating timeline: {str(e)}")
            return {"error": f"Error updating timeline: {str(e)}"}
    
    def update_memory_project_data(self):
        """Update project data in Memory Companion with Issue Tracker stats"""
        try:
            all_issues = self.get_all_issues()
            
            if "error" in all_issues:
                return all_issues
            
            issue_counts = {
                "total": len(all_issues),
                "open": len([i for i in all_issues if i["status"] == "open"]),
                "in_progress": len([i for i in all_issues if i["status"] == "in_progress"]),
                "resolved": len([i for i in all_issues if i["status"] == "resolved"]),
                "closed": len([i for i in all_issues if i["status"] == "closed"]),
                "by_type": {}
            }
            
            # Count by type
            for issue in all_issues:
                issue_type = issue["issue_type"]
                if issue_type not in issue_counts["by_type"]:
                    issue_counts["by_type"][issue_type] = 0
                issue_counts["by_type"][issue_type] += 1
            
            response = requests.post(
                f"{self.memory_api_url}/update_project_stats",
                json={"issue_stats": issue_counts}
            )
            
            if response.status_code == 200:
                logger.info("Updated project statistics in Memory Companion")
                return {"success": True}
            else:
                logger.error(f"Failed to update project stats: {response.status_code}")
                return {"error": f"Failed to update project stats: {response.status_code}"}
        except Exception as e:
            logger.error(f"Error updating project stats: {str(e)}")
            return {"error": f"Error updating project stats: {str(e)}"}
    
    def sync_all(self):
        """Perform a full sync from Issue Tracker to Memory Companion"""
        logger.info("Starting sync from Issue Tracker to Memory Companion")
        
        # Get data from Issue Tracker
        opportunities = self.get_opportunities()
        if "error" in opportunities:
            return opportunities
        
        all_issues = self.get_all_issues()
        if "error" in all_issues:
            return all_issues
        
        # Update Memory Companion
        self.update_memory_opportunities(opportunities)
        self.update_memory_timeline(all_issues)
        self.update_memory_project_data()
        
        self.last_sync_time = datetime.now().isoformat()
        logger.info(f"Completed sync at {self.last_sync_time}")
        
        return {"success": True, "sync_time": self.last_sync_time}

def run_scheduled_sync(sync_service, interval_minutes=15):
    """Run the sync service on a schedule"""
    logger.info(f"Setting up scheduled sync every {interval_minutes} minutes")
    
    def job():
        sync_service.sync_all()
    
    # Run once immediately
    job()
    
    # Schedule future runs
    schedule.every(interval_minutes).minutes.do(job)
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Issue Tracker to Memory Companion Sync Service')
    parser.add_argument('--issue-api', default="http://localhost:5025/api/issues", help='Issue Tracker API URL')
    parser.add_argument('--memory-api', default="http://localhost:5030/api/memory_companion", help='Memory Companion API URL')
    parser.add_argument('--interval', type=int, default=15, help='Sync interval in minutes')
    parser.add_argument('--once', action='store_true', help='Run sync once and exit')
    
    args = parser.parse_args()
    
    sync_service = IssueToMemorySync(args.issue_api, args.memory_api)
    
    if args.once:
        sync_service.sync_all()
    else:
        run_scheduled_sync(sync_service, args.interval) 