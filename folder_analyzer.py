# -*- coding: utf-8 -*-
"""
Smart Folder Analyzer - Understands folder PURPOSE using AI.
Analyzes: folder name, file names, README, config files, structure.
"""
import os
import json
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL

# Files that indicate project type
PROJECT_INDICATORS = {
    "python": ["requirements.txt", "setup.py", "pyproject.toml", "*.py", "Pipfile"],
    "javascript": ["package.json", "node_modules", "*.js", "*.ts", "yarn.lock"],
    "web": ["index.html", "*.html", "*.css", "style.css"],
    "rust": ["Cargo.toml", "*.rs"],
    "java": ["pom.xml", "build.gradle", "*.java"],
    "csharp": ["*.csproj", "*.sln", "*.cs"],
    "documents": ["*.docx", "*.pdf", "*.xlsx", "*.pptx"],
    "images": ["*.jpg", "*.png", "*.gif", "*.psd", "*.ai"],
    "videos": ["*.mp4", "*.mov", "*.avi", "*.mkv"],
    "music": ["*.mp3", "*.wav", "*.flac"],
    "game": ["*.exe", "*.dll", "Assets", "Resources"],
    "android": ["AndroidManifest.xml", "*.apk", "gradle"],
    "firefox_extension": ["manifest.json", "popup.html", "background.js"],
    "chrome_extension": ["manifest.json", "popup.html", "content.js"],
}

# Files to read for context
CONTEXT_FILES = ["README.md", "readme.md", "README.txt", "readme.txt", 
                 "package.json", "pyproject.toml", "Cargo.toml", 
                 "manifest.json", "description.txt", ".project"]


def get_folder_context(folder_path: str) -> dict:
    """
    Gather context about a folder: name, files, structure, README content.
    """
    folder_path = os.path.abspath(folder_path)
    if not os.path.isdir(folder_path):
        return {"error": "Not a valid folder"}
    
    folder_name = os.path.basename(folder_path)
    
    # Get all files and folders (first level)
    try:
        items = os.listdir(folder_path)
    except PermissionError:
        return {"error": "Permission denied"}
    
    files = []
    subdirs = []
    for item in items:
        full_path = os.path.join(folder_path, item)
        if os.path.isfile(full_path):
            files.append(item)
        elif os.path.isdir(full_path):
            subdirs.append(item)
    
    # Read README or other context files
    readme_content = ""
    for ctx_file in CONTEXT_FILES:
        ctx_path = os.path.join(folder_path, ctx_file)
        if os.path.isfile(ctx_path):
            try:
                with open(ctx_path, "r", encoding="utf-8", errors="ignore") as f:
                    readme_content = f.read()[:2000]  # First 2000 chars
                break
            except:
                pass
    
    # Detect project type from indicators
    detected_types = []
    all_items_lower = [i.lower() for i in items]
    for proj_type, indicators in PROJECT_INDICATORS.items():
        for indicator in indicators:
            if indicator.startswith("*."):
                ext = indicator[1:]  # .py, .js, etc.
                if any(f.lower().endswith(ext) for f in files):
                    if proj_type not in detected_types:
                        detected_types.append(proj_type)
                    break
            else:
                if indicator.lower() in all_items_lower:
                    if proj_type not in detected_types:
                        detected_types.append(proj_type)
                    break
    
    return {
        "folder_path": folder_path,
        "folder_name": folder_name,
        "files": files[:100],  # Limit for API
        "subdirs": subdirs[:50],
        "total_files": len(files),
        "total_subdirs": len(subdirs),
        "readme_content": readme_content,
        "detected_types": detected_types,
    }


def analyze_folder_purpose(folder_path: str) -> dict:
    """
    Use AI to understand what this folder is about.
    Returns: purpose, expected_file_types, description
    """
    context = get_folder_context(folder_path)
    if "error" in context:
        return context
    
    # If no API key, use rule-based analysis
    if not DEEPSEEK_API_KEY:
        return _rule_based_analysis(context)
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
        
        prompt = f"""Analyze this folder and tell me:
1. What is this folder's PURPOSE? (e.g., "Python web project", "Photo collection", "Firefox extension")
2. What types of files SHOULD be here?
3. What types of files should NOT be here?

Folder name: {context['folder_name']}
Detected types: {', '.join(context['detected_types']) or 'unknown'}
Subdirectories: {', '.join(context['subdirs'][:20])}
Files (sample): {', '.join(context['files'][:30])}
README/Config content: {context['readme_content'][:500] if context['readme_content'] else 'None'}

Reply in JSON format ONLY:
{{
    "purpose": "short description of folder purpose",
    "category": "one of: python_project, js_project, web_project, extension, documents, images, videos, music, mixed, unknown",
    "expected_extensions": [".py", ".txt", ...],
    "unexpected_extensions": [".mp3", ".jpg", ...],
    "description": "detailed explanation"
}}"""

        resp = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        text = (resp.choices[0].message.content or "").strip()
        
        # Extract JSON
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        
        result = json.loads(text)
        result["folder_path"] = context["folder_path"]
        result["folder_name"] = context["folder_name"]
        result["files"] = context["files"]
        result["detected_types"] = context["detected_types"]
        return result
        
    except Exception as e:
        # Fallback to rule-based
        result = _rule_based_analysis(context)
        result["ai_error"] = str(e)
        return result


def _rule_based_analysis(context: dict) -> dict:
    """Fallback analysis without AI."""
    detected = context.get("detected_types", [])
    folder_name = context.get("folder_name", "").lower()
    
    # Determine category
    if "python" in detected:
        category = "python_project"
        expected = [".py", ".txt", ".md", ".json", ".yml", ".yaml", ".toml", ".cfg", ".ini"]
        unexpected = [".mp3", ".mp4", ".jpg", ".png", ".doc", ".docx", ".psd"]
    elif "javascript" in detected:
        category = "js_project"
        expected = [".js", ".ts", ".json", ".md", ".css", ".html", ".jsx", ".tsx"]
        unexpected = [".mp3", ".mp4", ".py", ".exe", ".doc", ".docx", ".psd"]
    elif "firefox_extension" in detected or "chrome_extension" in detected:
        category = "extension"
        expected = [".js", ".json", ".html", ".css", ".png", ".svg", ".md"]
        unexpected = [".mp3", ".mp4", ".py", ".exe", ".doc", ".docx", ".psd", ".jpg"]
    elif "documents" in detected:
        category = "documents"
        expected = [".doc", ".docx", ".pdf", ".xlsx", ".pptx", ".txt", ".md"]
        unexpected = [".py", ".js", ".exe", ".mp3", ".mp4"]
    elif "images" in detected:
        category = "images"
        expected = [".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".psd", ".ai"]
        unexpected = [".py", ".js", ".exe", ".mp3", ".doc"]
    elif "videos" in detected:
        category = "videos"
        expected = [".mp4", ".mov", ".avi", ".mkv", ".webm"]
        unexpected = [".py", ".js", ".exe", ".doc", ".jpg"]
    elif "music" in detected:
        category = "music"
        expected = [".mp3", ".wav", ".flac", ".m4a", ".ogg"]
        unexpected = [".py", ".js", ".exe", ".doc", ".jpg", ".mp4"]
    else:
        category = "mixed"
        expected = []
        unexpected = []
    
    # Check folder name for hints
    if "photo" in folder_name or "image" in folder_name or "picture" in folder_name:
        category = "images"
    elif "music" in folder_name or "audio" in folder_name or "song" in folder_name:
        category = "music"
    elif "video" in folder_name or "movie" in folder_name or "film" in folder_name:
        category = "videos"
    elif "document" in folder_name or "doc" in folder_name:
        category = "documents"
    
    return {
        "folder_path": context["folder_path"],
        "folder_name": context["folder_name"],
        "purpose": f"{category.replace('_', ' ').title()} folder",
        "category": category,
        "expected_extensions": expected,
        "unexpected_extensions": unexpected,
        "description": f"Detected as {category} based on file types: {', '.join(detected) or 'unknown'}",
        "files": context["files"],
        "detected_types": detected,
    }


def get_all_files_deep(folder_path: str, skip_dirs: set = None) -> list:
    """Get all files recursively with their info."""
    if skip_dirs is None:
        skip_dirs = {"node_modules", ".git", "__pycache__", ".venv", "venv", "$RECYCLE.BIN"}
    
    files = []
    folder_path = os.path.abspath(folder_path)
    
    for dirpath, dirnames, filenames in os.walk(folder_path, topdown=True):
        # Skip unwanted directories
        dirnames[:] = [d for d in dirnames if d.lower() not in skip_dirs]
        
        for name in filenames:
            try:
                full_path = os.path.join(dirpath, name)
                rel_path = os.path.relpath(full_path, folder_path)
                _, ext = os.path.splitext(name)
                size = os.path.getsize(full_path)
                files.append({
                    "path": full_path,
                    "rel_path": rel_path,
                    "name": name,
                    "ext": ext.lower(),
                    "size": size,
                    "dir": os.path.relpath(dirpath, folder_path),
                })
            except (OSError, PermissionError):
                continue
    
    return files
