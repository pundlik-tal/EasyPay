#!/usr/bin/env python3
"""
Dashboard update script for EasyPay MVP progress tracking.
This script updates the progress tracking dashboard with current metrics.
"""

import json
import re
from datetime import datetime
from pathlib import Path

def load_metrics():
    """Load progress metrics from file."""
    try:
        with open('progress_metrics.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return None

def update_progress_section(content, metrics):
    """Update the progress summary section."""
    progress = metrics['progress']
    
    # Update overall progress
    pattern = r'(\*\*Total Tasks\*\*: )\d+'
    replacement = f'\\g<1>{progress["total_tasks"]}'
    content = re.sub(pattern, replacement, content)
    
    pattern = r'(\*\*Completed\*\*: )\d+'
    replacement = f'\\g<1>{progress["completed_tasks"]}'
    content = re.sub(pattern, replacement, content)
    
    pattern = r'(\*\*In Progress\*\*: )\d+'
    replacement = f'\\g<1>{progress["completed_tasks"]}'  # Mock in progress
    content = re.sub(pattern, replacement, content)
    
    pattern = r'(\*\*Not Started\*\*: )\d+'
    replacement = f'\\g<1>{progress["total_tasks"] - progress["completed_tasks"]}'
    content = re.sub(pattern, replacement, content)
    
    return content

def update_phase_progress(content, metrics):
    """Update phase progress table."""
    phases = metrics['phases']
    
    # Update Phase 1 progress
    phase_1 = phases['phase_1']
    pattern = r'(\| Phase 1: Foundation \| Week 1 \| 40 \| )\d+ \| \d+% \| \w+ \|'
    replacement = f'\\g<1>{phase_1["completed"]} | {phase_1["progress"]}% | {"In Progress" if phase_1["progress"] > 0 else "Not Started"} |'
    content = re.sub(pattern, replacement, content)
    
    # Update other phases similarly
    for phase_name, phase_data in phases.items():
        if phase_name != 'phase_1':
            phase_display = phase_name.replace('_', ' ').title()
            pattern = f'(\\| {phase_display} \\| Week \\d+ \\| \\d+ \\| )\\d+ \\| \\d+% \\| \\w+ \\|'
            replacement = f'\\g<1>{phase_data["completed"]} | {phase_data["progress"]}% | {"In Progress" if phase_data["progress"] > 0 else "Not Started"} |'
            content = re.sub(pattern, replacement, content)
    
    return content

def update_metrics_section(content, metrics):
    """Update key metrics section."""
    code_metrics = metrics['code_metrics']
    
    # Update test coverage
    pattern = r'(\*\*Test Coverage\*\*: )\d+%'
    replacement = f'\\g<1>{code_metrics["test_coverage"]}%'
    content = re.sub(pattern, replacement, content)
    
    # Update code files count
    pattern = r'(\*\*Code Files\*\*: )\d+'
    replacement = f'\\g<1>{code_metrics["python_files"]}'
    content = re.sub(pattern, replacement, content)
    
    return content

def update_burndown_chart(content, metrics):
    """Update burndown chart visualization."""
    progress = metrics['progress']
    total_tasks = progress['total_tasks']
    completed_tasks = progress['completed_tasks']
    remaining_tasks = total_tasks - completed_tasks
    
    # Create simple ASCII burndown chart
    chart_lines = []
    for week in range(1, 7):
        if week == 1:
            tasks_remaining = remaining_tasks
        else:
            # Simple linear projection
            tasks_remaining = max(0, total_tasks - (completed_tasks + (week - 1) * 8))
        
        bar_length = int(tasks_remaining / total_tasks * 40)
        bar = "█" * bar_length + " " * (40 - bar_length)
        chart_lines.append(f"{tasks_remaining:3d} |{bar}|")
    
    # Update chart in content
    chart_pattern = r'```\nTasks Remaining\n.*?\n```'
    chart_content = f"```\nTasks Remaining\n" + "\n".join(chart_lines) + "\n```"
    content = re.sub(chart_pattern, chart_content, content, flags=re.DOTALL)
    
    return content

def update_timestamp(content):
    """Update the last updated timestamp."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
    pattern = r'(\*\*Last Updated\*\*: ).*'
    replacement = f'\\g<1>{now}'
    content = re.sub(pattern, replacement, content)
    
    return content

def main():
    """Main function to update the dashboard."""
    
    # Load metrics
    metrics = load_metrics()
    if not metrics:
        print("No metrics found. Run calculate_progress.py first.")
        return
    
    # Read dashboard file
    dashboard_file = "docs/sources/04-progress-tracking-dashboard.md"
    try:
        with open(dashboard_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Dashboard file not found: {dashboard_file}")
        return
    
    # Update sections
    content = update_progress_section(content, metrics)
    content = update_phase_progress(content, metrics)
    content = update_metrics_section(content, metrics)
    content = update_burndown_chart(content, metrics)
    content = update_timestamp(content)
    
    # Write updated content
    with open(dashboard_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("Dashboard updated successfully!")
    print(f"Progress: {metrics['progress']['completed_tasks']}/{metrics['progress']['total_tasks']} tasks completed")

if __name__ == "__main__":
    main()
