import os
import shutil

def migrate_files_with_collision_logging(source_root, target_root, skip_files=None):
    if skip_files is None:
        skip_files = ['.DS_Store'] # Common files to skip
    
    collided_files_log = []
    moved_files_count = 0
    error_files_count = 0
    
    print(f"Starting migration from '{source_root}' to '{target_root}'...")
    print(f"Script is running from: {os.getcwd()}")
    print(f"Source directory (absolute): {os.path.abspath(source_root)}")
    print(f"Target directory (absolute): {os.path.abspath(target_root)}")

    if not os.path.isdir(source_root):
        print(f"ERROR: Source directory '{source_root}' does not exist. Aborting.")
        return [], moved_files_count, error_files_count
    if not os.path.isdir(target_root):
        print(f"ERROR: Target directory '{target_root}' does not exist. Aborting.")
        return [], moved_files_count, error_files_count

    for dirpath, dirnames, filenames in os.walk(source_root):
        # Avoid processing .git directory if it's somehow inside the source_root
        if '.git' in dirnames:
            dirnames.remove('.git')

        for filename in filenames:
            if filename in skip_files:
                print(f"SKIPPING specific file: {os.path.join(dirpath, filename)}")
                continue

            source_file_path = os.path.join(dirpath, filename)
            
            # Calculate relative path from the source_root
            relative_dir_path = os.path.relpath(dirpath, source_root)
            
            if relative_dir_path == ".": # File is in the root of source_root
                target_file_dir = target_root
            else:
                target_file_dir = os.path.join(target_root, relative_dir_path)
            
            target_file_path = os.path.join(target_file_dir, filename)

            # Ensure target directory exists
            try:
                if not os.path.exists(target_file_dir):
                    os.makedirs(target_file_dir)
                    print(f"CREATED directory: {target_file_dir}")
            except Exception as e:
                error_info = {
                    "source_file": source_file_path,
                    "target_file_dir": target_file_dir,
                    "message": f"Error creating target directory: {e}"
                }
                collided_files_log.append(error_info)
                print(f"ERROR creating target directory '{target_file_dir}' for '{source_file_path}': {e}")
                error_files_count += 1
                continue # Skip this file if its target directory cannot be made

            if os.path.exists(target_file_path):
                collision_info = {
                    "source_file": source_file_path,
                    "target_file": target_file_path,
                    "message": "Collision detected. File already exists in target. NOT MOVED."
                }
                collided_files_log.append(collision_info)
                print(f"COLLISION: '{source_file_path}' -> '{target_file_path}' (already exists). NOT MOVED.")
            else:
                try:
                    shutil.move(source_file_path, target_file_path)
                    print(f"MOVED: '{source_file_path}' -> '{target_file_path}'")
                    moved_files_count += 1
                except Exception as e:
                    error_info = {
                        "source_file": source_file_path,
                        "target_file": target_file_path,
                        "message": f"Error moving file: {e}"
                    }
                    collided_files_log.append(error_info) # Log as a collision/error
                    print(f"ERROR moving '{source_file_path}' to '{target_file_path}': {e}")
                    error_files_count += 1

    print("\n--- Migration Summary ---")
    print(f"Total files successfully moved: {moved_files_count}")
    print(f"Total collisions (file existed in target) or errors during move/dir creation: {len(collided_files_log)}")
    
    if collided_files_log:
        print("\nDetails of collisions/errors (files NOT MOVED or errors encountered):")
        for item in collided_files_log:
            print(f"  Source: {item.get('source_file', 'N/A')}")
            if 'target_file_dir' in item: # For directory creation errors
                 print(f"  Target Dir: {item.get('target_file_dir')}")
            else: # For file collision or move errors
                 print(f"  Target: {item.get('target_file', 'N/A')}")
            print(f"  Issue: {item['message']}\n")
    else:
        print("No collisions or errors reported during the migration process.")

    return collided_files_log, moved_files_count, error_files_count

if __name__ == "__main__":
    source_dir = "khora-kernel-vnext"
    target_dir = "khora-kernel"
    
    print("IMPORTANT:")
    print(f"This script will attempt to MOVE files from the source directory ('{source_dir}')")
    print(f"to the target directory ('{target_dir}').")
    print("Files in the source directory will be PERMANENTLY REMOVED if successfully moved and no collision occurs.")
    print("If a file with the same relative path already exists in the target, it will be logged as a COLLISION and the source file will NOT be moved.")
    print("\nEnsure you have adequate backups or are using version control (e.g., a dedicated Git branch).")
    print(f"This script should be run from your workspace root. Current directory: {os.getcwd()}")
    
    # Confirmation step
    confirm = input(f"Are you sure you want to proceed with moving files from '{source_dir}' to '{target_dir}'? (yes/no): ")
    if confirm.lower() == 'yes':
        print("\nStarting migration process...\n")
        collisions, _, _ = migrate_files_with_collision_logging(source_dir, target_dir)
        
        print("\n--- End of Migration Process ---")
        if collisions:
            print("Migration process completed. Collisions/errors were logged above. Please review them carefully.")
            print("The files listed as collisions/errors were NOT moved from the source directory or encountered issues.")
            print("You will need to manually review and merge/handle these collided/error files.")
        else:
            print("Migration process completed. No collisions or errors were reported.")
        print(f"\nRemember to check the status of your '{source_dir}' directory.")
        print("Review the changes in Git, commit them, and then proceed with content renaming and further steps.")
    else:
        print("Migration aborted by user.") 