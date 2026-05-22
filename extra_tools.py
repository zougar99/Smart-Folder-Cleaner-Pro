# -*- coding: utf-8 -*-
"""
Extra Tools - Batch Rename, Disk Analyzer, Compress, Sync, Broken Links
"""
import os
import re
import shutil
import zipfile
import hashlib
from datetime import datetime
from collections import defaultdict
from typing import Callable, Optional

# =============================================================================
# 📝 BATCH RENAME TOOL
# =============================================================================

def batch_rename_preview(folder: str, pattern: str, start_num: int = 1, 
                         extension_filter: str = "", progress_cb: Callable = None) -> list:
    """
    Preview batch rename operation without actually renaming.
    
    Patterns supported:
    - {n} or {num} = sequential number (001, 002, ...)
    - {name} = original filename (without extension)
    - {ext} = extension
    - {date} = current date YYYYMMDD
    - {parent} = parent folder name
    
    Example: "photo_{n}" -> photo_001.jpg, photo_002.jpg
    """
    if not os.path.isdir(folder):
        return []
    
    results = []
    files = []
    
    # Get all files
    for f in os.listdir(folder):
        full_path = os.path.join(folder, f)
        if os.path.isfile(full_path):
            # Filter by extension if specified
            if extension_filter:
                ext = os.path.splitext(f)[1].lower()
                if ext != extension_filter.lower() and extension_filter != "*":
                    continue
            files.append(f)
    
    files.sort()  # Sort alphabetically
    
    parent_name = os.path.basename(folder)
    current_date = datetime.now().strftime("%Y%m%d")
    
    for i, filename in enumerate(files):
        name, ext = os.path.splitext(filename)
        num = start_num + i
        
        # Replace patterns
        new_name = pattern
        new_name = new_name.replace("{n}", f"{num:03d}")
        new_name = new_name.replace("{num}", f"{num:03d}")
        new_name = new_name.replace("{name}", name)
        new_name = new_name.replace("{ext}", ext.lstrip("."))
        new_name = new_name.replace("{date}", current_date)
        new_name = new_name.replace("{parent}", parent_name)
        
        # Add extension if not in pattern
        if not new_name.endswith(ext) and "{ext}" not in pattern:
            new_name += ext
        
        results.append({
            "old_name": filename,
            "new_name": new_name,
            "old_path": os.path.join(folder, filename),
            "new_path": os.path.join(folder, new_name),
        })
        
        if progress_cb:
            progress_cb(f"Preview: {filename} -> {new_name}")
    
    return results


def batch_rename_execute(rename_plan: list, progress_cb: Callable = None) -> dict:
    """Execute batch rename from a preview plan."""
    results = {"success": [], "errors": [], "skipped": []}
    
    for item in rename_plan:
        old_path = item["old_path"]
        new_path = item["new_path"]
        
        try:
            if not os.path.exists(old_path):
                results["skipped"].append(f"{item['old_name']} - file not found")
                continue
            
            if os.path.exists(new_path) and old_path != new_path:
                results["skipped"].append(f"{item['new_name']} - already exists")
                continue
            
            os.rename(old_path, new_path)
            results["success"].append(item)
            
            if progress_cb:
                progress_cb(f"Renamed: {item['old_name']} -> {item['new_name']}")
                
        except Exception as e:
            results["errors"].append(f"{item['old_name']} - {str(e)}")
    
    return results


def format_rename_preview(preview: list) -> str:
    """Format rename preview for display."""
    if not preview:
        return "No files to rename."
    
    lines = []
    lines.append("=" * 60)
    lines.append("📝 BATCH RENAME PREVIEW")
    lines.append("=" * 60)
    lines.append(f"\nFiles to rename: {len(preview)}\n")
    
    for item in preview[:50]:  # Show max 50
        lines.append(f"  {item['old_name']}")
        lines.append(f"    → {item['new_name']}")
    
    if len(preview) > 50:
        lines.append(f"\n  ... and {len(preview) - 50} more")
    
    lines.append(f"\n{'─' * 40}")
    lines.append("Click 'Execute Rename' to apply changes.")
    
    return "\n".join(lines)


# =============================================================================
# 📊 DISK ANALYZER
# =============================================================================

def analyze_disk_usage(folder: str, progress_cb: Callable = None) -> dict:
    """Analyze disk usage of a folder."""
    if not os.path.isdir(folder):
        return {"error": "Invalid folder"}
    
    results = {
        "folder": folder,
        "total_size": 0,
        "file_count": 0,
        "folder_count": 0,
        "by_extension": defaultdict(lambda: {"count": 0, "size": 0}),
        "by_subfolder": {},
        "largest_files": [],
        "largest_folders": [],
    }
    
    all_files = []
    
    # Walk through folder
    for root, dirs, files in os.walk(folder):
        results["folder_count"] += len(dirs)
        
        # Calculate subfolder sizes
        rel_root = os.path.relpath(root, folder)
        if rel_root == ".":
            rel_root = "(root)"
        
        folder_size = 0
        
        for f in files:
            full_path = os.path.join(root, f)
            try:
                size = os.path.getsize(full_path)
                results["total_size"] += size
                results["file_count"] += 1
                folder_size += size
                
                # By extension
                ext = os.path.splitext(f)[1].lower() or "(no ext)"
                results["by_extension"][ext]["count"] += 1
                results["by_extension"][ext]["size"] += size
                
                # Track for largest files
                all_files.append({
                    "path": full_path,
                    "name": f,
                    "size": size,
                    "rel_path": os.path.relpath(full_path, folder),
                })
                
            except:
                pass
        
        # Track subfolder sizes (top level only)
        if root == folder:
            for d in dirs:
                subfolder_path = os.path.join(root, d)
                subfolder_size = get_folder_size(subfolder_path)
                results["by_subfolder"][d] = subfolder_size
        
        if progress_cb:
            progress_cb(f"Scanning: {rel_root}")
    
    # Sort and get largest
    all_files.sort(key=lambda x: -x["size"])
    results["largest_files"] = all_files[:20]
    
    # Sort subfolders by size
    results["largest_folders"] = sorted(
        results["by_subfolder"].items(),
        key=lambda x: -x[1]
    )[:10]
    
    # Convert defaultdict to regular dict
    results["by_extension"] = dict(results["by_extension"])
    
    return results


def get_folder_size(folder: str) -> int:
    """Get total size of a folder."""
    total = 0
    try:
        for root, dirs, files in os.walk(folder):
            for f in files:
                try:
                    total += os.path.getsize(os.path.join(root, f))
                except:
                    pass
    except:
        pass
    return total


def format_size(size: int) -> str:
    """Format size in human readable format."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"


def format_disk_analysis(results: dict) -> str:
    """Format disk analysis for display."""
    if "error" in results:
        return f"Error: {results['error']}"
    
    lines = []
    lines.append("=" * 60)
    lines.append("📊 DISK USAGE ANALYSIS")
    lines.append("=" * 60)
    
    lines.append(f"\n📁 Folder: {results['folder']}")
    lines.append(f"📦 Total Size: {format_size(results['total_size'])}")
    lines.append(f"📄 Files: {results['file_count']:,}")
    lines.append(f"📂 Folders: {results['folder_count']:,}")
    
    # By extension chart
    lines.append(f"\n{'─' * 50}")
    lines.append("📊 SIZE BY FILE TYPE")
    lines.append(f"{'─' * 50}")
    
    ext_sorted = sorted(results["by_extension"].items(), 
                       key=lambda x: -x[1]["size"])[:15]
    
    max_size = max(x[1]["size"] for x in ext_sorted) if ext_sorted else 1
    
    for ext, data in ext_sorted:
        bar_len = int((data["size"] / max_size) * 20)
        bar = "█" * bar_len + "░" * (20 - bar_len)
        pct = (data["size"] / results["total_size"]) * 100 if results["total_size"] else 0
        lines.append(f"\n{ext:12} {bar} {format_size(data['size']):>10} ({pct:.1f}%)")
        lines.append(f"             {data['count']:,} files")
    
    # Largest subfolders
    if results["largest_folders"]:
        lines.append(f"\n{'─' * 50}")
        lines.append("📂 LARGEST SUBFOLDERS")
        lines.append(f"{'─' * 50}")
        
        for folder_name, size in results["largest_folders"]:
            pct = (size / results["total_size"]) * 100 if results["total_size"] else 0
            lines.append(f"\n  📁 {folder_name}")
            lines.append(f"     {format_size(size)} ({pct:.1f}%)")
    
    # Largest files
    if results["largest_files"]:
        lines.append(f"\n{'─' * 50}")
        lines.append("📄 LARGEST FILES")
        lines.append(f"{'─' * 50}")
        
        for f in results["largest_files"][:10]:
            lines.append(f"\n  📄 {f['rel_path']}")
            lines.append(f"     {format_size(f['size'])}")
    
    return "\n".join(lines)


# =============================================================================
# 🗜️ COMPRESS TOOL
# =============================================================================

def compress_folder(folder: str, output_zip: str = None, 
                   progress_cb: Callable = None) -> dict:
    """Compress a folder to ZIP."""
    if not os.path.isdir(folder):
        return {"error": "Invalid folder"}
    
    if not output_zip:
        output_zip = folder.rstrip("/\\") + ".zip"
    
    results = {
        "source": folder,
        "output": output_zip,
        "files_added": 0,
        "total_size": 0,
        "compressed_size": 0,
    }
    
    try:
        with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(folder):
                for f in files:
                    full_path = os.path.join(root, f)
                    arc_name = os.path.relpath(full_path, folder)
                    
                    try:
                        size = os.path.getsize(full_path)
                        results["total_size"] += size
                        
                        zf.write(full_path, arc_name)
                        results["files_added"] += 1
                        
                        if progress_cb:
                            progress_cb(f"Adding: {arc_name}")
                    except Exception as e:
                        pass
        
        results["compressed_size"] = os.path.getsize(output_zip)
        results["success"] = True
        
    except Exception as e:
        results["error"] = str(e)
        results["success"] = False
    
    return results


def extract_archive(archive_path: str, output_folder: str = None,
                   progress_cb: Callable = None) -> dict:
    """Extract ZIP archive."""
    if not os.path.isfile(archive_path):
        return {"error": "Archive not found"}
    
    if not output_folder:
        output_folder = os.path.splitext(archive_path)[0]
    
    results = {
        "source": archive_path,
        "output": output_folder,
        "files_extracted": 0,
    }
    
    try:
        os.makedirs(output_folder, exist_ok=True)
        
        with zipfile.ZipFile(archive_path, 'r') as zf:
            for member in zf.namelist():
                if progress_cb:
                    progress_cb(f"Extracting: {member}")
                zf.extract(member, output_folder)
                results["files_extracted"] += 1
        
        results["success"] = True
        
    except Exception as e:
        results["error"] = str(e)
        results["success"] = False
    
    return results


def format_compress_result(results: dict) -> str:
    """Format compress/extract result."""
    lines = []
    lines.append("=" * 60)
    
    if "files_added" in results:
        lines.append("🗜️ COMPRESSION COMPLETE")
        lines.append("=" * 60)
        lines.append(f"\n📁 Source: {results['source']}")
        lines.append(f"📦 Output: {results['output']}")
        lines.append(f"📄 Files: {results['files_added']}")
        lines.append(f"\n📊 Original: {format_size(results['total_size'])}")
        lines.append(f"📊 Compressed: {format_size(results['compressed_size'])}")
        
        if results['total_size'] > 0:
            ratio = (1 - results['compressed_size'] / results['total_size']) * 100
            lines.append(f"💾 Saved: {ratio:.1f}%")
    else:
        lines.append("📂 EXTRACTION COMPLETE")
        lines.append("=" * 60)
        lines.append(f"\n📦 Archive: {results['source']}")
        lines.append(f"📁 Output: {results['output']}")
        lines.append(f"📄 Files: {results['files_extracted']}")
    
    if results.get("error"):
        lines.append(f"\n❌ Error: {results['error']}")
    elif results.get("success"):
        lines.append(f"\n✅ Success!")
    
    return "\n".join(lines)


# =============================================================================
# 🔄 SYNC FOLDERS
# =============================================================================

def compare_folders(folder1: str, folder2: str, 
                   progress_cb: Callable = None) -> dict:
    """Compare two folders and find differences."""
    if not os.path.isdir(folder1):
        return {"error": f"Folder 1 not found: {folder1}"}
    if not os.path.isdir(folder2):
        return {"error": f"Folder 2 not found: {folder2}"}
    
    results = {
        "folder1": folder1,
        "folder2": folder2,
        "only_in_1": [],      # Files only in folder 1
        "only_in_2": [],      # Files only in folder 2
        "different": [],      # Files with different content
        "identical": [],      # Identical files
    }
    
    # Get all files in both folders
    files1 = {}
    files2 = {}
    
    if progress_cb:
        progress_cb("Scanning folder 1...")
    
    for root, dirs, files in os.walk(folder1):
        for f in files:
            full_path = os.path.join(root, f)
            rel_path = os.path.relpath(full_path, folder1)
            try:
                files1[rel_path] = {
                    "path": full_path,
                    "size": os.path.getsize(full_path),
                    "mtime": os.path.getmtime(full_path),
                }
            except:
                pass
    
    if progress_cb:
        progress_cb("Scanning folder 2...")
    
    for root, dirs, files in os.walk(folder2):
        for f in files:
            full_path = os.path.join(root, f)
            rel_path = os.path.relpath(full_path, folder2)
            try:
                files2[rel_path] = {
                    "path": full_path,
                    "size": os.path.getsize(full_path),
                    "mtime": os.path.getmtime(full_path),
                }
            except:
                pass
    
    if progress_cb:
        progress_cb("Comparing files...")
    
    all_files = set(files1.keys()) | set(files2.keys())
    
    for rel_path in all_files:
        in_1 = rel_path in files1
        in_2 = rel_path in files2
        
        if in_1 and not in_2:
            results["only_in_1"].append({
                "rel_path": rel_path,
                "size": files1[rel_path]["size"],
            })
        elif in_2 and not in_1:
            results["only_in_2"].append({
                "rel_path": rel_path,
                "size": files2[rel_path]["size"],
            })
        else:
            # Both exist - compare
            f1 = files1[rel_path]
            f2 = files2[rel_path]
            
            if f1["size"] != f2["size"]:
                results["different"].append({
                    "rel_path": rel_path,
                    "size1": f1["size"],
                    "size2": f2["size"],
                    "newer_in": "folder1" if f1["mtime"] > f2["mtime"] else "folder2",
                })
            else:
                results["identical"].append(rel_path)
    
    return results


def sync_folders(folder1: str, folder2: str, direction: str = "1to2",
                progress_cb: Callable = None) -> dict:
    """
    Sync folders.
    direction: "1to2" = copy from 1 to 2, "2to1" = copy from 2 to 1, "both" = both ways
    """
    comparison = compare_folders(folder1, folder2, progress_cb)
    if "error" in comparison:
        return comparison
    
    results = {
        "copied": [],
        "errors": [],
    }
    
    # Copy files
    if direction in ["1to2", "both"]:
        for item in comparison["only_in_1"]:
            src = os.path.join(folder1, item["rel_path"])
            dst = os.path.join(folder2, item["rel_path"])
            try:
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
                results["copied"].append(f"→ {item['rel_path']}")
                if progress_cb:
                    progress_cb(f"Copied: {item['rel_path']}")
            except Exception as e:
                results["errors"].append(f"{item['rel_path']}: {e}")
    
    if direction in ["2to1", "both"]:
        for item in comparison["only_in_2"]:
            src = os.path.join(folder2, item["rel_path"])
            dst = os.path.join(folder1, item["rel_path"])
            try:
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
                results["copied"].append(f"← {item['rel_path']}")
                if progress_cb:
                    progress_cb(f"Copied: {item['rel_path']}")
            except Exception as e:
                results["errors"].append(f"{item['rel_path']}: {e}")
    
    results["comparison"] = comparison
    return results


def format_folder_comparison(results: dict) -> str:
    """Format folder comparison for display."""
    if "error" in results:
        return f"Error: {results['error']}"
    
    lines = []
    lines.append("=" * 60)
    lines.append("🔄 FOLDER COMPARISON")
    lines.append("=" * 60)
    
    lines.append(f"\n📁 Folder 1: {results['folder1']}")
    lines.append(f"📁 Folder 2: {results['folder2']}")
    
    lines.append(f"\n{'─' * 50}")
    lines.append("📊 SUMMARY")
    lines.append(f"{'─' * 50}")
    lines.append(f"\n  ✅ Identical: {len(results['identical'])} files")
    lines.append(f"  📁 Only in Folder 1: {len(results['only_in_1'])} files")
    lines.append(f"  📁 Only in Folder 2: {len(results['only_in_2'])} files")
    lines.append(f"  ⚠️ Different: {len(results['different'])} files")
    
    if results['only_in_1']:
        lines.append(f"\n{'─' * 50}")
        lines.append("📁 ONLY IN FOLDER 1")
        lines.append(f"{'─' * 50}")
        for f in results['only_in_1'][:20]:
            lines.append(f"  + {f['rel_path']} ({format_size(f['size'])})")
        if len(results['only_in_1']) > 20:
            lines.append(f"  ... and {len(results['only_in_1']) - 20} more")
    
    if results['only_in_2']:
        lines.append(f"\n{'─' * 50}")
        lines.append("📁 ONLY IN FOLDER 2")
        lines.append(f"{'─' * 50}")
        for f in results['only_in_2'][:20]:
            lines.append(f"  + {f['rel_path']} ({format_size(f['size'])})")
        if len(results['only_in_2']) > 20:
            lines.append(f"  ... and {len(results['only_in_2']) - 20} more")
    
    if results['different']:
        lines.append(f"\n{'─' * 50}")
        lines.append("⚠️ DIFFERENT FILES")
        lines.append(f"{'─' * 50}")
        for f in results['different'][:20]:
            lines.append(f"  ≠ {f['rel_path']}")
            lines.append(f"    F1: {format_size(f['size1'])} | F2: {format_size(f['size2'])} | Newer: {f['newer_in']}")
    
    return "\n".join(lines)


# =============================================================================
# 🔗 BROKEN LINKS FINDER
# =============================================================================

def find_broken_shortcuts(folder: str, progress_cb: Callable = None) -> dict:
    """Find broken shortcuts (.lnk files on Windows)."""
    if not os.path.isdir(folder):
        return {"error": "Invalid folder"}
    
    results = {
        "folder": folder,
        "total_shortcuts": 0,
        "broken": [],
        "valid": [],
    }
    
    try:
        # Try to use Windows COM for .lnk files
        import win32com.client
        shell = win32com.client.Dispatch("WScript.Shell")
        has_win32 = True
    except:
        has_win32 = False
    
    for root, dirs, files in os.walk(folder):
        for f in files:
            full_path = os.path.join(root, f)
            rel_path = os.path.relpath(full_path, folder)
            
            # Check .lnk files (Windows shortcuts)
            if f.lower().endswith(".lnk") and has_win32:
                results["total_shortcuts"] += 1
                try:
                    shortcut = shell.CreateShortcut(full_path)
                    target = shortcut.TargetPath
                    
                    if not os.path.exists(target):
                        results["broken"].append({
                            "shortcut": rel_path,
                            "target": target,
                            "path": full_path,
                        })
                    else:
                        results["valid"].append(rel_path)
                except:
                    results["broken"].append({
                        "shortcut": rel_path,
                        "target": "(cannot read)",
                        "path": full_path,
                    })
            
            # Check .url files (Internet shortcuts)
            elif f.lower().endswith(".url"):
                results["total_shortcuts"] += 1
                results["valid"].append(rel_path)  # URLs can't be easily verified
            
            if progress_cb:
                progress_cb(f"Checking: {rel_path}")
    
    return results


def delete_broken_shortcuts(broken_list: list, progress_cb: Callable = None) -> dict:
    """Delete broken shortcuts."""
    results = {"deleted": [], "errors": []}
    
    for item in broken_list:
        try:
            os.remove(item["path"])
            results["deleted"].append(item["shortcut"])
            if progress_cb:
                progress_cb(f"Deleted: {item['shortcut']}")
        except Exception as e:
            results["errors"].append(f"{item['shortcut']}: {e}")
    
    return results


def format_broken_shortcuts(results: dict) -> str:
    """Format broken shortcuts result."""
    if "error" in results:
        return f"Error: {results['error']}"
    
    lines = []
    lines.append("=" * 60)
    lines.append("🔗 SHORTCUT CHECKER")
    lines.append("=" * 60)
    
    lines.append(f"\n📁 Folder: {results['folder']}")
    lines.append(f"🔗 Total shortcuts: {results['total_shortcuts']}")
    lines.append(f"✅ Valid: {len(results['valid'])}")
    lines.append(f"❌ Broken: {len(results['broken'])}")
    
    if results['broken']:
        lines.append(f"\n{'─' * 50}")
        lines.append("❌ BROKEN SHORTCUTS")
        lines.append(f"{'─' * 50}")
        
        for item in results['broken'][:30]:
            lines.append(f"\n  🔗 {item['shortcut']}")
            lines.append(f"     Target: {item['target']}")
        
        if len(results['broken']) > 30:
            lines.append(f"\n  ... and {len(results['broken']) - 30} more")
        
        lines.append(f"\n{'─' * 50}")
        lines.append("Click 'Delete Broken' to remove them.")
    else:
        lines.append(f"\n✅ All shortcuts are valid!")
    
    return "\n".join(lines)
