# -*- coding: utf-8 -*-
"""
File Tools - Search, Big Files, Old Files, Empty Folders, Export
"""
import os
import re
import json
from datetime import datetime, timedelta
from collections import defaultdict


def format_size(size_bytes: int) -> str:
    """Format bytes to human readable."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


# ===== SEARCH =====
def search_files(folder_path: str, query: str, progress_cb=None) -> list:
    """
    Search for files by name (supports wildcards * and ?).
    """
    folder_path = os.path.abspath(folder_path)
    if not os.path.isdir(folder_path):
        return []
    
    skip_dirs = {"node_modules", ".git", "__pycache__", ".venv", "venv", 
                 "$RECYCLE.BIN", "System Volume Information"}
    
    # Convert query to regex
    query_lower = query.lower()
    if "*" in query or "?" in query:
        # Wildcard search
        pattern = query_lower.replace(".", r"\.").replace("*", ".*").replace("?", ".")
        regex = re.compile(f"^{pattern}$", re.IGNORECASE)
        match_func = lambda name: regex.match(name.lower())
    else:
        # Simple contains search
        match_func = lambda name: query_lower in name.lower()
    
    results = []
    count = 0
    
    for dirpath, dirnames, filenames in os.walk(folder_path, topdown=True):
        dirnames[:] = [d for d in dirnames if d not in skip_dirs]
        
        for name in filenames:
            count += 1
            if progress_cb and count % 500 == 0:
                progress_cb(f"Searching: {count} files...")
            
            if match_func(name):
                try:
                    full_path = os.path.join(dirpath, name)
                    stat = os.stat(full_path)
                    results.append({
                        "name": name,
                        "path": full_path,
                        "rel_path": os.path.relpath(full_path, folder_path),
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                    })
                except (OSError, PermissionError):
                    continue
    
    # Sort by name
    results.sort(key=lambda x: x["name"].lower())
    return results


# ===== EMPTY FOLDERS =====
def find_empty_folders(folder_path: str, progress_cb=None) -> list:
    """
    Find all empty folders (no files, only empty subfolders).
    """
    folder_path = os.path.abspath(folder_path)
    if not os.path.isdir(folder_path):
        return []
    
    skip_dirs = {"node_modules", ".git", "__pycache__", ".venv", "venv", 
                 "$RECYCLE.BIN", "System Volume Information"}
    
    empty_folders = []
    count = 0
    
    # Walk bottom-up to find truly empty folders
    for dirpath, dirnames, filenames in os.walk(folder_path, topdown=False):
        count += 1
        if progress_cb and count % 100 == 0:
            progress_cb(f"Checking: {count} folders...")
        
        # Skip system folders
        dirname = os.path.basename(dirpath)
        if dirname.lower() in skip_dirs:
            continue
        
        # Check if folder is empty (no files, and all subdirs are empty/removed)
        try:
            remaining_items = os.listdir(dirpath)
            # Filter out items that are in skip_dirs
            remaining_items = [i for i in remaining_items if i.lower() not in skip_dirs]
            
            if not remaining_items:
                # Truly empty
                empty_folders.append({
                    "path": dirpath,
                    "name": dirname,
                    "rel_path": os.path.relpath(dirpath, folder_path),
                })
        except (OSError, PermissionError):
            continue
    
    return empty_folders


def delete_empty_folders(empty_folders: list, simulation: bool = False) -> dict:
    """Delete empty folders."""
    results = {"deleted": [], "errors": [], "simulation": simulation}
    
    # Sort by depth (deepest first) to delete children before parents
    sorted_folders = sorted(empty_folders, key=lambda x: x["path"].count(os.sep), reverse=True)
    
    for folder in sorted_folders:
        path = folder.get("path", "")
        if not path:
            continue
        
        if simulation:
            results["deleted"].append({"path": path, "action": "would_delete"})
        else:
            try:
                os.rmdir(path)
                results["deleted"].append({"path": path, "action": "deleted"})
            except Exception as e:
                results["errors"].append({"path": path, "error": str(e)})
    
    return results


# ===== BIG FILES =====
def find_big_files(folder_path: str, min_size_mb: float = 100, progress_cb=None) -> list:
    """
    Find files larger than min_size_mb.
    """
    folder_path = os.path.abspath(folder_path)
    if not os.path.isdir(folder_path):
        return []
    
    skip_dirs = {"node_modules", ".git", "__pycache__", ".venv", "venv", 
                 "$RECYCLE.BIN", "System Volume Information"}
    
    min_size = min_size_mb * 1024 * 1024  # Convert to bytes
    big_files = []
    count = 0
    
    for dirpath, dirnames, filenames in os.walk(folder_path, topdown=True):
        dirnames[:] = [d for d in dirnames if d not in skip_dirs]
        
        for name in filenames:
            count += 1
            if progress_cb and count % 500 == 0:
                progress_cb(f"Scanning: {count} files...")
            
            try:
                full_path = os.path.join(dirpath, name)
                size = os.path.getsize(full_path)
                
                if size >= min_size:
                    stat = os.stat(full_path)
                    _, ext = os.path.splitext(name)
                    big_files.append({
                        "name": name,
                        "path": full_path,
                        "rel_path": os.path.relpath(full_path, folder_path),
                        "size": size,
                        "size_str": format_size(size),
                        "ext": ext.lower(),
                        "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                    })
            except (OSError, PermissionError):
                continue
    
    # Sort by size (largest first)
    big_files.sort(key=lambda x: x["size"], reverse=True)
    return big_files


# ===== OLD FILES =====
def find_old_files(folder_path: str, days_old: int = 365, progress_cb=None) -> list:
    """
    Find files not modified in the last X days.
    """
    folder_path = os.path.abspath(folder_path)
    if not os.path.isdir(folder_path):
        return []
    
    skip_dirs = {"node_modules", ".git", "__pycache__", ".venv", "venv", 
                 "$RECYCLE.BIN", "System Volume Information", "Windows", 
                 "Program Files", "Program Files (x86)"}
    
    cutoff_date = datetime.now() - timedelta(days=days_old)
    cutoff_timestamp = cutoff_date.timestamp()
    
    old_files = []
    count = 0
    total_size = 0
    
    for dirpath, dirnames, filenames in os.walk(folder_path, topdown=True):
        dirnames[:] = [d for d in dirnames if d.lower() not in skip_dirs]
        
        for name in filenames:
            count += 1
            if progress_cb and count % 500 == 0:
                progress_cb(f"Scanning: {count} files...")
            
            try:
                full_path = os.path.join(dirpath, name)
                stat = os.stat(full_path)
                
                # Check modification time and access time
                mtime = stat.st_mtime
                atime = stat.st_atime
                last_used = max(mtime, atime)
                
                if last_used < cutoff_timestamp:
                    _, ext = os.path.splitext(name)
                    age_days = (datetime.now() - datetime.fromtimestamp(mtime)).days
                    old_files.append({
                        "name": name,
                        "path": full_path,
                        "rel_path": os.path.relpath(full_path, folder_path),
                        "size": stat.st_size,
                        "size_str": format_size(stat.st_size),
                        "ext": ext.lower(),
                        "modified": datetime.fromtimestamp(mtime).strftime("%Y-%m-%d"),
                        "age_days": age_days,
                    })
                    total_size += stat.st_size
            except (OSError, PermissionError):
                continue
    
    # Sort by age (oldest first)
    old_files.sort(key=lambda x: x["age_days"], reverse=True)
    
    return {
        "files": old_files,
        "count": len(old_files),
        "total_size": total_size,
        "total_size_str": format_size(total_size),
    }


# ===== EXPORT =====
def export_report(data: dict, output_path: str, format_type: str = "txt") -> str:
    """
    Export report to file (txt or json).
    """
    try:
        if format_type == "json":
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        else:
            # Text format
            lines = []
            lines.append("=" * 60)
            lines.append("FOLDER ANALYSIS REPORT")
            lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            lines.append("=" * 60)
            
            if "folder_info" in data:
                info = data["folder_info"]
                lines.append(f"\n📁 FOLDER: {info.get('folder_name', '')}")
                lines.append(f"📍 Path: {info.get('folder_path', '')}")
                lines.append(f"💾 Size: {format_size(info.get('total_size', 0))}")
                lines.append(f"📄 Files: {info.get('total_files', 0)}")
                lines.append(f"📁 Folders: {info.get('total_subdirs', 0)}")
            
            if "mismatched_files" in data and data["mismatched_files"]:
                lines.append(f"\n{'─' * 40}")
                lines.append("⚠️ MISMATCHED FILES")
                lines.append(f"{'─' * 40}")
                for f in data["mismatched_files"][:50]:
                    lines.append(f"  {f.get('rel_path', f.get('name', ''))}")
                    lines.append(f"    Reason: {f.get('reason', '')}")
            
            if "duplicates" in data and data["duplicates"].get("groups"):
                lines.append(f"\n{'─' * 40}")
                lines.append("📋 DUPLICATE FILES")
                lines.append(f"{'─' * 40}")
                lines.append(f"  Groups: {data['duplicates'].get('duplicate_groups', 0)}")
                lines.append(f"  Total duplicates: {data['duplicates'].get('total_duplicate_files', 0)}")
                lines.append(f"  Wasted space: {data['duplicates'].get('total_duplicate_size_mb', 0):.1f} MB")
            
            if "big_files" in data and data["big_files"]:
                lines.append(f"\n{'─' * 40}")
                lines.append("📦 BIG FILES")
                lines.append(f"{'─' * 40}")
                for f in data["big_files"][:20]:
                    lines.append(f"  {f.get('size_str', '')}: {f.get('rel_path', '')}")
            
            if "old_files" in data and data["old_files"].get("files"):
                lines.append(f"\n{'─' * 40}")
                lines.append("🕐 OLD FILES")
                lines.append(f"{'─' * 40}")
                lines.append(f"  Count: {data['old_files'].get('count', 0)}")
                lines.append(f"  Total size: {data['old_files'].get('total_size_str', '')}")
            
            if "empty_folders" in data and data["empty_folders"]:
                lines.append(f"\n{'─' * 40}")
                lines.append("🗑️ EMPTY FOLDERS")
                lines.append(f"{'─' * 40}")
                for f in data["empty_folders"][:30]:
                    lines.append(f"  {f.get('rel_path', f.get('path', ''))}")
            
            lines.append("\n" + "=" * 60)
            
            with open(output_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
        
        return output_path
    except Exception as e:
        return f"Error: {e}"


def generate_full_report(folder_path: str, progress_cb=None) -> dict:
    """
    Generate a complete report of the folder.
    """
    from folder_info import get_folder_details
    from mismatch_detector import find_mismatched_files
    from duplicate_detector import find_duplicates
    
    report = {
        "generated_at": datetime.now().isoformat(),
        "folder_path": folder_path,
    }
    
    if progress_cb:
        progress_cb("Getting folder info...")
    report["folder_info"] = get_folder_details(folder_path)
    
    if progress_cb:
        progress_cb("Analyzing folder purpose...")
    analysis = find_mismatched_files(folder_path, use_ai=False)
    report["mismatched_files"] = analysis.get("mismatched_files", [])
    report["analysis"] = {
        "purpose": analysis.get("purpose"),
        "category": analysis.get("category"),
    }
    
    if progress_cb:
        progress_cb("Finding duplicates...")
    report["duplicates"] = find_duplicates(folder_path)
    
    if progress_cb:
        progress_cb("Finding big files...")
    report["big_files"] = find_big_files(folder_path, min_size_mb=50)
    
    if progress_cb:
        progress_cb("Finding old files...")
    report["old_files"] = find_old_files(folder_path, days_old=365)
    
    if progress_cb:
        progress_cb("Finding empty folders...")
    report["empty_folders"] = find_empty_folders(folder_path)
    
    return report
