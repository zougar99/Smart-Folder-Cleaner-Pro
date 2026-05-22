# -*- coding: utf-8 -*-
"""
Scan a folder or drive: list all files with path, size, extension, category.
Skips system folders (Windows, Program Files, node_modules, etc.).
"""
import os
from config import SKIP_DIRS

# Extension -> category (for summary and "organize by type")
EXT_CATEGORIES = {
    "documents": (".doc", ".docx", ".odt", ".txt", ".rtf", ".xls", ".xlsx", ".ods", ".ppt", ".pptx"),
    "images": (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".ico", ".heic"),
    "pdf": (".pdf",),
    "videos": (".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm", ".m4v"),
    "audio": (".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma"),
    "archives": (".zip", ".rar", ".7z", ".tar", ".gz", ".bz2"),
    "code": (".py", ".js", ".ts", ".html", ".css", ".json", ".xml", ".java", ".c", ".cpp", ".cs", ".php", ".rb", ".go"),
}


def _category_for_ext(ext: str) -> str:
    ext = (ext or "").lower()
    for cat, exts in EXT_CATEGORIES.items():
        if ext in exts:
            return cat
    return "other"


def scan_root(root_path: str, progress_cb=None):
    """
    Scan root_path (folder or drive). Yield dicts: path, size, ext, category.
    progress_cb(current_count) optional for GUI.
    """
    root_path = os.path.abspath(root_path)
    if not os.path.isdir(root_path):
        return
    count = 0
    for dirpath, _dirnames, filenames in os.walk(root_path, topdown=True):
        # Skip system/heavy dirs
        dirname_lower = os.path.basename(dirpath).lower()
        if dirname_lower in SKIP_DIRS:
            _dirnames.clear()
            continue
        for name in filenames:
            try:
                full = os.path.join(dirpath, name)
                if not os.path.isfile(full):
                    continue
                size = os.path.getsize(full)
            except OSError:
                continue
            _, ext = os.path.splitext(name)
            cat = _category_for_ext(ext)
            count += 1
            if progress_cb and count % 100 == 0:
                progress_cb(count)
            yield {"path": full, "name": name, "size": size, "ext": ext, "category": cat}


def get_scan_results_list(root_path: str, progress_cb=None):
    """Return list of all file dicts for root_path."""
    return list(scan_root(root_path, progress_cb))


def get_summary_by_category(files: list) -> dict:
    """Aggregate: category -> { count, total_size }."""
    summary = {}
    for f in files:
        cat = f.get("category", "other")
        if cat not in summary:
            summary[cat] = {"count": 0, "total_size": 0}
        summary[cat]["count"] += 1
        summary[cat]["total_size"] += f.get("size", 0)
    return summary


def get_available_drives():
    r"""Windows: list drive letters (C:\, D:\, ...). Other: common roots."""
    import sys
    if sys.platform == "win32":
        import string
        drives = []
        for letter in string.ascii_uppercase:
            d = letter + ":\\"
            if os.path.exists(d):
                drives.append(d)
        return drives
    return ["/"] if os.path.exists("/") else []
