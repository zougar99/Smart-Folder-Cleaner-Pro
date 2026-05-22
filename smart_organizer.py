# -*- coding: utf-8 -*-
"""
Smart Organizer - Safely move mismatched files out of projects.
Creates backup before any operation for complete recovery.
"""
import os
import shutil
import json
from datetime import datetime
from backup_manager import create_backup_session, add_operation, complete_session


def execute_separation(plan: list, simulation: bool = False, progress_cb=None, description: str = "") -> dict:
    """
    Execute the separation plan - move files to destination.
    Creates automatic backup for easy restore.
    Returns summary with results and backup info.
    """
    results = {
        "success": [],
        "errors": [],
        "skipped": [],
        "simulation": simulation,
        "timestamp": datetime.now().isoformat(),
    }
    
    undo_log = []
    total = len(plan)
    
    # Create backup session BEFORE any operation
    backup_session = None
    if not simulation:
        backup_session = create_backup_session(description or f"Moving {total} files")
        results["backup_id"] = backup_session.get("id", "")
    
    for i, item in enumerate(plan):
        src = item.get("src", "")
        dest = item.get("dest", "")
        
        if not src or not os.path.isfile(src):
            results["skipped"].append({**item, "reason": "Source file not found"})
            continue
        
        if not dest:
            results["skipped"].append({**item, "reason": "No destination specified"})
            continue
        
        # Handle duplicate names
        if os.path.exists(dest) and not simulation:
            base, ext = os.path.splitext(dest)
            n = 1
            while os.path.exists(dest):
                dest = f"{base}_{n}{ext}"
                n += 1
        
        if simulation:
            results["success"].append({
                "src": src,
                "dest": dest,
                "reason": item.get("reason", ""),
                "action": "would_move"
            })
        else:
            try:
                # Create destination directory
                dest_dir = os.path.dirname(dest)
                os.makedirs(dest_dir, exist_ok=True)
                
                # Move file
                shutil.move(src, dest)
                
                results["success"].append({
                    "src": src,
                    "dest": dest,
                    "reason": item.get("reason", ""),
                    "action": "moved"
                })
                
                # Log for undo
                undo_log.append({
                    "original": src,
                    "moved_to": dest,
                })
                
                # Add to backup session
                if backup_session:
                    add_operation(backup_session["id"], {
                        "action": "move",
                        "src": src,
                        "dest": dest,
                        "size": item.get("size", 0),
                    })
                
            except Exception as e:
                results["errors"].append({
                    "src": src,
                    "dest": dest,
                    "error": str(e)
                })
        
        if progress_cb:
            progress_cb(i + 1, total)
    
    # Complete backup session
    if backup_session and not simulation:
        complete_session(
            backup_session["id"],
            len(results["success"]),
            len(results["errors"])
        )
    
    # Save undo log (legacy support)
    if not simulation and undo_log:
        results["undo_log"] = _save_undo_log(undo_log)
    
    return results


def _save_undo_log(undo_log: list) -> str:
    """Save undo log to tmp folder for recovery."""
    tmp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_path = os.path.join(tmp_dir, f"undo_log_{timestamp}.json")
    
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": timestamp,
            "operations": undo_log,
        }, f, indent=2, ensure_ascii=False)
    
    return log_path


def undo_separation(undo_log_path: str, progress_cb=None) -> dict:
    """
    Undo a previous separation by moving files back.
    """
    results = {
        "restored": [],
        "errors": [],
        "skipped": [],
    }
    
    if not os.path.isfile(undo_log_path):
        return {"error": "Undo log not found"}
    
    try:
        with open(undo_log_path, "r", encoding="utf-8") as f:
            log_data = json.load(f)
    except Exception as e:
        return {"error": f"Failed to read undo log: {e}"}
    
    operations = log_data.get("operations", [])
    total = len(operations)
    
    for i, op in enumerate(operations):
        moved_to = op.get("moved_to", "")
        original = op.get("original", "")
        
        if not os.path.isfile(moved_to):
            results["skipped"].append({
                "file": moved_to,
                "reason": "File no longer exists at moved location"
            })
            continue
        
        try:
            # Recreate original directory if needed
            original_dir = os.path.dirname(original)
            os.makedirs(original_dir, exist_ok=True)
            
            # Move back
            shutil.move(moved_to, original)
            
            results["restored"].append({
                "from": moved_to,
                "to": original,
            })
            
        except Exception as e:
            results["errors"].append({
                "file": moved_to,
                "target": original,
                "error": str(e)
            })
        
        if progress_cb:
            progress_cb(i + 1, total)
    
    return results


def get_undo_logs() -> list:
    """List available undo logs."""
    tmp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tmp")
    if not os.path.isdir(tmp_dir):
        return []
    
    logs = []
    for f in os.listdir(tmp_dir):
        if f.startswith("undo_log_") and f.endswith(".json"):
            path = os.path.join(tmp_dir, f)
            try:
                with open(path, "r", encoding="utf-8") as file:
                    data = json.load(file)
                    logs.append({
                        "path": path,
                        "name": f,
                        "timestamp": data.get("timestamp", ""),
                        "count": len(data.get("operations", [])),
                    })
            except:
                continue
    
    return sorted(logs, key=lambda x: x.get("timestamp", ""), reverse=True)


def clean_empty_folders(root_path: str) -> list:
    """Remove empty folders after separation."""
    removed = []
    
    for dirpath, dirnames, filenames in os.walk(root_path, topdown=False):
        if not dirnames and not filenames:
            try:
                os.rmdir(dirpath)
                removed.append(dirpath)
            except:
                pass
    
    return removed
