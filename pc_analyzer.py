# -*- coding: utf-8 -*-
"""
PC Analyzer - Full system health check and problem detection.
"""
import os
import shutil
import platform
import subprocess
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Callable, Dict, List, Optional
import ctypes
import sys

# =============================================================================
# 💻 SYSTEM INFO
# =============================================================================

def get_system_info() -> Dict:
    """Get basic system information."""
    info = {
        "os": platform.system(),
        "os_version": platform.version(),
        "os_release": platform.release(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
        "computer_name": platform.node(),
    }
    
    # Get username
    try:
        info["username"] = os.getlogin()
    except:
        info["username"] = os.environ.get("USERNAME", "Unknown")
    
    return info


def get_disk_info() -> List[Dict]:
    """Get information about all disk drives."""
    disks = []
    
    if platform.system() == "Windows":
        # Get all drive letters
        import string
        drives = [f"{d}:\\" for d in string.ascii_uppercase if os.path.exists(f"{d}:\\")]
        
        for drive in drives:
            try:
                total, used, free = shutil.disk_usage(drive)
                usage_percent = (used / total) * 100 if total > 0 else 0
                
                disks.append({
                    "drive": drive,
                    "total": total,
                    "used": used,
                    "free": free,
                    "usage_percent": usage_percent,
                    "status": "critical" if usage_percent > 90 else "warning" if usage_percent > 75 else "ok",
                })
            except:
                pass
    else:
        # Unix-like systems
        try:
            total, used, free = shutil.disk_usage("/")
            usage_percent = (used / total) * 100 if total > 0 else 0
            disks.append({
                "drive": "/",
                "total": total,
                "used": used,
                "free": free,
                "usage_percent": usage_percent,
                "status": "critical" if usage_percent > 90 else "warning" if usage_percent > 75 else "ok",
            })
        except:
            pass
    
    return disks


# =============================================================================
# 🔍 PROBLEM DETECTION
# =============================================================================

def find_temp_files(progress_cb: Callable = None) -> Dict:
    """Find temporary files that can be safely deleted."""
    temp_locations = []
    
    if platform.system() == "Windows":
        # Common temp locations
        temp_locations = [
            os.environ.get("TEMP", ""),
            os.environ.get("TMP", ""),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Temp"),
            os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Temp"),
            os.path.join(os.environ.get("USERPROFILE", ""), "AppData", "Local", "Temp"),
        ]
        
        # Browser caches
        user_profile = os.environ.get("USERPROFILE", "")
        browser_caches = [
            os.path.join(user_profile, "AppData", "Local", "Google", "Chrome", "User Data", "Default", "Cache"),
            os.path.join(user_profile, "AppData", "Local", "Microsoft", "Edge", "User Data", "Default", "Cache"),
            os.path.join(user_profile, "AppData", "Local", "Mozilla", "Firefox", "Profiles"),
        ]
        temp_locations.extend(browser_caches)
    
    results = {
        "locations": [],
        "total_size": 0,
        "total_files": 0,
    }
    
    for loc in temp_locations:
        if not loc or not os.path.isdir(loc):
            continue
        
        if progress_cb:
            progress_cb(f"Scanning: {loc[:50]}...")
        
        loc_size = 0
        loc_files = 0
        
        try:
            for root, dirs, files in os.walk(loc):
                for f in files:
                    try:
                        fp = os.path.join(root, f)
                        size = os.path.getsize(fp)
                        loc_size += size
                        loc_files += 1
                    except:
                        pass
        except:
            pass
        
        if loc_size > 0:
            results["locations"].append({
                "path": loc,
                "size": loc_size,
                "files": loc_files,
            })
            results["total_size"] += loc_size
            results["total_files"] += loc_files
    
    return results


def find_large_folders(min_size_gb: float = 1.0, progress_cb: Callable = None) -> List[Dict]:
    """Find unusually large folders."""
    large_folders = []
    min_size = min_size_gb * 1024 * 1024 * 1024
    
    # Common locations to check
    check_paths = []
    
    if platform.system() == "Windows":
        user_profile = os.environ.get("USERPROFILE", "")
        check_paths = [
            os.path.join(user_profile, "Downloads"),
            os.path.join(user_profile, "Desktop"),
            os.path.join(user_profile, "Documents"),
            os.path.join(user_profile, "Videos"),
            os.path.join(user_profile, "Pictures"),
            os.path.join(user_profile, "AppData", "Local"),
            os.path.join(user_profile, "AppData", "Roaming"),
        ]
    
    for path in check_paths:
        if not os.path.isdir(path):
            continue
        
        if progress_cb:
            progress_cb(f"Checking: {os.path.basename(path)}...")
        
        try:
            # Get immediate subfolders and their sizes
            for item in os.listdir(path):
                item_path = os.path.join(path, item)
                if os.path.isdir(item_path):
                    try:
                        size = get_folder_size_fast(item_path)
                        if size >= min_size:
                            large_folders.append({
                                "path": item_path,
                                "name": item,
                                "size": size,
                                "parent": os.path.basename(path),
                            })
                    except:
                        pass
        except:
            pass
    
    # Sort by size
    large_folders.sort(key=lambda x: -x["size"])
    return large_folders[:20]


def get_folder_size_fast(folder: str, max_depth: int = 3) -> int:
    """Get folder size with depth limit for speed."""
    total = 0
    current_depth = 0
    
    try:
        for root, dirs, files in os.walk(folder):
            # Limit depth
            depth = root.replace(folder, '').count(os.sep)
            if depth >= max_depth:
                dirs[:] = []  # Don't go deeper
                continue
            
            for f in files:
                try:
                    total += os.path.getsize(os.path.join(root, f))
                except:
                    pass
    except:
        pass
    
    return total


def find_old_downloads(days: int = 90, progress_cb: Callable = None) -> Dict:
    """Find old files in Downloads folder."""
    results = {
        "files": [],
        "total_size": 0,
        "count": 0,
    }
    
    downloads_path = os.path.join(os.environ.get("USERPROFILE", ""), "Downloads")
    
    if not os.path.isdir(downloads_path):
        return results
    
    if progress_cb:
        progress_cb("Scanning Downloads folder...")
    
    cutoff = datetime.now() - timedelta(days=days)
    
    try:
        for f in os.listdir(downloads_path):
            fp = os.path.join(downloads_path, f)
            try:
                if os.path.isfile(fp):
                    mtime = datetime.fromtimestamp(os.path.getmtime(fp))
                    if mtime < cutoff:
                        size = os.path.getsize(fp)
                        results["files"].append({
                            "name": f,
                            "path": fp,
                            "size": size,
                            "age_days": (datetime.now() - mtime).days,
                        })
                        results["total_size"] += size
                        results["count"] += 1
            except:
                pass
    except:
        pass
    
    # Sort by size
    results["files"].sort(key=lambda x: -x["size"])
    return results


def find_duplicate_downloads(progress_cb: Callable = None) -> List[Dict]:
    """Find files with similar names in Downloads (likely duplicates)."""
    downloads_path = os.path.join(os.environ.get("USERPROFILE", ""), "Downloads")
    
    if not os.path.isdir(downloads_path):
        return []
    
    if progress_cb:
        progress_cb("Checking for duplicate downloads...")
    
    # Group by base name
    files_by_base = defaultdict(list)
    
    import re
    
    for f in os.listdir(downloads_path):
        fp = os.path.join(downloads_path, f)
        if not os.path.isfile(fp):
            continue
        
        # Remove common duplicate patterns
        base = f
        base = re.sub(r'\s*\(\d+\)\s*', '', base)  # file (1).txt
        base = re.sub(r'\s*-\s*Copy\s*', '', base, flags=re.IGNORECASE)  # file - Copy.txt
        base = re.sub(r'_\d{10,}', '', base)  # file_1234567890.txt (timestamps)
        
        try:
            size = os.path.getsize(fp)
            files_by_base[base].append({
                "name": f,
                "path": fp,
                "size": size,
            })
        except:
            pass
    
    # Find groups with duplicates
    duplicates = []
    for base, files in files_by_base.items():
        if len(files) > 1:
            total_size = sum(f["size"] for f in files)
            duplicates.append({
                "base_name": base,
                "files": files,
                "count": len(files),
                "total_size": total_size,
            })
    
    duplicates.sort(key=lambda x: -x["total_size"])
    return duplicates


def check_startup_programs(progress_cb: Callable = None) -> List[Dict]:
    """Check startup programs (Windows only)."""
    startups = []
    
    if platform.system() != "Windows":
        return startups
    
    if progress_cb:
        progress_cb("Checking startup programs...")
    
    # Startup folders
    startup_locations = [
        os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows", "Start Menu", "Programs", "Startup"),
        os.path.join(os.environ.get("PROGRAMDATA", ""), "Microsoft", "Windows", "Start Menu", "Programs", "Startup"),
    ]
    
    for loc in startup_locations:
        if os.path.isdir(loc):
            for f in os.listdir(loc):
                fp = os.path.join(loc, f)
                startups.append({
                    "name": f,
                    "path": fp,
                    "location": "Startup Folder",
                })
    
    return startups


def check_recycle_bin(progress_cb: Callable = None) -> Dict:
    """Check Recycle Bin size."""
    result = {
        "size": 0,
        "count": 0,
        "status": "ok",
    }
    
    if platform.system() != "Windows":
        return result
    
    if progress_cb:
        progress_cb("Checking Recycle Bin...")
    
    try:
        # Check $RECYCLE.BIN on each drive
        import string
        drives = [f"{d}:\\" for d in string.ascii_uppercase if os.path.exists(f"{d}:\\")]
        
        for drive in drives:
            recycle_path = os.path.join(drive, "$RECYCLE.BIN")
            if os.path.isdir(recycle_path):
                try:
                    for root, dirs, files in os.walk(recycle_path):
                        for f in files:
                            try:
                                result["size"] += os.path.getsize(os.path.join(root, f))
                                result["count"] += 1
                            except:
                                pass
                except:
                    pass
    except:
        pass
    
    if result["size"] > 1024 * 1024 * 1024:  # > 1GB
        result["status"] = "warning"
    if result["size"] > 5 * 1024 * 1024 * 1024:  # > 5GB
        result["status"] = "critical"
    
    return result


# =============================================================================
# 📊 FULL PC ANALYSIS
# =============================================================================

def run_full_pc_analysis(progress_cb: Callable = None) -> Dict:
    """Run complete PC analysis and find all problems."""
    results = {
        "system_info": {},
        "disk_info": [],
        "problems": [],
        "warnings": [],
        "recommendations": [],
        "stats": {
            "total_cleanable": 0,
            "problem_count": 0,
            "warning_count": 0,
        },
    }
    
    # 1. System Info
    if progress_cb:
        progress_cb("Getting system information...")
    results["system_info"] = get_system_info()
    
    # 2. Disk Info
    if progress_cb:
        progress_cb("Checking disk space...")
    results["disk_info"] = get_disk_info()
    
    # Check for disk problems
    for disk in results["disk_info"]:
        if disk["status"] == "critical":
            results["problems"].append({
                "type": "disk_critical",
                "severity": "critical",
                "icon": "🔴",
                "title": f"Disk {disk['drive']} Almost Full!",
                "description": f"Only {format_size(disk['free'])} free ({100 - disk['usage_percent']:.1f}%)",
                "recommendation": "Delete unnecessary files or move to external storage",
            })
            results["stats"]["problem_count"] += 1
        elif disk["status"] == "warning":
            results["warnings"].append({
                "type": "disk_warning",
                "severity": "warning",
                "icon": "🟡",
                "title": f"Disk {disk['drive']} Getting Full",
                "description": f"{format_size(disk['free'])} free ({100 - disk['usage_percent']:.1f}%)",
                "recommendation": "Consider cleaning up soon",
            })
            results["stats"]["warning_count"] += 1
    
    # 3. Temp Files
    if progress_cb:
        progress_cb("Scanning temporary files...")
    temp_result = find_temp_files(progress_cb)
    
    if temp_result["total_size"] > 500 * 1024 * 1024:  # > 500MB
        severity = "critical" if temp_result["total_size"] > 2 * 1024 * 1024 * 1024 else "warning"
        results["problems" if severity == "critical" else "warnings"].append({
            "type": "temp_files",
            "severity": severity,
            "icon": "🗑️",
            "title": "Temporary Files",
            "description": f"{format_size(temp_result['total_size'])} in {temp_result['total_files']} temp files",
            "recommendation": "Run Disk Cleanup or delete temp files",
            "cleanable_size": temp_result["total_size"],
        })
        results["stats"]["total_cleanable"] += temp_result["total_size"]
        results["stats"]["problem_count" if severity == "critical" else "warning_count"] += 1
    
    results["temp_files"] = temp_result
    
    # 4. Large Folders
    if progress_cb:
        progress_cb("Finding large folders...")
    large_folders = find_large_folders(1.0, progress_cb)
    
    if large_folders:
        results["warnings"].append({
            "type": "large_folders",
            "severity": "info",
            "icon": "📁",
            "title": "Large Folders Found",
            "description": f"{len(large_folders)} folders over 1GB",
            "recommendation": "Review if all files are needed",
            "details": large_folders[:5],
        })
    
    results["large_folders"] = large_folders
    
    # 5. Old Downloads
    if progress_cb:
        progress_cb("Checking old downloads...")
    old_downloads = find_old_downloads(90, progress_cb)
    
    if old_downloads["count"] > 10 or old_downloads["total_size"] > 500 * 1024 * 1024:
        results["warnings"].append({
            "type": "old_downloads",
            "severity": "warning",
            "icon": "📥",
            "title": "Old Downloads",
            "description": f"{old_downloads['count']} files older than 90 days ({format_size(old_downloads['total_size'])})",
            "recommendation": "Review and delete old downloads",
            "cleanable_size": old_downloads["total_size"],
        })
        results["stats"]["total_cleanable"] += old_downloads["total_size"]
        results["stats"]["warning_count"] += 1
    
    results["old_downloads"] = old_downloads
    
    # 6. Duplicate Downloads
    if progress_cb:
        progress_cb("Finding duplicate downloads...")
    dup_downloads = find_duplicate_downloads(progress_cb)
    
    if dup_downloads:
        total_dup_size = sum(d["total_size"] for d in dup_downloads)
        results["warnings"].append({
            "type": "duplicate_downloads",
            "severity": "info",
            "icon": "📋",
            "title": "Possible Duplicate Downloads",
            "description": f"{len(dup_downloads)} groups of similar files",
            "recommendation": "Check for duplicate downloads",
        })
    
    results["duplicate_downloads"] = dup_downloads
    
    # 7. Recycle Bin
    if progress_cb:
        progress_cb("Checking Recycle Bin...")
    recycle = check_recycle_bin(progress_cb)
    
    if recycle["status"] != "ok":
        severity = recycle["status"]
        results["problems" if severity == "critical" else "warnings"].append({
            "type": "recycle_bin",
            "severity": severity,
            "icon": "🗑️",
            "title": "Recycle Bin",
            "description": f"{format_size(recycle['size'])} in {recycle['count']} deleted files",
            "recommendation": "Empty Recycle Bin",
            "cleanable_size": recycle["size"],
        })
        results["stats"]["total_cleanable"] += recycle["size"]
        results["stats"]["problem_count" if severity == "critical" else "warning_count"] += 1
    
    results["recycle_bin"] = recycle
    
    # 8. Generate recommendations
    if results["stats"]["total_cleanable"] > 0:
        results["recommendations"].append({
            "icon": "🧹",
            "title": "Clean Up",
            "description": f"You can free up {format_size(results['stats']['total_cleanable'])} by cleaning temp files, old downloads, and emptying Recycle Bin.",
        })
    
    if any(d["status"] == "critical" for d in results["disk_info"]):
        results["recommendations"].append({
            "icon": "💾",
            "title": "Free Disk Space",
            "description": "One or more disks are critically low on space. Delete files or move to external storage.",
        })
    
    return results


def format_size(size: int) -> str:
    """Format size in human readable format."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"


def format_pc_analysis(results: Dict) -> str:
    """Format PC analysis results for display."""
    lines = []
    
    # Header
    lines.append("=" * 70)
    lines.append("🖥️  PC HEALTH ANALYSIS REPORT")
    lines.append("=" * 70)
    lines.append(f"\n📅 Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # System Info
    info = results.get("system_info", {})
    lines.append(f"\n{'─' * 60}")
    lines.append("💻 SYSTEM INFORMATION")
    lines.append(f"{'─' * 60}")
    lines.append(f"  Computer: {info.get('computer_name', 'Unknown')}")
    lines.append(f"  User: {info.get('username', 'Unknown')}")
    lines.append(f"  OS: {info.get('os', '')} {info.get('os_release', '')}")
    
    # Summary
    stats = results.get("stats", {})
    lines.append(f"\n{'─' * 60}")
    lines.append("📊 SUMMARY")
    lines.append(f"{'─' * 60}")
    
    if stats.get("problem_count", 0) > 0:
        lines.append(f"  🔴 Critical Problems: {stats['problem_count']}")
    if stats.get("warning_count", 0) > 0:
        lines.append(f"  🟡 Warnings: {stats['warning_count']}")
    if stats.get("total_cleanable", 0) > 0:
        lines.append(f"  🧹 Cleanable Space: {format_size(stats['total_cleanable'])}")
    
    if stats.get("problem_count", 0) == 0 and stats.get("warning_count", 0) == 0:
        lines.append("  ✅ No critical problems found!")
    
    # Disk Status
    lines.append(f"\n{'─' * 60}")
    lines.append("💾 DISK STATUS")
    lines.append(f"{'─' * 60}")
    
    for disk in results.get("disk_info", []):
        status_icon = "🔴" if disk["status"] == "critical" else "🟡" if disk["status"] == "warning" else "🟢"
        bar_len = int(disk["usage_percent"] / 5)
        bar = "█" * bar_len + "░" * (20 - bar_len)
        
        lines.append(f"\n  {status_icon} Drive {disk['drive']}")
        lines.append(f"     {bar} {disk['usage_percent']:.1f}%")
        lines.append(f"     Used: {format_size(disk['used'])} / {format_size(disk['total'])}")
        lines.append(f"     Free: {format_size(disk['free'])}")
    
    # Problems
    if results.get("problems"):
        lines.append(f"\n{'─' * 60}")
        lines.append("🔴 CRITICAL PROBLEMS")
        lines.append(f"{'─' * 60}")
        
        for p in results["problems"]:
            lines.append(f"\n  {p['icon']} {p['title']}")
            lines.append(f"     {p['description']}")
            lines.append(f"     💡 {p['recommendation']}")
    
    # Warnings
    if results.get("warnings"):
        lines.append(f"\n{'─' * 60}")
        lines.append("🟡 WARNINGS")
        lines.append(f"{'─' * 60}")
        
        for w in results["warnings"]:
            lines.append(f"\n  {w['icon']} {w['title']}")
            lines.append(f"     {w['description']}")
            lines.append(f"     💡 {w['recommendation']}")
    
    # Large Folders
    large_folders = results.get("large_folders", [])
    if large_folders:
        lines.append(f"\n{'─' * 60}")
        lines.append("📁 LARGE FOLDERS (>1GB)")
        lines.append(f"{'─' * 60}")
        
        for f in large_folders[:10]:
            lines.append(f"  📁 {f['name']}")
            lines.append(f"     {format_size(f['size'])} in {f['parent']}")
    
    # Recommendations
    if results.get("recommendations"):
        lines.append(f"\n{'─' * 60}")
        lines.append("💡 RECOMMENDATIONS")
        lines.append(f"{'─' * 60}")
        
        for r in results["recommendations"]:
            lines.append(f"\n  {r['icon']} {r['title']}")
            lines.append(f"     {r['description']}")
    
    lines.append(f"\n{'=' * 70}")
    lines.append("End of Report")
    lines.append(f"{'=' * 70}")
    
    return "\n".join(lines)
