# -*- coding: utf-8 -*-
"""
Backup Manager - Auto backup before operations, easy restore.
Keeps history of all file movements for complete undo capability.
"""
import os
import json
import shutil
from datetime import datetime
from collections import defaultdict

BACKUP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backups")
os.makedirs(BACKUP_DIR, exist_ok=True)


def create_backup_session(description: str = "") -> dict:
    """
    Create a new backup session before any operation.
    Returns session info with unique ID.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_id = f"backup_{timestamp}"
    
    session = {
        "id": session_id,
        "timestamp": timestamp,
        "created_at": datetime.now().isoformat(),
        "description": description,
        "operations": [],
        "status": "active",
    }
    
    # Save session file
    session_path = os.path.join(BACKUP_DIR, f"{session_id}.json")
    with open(session_path, "w", encoding="utf-8") as f:
        json.dump(session, f, indent=2, ensure_ascii=False)
    
    return session


def add_operation(session_id: str, operation: dict) -> bool:
    """
    Add an operation to the backup session.
    operation: {action, src, dest, size, ...}
    """
    session_path = os.path.join(BACKUP_DIR, f"{session_id}.json")
    
    if not os.path.isfile(session_path):
        return False
    
    try:
        with open(session_path, "r", encoding="utf-8") as f:
            session = json.load(f)
        
        session["operations"].append({
            **operation,
            "recorded_at": datetime.now().isoformat(),
        })
        
        with open(session_path, "w", encoding="utf-8") as f:
            json.dump(session, f, indent=2, ensure_ascii=False)
        
        return True
    except:
        return False


def complete_session(session_id: str, success_count: int, error_count: int) -> bool:
    """Mark a backup session as complete."""
    session_path = os.path.join(BACKUP_DIR, f"{session_id}.json")
    
    if not os.path.isfile(session_path):
        return False
    
    try:
        with open(session_path, "r", encoding="utf-8") as f:
            session = json.load(f)
        
        session["status"] = "completed"
        session["completed_at"] = datetime.now().isoformat()
        session["success_count"] = success_count
        session["error_count"] = error_count
        
        with open(session_path, "w", encoding="utf-8") as f:
            json.dump(session, f, indent=2, ensure_ascii=False)
        
        return True
    except:
        return False


def get_all_backups() -> list:
    """Get all backup sessions, newest first."""
    backups = []
    
    if not os.path.isdir(BACKUP_DIR):
        return backups
    
    for filename in os.listdir(BACKUP_DIR):
        if filename.startswith("backup_") and filename.endswith(".json"):
            filepath = os.path.join(BACKUP_DIR, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    session = json.load(f)
                    session["filepath"] = filepath
                    backups.append(session)
            except:
                continue
    
    # Sort by timestamp (newest first)
    backups.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return backups


def get_backup_details(session_id: str) -> dict:
    """Get full details of a backup session."""
    session_path = os.path.join(BACKUP_DIR, f"{session_id}.json")
    
    if not os.path.isfile(session_path):
        return {"error": "Backup not found"}
    
    try:
        with open(session_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        return {"error": str(e)}


def restore_backup(session_id: str, progress_cb=None) -> dict:
    """
    Restore all files from a backup session to their original locations.
    """
    session = get_backup_details(session_id)
    
    if "error" in session:
        return session
    
    operations = session.get("operations", [])
    if not operations:
        return {"error": "No operations to restore"}
    
    results = {
        "restored": [],
        "errors": [],
        "skipped": [],
        "total": len(operations),
    }
    
    # Reverse order to undo in correct sequence
    for i, op in enumerate(reversed(operations)):
        src = op.get("src", "")  # Original location
        dest = op.get("dest", "")  # Where it was moved to
        
        if progress_cb:
            progress_cb(i + 1, len(operations))
        
        # Check if file exists at destination
        if not dest or not os.path.isfile(dest):
            results["skipped"].append({
                "file": dest,
                "reason": "File not found at moved location"
            })
            continue
        
        # Check if original location is free
        if os.path.exists(src):
            # File already exists at original location
            results["skipped"].append({
                "file": src,
                "reason": "File already exists at original location"
            })
            continue
        
        try:
            # Recreate original directory if needed
            src_dir = os.path.dirname(src)
            if src_dir and not os.path.exists(src_dir):
                os.makedirs(src_dir, exist_ok=True)
            
            # Move file back to original location
            shutil.move(dest, src)
            
            results["restored"].append({
                "from": dest,
                "to": src,
            })
            
        except Exception as e:
            results["errors"].append({
                "file": dest,
                "target": src,
                "error": str(e)
            })
    
    # Mark backup as restored
    _mark_restored(session_id)
    
    return results


def _mark_restored(session_id: str):
    """Mark a backup session as restored."""
    session_path = os.path.join(BACKUP_DIR, f"{session_id}.json")
    
    if not os.path.isfile(session_path):
        return
    
    try:
        with open(session_path, "r", encoding="utf-8") as f:
            session = json.load(f)
        
        session["status"] = "restored"
        session["restored_at"] = datetime.now().isoformat()
        
        with open(session_path, "w", encoding="utf-8") as f:
            json.dump(session, f, indent=2, ensure_ascii=False)
    except:
        pass


def delete_backup(session_id: str) -> bool:
    """Delete a backup session file."""
    session_path = os.path.join(BACKUP_DIR, f"{session_id}.json")
    
    try:
        if os.path.isfile(session_path):
            os.remove(session_path)
            return True
    except:
        pass
    return False


def get_last_backup() -> dict:
    """Get the most recent backup session."""
    backups = get_all_backups()
    if backups:
        return backups[0]
    return {}


def format_backup_list(backups: list) -> str:
    """Format backup list for display."""
    if not backups:
        return "No backups found.\n\nBackups are created automatically when you move files."
    
    lines = []
    lines.append("=" * 55)
    lines.append("📦 BACKUP HISTORY")
    lines.append("=" * 55)
    
    for b in backups[:20]:
        status_icon = {
            "active": "🔄",
            "completed": "✅",
            "restored": "⏪",
        }.get(b.get("status", ""), "❓")
        
        lines.append(f"\n{status_icon} {b.get('id', 'Unknown')}")
        lines.append(f"   📅 {b.get('created_at', '')[:19]}")
        lines.append(f"   📝 {b.get('description', 'No description')}")
        lines.append(f"   📄 Operations: {len(b.get('operations', []))}")
        lines.append(f"   Status: {b.get('status', 'unknown').upper()}")
        
        if b.get("restored_at"):
            lines.append(f"   ⏪ Restored: {b.get('restored_at', '')[:19]}")
    
    if len(backups) > 20:
        lines.append(f"\n... and {len(backups) - 20} more backups")
    
    return "\n".join(lines)


def quick_restore_last() -> dict:
    """Quick restore the last backup with one call."""
    last = get_last_backup()
    if not last:
        return {"error": "No backups found"}
    
    return restore_backup(last.get("id", ""))
