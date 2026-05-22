# -*- coding: utf-8 -*-
"""
AI Deep Analyzer - Reads entire folder content before making decisions.
Uses AI to understand project context and make intelligent separation decisions.
"""
import os
import json
from collections import defaultdict
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL

# Files to read for understanding project
CONTEXT_FILES = [
    "README.md", "readme.md", "README.txt", "README",
    "package.json", "requirements.txt", "setup.py", "pyproject.toml",
    "Cargo.toml", "pom.xml", "build.gradle",
    "manifest.json", "composer.json",
    ".gitignore", "Makefile", "Dockerfile",
    "index.html", "main.py", "app.py", "index.js", "main.js", "App.js",
]

# Maximum content to read per file
MAX_FILE_CONTENT = 1500
MAX_TOTAL_CONTEXT = 8000


def read_file_safe(filepath: str, max_chars: int = MAX_FILE_CONTENT) -> str:
    """Safely read file content."""
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            return f.read(max_chars)
    except:
        return ""


def gather_deep_context(folder_path: str, progress_cb=None) -> dict:
    """
    Gather comprehensive information about a folder.
    Reads file contents, structure, and metadata.
    """
    folder_path = os.path.abspath(folder_path)
    if not os.path.isdir(folder_path):
        return {"error": "Invalid folder"}
    
    folder_name = os.path.basename(folder_path)
    
    if progress_cb:
        progress_cb("Reading folder structure...")
    
    # Collect all files info
    all_files = []
    extensions_count = defaultdict(int)
    total_size = 0
    skip_dirs = {"node_modules", ".git", "__pycache__", ".venv", "venv", 
                 "$RECYCLE.BIN", "System Volume Information"}
    
    for dirpath, dirnames, filenames in os.walk(folder_path, topdown=True):
        dirnames[:] = [d for d in dirnames if d.lower() not in skip_dirs]
        
        for name in filenames:
            try:
                full_path = os.path.join(dirpath, name)
                rel_path = os.path.relpath(full_path, folder_path)
                size = os.path.getsize(full_path)
                _, ext = os.path.splitext(name)
                
                all_files.append({
                    "name": name,
                    "path": full_path,
                    "rel_path": rel_path,
                    "ext": ext.lower(),
                    "size": size,
                })
                
                extensions_count[ext.lower()] += 1
                total_size += size
            except:
                continue
    
    if progress_cb:
        progress_cb("Reading important files...")
    
    # Read context files content
    context_contents = {}
    total_context_length = 0
    
    for ctx_file in CONTEXT_FILES:
        if total_context_length >= MAX_TOTAL_CONTEXT:
            break
            
        ctx_path = os.path.join(folder_path, ctx_file)
        if os.path.isfile(ctx_path):
            content = read_file_safe(ctx_path)
            if content:
                context_contents[ctx_file] = content[:MAX_FILE_CONTENT]
                total_context_length += len(content)
    
    # Also read first code file of each type
    code_extensions = [".py", ".js", ".ts", ".html", ".css", ".java", ".cs", ".go"]
    for ext in code_extensions:
        if total_context_length >= MAX_TOTAL_CONTEXT:
            break
            
        for f in all_files:
            if f["ext"] == ext and f["size"] < 50000:  # Skip huge files
                content = read_file_safe(f["path"], max_chars=1000)
                if content:
                    context_contents[f"sample{ext}"] = content
                    total_context_length += len(content)
                break
    
    # Get folder structure (first 2 levels)
    structure = []
    try:
        for item in sorted(os.listdir(folder_path)):
            item_path = os.path.join(folder_path, item)
            if os.path.isdir(item_path):
                structure.append(f"📁 {item}/")
                if item.lower() not in skip_dirs:
                    try:
                        for sub in sorted(os.listdir(item_path))[:5]:
                            structure.append(f"   ├─ {sub}")
                    except:
                        pass
            else:
                structure.append(f"📄 {item}")
    except:
        pass
    
    return {
        "folder_path": folder_path,
        "folder_name": folder_name,
        "total_files": len(all_files),
        "total_size": total_size,
        "extensions": dict(extensions_count),
        "structure": structure[:50],
        "context_contents": context_contents,
        "all_files": all_files,
    }


def smart_rule_analysis(context: dict) -> dict:
    """
    Smart analysis without AI - uses rules and heuristics.
    """
    folder_name = context.get("folder_name", "").lower()
    extensions = context.get("extensions", {})
    all_files = context.get("all_files", [])
    
    # Detect folder type from extensions and name
    py_count = extensions.get(".py", 0)
    js_count = extensions.get(".js", 0) + extensions.get(".ts", 0)
    html_count = extensions.get(".html", 0)
    img_count = sum(extensions.get(e, 0) for e in [".jpg", ".jpeg", ".png", ".gif", ".webp"])
    audio_count = sum(extensions.get(e, 0) for e in [".mp3", ".wav", ".flac", ".m4a"])
    video_count = sum(extensions.get(e, 0) for e in [".mp4", ".avi", ".mkv", ".mov"])
    doc_count = sum(extensions.get(e, 0) for e in [".doc", ".docx", ".pdf", ".xls", ".xlsx"])
    
    total = len(all_files)
    
    # Determine folder type
    folder_type = "Mixed folder"
    expected_exts = set()
    unexpected_exts = set()
    
    # Check for project indicators in context files
    context_contents = context.get("context_contents", {})
    has_package_json = "package.json" in context_contents
    has_requirements = "requirements.txt" in context_contents or "setup.py" in context_contents
    has_manifest = "manifest.json" in context_contents
    
    if has_requirements or py_count > total * 0.3 or "python" in folder_name:
        folder_type = "Python project"
        expected_exts = {".py", ".pyw", ".txt", ".md", ".json", ".yaml", ".yml", ".toml", ".cfg", ".ini", ".sh", ".bat", ".gitignore", ".env"}
        unexpected_exts = {".mp3", ".mp4", ".avi", ".mkv", ".jpg", ".jpeg", ".png", ".gif", ".msi", ".doc", ".docx", ".psd", ".wav"}
    
    elif has_package_json or js_count > total * 0.3 or "node" in folder_name or "react" in folder_name:
        folder_type = "JavaScript/Node.js project"
        expected_exts = {".js", ".jsx", ".ts", ".tsx", ".json", ".md", ".html", ".css", ".scss", ".svg", ".png", ".ico", ".gitignore", ".env"}
        unexpected_exts = {".mp3", ".mp4", ".avi", ".py", ".exe", ".msi", ".doc", ".docx", ".psd", ".wav"}
    
    elif has_manifest or "extension" in folder_name or "addon" in folder_name:
        folder_type = "Browser extension"
        expected_exts = {".js", ".json", ".html", ".css", ".png", ".svg", ".ico", ".md"}
        unexpected_exts = {".mp3", ".mp4", ".py", ".exe", ".doc", ".jpg", ".jpeg", ".gif", ".psd"}
    
    elif html_count > total * 0.2 or "web" in folder_name or "site" in folder_name:
        folder_type = "Web project"
        expected_exts = {".html", ".htm", ".css", ".js", ".json", ".svg", ".png", ".jpg", ".ico", ".webp", ".md"}
        unexpected_exts = {".mp3", ".mp4", ".py", ".exe", ".doc", ".docx", ".psd"}
    
    elif img_count > total * 0.5 or "photo" in folder_name or "image" in folder_name or "picture" in folder_name:
        folder_type = "Images/Photos folder"
        expected_exts = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg", ".ico", ".tiff", ".raw", ".heic"}
        unexpected_exts = {".py", ".js", ".exe", ".mp3", ".mp4", ".doc", ".html"}
    
    elif audio_count > total * 0.5 or "music" in folder_name or "audio" in folder_name:
        folder_type = "Music/Audio folder"
        expected_exts = {".mp3", ".wav", ".flac", ".m4a", ".ogg", ".aac", ".wma"}
        unexpected_exts = {".py", ".js", ".exe", ".mp4", ".doc", ".html", ".jpg"}
    
    elif video_count > total * 0.5 or "video" in folder_name or "movie" in folder_name:
        folder_type = "Videos folder"
        expected_exts = {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".webm", ".srt", ".sub"}
        unexpected_exts = {".py", ".js", ".exe", ".mp3", ".doc", ".html"}
    
    elif doc_count > total * 0.5 or "document" in folder_name or "doc" in folder_name:
        folder_type = "Documents folder"
        expected_exts = {".doc", ".docx", ".pdf", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".rtf"}
        unexpected_exts = {".py", ".js", ".exe", ".mp3", ".mp4", ".jpg"}
    
    # SPECIAL CASE: Mixed folder - but first check if it's actually a PROJECT
    # Projects have many file types that BELONG together!
    if folder_type == "Mixed folder":
        unique_extensions = len(extensions)
        
        # ===========================================
        # FIRST: Check if this looks like a PROJECT
        # ===========================================
        
        # Project-related extensions (code + config + assets that go together)
        project_exts = {".js", ".ts", ".jsx", ".tsx", ".py", ".html", ".htm", ".css", ".scss", ".less",
                       ".json", ".yaml", ".yml", ".xml", ".md", ".txt", ".gitignore", ".env",
                       ".svg", ".ico", ".png", ".jpg", ".gif", ".webp",  # Icons/assets for apps
                       ".sh", ".bat", ".cmd", ".ps1", ".exe", ".dll",  # Scripts & compiled
                       ".lock", ".config", ".rc", ".ini", ".cfg", ".toml",
                       ".example", ".sample", ".template", ".dist",  # Config templates
                       ".editorconfig", ".prettierrc", ".eslintrc", ".babelrc",  # Dev configs
                       ".dockerignore", ".nvmrc", ".python-version"}  # More dev files
        
        # Media/personal files that usually DON'T belong in projects
        personal_media_exts = {".mp3", ".wav", ".flac", ".m4a", ".ogg", ".aac", ".wma",  # Music
                              ".mp4", ".avi", ".mkv", ".mov", ".wmv", ".webm", ".flv",  # Videos
                              ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",  # Office docs
                              ".psd", ".ai", ".sketch",  # Design files
                              ".msi", ".dmg", ".deb", ".rpm",  # Installers (but NOT .exe - used in projects)
                              ".rar", ".zip", ".7z", ".tar", ".gz"}  # Archives
        
        # Count project vs personal files
        project_file_count = 0
        personal_file_count = 0
        
        for ext, count in extensions.items():
            ext_lower = ext.lower()
            if ext_lower in project_exts:
                project_file_count += count
            elif ext_lower in personal_media_exts:
                personal_file_count += count
        
        # Check for project indicators
        has_code = any(extensions.get(e, 0) > 0 for e in [".js", ".ts", ".py", ".html", ".css", ".java", ".cpp", ".go", ".rs", ".php"])
        has_config = any(extensions.get(e, 0) > 0 for e in [".json", ".yaml", ".yml", ".xml", ".toml", ".ini", ".env"])
        has_project_structure = has_code and has_config
        
        # If mostly project files (>70%) OR has code+config, treat as PROJECT
        project_ratio = project_file_count / max(total, 1)
        
        if has_project_structure or project_ratio > 0.7:
            # This is likely a PROJECT - only flag truly unrelated files
            folder_type = "Software Project (multi-language)"
            expected_exts = project_exts
            unexpected_exts = personal_media_exts
            
            # Find only the personal/media files that don't belong
            unrelated_files = []
            for f in all_files:
                ext = f.get("ext", "").lower()
                name = f.get("name", "").lower()
                
                # Skip common project files
                if name in [".gitignore", "license", "readme.md", ".env", "dockerfile", "makefile"]:
                    continue
                
                if ext in personal_media_exts:
                    unrelated_files.append({
                        **f,
                        "reason": f"Personal/media file ({ext}) in a software project",
                        "status": "rule_flagged",
                    })
            
            unrelated_count = len(unrelated_files)
            definite_count = unrelated_count
            
            if unrelated_count == 0:
                should_separate = "NO"
                confidence = "HIGH"
                reason = "✅ This is a software project - all files belong together!"
                recommendation = f"🛡️ PROTECTED: This folder contains {total} files across multiple languages/types, but they're all project-related."
            elif unrelated_count >= 10:
                should_separate = "YES"
                confidence = "HIGH"
                reason = f"⚠️ Project folder has {unrelated_count} personal/media files mixed in."
                recommendation = f"🧹 Clean up {unrelated_count} files that don't belong in this project."
            else:
                should_separate = "MAYBE"
                confidence = "MEDIUM"
                reason = f"🤔 Found {unrelated_count} files that might not belong in this project."
                recommendation = f"👀 Review the {unrelated_count} flagged files - they look like personal files."
            
            return {
                **context,
                "ai_available": False,
                "analysis_type": "Smart Rules (Local Analysis)",
                "folder_type": folder_type,
                "purpose": f"Software project with {project_file_count} code/config files",
                "should_separate": should_separate,
                "confidence": confidence,
                "reason": reason,
                "recommendation": recommendation,
                "unrelated_files": unrelated_files,
                "unrelated_count": unrelated_count,
                "definite_unrelated_count": definite_count,
                "is_project": True,
            }
        
        # ===========================================
        # NOT a project - check if it's truly MESSY
        # ===========================================
        
        # Count files by category
        categories = {
            "🖼️ Images": sum(extensions.get(e, 0) for e in [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".ico", ".svg", ".tiff", ".raw", ".heic", ".psd"]),
            "🎵 Audio": sum(extensions.get(e, 0) for e in [".mp3", ".wav", ".flac", ".m4a", ".ogg", ".aac", ".wma"]),
            "🎬 Video": sum(extensions.get(e, 0) for e in [".mp4", ".avi", ".mkv", ".mov", ".wmv", ".webm", ".flv"]),
            "📄 Documents": sum(extensions.get(e, 0) for e in [".doc", ".docx", ".pdf", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".rtf", ".odt"]),
            "💻 Code": sum(extensions.get(e, 0) for e in [".py", ".js", ".ts", ".html", ".css", ".java", ".cpp", ".c", ".h", ".cs", ".php", ".rb", ".go", ".rs"]),
            "📦 Archives": sum(extensions.get(e, 0) for e in [".zip", ".rar", ".7z", ".tar", ".gz"]),
            "⚙️ Executables": sum(extensions.get(e, 0) for e in [".exe", ".msi", ".bat", ".sh", ".cmd"]),
        }
        
        # Count how many categories have SIGNIFICANT files (not just 1-2)
        active_categories = {k: v for k, v in categories.items() if v >= 5}
        
        # Only flag as messy if there are multiple UNRELATED categories with many files each
        # AND personal files make up a significant portion
        personal_ratio = personal_file_count / max(total, 1)
        
        if len(active_categories) >= 3 and personal_ratio > 0.5:
            # This is a messy mixed folder - suggest organizing by type
            
            # Build categorized file list for display
            categorized_files = []
            for f in all_files:
                ext = f.get("ext", "").lower()
                category = "📁 Other"
                
                if ext in [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".ico", ".svg", ".tiff", ".raw", ".heic", ".psd"]:
                    category = "🖼️ Images"
                elif ext in [".mp3", ".wav", ".flac", ".m4a", ".ogg", ".aac", ".wma"]:
                    category = "🎵 Audio"
                elif ext in [".mp4", ".avi", ".mkv", ".mov", ".wmv", ".webm", ".flv"]:
                    category = "🎬 Video"
                elif ext in [".doc", ".docx", ".pdf", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".rtf", ".odt"]:
                    category = "📄 Documents"
                elif ext in [".py", ".js", ".ts", ".html", ".css", ".java", ".cpp", ".c", ".h", ".cs", ".php", ".rb", ".go", ".rs"]:
                    category = "💻 Code"
                elif ext in [".zip", ".rar", ".7z", ".tar", ".gz"]:
                    category = "📦 Archives"
                elif ext in [".exe", ".msi", ".bat", ".sh", ".cmd"]:
                    category = "⚙️ Executables"
                
                categorized_files.append({
                    **f,
                    "category": category,
                    "reason": f"Can be organized into {category} folder",
                    "status": "organize_by_type",
                })
            
            # Build category summary
            category_summary = "\n".join([f"   {cat}: {count} files" for cat, count in sorted(active_categories.items(), key=lambda x: -x[1])])
            
            return {
                **context,
                "ai_available": False,
                "analysis_type": "Smart Rules (Local Analysis)",
                "folder_type": "Mixed folder (needs organization)",
                "purpose": "This folder contains many different types of files mixed together",
                "should_separate": "YES",
                "confidence": "HIGH",
                "reason": f"⚠️ This folder has {total} files across {len(active_categories)} different categories:\n{category_summary}",
                "recommendation": f"🧹 This folder is MESSY! It has {unique_extensions} different file types. Consider organizing by category (Images, Music, Documents, etc.)",
                "unrelated_files": [],  # Not unrelated, just needs organizing
                "unrelated_count": 0,
                "categories": active_categories,
                "all_categorized": categorized_files,
                "is_mixed_folder": True,
            }
    
    # Find unrelated files
    unrelated_files = []
    for f in all_files:
        ext = f.get("ext", "").lower()
        name = f.get("name", "").lower()
        
        # Skip common project files (these are ALWAYS expected)
        common_project_files = {
            ".gitignore", ".gitattributes", ".gitmodules",
            "license", "license.md", "license.txt",
            "readme", "readme.md", "readme.txt", "readme.rst",
            ".env", ".env.example", ".env.sample", ".env.local", ".env.development", ".env.production",
            "dockerfile", "docker-compose.yml", "docker-compose.yaml",
            "makefile", "cmakelists.txt",
            ".editorconfig", ".prettierrc", ".eslintrc", ".eslintrc.json", ".eslintrc.js",
            ".babelrc", ".browserslistrc", ".nvmrc", ".python-version", ".ruby-version",
            "package-lock.json", "yarn.lock", "poetry.lock", "pipfile.lock",
            "requirements.txt", "requirements-dev.txt", "setup.py", "setup.cfg",
            "pyproject.toml", "tox.ini", "pytest.ini", ".coveragerc",
            "tsconfig.json", "jsconfig.json", "webpack.config.js", "vite.config.js",
            "manifest.json", "package.json", "composer.json", "cargo.toml",
            ".pre-commit-config.yaml", ".travis.yml", ".gitlab-ci.yml", "jenkinsfile",
            "contributing.md", "changelog.md", "history.md", "authors.md",
        }
        if name in common_project_files:
            continue
        
        # Also skip files with common project suffixes
        if any(name.endswith(suffix) for suffix in ['.example', '.sample', '.template', '.dist', '.local']):
            continue
        
        if ext in unexpected_exts:
            unrelated_files.append({
                **f,
                "reason": f"{ext} files don't belong in {folder_type}",
                "status": "rule_flagged",
            })
        elif expected_exts and ext and ext not in expected_exts:
            # Only flag if we have clear expectations
            if len(expected_exts) > 3:  # We're confident about the folder type
                unrelated_files.append({
                    **f,
                    "reason": f"{ext} is unusual for {folder_type}",
                    "status": "possibly_unrelated",
                })
    
    # Determine if separation is needed
    # Be CONSERVATIVE - only suggest separation if there are MANY unrelated files
    # This protects working projects from accidental changes
    
    unrelated_count = len(unrelated_files)
    unrelated_ratio = unrelated_count / max(total, 1)
    
    # Count truly problematic files (not just "possibly" unrelated)
    definite_unrelated = [f for f in unrelated_files if f.get("status") == "rule_flagged"]
    definite_count = len(definite_unrelated)
    
    if unrelated_count == 0:
        should_separate = "NO"
        confidence = "HIGH"
        reason = "✅ Folder clean - all files belong to this project."
    
    elif definite_count >= 10 or (definite_count >= 5 and unrelated_ratio > 0.2):
        # Many definite mismatches - recommend separation
        should_separate = "YES"
        confidence = "HIGH"
        reason = f"⚠️ Found {definite_count} files that clearly don't belong (e.g., media files in code project)."
    
    elif definite_count >= 3:
        # Some mismatches but not too many
        should_separate = "MAYBE"
        confidence = "MEDIUM"
        reason = f"🤔 Found {definite_count} files that might not belong. Review the list."
    
    elif unrelated_count > 0 and unrelated_count <= 3:
        # Very few questionable files - probably fine
        should_separate = "NO"
        confidence = "MEDIUM"
        reason = f"✅ Only {unrelated_count} slightly unusual files - probably OK to keep."
    
    else:
        # Edge cases
        should_separate = "MAYBE"
        confidence = "LOW"
        reason = f"🤔 Found {unrelated_count} possibly unrelated files. Manual review recommended."
    
    # Build smart recommendation
    if should_separate == "NO":
        recommendation = f"🛡️ This {folder_type} looks clean. No action needed - your project is safe."
    elif should_separate == "YES":
        recommendation = f"🧹 This {folder_type} has {definite_count} files that don't belong. Separating them will clean up your project without touching important files."
    else:  # MAYBE
        recommendation = f"👀 Review the {unrelated_count} flagged files below. Some might be intentional, some might be junk."
    
    return {
        **context,
        "ai_available": False,
        "analysis_type": "Smart Rules (Local Analysis)",
        "folder_type": folder_type,
        "purpose": f"{folder_type} detected from file patterns",
        "should_separate": should_separate,
        "confidence": confidence,
        "reason": reason,
        "recommendation": recommendation,
        "unrelated_files": unrelated_files,
        "unrelated_count": unrelated_count,
        "definite_unrelated_count": definite_count,
    }


def ai_analyze_folder(folder_path: str, progress_cb=None) -> dict:
    """
    Analyze folder - uses AI if available, otherwise smart rules.
    """
    if progress_cb:
        progress_cb("Gathering folder information...")
    
    context = gather_deep_context(folder_path, progress_cb)
    if "error" in context:
        return context
    
    # Try AI first, fall back to rules
    if not DEEPSEEK_API_KEY:
        if progress_cb:
            progress_cb("Using smart rules (no API key)...")
        return smart_rule_analysis(context)
    
    if progress_cb:
        progress_cb("AI is analyzing the folder...")
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
        
        # Build comprehensive prompt
        structure_text = "\n".join(context["structure"][:30])
        extensions_text = ", ".join([f"{ext}: {count}" for ext, count in 
                                     sorted(context["extensions"].items(), key=lambda x: -x[1])[:15]])
        
        # Include file contents
        contents_text = ""
        for filename, content in list(context["context_contents"].items())[:5]:
            contents_text += f"\n--- {filename} ---\n{content[:800]}\n"
        
        # Sample of all files
        files_sample = "\n".join([f["rel_path"] for f in context["all_files"][:40]])
        
        prompt = f"""You are an expert file organizer. Analyze this folder deeply and make a decision.

FOLDER: {context['folder_name']}
PATH: {context['folder_path']}
TOTAL FILES: {context['total_files']}
SIZE: {context['total_size'] / (1024*1024):.1f} MB

EXTENSIONS: {extensions_text}

STRUCTURE:
{structure_text}

FILE CONTENTS:
{contents_text}

ALL FILES (sample):
{files_sample}

Based on ALL this information, answer these questions:

1. WHAT IS THIS FOLDER? (e.g., "Python web project", "Personal photo collection", "Browser extension", "Mixed junk folder")

2. SHOULD FILES BE SEPARATED? Answer one of:
   - "YES" - there are clearly files that don't belong
   - "NO" - all files seem to belong together
   - "MAYBE" - some files are questionable

3. IF YES, which specific files don't belong and why?

4. CONFIDENCE LEVEL: HIGH / MEDIUM / LOW

Reply ONLY in this JSON format:
{{
    "folder_type": "description of what this folder is",
    "purpose": "the main purpose of this folder",
    "should_separate": "YES/NO/MAYBE",
    "confidence": "HIGH/MEDIUM/LOW",
    "reason": "explanation of your decision",
    "unrelated_files": [
        {{"file": "path/to/file.ext", "reason": "why it doesn't belong"}},
        ...
    ],
    "recommendation": "what the user should do"
}}"""

        if progress_cb:
            progress_cb("Waiting for AI response...")
        
        resp = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        
        text = (resp.choices[0].message.content or "").strip()
        
        # Extract JSON
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        
        ai_result = json.loads(text)
        
        # Merge with context
        result = {
            **context,
            "ai_available": True,
            "folder_type": ai_result.get("folder_type", "Unknown"),
            "purpose": ai_result.get("purpose", "Unknown"),
            "should_separate": ai_result.get("should_separate", "MAYBE"),
            "confidence": ai_result.get("confidence", "LOW"),
            "reason": ai_result.get("reason", ""),
            "recommendation": ai_result.get("recommendation", ""),
            "ai_unrelated_files": ai_result.get("unrelated_files", []),
        }
        
        # Match AI suggestions with actual file info
        unrelated_with_info = []
        for ai_file in result["ai_unrelated_files"]:
            file_path = ai_file.get("file", "")
            # Find in all_files
            for f in context["all_files"]:
                if f["rel_path"] == file_path or f["name"] == file_path or file_path in f["rel_path"]:
                    unrelated_with_info.append({
                        **f,
                        "reason": ai_file.get("reason", "AI flagged as unrelated"),
                        "status": "ai_flagged",
                    })
                    break
        
        result["unrelated_files"] = unrelated_with_info
        result["unrelated_count"] = len(unrelated_with_info)
        
        return result
        
    except Exception as e:
        # AI failed - fall back to smart rules
        if progress_cb:
            progress_cb("AI failed, using smart rules...")
        
        result = smart_rule_analysis(context)
        result["ai_error"] = str(e)
        result["analysis_type"] = "Smart Rules (AI unavailable)"
        return result


def format_ai_analysis(result: dict) -> str:
    """Format AI analysis result for display."""
    lines = []
    
    analysis_type = result.get("analysis_type", "AI Analysis")
    
    if result.get("ai_available") and not result.get("ai_error"):
        lines.append("=" * 60)
        lines.append("🤖 AI DEEP ANALYSIS")
        lines.append("=" * 60)
    else:
        lines.append("=" * 60)
        lines.append("🧠 SMART ANALYSIS (Rule-Based)")
        lines.append("=" * 60)
        
        if result.get("ai_error"):
            lines.append(f"\n⚠️ Note: AI unavailable - {result.get('ai_error', '')[:50]}...")
            lines.append("📋 Using smart pattern-based analysis instead.\n")
    
    lines.append(f"\n📁 Folder: {result.get('folder_name', '')}")
    lines.append(f"📍 Path: {result.get('folder_path', '')}")
    lines.append(f"📊 Total files: {result.get('total_files', 0)}")
    
    lines.append(f"\n{'─' * 50}")
    lines.append("🎯 FOLDER ANALYSIS")
    lines.append(f"{'─' * 50}")
    
    folder_type = result.get('folder_type', 'Unknown')
    lines.append(f"\n🏷️ Detected Type: {folder_type}")
    
    # Show if it's a protected project type
    protected_types = ["Python project", "JavaScript/Node.js project", "Browser extension", "Web project"]
    if folder_type in protected_types:
        lines.append(f"🛡️ STATUS: This is a PROTECTED PROJECT - scripts/code will NOT be touched!")
    
    should_sep = result.get("should_separate", "MAYBE")
    if should_sep == "YES":
        sep_icon = "✅ YES"
        sep_color = "Files need to be separated"
    elif should_sep == "NO":
        sep_icon = "❌ NO"
        sep_color = "All files belong together"
    else:
        sep_icon = "⚠️ MAYBE"
        sep_color = "Some files are questionable"
    
    lines.append(f"\n{'─' * 50}")
    lines.append("📋 AI DECISION")
    lines.append(f"{'─' * 50}")
    lines.append(f"\n🔍 Should Separate: {sep_icon}")
    lines.append(f"📊 Confidence: {result.get('confidence', 'LOW')}")
    lines.append(f"\n💭 Reason: {result.get('reason', '')}")
    lines.append(f"\n💡 Recommendation: {result.get('recommendation', '')}")
    
    # Check if this is a mixed folder that needs organizing by category
    if result.get("is_mixed_folder"):
        categories = result.get("categories", {})
        lines.append(f"\n{'─' * 50}")
        lines.append("📊 FILE BREAKDOWN BY CATEGORY")
        lines.append(f"{'─' * 50}")
        
        for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
            percentage = (count / result.get("total_files", 1)) * 100
            bar_len = int(percentage / 5)  # 20 chars max
            bar = "█" * bar_len + "░" * (20 - bar_len)
            lines.append(f"\n{cat}")
            lines.append(f"   {bar} {count} files ({percentage:.1f}%)")
        
        lines.append(f"\n{'─' * 50}")
        lines.append("💡 SUGGESTED ACTION")
        lines.append(f"{'─' * 50}")
        lines.append("\n   Click '📁 Move Mismatched' to organize files into category folders!")
        lines.append("   Files will be moved to: Images/, Audio/, Video/, Documents/, etc.")
    
    else:
        unrelated = result.get("unrelated_files", [])
        if unrelated:
            # Separate definite from possible
            definite = [f for f in unrelated if f.get("status") == "rule_flagged"]
            possible = [f for f in unrelated if f.get("status") != "rule_flagged"]
            
            lines.append(f"\n{'─' * 50}")
            lines.append(f"📋 FLAGGED FILES ({len(unrelated)} total)")
            lines.append(f"{'─' * 50}")
            
            if definite:
                lines.append(f"\n🚫 DEFINITELY DON'T BELONG ({len(definite)}):")
                for f in definite[:20]:
                    lines.append(f"   ❌ {f.get('rel_path', f.get('name', ''))}")
                    lines.append(f"      └─ {f.get('reason', '')}")
            
            if possible:
                lines.append(f"\n❓ POSSIBLY UNRELATED ({len(possible)}):")
                for f in possible[:10]:
                    lines.append(f"   ⚠️ {f.get('rel_path', f.get('name', ''))}")
                    lines.append(f"      └─ {f.get('reason', '')}")
        elif should_sep == "NO":
            lines.append(f"\n{'─' * 50}")
            lines.append("✅ ALL FILES BELONG HERE")
            lines.append(f"{'─' * 50}")
            lines.append("\n  Analysis determined all files are related to this folder's purpose.")
    
    return "\n".join(lines)


def get_ai_cleanup_plan(result: dict, dest_folder: str) -> list:
    """Create cleanup plan from AI analysis."""
    plan = []
    dest_folder = os.path.abspath(dest_folder)
    
    # Handle mixed folder - organize ALL files by category
    if result.get("is_mixed_folder"):
        all_categorized = result.get("all_categorized", [])
        for f in all_categorized:
            src = f.get("path", "")
            if not src or not os.path.isfile(src):
                continue
            
            category = f.get("category", "📁 Other")
            name = f.get("name", os.path.basename(src))
            
            # Map category to folder name
            category_folders = {
                "🖼️ Images": "Images",
                "🎵 Audio": "Audio_Music",
                "🎬 Video": "Videos",
                "📄 Documents": "Documents",
                "💻 Code": "Code_Scripts",
                "📦 Archives": "Archives",
                "⚙️ Executables": "Programs",
                "📁 Other": "Other",
            }
            
            sub = category_folders.get(category, "Other")
            dest = os.path.join(dest_folder, sub, name)
            
            plan.append({
                "src": src,
                "dest": dest,
                "name": name,
                "reason": f"Organizing to {sub}/",
                "size": f.get("size", 0),
            })
        
        return plan
    
    # Regular unrelated files handling
    for f in result.get("unrelated_files", []):
        src = f.get("path", "")
        if not src or not os.path.isfile(src):
            continue
        
        name = f.get("name", os.path.basename(src))
        ext = f.get("ext", "").lower()
        
        # Organize by type
        if ext in [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"]:
            sub = "images"
        elif ext in [".mp3", ".wav", ".flac", ".m4a"]:
            sub = "audio"
        elif ext in [".mp4", ".avi", ".mkv", ".mov"]:
            sub = "videos"
        elif ext in [".doc", ".docx", ".pdf", ".xls", ".xlsx"]:
            sub = "documents"
        elif ext in [".exe", ".msi", ".dll"]:
            sub = "executables"
        else:
            sub = "other"
        
        dest_path = os.path.join(dest_folder, sub, name)
        
        plan.append({
            "src": src,
            "dest": dest_path,
            "reason": f.get("reason", "AI flagged as unrelated"),
            "size": f.get("size", 0),
        })
    
    return plan
