#!/usr/bin/env python3
import subprocess
import datetime
import os
import re

def run_command(cmd):
    try:
        if isinstance(cmd, str):
            cmd = cmd.split()
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error: {e.stderr}")
        return None
    except Exception as e:
        print(f"Error: {str(e)}")
        return None

def analyze_changes(file_path):
    """Analyze changes in a file to generate a meaningful description."""
    try:
        # Get the diff for the file
        diff = subprocess.run(['git', 'diff', '--cached', file_path], 
                            capture_output=True, text=True).stdout
        
        # Count additions and deletions
        additions = len([l for l in diff.split('\n') if l.startswith('+')])
        deletions = len([l for l in diff.split('\n') if l.startswith('-')])
        
        # Analyze file type and changes
        if file_path.endswith('.py'):
            if 'def ' in diff:
                return "Update Python functions"
            elif 'class ' in diff:
                return "Update Python classes"
            elif 'import ' in diff:
                return "Update Python dependencies"
            return "Update Python code"
            
        elif file_path.endswith('.md'):
            if '## ' in diff:
                return "Update documentation sections"
            return "Update documentation"
            
        elif file_path.endswith('.json'):
            return "Update configuration"
            
        elif file_path.endswith('.html'):
            if '<script' in diff:
                return "Update JavaScript"
            elif '<style' in diff:
                return "Update styles"
            return "Update HTML template"
            
        elif file_path.endswith('.css'):
            return "Update styles"
            
        elif file_path.endswith('.js'):
            return "Update JavaScript functionality"
            
        # Generic analysis based on size of changes
        if additions > deletions * 2:
            return "Add new content"
        elif deletions > additions * 2:
            return "Remove outdated content"
        else:
            return "Update content"
            
    except Exception:
        return "Update file"

def generate_commit_message(changed_files):
    """Generate an intelligent commit message based on the changes."""
    try:
        # Analyze each changed file
        changes = {}
        for file in changed_files:
            change_type = analyze_changes(file)
            changes[change_type] = changes.get(change_type, []) + [file]
        
        # Group similar changes
        message_parts = []
        for change_type, files in changes.items():
            if len(files) == 1:
                message_parts.append(f"{change_type} in {os.path.basename(files[0])}")
            else:
                file_count = len(files)
                message_parts.append(f"{change_type} in {file_count} files")
        
        # Create final message
        if message_parts:
            msg = "; ".join(message_parts)
        else:
            msg = "Update files"
            
        # Add timestamp
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"{msg} [{timestamp}]"
        
    except Exception as e:
        print(f"Error generating commit message: {str(e)}")
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"Update repository [{timestamp}]"

def backup():
    try:
        # Add all changes
        print("Adding changes...")
        subprocess.run(['git', 'add', '.'], check=True)
        
        # Get status
        status = subprocess.run(['git', 'status', '--porcelain'], 
                              capture_output=True, text=True, check=True).stdout
        
        if status.strip():
            # Get list of changed files (excluding .DS_Store)
            changed_files = [line[3:] for line in status.split("\n") 
                           if line and not line.endswith('.DS_Store')]
            
            if changed_files:
                # Generate intelligent commit message
                msg = generate_commit_message(changed_files)
                
                # Commit changes
                print(f"Committing: {msg}")
                subprocess.run(['git', 'commit', '-m', msg], check=True)
                
                # Push to GitHub
                print("Pushing to GitHub...")
                subprocess.run(['git', 'push', 'origin', 'main'], check=True)
                print("Successfully pushed to GitHub!")
            else:
                print("No changes to commit (excluding .DS_Store).")
        else:
            print("No changes to commit.")
            
    except subprocess.CalledProcessError as e:
        print(f"Git command failed: {e.stderr}")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    print("Starting backup...")
    backup()
    print("Done!") 