#!/usr/bin/env python3
"""
Notification script for EasyPay MVP progress tracking.
This script sends notifications about progress tracking status.
"""

import os
import sys
import json
from datetime import datetime

def send_slack_notification(webhook_url, message):
    """Send notification to Slack."""
    if not webhook_url:
        print("No Slack webhook URL configured")
        return False
    
    try:
        import requests
        
        payload = {
            "text": message,
            "username": "EasyPay Progress Tracker",
            "icon_emoji": ":chart_with_upwards_trend:"
        }
        
        response = requests.post(webhook_url, json=payload, timeout=10)
        response.raise_for_status()
        print("Slack notification sent successfully")
        return True
    except Exception as e:
        print(f"Failed to send Slack notification: {e}")
        return False

def send_teams_notification(webhook_url, message):
    """Send notification to Microsoft Teams."""
    if not webhook_url:
        print("No Teams webhook URL configured")
        return False
    
    try:
        import requests
        
        payload = {
            "text": message,
            "title": "EasyPay Progress Update",
            "themeColor": "0078D4"
        }
        
        response = requests.post(webhook_url, json=payload, timeout=10)
        response.raise_for_status()
        print("Teams notification sent successfully")
        return True
    except Exception as e:
        print(f"Failed to send Teams notification: {e}")
        return False

def load_progress_metrics():
    """Load progress metrics from file."""
    try:
        with open('progress_metrics.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return None

def generate_notification_message(metrics):
    """Generate notification message."""
    if not metrics:
        return "⚠️ Progress tracking completed but no metrics found."
    
    progress = metrics.get('progress', {})
    completed = progress.get('completed_tasks', 0)
    total = progress.get('total_tasks', 0)
    percentage = progress.get('progress_percentage', 0)
    
    message = f"""📊 EasyPay Progress Update
    
✅ **Overall Progress**: {completed}/{total} tasks completed ({percentage}%)
📅 **Last Updated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}

🎯 **Status**: {"On track" if percentage > 0 else "Ready to begin"}
📈 **Next Steps**: {"Continue development" if percentage < 100 else "Project completed!"}

For detailed reports, check the project repository."""
    
    return message

def main():
    """Main function to send notifications."""
    print("Starting progress notification...")
    
    # Load metrics
    metrics = load_progress_metrics()
    
    # Generate message
    message = generate_notification_message(metrics)
    
    # Get webhook URLs from environment
    slack_webhook = os.getenv('SLACK_WEBHOOK_URL')
    teams_webhook = os.getenv('TEAMS_WEBHOOK_URL')
    
    # Send notifications
    success_count = 0
    
    if slack_webhook:
        if send_slack_notification(slack_webhook, message):
            success_count += 1
    
    if teams_webhook:
        if send_teams_notification(teams_webhook, message):
            success_count += 1
    
    # If no webhooks configured, just log the message
    if not slack_webhook and not teams_webhook:
        print("No webhook URLs configured. Notification message:")
        print(message)
        success_count = 1  # Consider this a success since we logged the message
    
    if success_count > 0:
        print("Progress notification completed successfully")
        sys.exit(0)
    else:
        print("Failed to send any notifications")
        sys.exit(1)

if __name__ == "__main__":
    main()
