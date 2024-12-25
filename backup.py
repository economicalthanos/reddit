#!/usr/bin/env python3
import subprocess
import datetime
import os

def run_command(cmd):
    try:
        # Run with shell=False for better security
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

def backup():
    try:
        # Add all changes
        print("Adding changes...")
        subprocess.run(['git', 'add', '.'], check=True)
        
        # Get status
        status = subprocess.run(['git', 'status', '--porcelain'], 
                              capture_output=True, text=True, check=True).stdout
        
        if status.strip():
            # Create commit message
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            changed_files = [line[3:] for line in status.split("\n") 
                           if line and not line.endswith('.DS_Store')]
            
            if changed_files:
                # Format commit message
                files_list = ", ".join(changed_files[:3])
                if len(changed_files) > 3:
                    files_list += f" and {len(changed_files) - 3} more"
                msg = f"Update {files_list} [{timestamp}]"
                
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