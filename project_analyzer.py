# -*- coding: utf-8 -*-
"""
Smart Project Analyzer - Understands project types and identifies unrelated files.
Detects: Python, JavaScript, Web, Game, Extension, Documents, Media collections, etc.
"""
import os
import json
from collections import defaultdict
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL

# Project type detection rules
PROJECT_SIGNATURES = {
    "python_project": {
        "required_files": ["*.py"],
        "indicator_files": ["requirements.txt", "setup.py", "pyproject.toml", "Pipfile", "setup.cfg", "tox.ini", "pytest.ini"],
        "indicator_folders": ["venv", ".venv", "__pycache__", "src", "tests", "lib"],
        "expected_extensions": [".py", ".pyw", ".pyx", ".pyi", ".txt", ".md", ".rst", ".json", ".yaml", ".yml", ".toml", ".cfg", ".ini", ".env", ".gitignore", ".sh", ".bat"],
        "unexpected_extensions": [".mp3", ".mp4", ".avi", ".mkv", ".mov", ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".psd", ".ai", ".msi", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".wav", ".flac"],
        "description": "Python programming project"
    },
    "javascript_project": {
        "required_files": ["package.json"],
        "indicator_files": ["package.json", "package-lock.json", "yarn.lock", "tsconfig.json", "webpack.config.js", ".babelrc", "vite.config.js"],
        "indicator_folders": ["node_modules", "src", "dist", "build", "public"],
        "expected_extensions": [".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".json", ".md", ".html", ".css", ".scss", ".sass", ".less", ".svg", ".png", ".ico", ".env", ".gitignore"],
        "unexpected_extensions": [".mp3", ".mp4", ".avi", ".mkv", ".py", ".exe", ".msi", ".dll", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".psd", ".ai", ".wav", ".flac"],
        "description": "JavaScript/Node.js project"
    },
    "web_project": {
        "required_files": ["*.html"],
        "indicator_files": ["index.html", "style.css", "styles.css", "main.css", "script.js", "app.js"],
        "indicator_folders": ["css", "js", "images", "img", "assets", "fonts"],
        "expected_extensions": [".html", ".htm", ".css", ".scss", ".js", ".json", ".svg", ".png", ".jpg", ".jpeg", ".gif", ".ico", ".webp", ".woff", ".woff2", ".ttf", ".eot", ".md"],
        "unexpected_extensions": [".mp3", ".mp4", ".avi", ".mkv", ".py", ".exe", ".msi", ".dll", ".doc", ".docx", ".xls", ".xlsx", ".psd", ".ai", ".wav", ".flac"],
        "description": "Web/HTML project"
    },
    "firefox_extension": {
        "required_files": ["manifest.json"],
        "indicator_files": ["manifest.json", "popup.html", "background.js", "content.js", "options.html"],
        "indicator_folders": ["icons", "_locales"],
        "expected_extensions": [".js", ".json", ".html", ".css", ".png", ".svg", ".md", ".ico"],
        "unexpected_extensions": [".mp3", ".mp4", ".avi", ".py", ".exe", ".doc", ".docx", ".jpg", ".jpeg", ".gif", ".psd"],
        "description": "Firefox/Chrome browser extension"
    },
    "unity_game": {
        "required_files": ["*.unity", "ProjectSettings"],
        "indicator_files": ["Assembly-CSharp.csproj", "ProjectSettings/ProjectSettings.asset"],
        "indicator_folders": ["Assets", "Library", "ProjectSettings", "Packages"],
        "expected_extensions": [".cs", ".unity", ".meta", ".asset", ".prefab", ".mat", ".shader", ".anim", ".controller", ".png", ".jpg", ".wav", ".mp3", ".fbx", ".obj"],
        "unexpected_extensions": [".py", ".js", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx"],
        "description": "Unity game project"
    },
    "documents_folder": {
        "required_files": ["*.doc", "*.docx", "*.pdf", "*.txt"],
        "indicator_files": [],
        "indicator_folders": [],
        "expected_extensions": [".doc", ".docx", ".pdf", ".txt", ".rtf", ".odt", ".xls", ".xlsx", ".ods", ".ppt", ".pptx", ".odp", ".md", ".csv"],
        "unexpected_extensions": [".py", ".js", ".exe", ".dll", ".mp3", ".mp4", ".avi", ".jpg", ".png", ".psd"],
        "description": "Documents folder"
    },
    "images_folder": {
        "required_files": ["*.jpg", "*.png", "*.gif"],
        "indicator_files": [],
        "indicator_folders": [],
        "expected_extensions": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".ico", ".tiff", ".raw", ".psd", ".ai", ".heic"],
        "unexpected_extensions": [".py", ".js", ".exe", ".dll", ".mp3", ".mp4", ".doc", ".docx", ".xls", ".txt"],
        "description": "Images/Photos folder"
    },
    "music_folder": {
        "required_files": ["*.mp3", "*.wav", "*.flac"],
        "indicator_files": [],
        "indicator_folders": [],
        "expected_extensions": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma", ".opus", ".txt", ".jpg", ".png"],
        "unexpected_extensions": [".py", ".js", ".exe", ".dll", ".mp4", ".avi", ".doc", ".docx", ".html"],
        "description": "Music/Audio folder"
    },
    "video_folder": {
        "required_files": ["*.mp4", "*.avi", "*.mkv"],
        "indicator_files": [],
        "indicator_folders": [],
        "expected_extensions": [".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm", ".m4v", ".srt", ".sub", ".txt", ".jpg", ".png"],
        "unexpected_extensions": [".py", ".js", ".exe", ".dll", ".mp3", ".doc", ".docx", ".html", ".psd"],
        "description": "Videos folder"
    },
}


def detect_project_type(folder_path: str) -> dict:
    """
    Analyze folder and detect what type of project/collection it is.
    Returns project type, confidence, and relevant info.
    """
    folder_path = os.path.abspath(folder_path)
    if not os.path.isdir(folder_path):
        return {"error": "Not a valid folder"}
    
    folder_name = os.path.basename(folder_path).lower()
    
    # Get files in folder (top level and one level deep)
    all_files = []
    all_folders = []
    extensions_count = defaultdict(int)
    
    try:
        for item in os.listdir(folder_path):
            item_path = os.path.join(folder_path, item)
            if os.path.isfile(item_path):
                all_files.append(item)
                _, ext = os.path.splitext(item)
                extensions_count[ext.lower()] += 1
            elif os.path.isdir(item_path):
                all_folders.append(item)
                # Check one level deep
                try:
                    for sub_item in os.listdir(item_path):
                        sub_path = os.path.join(item_path, sub_item)
                        if os.path.isfile(sub_path):
                            _, ext = os.path.splitext(sub_item)
                            extensions_count[ext.lower()] += 1
                except:
                    pass
    except PermissionError:
        return {"error": "Permission denied"}
    
    # Score each project type
    scores = {}
    for proj_type, rules in PROJECT_SIGNATURES.items():
        score = 0
        
        # Check indicator files
        for indicator in rules.get("indicator_files", []):
            if indicator in all_files or indicator.lower() in [f.lower() for f in all_files]:
                score += 10
        
        # Check indicator folders
        for indicator in rules.get("indicator_folders", []):
            if indicator in all_folders or indicator.lower() in [f.lower() for f in all_folders]:
                score += 5
        
        # Check required file patterns
        for pattern in rules.get("required_files", []):
            if pattern.startswith("*."):
                ext = pattern[1:]  # Get .py, .html, etc.
                if extensions_count.get(ext, 0) > 0:
                    score += extensions_count[ext] * 2
        
        # Check folder name hints
        if "python" in folder_name or "py" in folder_name:
            if proj_type == "python_project":
                score += 15
        if "web" in folder_name or "site" in folder_name or "html" in folder_name:
            if proj_type == "web_project":
                score += 15
        if "extension" in folder_name or "addon" in folder_name:
            if proj_type == "firefox_extension":
                score += 15
        if "photo" in folder_name or "image" in folder_name or "picture" in folder_name:
            if proj_type == "images_folder":
                score += 15
        if "music" in folder_name or "audio" in folder_name or "song" in folder_name:
            if proj_type == "music_folder":
                score += 15
        if "video" in folder_name or "movie" in folder_name or "film" in folder_name:
            if proj_type == "video_folder":
                score += 15
        if "document" in folder_name or "doc" in folder_name:
            if proj_type == "documents_folder":
                score += 15
        
        scores[proj_type] = score
    
    # Find best match
    best_type = max(scores, key=scores.get)
    best_score = scores[best_type]
    
    # Confidence level
    if best_score >= 30:
        confidence = "high"
    elif best_score >= 15:
        confidence = "medium"
    elif best_score >= 5:
        confidence = "low"
    else:
        confidence = "unknown"
        best_type = "mixed_folder"
    
    return {
        "folder_path": folder_path,
        "folder_name": os.path.basename(folder_path),
        "detected_type": best_type,
        "confidence": confidence,
        "score": best_score,
        "all_scores": scores,
        "rules": PROJECT_SIGNATURES.get(best_type, {}),
        "extensions_found": dict(extensions_count),
        "files_count": len(all_files),
        "folders_count": len(all_folders),
    }


def find_unrelated_files(folder_path: str, use_ai: bool = True) -> dict:
    """
    Find files that don't belong to the detected project type.
    """
    # First detect project type
    detection = detect_project_type(folder_path)
    if "error" in detection:
        return detection
    
    project_type = detection["detected_type"]
    rules = detection.get("rules", {})
    expected_exts = set(rules.get("expected_extensions", []))
    unexpected_exts = set(rules.get("unexpected_extensions", []))
    
    folder_path = os.path.abspath(folder_path)
    skip_dirs = {"node_modules", ".git", "__pycache__", ".venv", "venv", "$RECYCLE.BIN"}
    
    related_files = []
    unrelated_files = []
    total_files = 0
    
    for dirpath, dirnames, filenames in os.walk(folder_path, topdown=True):
        dirnames[:] = [d for d in dirnames if d.lower() not in skip_dirs]
        
        for name in filenames:
            total_files += 1
            full_path = os.path.join(dirpath, name)
            rel_path = os.path.relpath(full_path, folder_path)
            _, ext = os.path.splitext(name)
            ext = ext.lower()
            
            try:
                size = os.path.getsize(full_path)
            except:
                size = 0
            
            file_info = {
                "name": name,
                "path": full_path,
                "rel_path": rel_path,
                "ext": ext,
                "size": size,
            }
            
            # Determine if file is related or not
            if ext in unexpected_exts:
                file_info["reason"] = f"{ext} files don't belong in {rules.get('description', project_type)}"
                file_info["status"] = "unrelated"
                unrelated_files.append(file_info)
            elif ext in expected_exts or not expected_exts:
                file_info["status"] = "related"
                related_files.append(file_info)
            elif expected_exts and ext not in expected_exts:
                # Extension not in expected list
                file_info["reason"] = f"{ext} is unusual for {rules.get('description', project_type)}"
                file_info["status"] = "possibly_unrelated"
                unrelated_files.append(file_info)
            else:
                file_info["status"] = "unknown"
                related_files.append(file_info)
    
    # Use AI to refine if available
    if use_ai and DEEPSEEK_API_KEY and unrelated_files:
        unrelated_files = _refine_with_ai(detection, unrelated_files)
    
    return {
        "folder_path": folder_path,
        "folder_name": detection["folder_name"],
        "project_type": project_type,
        "project_description": rules.get("description", "Unknown type"),
        "confidence": detection["confidence"],
        "total_files": total_files,
        "related_count": len(related_files),
        "unrelated_count": len(unrelated_files),
        "related_files": related_files,
        "unrelated_files": unrelated_files,
    }


def _refine_with_ai(detection: dict, unrelated_files: list) -> list:
    """Use AI to confirm unrelated files."""
    if not unrelated_files:
        return unrelated_files
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
        
        sample = unrelated_files[:25]
        file_list = "\n".join([f"- {f['rel_path']}" for f in sample])
        
        prompt = f"""This folder is a: {detection.get('rules', {}).get('description', detection.get('detected_type', 'unknown'))}

These files were flagged as possibly NOT related to this project:
{file_list}

For each file, tell me:
1. Is it related to the project? (yes/no/maybe)
2. Brief reason

Reply in JSON:
{{
    "file_path": {{"related": "yes/no/maybe", "reason": "..."}},
    ...
}}"""

        resp = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        text = (resp.choices[0].message.content or "").strip()
        
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        
        ai_results = json.loads(text)
        
        refined = []
        for f in unrelated_files:
            rel_path = f.get("rel_path", "")
            ai_info = ai_results.get(rel_path, {})
            
            related = ai_info.get("related", "maybe")
            if related == "yes":
                f["status"] = "ai_approved_related"
            elif related == "no":
                f["status"] = "ai_confirmed_unrelated"
                f["reason"] = ai_info.get("reason", f["reason"])
                refined.append(f)
            else:
                f["status"] = "possibly_unrelated"
                refined.append(f)
        
        return refined
        
    except:
        return unrelated_files


def get_cleanup_plan(unrelated_files: list, dest_folder: str) -> list:
    """Create plan to move unrelated files."""
    plan = []
    dest_folder = os.path.abspath(dest_folder)
    
    for f in unrelated_files:
        src = f.get("path", "")
        if not src or not os.path.isfile(src):
            continue
        
        name = f.get("name", os.path.basename(src))
        ext = f.get("ext", "").lower()
        
        # Organize by type in destination
        if ext in [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg"]:
            sub = "images"
        elif ext in [".mp3", ".wav", ".flac", ".m4a", ".ogg"]:
            sub = "audio"
        elif ext in [".mp4", ".avi", ".mkv", ".mov", ".webm"]:
            sub = "videos"
        elif ext in [".doc", ".docx", ".pdf", ".xls", ".xlsx", ".ppt", ".pptx"]:
            sub = "documents"
        elif ext in [".exe", ".msi", ".dll"]:
            sub = "executables"
        elif ext in [".zip", ".rar", ".7z"]:
            sub = "archives"
        else:
            sub = "other"
        
        dest_path = os.path.join(dest_folder, sub, name)
        
        plan.append({
            "src": src,
            "dest": dest_path,
            "reason": f.get("reason", "Doesn't belong to project"),
            "size": f.get("size", 0),
        })
    
    return plan


def format_analysis_report(result: dict) -> str:
    """Format analysis result for display."""
    lines = []
    lines.append("=" * 55)
    lines.append("🔍 PROJECT ANALYSIS")
    lines.append("=" * 55)
    
    lines.append(f"\n📁 Folder: {result.get('folder_name', '')}")
    lines.append(f"📍 Path: {result.get('folder_path', '')}")
    
    lines.append(f"\n🎯 Detected Type: {result.get('project_description', 'Unknown')}")
    lines.append(f"📊 Confidence: {result.get('confidence', 'unknown').upper()}")
    
    lines.append(f"\n{'─' * 40}")
    lines.append("📈 STATISTICS")
    lines.append(f"{'─' * 40}")
    lines.append(f"  Total files: {result.get('total_files', 0)}")
    lines.append(f"  ✅ Related to project: {result.get('related_count', 0)}")
    lines.append(f"  ❌ NOT related: {result.get('unrelated_count', 0)}")
    
    if result.get("unrelated_files"):
        lines.append(f"\n{'─' * 40}")
        lines.append("❌ FILES THAT DON'T BELONG")
        lines.append(f"{'─' * 40}")
        
        for f in result.get("unrelated_files", [])[:50]:
            status_icon = "❌" if "unrelated" in f.get("status", "") else "⚠️"
            lines.append(f"\n  {status_icon} {f.get('rel_path', f.get('name', ''))}")
            lines.append(f"     Reason: {f.get('reason', 'Unknown')}")
    else:
        lines.append(f"\n✅ All files belong to this project!")
    
    return "\n".join(lines)
