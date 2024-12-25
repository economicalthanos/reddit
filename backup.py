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

def backup():
    # Add all changes
    print("Adding changes...")
    if run_command("git add ."):
        # Create commit message with timestamp
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status = run_command("git status --porcelain")
        if status:
            num_changes = len(status.split("\n"))
            msg = f"Update {num_changes} files [{timestamp}]"
            
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
                print("Nothing to commit.")
        else:
            print("No changes to commit.")
    else:
        print("Failed to add changes.")

if __name__ == "__main__":
    print("Starting backup...")
    backup()
    print("Done!") 