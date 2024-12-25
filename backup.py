#!/usr/bin/env python3
import subprocess
import datetime
import os

def run_command(cmd):
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error: {e.stderr}")
        return None

def update_timestamps():
    # Update timestamps of all tracked files
    files = run_command("git ls-files")
    if files:
        for file in files.split("\n"):
            if os.path.exists(file):
                os.utime(file, None)  # Update access and modification times to current time

def backup():
    # Update timestamps first
    print("Updating timestamps...")
    update_timestamps()
    
    # Add all changes
    print("Adding changes...")
    if run_command("git add -A"):  # Changed to -A to handle deletions better
        # Create commit message with timestamp
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status = run_command("git status --porcelain")
        if status:
            changed_files = [line[3:] for line in status.split("\n") if line and not line.startswith("??")]
            num_changes = len(changed_files)
            
            # Create more detailed commit message
            if num_changes > 0:
                files_list = ", ".join(changed_files[:3])
                if num_changes > 3:
                    files_list += f" and {num_changes - 3} more"
                msg = f"Update {files_list} [{timestamp}]"
                
                # Commit changes
                print(f"Committing: {msg}")
                if run_command(f'git commit -m "{msg}"'):
                    # Push to GitHub
                    print("Pushing to GitHub...")
                    if run_command("git push origin main"):
                        print("Successfully pushed to GitHub!")
                    else:
                        print("Failed to push. Check your GitHub credentials.")
                else:
                    print("Failed to commit changes.")
            else:
                print("No changes to commit.")
        else:
            print("No changes to commit.")
    else:
        print("Failed to add changes.")

if __name__ == "__main__":
    print("Starting backup...")
    backup()
    print("Done!") 