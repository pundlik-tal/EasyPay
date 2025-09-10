#!/usr/bin/env python3
"""
Progress calculation script for EasyPay MVP development.
This script analyzes the codebase and calculates progress metrics.
"""

import os
import re
import json
from datetime import datetime
from pathlib import Path

def count_tasks_in_file(file_path):
    """Count completed and total tasks in a markdown file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Count completed tasks (marked with [x])
        completed = len(re.findall(r'- \[x\]', content))
        
        # Count total tasks (marked with [ ] or [x])
        total = len(re.findall(r'- \[[ x]\]', content))
        
        return completed, total
    except FileNotFoundError:
        return 0, 0

def count_code_files(directory):
    """Count Python files in the project."""
    python_files = list(Path(directory).rglob("*.py"))
    return len(python_files)

def count_test_files(directory):
    """Count test files in the project."""
    test_files = list(Path(directory).rglob("test_*.py"))
    test_files.extend(Path(directory).rglob("*_test.py"))
    return len(test_files)

def calculate_test_coverage():
    """Calculate test coverage if coverage report exists."""
    coverage_file = "coverage.json"
    if os.path.exists(coverage_file):
        try:
            with open(coverage_file, 'r') as f:
                coverage_data = json.load(f)
                return coverage_data.get('totals', {}).get('percent_covered', 0)
        except:
            return 0
    return 0

def analyze_github_issues():
    """Analyze GitHub issues for progress tracking."""
    # This would integrate with GitHub API in a real implementation
    # For now, return mock data
    return {
        'open_issues': 0,
        'closed_issues': 0,
        'in_progress_issues': 0
    }

def main():
    """Main function to calculate progress metrics."""
    
    # Count tasks in progress tracking dashboard
    dashboard_file = "docs/sources/04-progress-tracking-dashboard.md"
    completed_tasks, total_tasks = count_tasks_in_file(dashboard_file)
    
    # Count code files
    code_files = count_code_files(".")
    test_files = count_test_files(".")
    
    # Calculate test coverage
    test_coverage = calculate_test_coverage()
    
    # Analyze GitHub issues
    issues = analyze_github_issues()
    
    # Calculate progress percentage
    progress_percentage = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
    
    # Generate metrics
    metrics = {
        'timestamp': datetime.now().isoformat(),
        'progress': {
            'completed_tasks': completed_tasks,
            'total_tasks': total_tasks,
            'progress_percentage': round(progress_percentage, 2)
        },
        'code_metrics': {
            'python_files': code_files,
            'test_files': test_files,
            'test_coverage': test_coverage
        },
        'issues': issues,
        'phases': {
            'phase_1': {'completed': 0, 'total': 40, 'progress': 0},
            'phase_2': {'completed': 0, 'total': 80, 'progress': 0},
            'phase_3': {'completed': 0, 'total': 40, 'progress': 0},
            'phase_4': {'completed': 0, 'total': 40, 'progress': 0},
            'phase_5': {'completed': 0, 'total': 40, 'progress': 0}
        }
    }
    
    # Save metrics to file
    with open('progress_metrics.json', 'w') as f:
        json.dump(metrics, f, indent=2)
    
    # Print summary
    print(f"Progress: {completed_tasks}/{total_tasks} tasks completed ({progress_percentage:.1f}%)")
    print(f"Code files: {code_files}")
    print(f"Test files: {test_files}")
    print(f"Test coverage: {test_coverage}%")
    
    return metrics

if __name__ == "__main__":
    main()
