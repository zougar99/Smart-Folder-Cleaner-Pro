# -*- coding: utf-8 -*-
"""
Duplicate File Detector - Find duplicate files and keep originals.
Uses file hash (MD5) to detect exact duplicates.
"""
import os
import hashlib
from collections import defaultdict
from datetime import datetime


def get_file_hash(filepath: str, chunk_size: int = 8192) -> str:
    """Calculate MD5 hash of a file."""
    hasher = hashlib.md5()
    try:
        with open(filepath, 'rb') as f:
            while chunk := f.read(chunk_size):
                hasher.update(chunk)
        return hasher.hexdigest()
    except (OSError, PermissionError):
        return ""


def find_duplicates(folder_path: str, progress_cb=None) -> dict:
    """
    Scan folder and find duplicate files.
    Returns dict with groups of duplicates.
    """
    folder_path = os.path.abspath(folder_path)
    if not os.path.isdir(folder_path):
        return {"error": "Invalid folder"}
    
    # Skip these directories
    skip_dirs = {"node_modules", ".git", "__pycache__", ".venv", "venv", 
                 "$RECYCLE.BIN", "System Volume Information"}
    
    # First pass: group files by size (quick filter)
    files_by_size = defaultdict(list)
    file_count = 0
    
    for dirpath, dirnames, filenames in os.walk(folder_path, topdown=True):
        dirnames[:] = [d for d in dirnames if d not in skip_dirs]
        
        for name in filenames:
            try:
                full_path = os.path.join(dirpath, name)
                size = os.path.getsize(full_path)
                if size > 0:  # Skip empty files
                    files_by_size[size].append({
                        "path": full_path,
                        "name": name,
                        "size": size,
                        "dir": dirpath,
                        "mtime": os.path.getmtime(full_path),
                    })
                    file_count += 1
                    if progress_cb and file_count % 100 == 0:
                        progress_cb(f"Scanning: {file_count} files...")
            except (OSError, PermissionError):
                continue
    
    # Second pass: hash files with same size
    hash_groups = defaultdict(list)
    potential_dupes = [files for files in files_by_size.values() if len(files) > 1]
    
    total_to_hash = sum(len(group) for group in potential_dupes)
    hashed = 0
    
    for group in potential_dupes:
        for f in group:
            file_hash = get_file_hash(f["path"])
            if file_hash:
                f["hash"] = file_hash
                hash_groups[file_hash].append(f)
            hashed += 1
            if progress_cb and hashed % 50 == 0:
                progress_cb(f"Hashing: {hashed}/{total_to_hash}...")
    
    # Filter to only groups with duplicates
    duplicate_groups = {h: files for h, files in hash_groups.items() if len(files) > 1}
    
    # For each group, determine which is the "original" (oldest by mtime)
    results = []
    total_duplicate_size = 0
    
    for file_hash, files in duplicate_groups.items():
        # Sort by modification time - oldest first (original)
        sorted_files = sorted(files, key=lambda x: x.get("mtime", 0))
        
        original = sorted_files[0]
        duplicates = sorted_files[1:]
        
        group_size = sum(f["size"] for f in duplicates)
        total_duplicate_size += group_size
        
        results.append({
            "hash": file_hash,
            "original": {
                "path": original["path"],
                "name": original["name"],
                "size": original["size"],
                "date": datetime.fromtimestamp(original["mtime"]).strftime("%Y-%m-%d %H:%M"),
            },
            "duplicates": [{
                "path": f["path"],
                "name": f["name"],
                "size": f["size"],
                "date": datetime.fromtimestamp(f["mtime"]).strftime("%Y-%m-%d %H:%M"),
            } for f in duplicates],
            "duplicate_count": len(duplicates),
        })
    
    # Sort by number of duplicates (most first)
    results.sort(key=lambda x: x["duplicate_count"], reverse=True)
    
    return {
        "folder_path": folder_path,
        "total_files_scanned": file_count,
        "duplicate_groups": len(results),
        "total_duplicate_files": sum(r["duplicate_count"] for r in results),
        "total_duplicate_size": total_duplicate_size,
        "total_duplicate_size_mb": total_duplicate_size / (1024 * 1024),
        "groups": results,
    }


def get_duplicate_cleanup_plan(duplicate_result: dict, dest_folder: str) -> list:
    """
    Create a plan to move duplicates to destination folder.
    Keeps originals in place.
    """
    plan = []
    dest_folder = os.path.abspath(dest_folder)
    
    for group in duplicate_result.get("groups", []):
        original = group.get("original", {})
        duplicates = group.get("duplicates", [])
        
        for dup in duplicates:
            src = dup.get("path", "")
            if not src or not os.path.isfile(src):
                continue
            
            name = dup.get("name", os.path.basename(src))
            dest_path = os.path.join(dest_folder, "duplicates", name)
            
            plan.append({
                "src": src,
                "dest": dest_path,
                "original_kept": original.get("path", ""),
                "size": dup.get("size", 0),
                "reason": f"Duplicate of: {original.get('name', '')}",
            })
    
    return plan


def find_similar_names(folder_path: str, progress_cb=None) -> list:
    """
    Find files with similar names (like file.txt, file(1).txt, file_copy.txt).
    """
    import re
    
    folder_path = os.path.abspath(folder_path)
    if not os.path.isdir(folder_path):
        return []
    
    skip_dirs = {"node_modules", ".git", "__pycache__", ".venv", "venv"}
    
    # Pattern to detect copy indicators
    copy_patterns = [
        r'^(.+?)[\s_-]*\((\d+)\)(\.[^.]+)?$',  # file (1).txt, file(2).pdf
        r'^(.+?)[\s_-]*copy[\s_-]*(\d*)(\.[^.]+)?$',  # file copy.txt, file copy 2.txt
        r'^(.+?)[\s_-]*copie[\s_-]*(\d*)(\.[^.]+)?$',  # file copie.txt (French)
        r'^(.+?)_(\d+)(\.[^.]+)?$',  # file_1.txt, file_2.txt
    ]
    
    all_files = []
    for dirpath, dirnames, filenames in os.walk(folder_path, topdown=True):
        dirnames[:] = [d for d in dirnames if d not in skip_dirs]
        
        for name in filenames:
            full_path = os.path.join(dirpath, name)
            all_files.append({
                "path": full_path,
                "name": name,
                "name_lower": name.lower(),
                "dir": dirpath,
            })
    
    # Find potential copies
    potential_copies = []
    for f in all_files:
        name_lower = f["name_lower"]
        for pattern in copy_patterns:
            match = re.match(pattern, name_lower, re.IGNORECASE)
            if match:
                base_name = match.group(1).strip()
                potential_copies.append({
                    **f,
                    "base_name": base_name,
                    "is_copy": True,
                })
                break
    
    return potential_copies
