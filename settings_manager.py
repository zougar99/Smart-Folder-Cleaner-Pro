# -*- coding: utf-8 -*-
"""
Settings Manager - User customizable rules and preferences.
"""
import os
import json
from datetime import datetime

SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "user_settings.json")

# Default settings
DEFAULT_SETTINGS = {
    # Big files threshold
    "big_files_min_mb": 100,
    
    # Old files threshold
    "old_files_days": 365,
    
    # Folders to skip when scanning
    "skip_folders": [
        "node_modules", ".git", "__pycache__", ".venv", "venv",
        "$RECYCLE.BIN", "System Volume Information", "Windows",
        "Program Files", "Program Files (x86)", "AppData"
    ],
    
    # File categories - which extensions belong to which category
    "file_categories": {
        "Python Project": [".py", ".pyw", ".pyx", ".pyi", ".pyc", ".pyd"],
        "JavaScript Project": [".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"],
        "Web Files": [".html", ".htm", ".css", ".scss", ".sass", ".less"],
        "Documents": [".doc", ".docx", ".pdf", ".xls", ".xlsx", ".ppt", ".pptx", ".odt", ".ods", ".odp"],
        "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".ico", ".tiff", ".psd", ".ai"],
        "Videos": [".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm", ".m4v"],
        "Audio": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma"],
        "Archives": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz"],
        "Executables": [".exe", ".msi", ".dll", ".bat", ".cmd", ".ps1", ".sh"],
        "Config/Data": [".json", ".xml", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".env"],
    },
    
    # Custom rules: what files DON'T belong in certain folder types
    "mismatch_rules": {
        "python_project": {
            "unexpected": [".mp3", ".mp4", ".avi", ".mkv", ".jpg", ".png", ".gif", ".msi", ".doc", ".docx", ".psd"],
            "description": "Media and document files don't belong in Python projects"
        },
        "javascript_project": {
            "unexpected": [".mp3", ".mp4", ".avi", ".mkv", ".py", ".exe", ".msi", ".doc", ".docx", ".psd"],
            "description": "Media, Python and document files don't belong in JS projects"
        },
        "images_folder": {
            "unexpected": [".py", ".js", ".exe", ".doc", ".mp3", ".mp4", ".zip"],
            "description": "Code and non-image files don't belong in image folders"
        },
        "documents_folder": {
            "unexpected": [".py", ".js", ".exe", ".mp3", ".mp4", ".jpg", ".png"],
            "description": "Code and media files don't belong in document folders"
        },
        "music_folder": {
            "unexpected": [".py", ".js", ".exe", ".doc", ".jpg", ".png", ".mp4", ".avi"],
            "description": "Code, documents and video files don't belong in music folders"
        },
        "video_folder": {
            "unexpected": [".py", ".js", ".exe", ".doc", ".jpg", ".png", ".mp3"],
            "description": "Code, documents and non-video files don't belong in video folders"
        },
    },
    
    # Extensions to always ignore (system files)
    "ignore_extensions": [".tmp", ".temp", ".bak", ".swp", ".swo", ".DS_Store", "Thumbs.db"],
    
    # Files to always ignore
    "ignore_files": ["desktop.ini", ".DS_Store", "Thumbs.db", ".gitkeep", ".placeholder"],
    
    # Custom notes/reminders
    "user_notes": "",
    
    # Last updated
    "last_updated": "",
}


def load_settings() -> dict:
    """Load user settings from file, or return defaults."""
    if os.path.isfile(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                # Merge with defaults (in case new settings were added)
                settings = DEFAULT_SETTINGS.copy()
                settings.update(saved)
                return settings
        except:
            pass
    return DEFAULT_SETTINGS.copy()


def save_settings(settings: dict) -> bool:
    """Save user settings to file."""
    try:
        settings["last_updated"] = datetime.now().isoformat()
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving settings: {e}")
        return False


def reset_settings() -> dict:
    """Reset to default settings."""
    save_settings(DEFAULT_SETTINGS)
    return DEFAULT_SETTINGS.copy()


def add_skip_folder(folder_name: str, settings: dict) -> dict:
    """Add a folder to skip list."""
    if folder_name and folder_name not in settings["skip_folders"]:
        settings["skip_folders"].append(folder_name)
    return settings


def remove_skip_folder(folder_name: str, settings: dict) -> dict:
    """Remove a folder from skip list."""
    if folder_name in settings["skip_folders"]:
        settings["skip_folders"].remove(folder_name)
    return settings


def add_mismatch_rule(category: str, extensions: list, description: str, settings: dict) -> dict:
    """Add a custom mismatch rule."""
    settings["mismatch_rules"][category] = {
        "unexpected": extensions,
        "description": description
    }
    return settings


def add_file_category(category_name: str, extensions: list, settings: dict) -> dict:
    """Add or update a file category."""
    settings["file_categories"][category_name] = extensions
    return settings


def get_unexpected_extensions(folder_type: str, settings: dict) -> list:
    """Get list of unexpected extensions for a folder type."""
    rules = settings.get("mismatch_rules", {})
    rule = rules.get(folder_type, {})
    return rule.get("unexpected", [])


def is_file_ignored(filename: str, settings: dict) -> bool:
    """Check if a file should be ignored."""
    if filename in settings.get("ignore_files", []):
        return True
    
    _, ext = os.path.splitext(filename)
    if ext.lower() in settings.get("ignore_extensions", []):
        return True
    
    return False


def format_settings_display(settings: dict) -> str:
    """Format settings for display in GUI."""
    lines = []
    lines.append("=" * 50)
    lines.append("⚙️ CURRENT SETTINGS")
    lines.append("=" * 50)
    
    lines.append(f"\n📦 Big Files Threshold: {settings.get('big_files_min_mb', 100)} MB")
    lines.append(f"🕐 Old Files Threshold: {settings.get('old_files_days', 365)} days")
    
    lines.append(f"\n{'─' * 40}")
    lines.append("🚫 FOLDERS TO SKIP:")
    lines.append(f"{'─' * 40}")
    for folder in settings.get("skip_folders", []):
        lines.append(f"  • {folder}")
    
    lines.append(f"\n{'─' * 40}")
    lines.append("📂 FILE CATEGORIES:")
    lines.append(f"{'─' * 40}")
    for cat, exts in settings.get("file_categories", {}).items():
        lines.append(f"  {cat}:")
        lines.append(f"    {', '.join(exts[:10])}")
        if len(exts) > 10:
            lines.append(f"    ... and {len(exts) - 10} more")
    
    lines.append(f"\n{'─' * 40}")
    lines.append("⚠️ MISMATCH RULES:")
    lines.append(f"{'─' * 40}")
    for cat, rule in settings.get("mismatch_rules", {}).items():
        lines.append(f"  {cat}:")
        lines.append(f"    Unexpected: {', '.join(rule.get('unexpected', [])[:8])}")
        lines.append(f"    {rule.get('description', '')}")
    
    lines.append(f"\n{'─' * 40}")
    lines.append("🙈 IGNORED FILES/EXTENSIONS:")
    lines.append(f"{'─' * 40}")
    lines.append(f"  Extensions: {', '.join(settings.get('ignore_extensions', []))}")
    lines.append(f"  Files: {', '.join(settings.get('ignore_files', []))}")
    
    if settings.get("user_notes"):
        lines.append(f"\n{'─' * 40}")
        lines.append("📝 YOUR NOTES:")
        lines.append(f"{'─' * 40}")
        lines.append(f"  {settings.get('user_notes', '')}")
    
    if settings.get("last_updated"):
        lines.append(f"\n\n📅 Last updated: {settings.get('last_updated', '')}")
    
    return "\n".join(lines)
