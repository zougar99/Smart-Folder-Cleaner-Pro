# -*- coding: utf-8 -*-
"""
Folder Info - Get detailed information about any folder.
Shows: path, size, structure, file types, everything!
"""
import os
from collections import defaultdict
from datetime import datetime


def get_folder_details(folder_path: str, progress_cb=None) -> dict:
    """
    Get complete details about a folder.
    """
    folder_path = os.path.abspath(folder_path)
    
    if not os.path.isdir(folder_path):
        return {"error": "Not a valid folder"}
    
    folder_name = os.path.basename(folder_path)
    parent_path = os.path.dirname(folder_path)
    
    # Get folder stats
    try:
        stat = os.stat(folder_path)
        created = datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M")
        modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
    except:
        created = "Unknown"
        modified = "Unknown"
    
    # Skip these
    skip_dirs = {"node_modules", ".git", "__pycache__", ".venv", "venv", 
                 "$RECYCLE.BIN", "System Volume Information"}
    
    # Scan folder
    total_files = 0
    total_size = 0
    total_subdirs = 0
    files_by_ext = defaultdict(lambda: {"count": 0, "size": 0})
    files_by_category = defaultdict(lambda: {"count": 0, "size": 0})
    top_level_items = []
    largest_files = []
    deepest_path = ""
    max_depth = 0
    
    # Category mapping
    ext_to_category = {
        ".py": "Python", ".pyw": "Python",
        ".js": "JavaScript", ".jsx": "JavaScript", ".ts": "TypeScript", ".tsx": "TypeScript",
        ".html": "Web", ".css": "Web", ".scss": "Web", ".sass": "Web",
        ".json": "Config/Data", ".xml": "Config/Data", ".yaml": "Config/Data", ".yml": "Config/Data",
        ".md": "Documentation", ".txt": "Text", ".rst": "Documentation",
        ".jpg": "Images", ".jpeg": "Images", ".png": "Images", ".gif": "Images", 
        ".webp": "Images", ".svg": "Images", ".ico": "Images", ".bmp": "Images",
        ".mp3": "Audio", ".wav": "Audio", ".flac": "Audio", ".m4a": "Audio", ".ogg": "Audio",
        ".mp4": "Video", ".avi": "Video", ".mkv": "Video", ".mov": "Video", ".webm": "Video",
        ".pdf": "PDF", ".doc": "Documents", ".docx": "Documents", 
        ".xls": "Spreadsheets", ".xlsx": "Spreadsheets",
        ".ppt": "Presentations", ".pptx": "Presentations",
        ".zip": "Archives", ".rar": "Archives", ".7z": "Archives", ".tar": "Archives", ".gz": "Archives",
        ".exe": "Executables", ".msi": "Executables", ".dll": "Libraries",
        ".c": "C/C++", ".cpp": "C/C++", ".h": "C/C++", ".hpp": "C/C++",
        ".java": "Java", ".jar": "Java",
        ".cs": "C#", ".go": "Go", ".rs": "Rust", ".rb": "Ruby", ".php": "PHP",
        ".sql": "Database", ".db": "Database", ".sqlite": "Database",
        ".sh": "Shell", ".bat": "Shell", ".cmd": "Shell", ".ps1": "Shell",
    }
    
    # Get top-level items first
    try:
        for item in os.listdir(folder_path):
            item_path = os.path.join(folder_path, item)
            if os.path.isdir(item_path):
                top_level_items.append({"name": item, "type": "folder", "icon": "📁"})
            else:
                _, ext = os.path.splitext(item)
                size = 0
                try:
                    size = os.path.getsize(item_path)
                except:
                    pass
                top_level_items.append({
                    "name": item, 
                    "type": "file", 
                    "icon": "📄",
                    "ext": ext,
                    "size": size
                })
    except PermissionError:
        return {"error": "Permission denied"}
    
    # Deep scan
    for dirpath, dirnames, filenames in os.walk(folder_path, topdown=True):
        # Skip unwanted dirs
        dirnames[:] = [d for d in dirnames if d not in skip_dirs]
        
        # Track depth
        rel_path = os.path.relpath(dirpath, folder_path)
        depth = rel_path.count(os.sep) + 1 if rel_path != "." else 0
        if depth > max_depth:
            max_depth = depth
            deepest_path = rel_path
        
        total_subdirs += len(dirnames)
        
        for name in filenames:
            try:
                full_path = os.path.join(dirpath, name)
                size = os.path.getsize(full_path)
                _, ext = os.path.splitext(name)
                ext = ext.lower()
                
                total_files += 1
                total_size += size
                
                files_by_ext[ext]["count"] += 1
                files_by_ext[ext]["size"] += size
                
                category = ext_to_category.get(ext, "Other")
                files_by_category[category]["count"] += 1
                files_by_category[category]["size"] += size
                
                # Track largest files
                largest_files.append({
                    "name": name,
                    "path": os.path.relpath(full_path, folder_path),
                    "size": size,
                })
                
                if progress_cb and total_files % 500 == 0:
                    progress_cb(f"Scanning: {total_files} files...")
                    
            except (OSError, PermissionError):
                continue
    
    # Sort largest files
    largest_files.sort(key=lambda x: x["size"], reverse=True)
    largest_files = largest_files[:20]
    
    # Sort extensions by count
    sorted_exts = sorted(files_by_ext.items(), key=lambda x: x[1]["count"], reverse=True)
    sorted_categories = sorted(files_by_category.items(), key=lambda x: x[1]["count"], reverse=True)
    
    return {
        "folder_name": folder_name,
        "folder_path": folder_path,
        "parent_path": parent_path,
        "created": created,
        "modified": modified,
        
        "total_files": total_files,
        "total_subdirs": total_subdirs,
        "total_size": total_size,
        "total_size_mb": total_size / (1024 * 1024),
        "total_size_gb": total_size / (1024 * 1024 * 1024),
        
        "max_depth": max_depth,
        "deepest_path": deepest_path,
        
        "top_level_items": top_level_items,
        "files_by_extension": dict(sorted_exts[:20]),
        "files_by_category": dict(sorted_categories),
        "largest_files": largest_files,
    }


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


def generate_folder_report(details: dict) -> str:
    """Generate a text report of folder details."""
    if "error" in details:
        return f"Error: {details['error']}"
    
    lines = []
    lines.append("=" * 60)
    lines.append("📁 FOLDER INFORMATION")
    lines.append("=" * 60)
    
    # Basic info
    lines.append(f"\n📌 Name: {details['folder_name']}")
    lines.append(f"📍 Full Path: {details['folder_path']}")
    lines.append(f"📂 Parent: {details['parent_path']}")
    lines.append(f"📅 Created: {details['created']}")
    lines.append(f"📅 Modified: {details['modified']}")
    
    # Size & counts
    lines.append(f"\n{'─' * 40}")
    lines.append("📊 STATISTICS")
    lines.append(f"{'─' * 40}")
    lines.append(f"📄 Total Files: {details['total_files']:,}")
    lines.append(f"📁 Total Subfolders: {details['total_subdirs']:,}")
    lines.append(f"💾 Total Size: {format_size(details['total_size'])}")
    lines.append(f"📏 Max Depth: {details['max_depth']} levels")
    if details['deepest_path'] and details['deepest_path'] != ".":
        lines.append(f"   Deepest: {details['deepest_path']}")
    
    # Structure preview
    lines.append(f"\n{'─' * 40}")
    lines.append("🗂️ FOLDER STRUCTURE (Top Level)")
    lines.append(f"{'─' * 40}")
    
    folders_first = sorted(details['top_level_items'], 
                          key=lambda x: (0 if x['type'] == 'folder' else 1, x['name'].lower()))
    
    for item in folders_first[:30]:
        if item['type'] == 'folder':
            lines.append(f"  📁 {item['name']}/")
        else:
            size_str = format_size(item.get('size', 0))
            lines.append(f"  📄 {item['name']} ({size_str})")
    
    if len(details['top_level_items']) > 30:
        lines.append(f"  ... +{len(details['top_level_items']) - 30} more items")
    
    # Files by category
    lines.append(f"\n{'─' * 40}")
    lines.append("📂 FILES BY CATEGORY")
    lines.append(f"{'─' * 40}")
    
    for category, data in details.get('files_by_category', {}).items():
        count = data['count']
        size = format_size(data['size'])
        bar_len = min(20, int(count / max(1, details['total_files']) * 40))
        bar = "█" * bar_len
        lines.append(f"  {category:15} {count:5,} files  {size:>10}  {bar}")
    
    # Files by extension
    lines.append(f"\n{'─' * 40}")
    lines.append("📋 TOP EXTENSIONS")
    lines.append(f"{'─' * 40}")
    
    for ext, data in list(details.get('files_by_extension', {}).items())[:15]:
        ext_name = ext if ext else "(no extension)"
        count = data['count']
        size = format_size(data['size'])
        lines.append(f"  {ext_name:10} {count:5,} files  {size:>10}")
    
    # Largest files
    if details.get('largest_files'):
        lines.append(f"\n{'─' * 40}")
        lines.append("📦 LARGEST FILES")
        lines.append(f"{'─' * 40}")
        
        for f in details['largest_files'][:10]:
            size = format_size(f['size'])
            lines.append(f"  {size:>10}  {f['path']}")
    
    lines.append("\n" + "=" * 60)
    
    return "\n".join(lines)
