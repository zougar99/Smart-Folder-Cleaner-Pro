# -*- coding: utf-8 -*-
"""
AI PC Organizer - Intelligent full PC analysis and organization.
Scans entire PC, understands file purposes, and organizes everything.
"""
import os
import shutil
import json
import hashlib
import string
import threading
from datetime import datetime, timedelta
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Dict, List, Optional, Tuple
import re

# =============================================================================
# 📁 FILE CATEGORIES - Smart categorization
# =============================================================================

FILE_CATEGORIES = {
    "💻 Programming": {
        "extensions": [".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".cpp", ".c", ".h", 
                      ".cs", ".go", ".rs", ".rb", ".php", ".swift", ".kt", ".scala",
                      ".html", ".css", ".scss", ".sass", ".less", ".vue", ".svelte"],
        "folder_name": "Programming",
        "subcategories": {
            "Python": [".py", ".pyw", ".pyx", ".pyi"],
            "JavaScript": [".js", ".jsx", ".mjs", ".cjs"],
            "TypeScript": [".ts", ".tsx"],
            "Web": [".html", ".htm", ".css", ".scss"],
            "Java": [".java", ".jar", ".class"],
            "C_CPP": [".c", ".cpp", ".h", ".hpp", ".cc"],
            "CSharp": [".cs"],
            "Other": []
        }
    },
    "📄 Documents": {
        "extensions": [".doc", ".docx", ".pdf", ".txt", ".rtf", ".odt", ".xls", ".xlsx",
                      ".ppt", ".pptx", ".ods", ".odp", ".csv", ".md", ".epub", ".mobi"],
        "folder_name": "Documents",
        "subcategories": {
            "Word": [".doc", ".docx", ".odt", ".rtf"],
            "PDF": [".pdf"],
            "Excel": [".xls", ".xlsx", ".ods", ".csv"],
            "PowerPoint": [".ppt", ".pptx", ".odp"],
            "Text": [".txt", ".md"],
            "Ebooks": [".epub", ".mobi"]
        }
    },
    "🖼️ Images": {
        "extensions": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".ico",
                      ".tiff", ".tif", ".raw", ".psd", ".ai", ".eps", ".heic", ".heif"],
        "folder_name": "Images",
        "subcategories": {
            "Photos": [".jpg", ".jpeg", ".png", ".heic", ".heif"],
            "Graphics": [".psd", ".ai", ".svg", ".eps"],
            "Screenshots": [],  # Detected by name
            "Wallpapers": [],   # Detected by size
            "Icons": [".ico"],
            "GIFs": [".gif"]
        }
    },
    "🎵 Music": {
        "extensions": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a", ".opus",
                      ".aiff", ".ape", ".alac"],
        "folder_name": "Music",
        "subcategories": {
            "MP3": [".mp3"],
            "Lossless": [".flac", ".wav", ".aiff", ".ape", ".alac"],
            "Other": [".aac", ".ogg", ".wma", ".m4a", ".opus"]
        }
    },
    "🎬 Videos": {
        "extensions": [".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm", ".m4v",
                      ".mpeg", ".mpg", ".3gp", ".vob"],
        "folder_name": "Videos",
        "subcategories": {
            "Movies": [],       # Detected by size/name
            "TV_Shows": [],     # Detected by name pattern
            "Clips": [],        # Smaller videos
            "Recordings": []    # Screen recordings
        }
    },
    "📦 Archives": {
        "extensions": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".iso",
                      ".dmg", ".cab"],
        "folder_name": "Archives",
        "subcategories": {
            "Compressed": [".zip", ".rar", ".7z", ".tar", ".gz"],
            "Disk_Images": [".iso", ".dmg"],
            "Installers": []  # Detected by name
        }
    },
    "⚙️ Applications": {
        "extensions": [".exe", ".msi", ".app", ".apk", ".deb", ".rpm", ".appimage"],
        "folder_name": "Applications",
        "subcategories": {
            "Installers": [".msi", ".exe"],  # If in Downloads
            "Portable": [],
            "Games": []
        }
    },
    "🎮 Games": {
        "extensions": [".sav", ".rom", ".nes", ".snes", ".gba", ".nds", ".3ds", ".cia"],
        "folder_name": "Games",
        "subcategories": {
            "Saves": [".sav"],
            "ROMs": [".rom", ".nes", ".snes", ".gba", ".nds"]
        }
    },
    "📊 Data": {
        "extensions": [".json", ".xml", ".yaml", ".yml", ".toml", ".ini", ".cfg",
                      ".sqlite", ".db", ".sql", ".log"],
        "folder_name": "Data",
        "subcategories": {
            "Databases": [".sqlite", ".db", ".sql"],
            "Config": [".json", ".xml", ".yaml", ".yml", ".toml", ".ini", ".cfg"],
            "Logs": [".log"]
        }
    },
    "🔒 Backups": {
        "extensions": [".bak", ".backup", ".old", ".orig"],
        "folder_name": "Backups",
        "subcategories": {}
    },
    "📁 Projects": {
        "extensions": [],  # Detected by structure
        "folder_name": "Projects",
        "subcategories": {
            "Python_Projects": [],
            "Web_Projects": [],
            "Other_Projects": []
        }
    }
}

# Folders that should NEVER be touched
PROTECTED_FOLDERS = [
    "Windows", "Program Files", "Program Files (x86)", "ProgramData",
    "$Recycle.Bin", "System Volume Information", "Recovery",
    "AppData", "Application Data", "Local Settings",
    ".git", ".svn", ".hg", "node_modules", "__pycache__",
    ".venv", "venv", "env", ".env",
    "Documents", "Desktop", "Downloads", "Pictures", "Music", "Videos"  # User folders - organize inside them
]

# =============================================================================
# 🧠 SMART NAME PATTERNS - Understanding file/folder names
# =============================================================================

NAME_PATTERNS = {
    # Programming/Development
    "programming": {
        "keywords": ["src", "source", "code", "dev", "lib", "libs", "api", "sdk", 
                    "backend", "frontend", "server", "client", "app", "core",
                    "module", "modules", "component", "components", "utils", "util",
                    "helper", "helpers", "service", "services", "controller",
                    "model", "models", "view", "views", "test", "tests", "spec",
                    "build", "dist", "bin", "out", "target", "release", "debug"],
        "patterns": [r"v\d+", r"ver\d+", r"version", r"_dev$", r"_prod$"],
        "category": "💻 Programming"
    },
    
    # Documents
    "documents": {
        "keywords": ["document", "documents", "docs", "doc", "report", "reports",
                    "paper", "papers", "thesis", "essay", "letter", "letters",
                    "resume", "cv", "invoice", "invoices", "contract", "contracts",
                    "manual", "guide", "tutorial", "note", "notes", "memo",
                    "presentation", "slides", "homework", "assignment", "work"],
        "patterns": [r"20\d{2}", r"q[1-4]", r"final", r"draft"],
        "category": "📄 Documents"
    },
    
    # Images/Photos
    "images": {
        "keywords": ["image", "images", "photo", "photos", "picture", "pictures",
                    "pic", "pics", "img", "screenshot", "screenshots", "screen",
                    "wallpaper", "wallpapers", "background", "backgrounds",
                    "icon", "icons", "logo", "logos", "banner", "banners",
                    "avatar", "profile", "gallery", "album", "camera", "dcim",
                    "graphic", "graphics", "design", "artwork", "art"],
        "patterns": [r"img_?\d+", r"dsc_?\d+", r"screenshot", r"capture"],
        "category": "🖼️ Images"
    },
    
    # Music/Audio
    "music": {
        "keywords": ["music", "musique", "song", "songs", "audio", "sound", "sounds",
                    "track", "tracks", "album", "albums", "artist", "playlist",
                    "podcast", "podcasts", "radio", "recording", "recordings",
                    "beat", "beats", "instrumental", "vocal", "mix", "remix"],
        "patterns": [r"track_?\d+", r"song_?\d+", r"\d+\s*-\s*"],
        "category": "🎵 Music"
    },
    
    # Videos
    "videos": {
        "keywords": ["video", "videos", "movie", "movies", "film", "films",
                    "clip", "clips", "episode", "episodes", "series", "season",
                    "trailer", "trailers", "recording", "recordings", "stream",
                    "youtube", "tutorial", "course", "lesson", "webinar",
                    "anime", "cartoon", "documentary", "show", "tv"],
        "patterns": [r"s\d{1,2}e\d{1,2}", r"episode_?\d+", r"ep_?\d+", 
                    r"1080p", r"720p", r"4k", r"hd", r"bluray", r"webrip"],
        "category": "🎬 Videos"
    },
    
    # Games
    "games": {
        "keywords": ["game", "games", "gaming", "save", "saves", "savegame",
                    "mod", "mods", "addon", "addons", "dlc", "crack", "trainer",
                    "rom", "roms", "emulator", "iso", "steam", "origin", "epic",
                    "minecraft", "gta", "fortnite", "valorant", "league"],
        "patterns": [r"save_?\d+", r"slot_?\d+"],
        "category": "🎮 Games"
    },
    
    # Downloads
    "downloads": {
        "keywords": ["download", "downloads", "downloaded", "torrent", "torrents",
                    "temp", "temporary", "cache", "new", "incoming"],
        "patterns": [],
        "category": "📥 Downloads"
    },
    
    # Backups
    "backups": {
        "keywords": ["backup", "backups", "bak", "old", "archive", "archives",
                    "copy", "copies", "duplicate", "restore", "recovery"],
        "patterns": [r"backup_?\d+", r"_old$", r"_bak$", r"\(\d+\)$"],
        "category": "🔒 Backups"
    },
    
    # Work/Office
    "work": {
        "keywords": ["work", "office", "job", "business", "company", "corporate",
                    "meeting", "meetings", "project", "projects", "client", "clients",
                    "finance", "accounting", "hr", "marketing", "sales", "legal"],
        "patterns": [r"20\d{2}", r"q[1-4]_?\d{4}"],
        "category": "💼 Work"
    },
    
    # Personal
    "personal": {
        "keywords": ["personal", "private", "family", "vacation", "holiday", "trip",
                    "birthday", "wedding", "party", "event", "memories", "diary",
                    "journal", "blog", "hobby", "hobbies"],
        "patterns": [],
        "category": "👤 Personal"
    },
    
    # Education/Learning
    "education": {
        "keywords": ["school", "university", "college", "course", "courses",
                    "class", "classes", "lecture", "lectures", "study", "studies",
                    "learn", "learning", "education", "academic", "semester",
                    "exam", "exams", "homework", "assignment", "book", "books",
                    "ebook", "ebooks", "pdf", "textbook"],
        "patterns": [r"chapter_?\d+", r"lesson_?\d+", r"week_?\d+"],
        "category": "📚 Education"
    },
    
    # System/Config
    "system": {
        "keywords": ["system", "config", "configuration", "settings", "preferences",
                    "cache", "temp", "temporary", "log", "logs", "data", "appdata",
                    "local", "roaming", "programdata"],
        "patterns": [],
        "category": "⚙️ System"
    }
}

# Folder name patterns that indicate specific purposes
FOLDER_PURPOSE_PATTERNS = {
    # Project indicators
    "project": {
        "indicators": ["src", "source", "lib", "bin", "build", "dist", "node_modules",
                      ".git", ".vscode", ".idea", "__pycache__", "venv", ".env"],
        "files": ["package.json", "requirements.txt", "setup.py", "Cargo.toml",
                 "pom.xml", "build.gradle", "Makefile", "CMakeLists.txt",
                 "README.md", "README.txt", ".gitignore"]
    },
    
    # Asset folders in projects
    "assets": {
        "indicators": ["assets", "resources", "res", "static", "public", "media",
                      "images", "img", "icons", "fonts", "css", "js", "styles"]
    },
    
    # Test folders
    "tests": {
        "indicators": ["test", "tests", "spec", "specs", "__tests__", "testing",
                      "unittest", "pytest", "jest"]
    }
}


# =============================================================================
# 🔍 SMART FILE ANALYZER
# =============================================================================

class SmartFileAnalyzer:
    """Analyzes files and determines their true category using names AND extensions."""
    
    def __init__(self):
        self._ext_to_category = {}
        self._build_extension_map()
        self._compiled_patterns = {}
        self._compile_name_patterns()
    
    def _build_extension_map(self):
        """Build extension to category mapping."""
        for category, info in FILE_CATEGORIES.items():
            for ext in info["extensions"]:
                self._ext_to_category[ext.lower()] = category
    
    def _compile_name_patterns(self):
        """Pre-compile regex patterns for performance."""
        for category, info in NAME_PATTERNS.items():
            self._compiled_patterns[category] = [
                re.compile(p, re.IGNORECASE) for p in info.get("patterns", [])
            ]
    
    def analyze_file(self, filepath: str) -> Dict:
        """
        Analyze a single file and determine its category.
        Uses BOTH extension AND name analysis for smart categorization.
        
        Returns:
            {
                'path': str,
                'name': str,
                'ext': str,
                'size': int,
                'category': str,
                'subcategory': str,
                'confidence': float,
                'suggested_location': str,
                'name_hints': list,  # What the name suggests
                'folder_context': str,  # What parent folder suggests
                'is_temp': bool,
                'is_old': bool
            }
        """
        try:
            stat = os.stat(filepath)
            filename = os.path.basename(filepath)
            name, ext = os.path.splitext(filename)
            ext = ext.lower()
            size = stat.st_size
            mtime = datetime.fromtimestamp(stat.st_mtime)
            parent_folder = os.path.basename(os.path.dirname(filepath))
            
            # Get extension-based category
            ext_category = self._ext_to_category.get(ext, "❓ Other")
            
            # Analyze name for hints
            name_hints = self._analyze_name(filename, parent_folder)
            name_category = name_hints.get('suggested_category')
            
            # Analyze folder context
            folder_context = self._analyze_folder_context(filepath)
            
            # Smart category decision: combine extension + name + folder
            category, confidence = self._smart_categorize(
                ext_category, name_category, folder_context, ext, filename, size
            )
            
            subcategory = self._determine_subcategory(filepath, filename, ext, size, category)
            
            # Check special conditions
            is_temp = self._is_temp_file(filename, filepath)
            is_old = (datetime.now() - mtime) > timedelta(days=365)
            
            # Determine suggested location based on all analysis
            suggested = self._suggest_smart_location(
                category, subcategory, filename, name_hints, folder_context
            )
            
            return {
                'path': filepath,
                'name': filename,
                'ext': ext,
                'size': size,
                'mtime': mtime.isoformat(),
                'category': category,
                'subcategory': subcategory,
                'confidence': confidence,
                'suggested_location': suggested,
                'name_hints': name_hints.get('keywords_found', []),
                'folder_context': folder_context,
                'is_temp': is_temp,
                'is_old': is_old
            }
        except Exception as e:
            return {
                'path': filepath,
                'error': str(e)
            }
    
    def _analyze_name(self, filename: str, parent_folder: str) -> Dict:
        """
        Analyze filename and parent folder to understand purpose.
        
        Returns hints about what the file might be.
        """
        result = {
            'keywords_found': [],
            'patterns_matched': [],
            'suggested_category': None,
            'confidence': 0.0
        }
        
        # Combine filename and parent folder for analysis
        name_lower = filename.lower()
        folder_lower = parent_folder.lower()
        combined = f"{folder_lower} {name_lower}"
        
        best_match = None
        best_score = 0
        
        for cat_key, cat_info in NAME_PATTERNS.items():
            score = 0
            keywords_found = []
            patterns_found = []
            
            # Check keywords
            for keyword in cat_info.get("keywords", []):
                if keyword in combined:
                    score += 2
                    keywords_found.append(keyword)
            
            # Check patterns
            for pattern in self._compiled_patterns.get(cat_key, []):
                if pattern.search(combined):
                    score += 1
                    patterns_found.append(pattern.pattern)
            
            if score > best_score:
                best_score = score
                best_match = cat_info.get("category")
                result['keywords_found'] = keywords_found
                result['patterns_matched'] = patterns_found
        
        if best_score >= 2:  # At least one keyword match
            result['suggested_category'] = best_match
            result['confidence'] = min(1.0, best_score / 5)
        
        return result
    
    def _analyze_folder_context(self, filepath: str) -> str:
        """
        Analyze the folder path to understand context.
        
        Returns the detected context (e.g., "project", "downloads", etc.)
        """
        path_lower = filepath.lower()
        path_parts = path_lower.split(os.sep)
        
        # Check for common folder names in path
        context_hints = []
        
        # Check each part of the path
        for part in path_parts:
            # Project indicators
            if part in FOLDER_PURPOSE_PATTERNS["project"]["indicators"]:
                return "project_folder"
            
            # Asset folders
            if part in FOLDER_PURPOSE_PATTERNS["assets"]["indicators"]:
                return "assets_folder"
            
            # Test folders
            if part in FOLDER_PURPOSE_PATTERNS["tests"]["indicators"]:
                return "test_folder"
            
            # Check NAME_PATTERNS for folder context
            for cat_key, cat_info in NAME_PATTERNS.items():
                if part in cat_info.get("keywords", []):
                    context_hints.append(cat_key)
        
        # Return most common context
        if context_hints:
            return context_hints[0]
        
        return "unknown"
    
    def _smart_categorize(self, ext_category: str, name_category: str, 
                         folder_context: str, ext: str, filename: str, 
                         size: int) -> Tuple[str, float]:
        """
        Smart categorization combining multiple signals.
        
        Returns (category, confidence)
        """
        # If in a project folder, be careful
        if folder_context in ["project_folder", "assets_folder", "test_folder"]:
            # Don't recategorize project files
            return ext_category, 0.9
        
        # If extension and name agree, high confidence
        if ext_category == name_category:
            return ext_category, 0.95
        
        # If name suggests something but extension is "Other", use name
        if ext_category == "❓ Other" and name_category:
            return name_category, 0.7
        
        # If extension is clear but name suggests different, prefer extension
        # unless name confidence is very high
        if ext_category != "❓ Other":
            return ext_category, 0.8
        
        # Fallback to name category or Other
        if name_category:
            return name_category, 0.6
        
        return "❓ Other", 0.3
    
    def _suggest_smart_location(self, category: str, subcategory: str,
                               filename: str, name_hints: Dict,
                               folder_context: str) -> str:
        """
        Suggest a smart location based on all analysis.
        """
        cat_info = FILE_CATEGORIES.get(category, {})
        folder_name = cat_info.get("folder_name", "Other")
        
        # Use name hints to suggest subfolder
        keywords = name_hints.get('keywords_found', [])
        
        # Special cases based on keywords
        if any(k in keywords for k in ['work', 'office', 'business', 'client']):
            return f"{folder_name}/Work"
        
        if any(k in keywords for k in ['personal', 'family', 'vacation', 'trip']):
            return f"{folder_name}/Personal"
        
        if any(k in keywords for k in ['school', 'university', 'course', 'study']):
            return f"{folder_name}/Education"
        
        if any(k in keywords for k in ['backup', 'old', 'archive']):
            return f"Backups/{folder_name}"
        
        if subcategory and subcategory != "Other":
            return f"{folder_name}/{subcategory}"
        
        return folder_name
    
    def _determine_subcategory(self, filepath: str, filename: str, ext: str, 
                               size: int, category: str) -> str:
        """Determine file subcategory based on various signals."""
        filename_lower = filename.lower()
        
        # Images
        if category == "🖼️ Images":
            if "screenshot" in filename_lower or "screen" in filename_lower:
                return "Screenshots"
            if size > 2 * 1024 * 1024:  # > 2MB likely wallpaper
                return "Wallpapers"
            if ext in [".psd", ".ai", ".svg"]:
                return "Graphics"
            return "Photos"
        
        # Videos
        if category == "🎬 Videos":
            if size > 700 * 1024 * 1024:  # > 700MB likely movie
                return "Movies"
            if re.search(r's\d{1,2}e\d{1,2}', filename_lower):  # S01E01 pattern
                return "TV_Shows"
            if "recording" in filename_lower or "capture" in filename_lower:
                return "Recordings"
            return "Clips"
        
        # Archives
        if category == "📦 Archives":
            if ext in [".iso", ".dmg"]:
                return "Disk_Images"
            if "setup" in filename_lower or "install" in filename_lower:
                return "Installers"
            return "Compressed"
        
        # Default: use extension-based subcategory
        cat_info = FILE_CATEGORIES.get(category, {})
        subcats = cat_info.get("subcategories", {})
        
        for subcat, exts in subcats.items():
            if ext in exts:
                return subcat
        
        return "Other"
    
    def _calculate_confidence(self, filepath: str, filename: str, 
                             ext: str, category: str) -> float:
        """Calculate confidence in categorization."""
        confidence = 0.5
        
        # Known extension = higher confidence
        if ext in self._ext_to_category:
            confidence += 0.3
        
        # File in matching folder = higher confidence
        parent = os.path.basename(os.path.dirname(filepath)).lower()
        cat_folder = FILE_CATEGORIES.get(category, {}).get("folder_name", "").lower()
        
        if cat_folder and cat_folder in parent:
            confidence += 0.2
        
        return min(1.0, confidence)
    
    def _is_temp_file(self, filename: str, filepath: str) -> bool:
        """Check if file is temporary."""
        temp_patterns = [
            r'\.tmp$', r'\.temp$', r'~$', r'^~',
            r'\.cache', r'\.log$', r'thumbs\.db',
            r'desktop\.ini', r'\.ds_store'
        ]
        
        filename_lower = filename.lower()
        for pattern in temp_patterns:
            if re.search(pattern, filename_lower):
                return True
        
        # Check if in temp folder
        temp_folders = ['temp', 'tmp', 'cache', 'temporary']
        path_lower = filepath.lower()
        for tf in temp_folders:
            if f"\\{tf}\\" in path_lower or f"/{tf}/" in path_lower:
                return True
        
        return False
    
    def _suggest_location(self, category: str, subcategory: str, filename: str) -> str:
        """Suggest ideal location for file."""
        cat_info = FILE_CATEGORIES.get(category, {})
        folder_name = cat_info.get("folder_name", "Other")
        
        if subcategory and subcategory != "Other":
            return f"{folder_name}/{subcategory}"
        
        return folder_name


# =============================================================================
# 🔄 PROJECT DETECTOR
# =============================================================================

class ProjectDetector:
    """Detects and classifies development projects."""
    
    PROJECT_INDICATORS = {
        "Python": ["requirements.txt", "setup.py", "pyproject.toml", "Pipfile", "main.py"],
        "NodeJS": ["package.json", "node_modules"],
        "Web": ["index.html", "index.htm"],
        "Java": ["pom.xml", "build.gradle"],
        "CSharp": [".csproj", ".sln"],
        "Rust": ["Cargo.toml"],
        "Go": ["go.mod"],
        "Git": [".git"]
    }
    
    def is_project_folder(self, folder_path: str) -> Tuple[bool, str, float]:
        """
        Check if folder is a project.
        
        Returns:
            (is_project, project_type, confidence)
        """
        try:
            files = os.listdir(folder_path)
            files_lower = [f.lower() for f in files]
            
            for proj_type, indicators in self.PROJECT_INDICATORS.items():
                for indicator in indicators:
                    if indicator.lower() in files_lower:
                        # Check for more indicators
                        matches = sum(1 for i in indicators if i.lower() in files_lower)
                        confidence = min(1.0, 0.5 + (matches * 0.15))
                        return True, proj_type, confidence
            
            # Check for code files ratio
            code_exts = {'.py', '.js', '.ts', '.java', '.cpp', '.c', '.cs', '.go', '.rs'}
            code_count = sum(1 for f in files if os.path.splitext(f)[1].lower() in code_exts)
            
            if code_count >= 3:
                return True, "Generic", 0.6
            
            return False, "", 0.0
        except:
            return False, "", 0.0


# =============================================================================
# 📁 SMART FOLDER ANALYZER
# =============================================================================

class SmartFolderAnalyzer:
    """
    Analyzes folder names and contents to understand their purpose.
    """
    
    def __init__(self):
        self.project_detector = ProjectDetector()
    
    def analyze_folder(self, folder_path: str) -> Dict:
        """
        Analyze a folder to understand its purpose.
        
        Returns:
            {
                'path': str,
                'name': str,
                'purpose': str,  # Detected purpose
                'category': str,  # Main category
                'is_project': bool,
                'project_type': str,
                'confidence': float,
                'should_organize': bool,  # Should contents be organized?
                'name_hints': list,
                'file_count': int,
                'dominant_type': str  # Most common file type
            }
        """
        try:
            folder_name = os.path.basename(folder_path)
            
            # Check if it's a project
            is_project, proj_type, proj_conf = self.project_detector.is_project_folder(folder_path)
            
            if is_project:
                return {
                    'path': folder_path,
                    'name': folder_name,
                    'purpose': f"{proj_type} Project",
                    'category': "💻 Programming",
                    'is_project': True,
                    'project_type': proj_type,
                    'confidence': proj_conf,
                    'should_organize': False,  # Don't organize projects!
                    'name_hints': [proj_type.lower(), 'project', 'code'],
                    'protected': True,
                    'reason': f"Detected as {proj_type} project - protected"
                }
            
            # Analyze folder name
            name_analysis = self._analyze_folder_name(folder_name)
            
            # Analyze contents
            content_analysis = self._analyze_contents(folder_path)
            
            # Combine analysis
            purpose, category, confidence = self._determine_purpose(
                name_analysis, content_analysis
            )
            
            # Determine if should organize
            should_organize = self._should_organize(
                purpose, content_analysis, confidence
            )
            
            return {
                'path': folder_path,
                'name': folder_name,
                'purpose': purpose,
                'category': category,
                'is_project': False,
                'project_type': None,
                'confidence': confidence,
                'should_organize': should_organize,
                'name_hints': name_analysis.get('keywords', []),
                'file_count': content_analysis.get('file_count', 0),
                'dominant_type': content_analysis.get('dominant_type', 'Unknown'),
                'is_mixed': content_analysis.get('is_mixed', False),
                'type_breakdown': content_analysis.get('type_breakdown', {})
            }
        except Exception as e:
            return {
                'path': folder_path,
                'name': os.path.basename(folder_path),
                'error': str(e)
            }
    
    def _analyze_folder_name(self, folder_name: str) -> Dict:
        """Analyze folder name for purpose hints."""
        name_lower = folder_name.lower()
        result = {'keywords': [], 'suggested_category': None, 'score': 0}
        
        best_score = 0
        best_category = None
        
        for cat_key, cat_info in NAME_PATTERNS.items():
            score = 0
            keywords_found = []
            
            for keyword in cat_info.get("keywords", []):
                if keyword in name_lower:
                    score += 2
                    keywords_found.append(keyword)
                # Partial match
                elif len(keyword) > 4 and keyword[:4] in name_lower:
                    score += 1
                    keywords_found.append(keyword + "(partial)")
            
            if score > best_score:
                best_score = score
                best_category = cat_info.get("category")
                result['keywords'] = keywords_found
        
        result['suggested_category'] = best_category
        result['score'] = best_score
        
        return result
    
    def _analyze_contents(self, folder_path: str, max_files: int = 100) -> Dict:
        """Analyze folder contents to understand composition."""
        result = {
            'file_count': 0,
            'type_breakdown': defaultdict(int),
            'dominant_type': 'Unknown',
            'is_mixed': False,
            'extensions': defaultdict(int)
        }
        
        try:
            files = os.listdir(folder_path)
            actual_files = [f for f in files if os.path.isfile(os.path.join(folder_path, f))]
            result['file_count'] = len(actual_files)
            
            # Analyze extensions
            ext_to_cat = {}
            for category, info in FILE_CATEGORIES.items():
                for ext in info["extensions"]:
                    ext_to_cat[ext.lower()] = category
            
            for filename in actual_files[:max_files]:
                ext = os.path.splitext(filename)[1].lower()
                result['extensions'][ext] += 1
                
                category = ext_to_cat.get(ext, "❓ Other")
                result['type_breakdown'][category] += 1
            
            # Find dominant type
            if result['type_breakdown']:
                dominant = max(result['type_breakdown'].items(), key=lambda x: x[1])
                result['dominant_type'] = dominant[0]
                
                # Check if mixed (multiple significant categories)
                total = sum(result['type_breakdown'].values())
                significant = [cat for cat, count in result['type_breakdown'].items()
                              if count / total > 0.2 and cat != "❓ Other"]
                result['is_mixed'] = len(significant) > 2
        except:
            pass
        
        return result
    
    def _determine_purpose(self, name_analysis: Dict, 
                          content_analysis: Dict) -> Tuple[str, str, float]:
        """Determine folder purpose from analysis."""
        name_cat = name_analysis.get('suggested_category')
        content_cat = content_analysis.get('dominant_type')
        name_score = name_analysis.get('score', 0)
        
        # If name strongly suggests category
        if name_score >= 4 and name_cat:
            return name_analysis['keywords'][0].title(), name_cat, 0.9
        
        # If content is clear and not mixed
        if not content_analysis.get('is_mixed') and content_cat != "❓ Other":
            purpose = content_cat.replace("🖼️ ", "").replace("🎵 ", "").replace("🎬 ", "")
            return purpose, content_cat, 0.8
        
        # If name gives hints
        if name_cat and name_score >= 2:
            purpose = name_analysis['keywords'][0].title() if name_analysis['keywords'] else "Files"
            return purpose, name_cat, 0.7
        
        # Mixed folder
        if content_analysis.get('is_mixed'):
            return "Mixed Files", "📁 Mixed", 0.5
        
        return "Miscellaneous", "❓ Other", 0.3
    
    def _should_organize(self, purpose: str, content_analysis: Dict, 
                        confidence: float) -> bool:
        """Determine if folder contents should be organized."""
        # Don't organize if low confidence
        if confidence < 0.5:
            return False
        
        # Don't organize if too few files
        if content_analysis.get('file_count', 0) < 5:
            return False
        
        # Organize mixed folders
        if content_analysis.get('is_mixed'):
            return True
        
        # Organize if many different extensions
        if len(content_analysis.get('extensions', {})) > 5:
            return True
        
        return False


# =============================================================================
# 🖥️ PC SCANNER
# =============================================================================

class PCScanner:
    """Scans entire PC or selected drives with smart name analysis."""
    
    def __init__(self, skip_system: bool = True, max_workers: int = 8):
        self.skip_system = skip_system
        self.max_workers = max_workers
        self.file_analyzer = SmartFileAnalyzer()
        self.project_detector = ProjectDetector()
        self.folder_analyzer = SmartFolderAnalyzer()
        self._stop_flag = threading.Event()
    
    def stop(self):
        """Stop scanning."""
        self._stop_flag.set()
    
    def get_drives(self) -> List[str]:
        """Get all available drives."""
        drives = []
        for letter in string.ascii_uppercase:
            drive = f"{letter}:\\"
            if os.path.exists(drive):
                drives.append(drive)
        return drives
    
    def _should_skip_folder(self, folder_path: str, folder_name: str) -> bool:
        """Check if folder should be skipped."""
        if not self.skip_system:
            return False
        
        name_lower = folder_name.lower()
        
        # Skip protected folders
        for protected in PROTECTED_FOLDERS:
            if name_lower == protected.lower():
                return True
        
        # Skip hidden folders
        if folder_name.startswith('.'):
            return True
        
        # Skip system paths
        path_lower = folder_path.lower()
        system_paths = ['windows', 'program files', 'programdata', '$recycle']
        for sp in system_paths:
            if sp in path_lower:
                return True
        
        return False
    
    def scan_location(self, location: str, 
                     progress_cb: Callable = None,
                     max_depth: int = 10) -> Dict:
        """
        Scan a location (drive or folder) with smart name analysis.
        
        Returns comprehensive analysis including folder purposes.
        """
        result = {
            'location': location,
            'timestamp': datetime.now().isoformat(),
            'files': [],
            'projects': [],
            'analyzed_folders': [],  # Folders with detected purposes
            'by_category': defaultdict(list),
            'by_folder_purpose': defaultdict(list),  # Group by folder purpose
            'stats': {
                'total_files': 0,
                'total_size': 0,
                'total_folders': 0,
                'temp_files': 0,
                'old_files': 0,
                'categories': {},
                'folder_purposes': {}  # Count of folder purposes
            },
            'organization_plan': [],
            'cleanup_suggestions': []
        }
        
        if not os.path.exists(location):
            result['error'] = f"Location not found: {location}"
            return result
        
        # Scan all files
        files_to_process = []
        
        for root, dirs, files in os.walk(location):
            if self._stop_flag.is_set():
                break
            
            # Calculate depth
            depth = root[len(location):].count(os.sep)
            if depth > max_depth:
                dirs.clear()
                continue
            
            # Filter directories
            dirs[:] = [d for d in dirs if not self._should_skip_folder(os.path.join(root, d), d)]
            
            result['stats']['total_folders'] += 1
            
            # Analyze folder name and purpose
            folder_analysis = self.folder_analyzer.analyze_folder(root)
            
            # If it's a project, protect it
            if folder_analysis.get('is_project'):
                result['projects'].append({
                    'path': root,
                    'name': folder_analysis.get('name'),
                    'type': folder_analysis.get('project_type'),
                    'confidence': folder_analysis.get('confidence'),
                    'purpose': folder_analysis.get('purpose')
                })
                # Don't scan inside projects
                dirs.clear()
                continue
            
            # Store folder analysis
            if folder_analysis.get('confidence', 0) >= 0.5:
                result['analyzed_folders'].append(folder_analysis)
                purpose = folder_analysis.get('purpose', 'Other')
                
                # Track folder purposes
                if purpose not in result['stats']['folder_purposes']:
                    result['stats']['folder_purposes'][purpose] = 0
                result['stats']['folder_purposes'][purpose] += 1
            
            # Collect files with their folder context
            folder_purpose = folder_analysis.get('purpose', 'Unknown')
            for filename in files:
                filepath = os.path.join(root, filename)
                files_to_process.append((filepath, folder_purpose))
            
            if progress_cb and len(files_to_process) % 500 == 0:
                progress_cb(f"Found {len(files_to_process):,} files...")
        
        # Analyze files in parallel
        if progress_cb:
            progress_cb(f"Analyzing {len(files_to_process):,} files...")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit with folder purpose context
            futures = {}
            for item in files_to_process:
                if isinstance(item, tuple):
                    filepath, folder_purpose = item
                else:
                    filepath, folder_purpose = item, "Unknown"
                
                future = executor.submit(self.file_analyzer.analyze_file, filepath)
                futures[future] = folder_purpose
            
            completed = 0
            for future in as_completed(futures):
                if self._stop_flag.is_set():
                    break
                
                folder_purpose = futures[future]
                file_info = future.result()
                
                if 'error' not in file_info:
                    # Add folder context to file info
                    file_info['folder_purpose'] = folder_purpose
                    
                    result['files'].append(file_info)
                    result['by_category'][file_info['category']].append(file_info)
                    result['by_folder_purpose'][folder_purpose].append(file_info)
                    result['stats']['total_files'] += 1
                    result['stats']['total_size'] += file_info.get('size', 0)
                    
                    if file_info.get('is_temp'):
                        result['stats']['temp_files'] += 1
                    if file_info.get('is_old'):
                        result['stats']['old_files'] += 1
                
                completed += 1
                if progress_cb and completed % 1000 == 0:
                    progress_cb(f"Analyzed {completed:,}/{len(files_to_process):,} files...")
        
        # Calculate category stats
        for category, files in result['by_category'].items():
            cat_size = sum(f.get('size', 0) for f in files)
            result['stats']['categories'][category] = {
                'count': len(files),
                'size': cat_size
            }
        
        # Generate organization plan
        result['organization_plan'] = self._generate_organization_plan(result)
        
        # Generate cleanup suggestions
        result['cleanup_suggestions'] = self._generate_cleanup_suggestions(result)
        
        return result
    
    def _generate_organization_plan(self, scan_result: Dict) -> List[Dict]:
        """Generate plan to organize files."""
        plan = []
        
        for category, files in scan_result['by_category'].items():
            if category == "❓ Other":
                continue
            
            cat_info = FILE_CATEGORIES.get(category, {})
            target_folder = cat_info.get("folder_name", "Other")
            
            # Group by suggested location
            by_location = defaultdict(list)
            for f in files:
                loc = f.get('suggested_location', target_folder)
                by_location[loc].append(f)
            
            for location, loc_files in by_location.items():
                if len(loc_files) >= 3:  # Only if significant number
                    plan.append({
                        'action': 'organize',
                        'category': category,
                        'target_folder': location,
                        'file_count': len(loc_files),
                        'total_size': sum(f.get('size', 0) for f in loc_files),
                        'files': [f['path'] for f in loc_files[:100]],  # Limit to 100
                        'description': f"Move {len(loc_files)} {category} files to {location}/"
                    })
        
        # Sort by file count (most files first)
        plan.sort(key=lambda x: x['file_count'], reverse=True)
        
        return plan
    
    def _generate_cleanup_suggestions(self, scan_result: Dict) -> List[Dict]:
        """Generate cleanup suggestions."""
        suggestions = []
        
        # Temp files
        temp_count = scan_result['stats']['temp_files']
        if temp_count > 10:
            temp_files = [f for f in scan_result['files'] if f.get('is_temp')]
            temp_size = sum(f.get('size', 0) for f in temp_files)
            suggestions.append({
                'type': 'cleanup',
                'reason': 'Temporary files',
                'icon': '🗑️',
                'file_count': temp_count,
                'size': temp_size,
                'files': [f['path'] for f in temp_files[:50]],
                'action': 'delete',
                'description': f"Delete {temp_count} temporary files ({format_size(temp_size)})"
            })
        
        # Old files (> 1 year)
        old_count = scan_result['stats']['old_files']
        if old_count > 20:
            old_files = [f for f in scan_result['files'] if f.get('is_old')]
            old_size = sum(f.get('size', 0) for f in old_files)
            suggestions.append({
                'type': 'review',
                'reason': 'Old files (> 1 year)',
                'icon': '📅',
                'file_count': old_count,
                'size': old_size,
                'action': 'review',
                'description': f"Review {old_count} old files ({format_size(old_size)})"
            })
        
        # Large files
        large_files = [f for f in scan_result['files'] if f.get('size', 0) > 100 * 1024 * 1024]
        if large_files:
            large_size = sum(f.get('size', 0) for f in large_files)
            suggestions.append({
                'type': 'review',
                'reason': 'Large files (> 100MB)',
                'icon': '📦',
                'file_count': len(large_files),
                'size': large_size,
                'files': [f['path'] for f in sorted(large_files, key=lambda x: x.get('size', 0), reverse=True)[:20]],
                'action': 'review',
                'description': f"Review {len(large_files)} large files ({format_size(large_size)})"
            })
        
        return suggestions


# =============================================================================
# 🔧 FILE ORGANIZER
# =============================================================================

class FileOrganizer:
    """Executes organization plans."""
    
    def __init__(self, base_path: str = None):
        self.base_path = base_path or os.path.expanduser("~")
        self.log = []
    
    def execute_plan(self, plan: List[Dict], 
                    dry_run: bool = True,
                    progress_cb: Callable = None) -> Dict:
        """
        Execute organization plan.
        
        Args:
            plan: List of organization actions
            dry_run: If True, only simulate
            progress_cb: Progress callback
        
        Returns:
            Execution result with stats
        """
        result = {
            'dry_run': dry_run,
            'timestamp': datetime.now().isoformat(),
            'actions': [],
            'stats': {
                'total_actions': len(plan),
                'files_moved': 0,
                'files_failed': 0,
                'space_organized': 0
            }
        }
        
        for i, action in enumerate(plan):
            if progress_cb:
                progress_cb(f"Processing {i+1}/{len(plan)}: {action.get('description', 'Unknown')}")
            
            if action.get('action') == 'organize':
                action_result = self._execute_organize(action, dry_run)
            elif action.get('action') == 'delete':
                action_result = self._execute_delete(action, dry_run)
            else:
                action_result = {'status': 'skipped', 'reason': 'Unknown action'}
            
            result['actions'].append({
                **action,
                'result': action_result
            })
            
            if action_result.get('status') == 'success':
                result['stats']['files_moved'] += action_result.get('files_processed', 0)
                result['stats']['space_organized'] += action.get('total_size', 0)
            else:
                result['stats']['files_failed'] += len(action.get('files', []))
        
        return result
    
    def _execute_organize(self, action: Dict, dry_run: bool) -> Dict:
        """Execute organize action."""
        target_folder = action.get('target_folder', 'Organized')
        files = action.get('files', [])
        
        # Create target in base path
        full_target = os.path.join(self.base_path, "Organized", target_folder)
        
        if not dry_run:
            os.makedirs(full_target, exist_ok=True)
        
        moved = 0
        errors = []
        
        for filepath in files:
            try:
                if os.path.exists(filepath):
                    filename = os.path.basename(filepath)
                    dest = os.path.join(full_target, filename)
                    
                    # Handle duplicates
                    if os.path.exists(dest):
                        name, ext = os.path.splitext(filename)
                        dest = os.path.join(full_target, f"{name}_{moved}{ext}")
                    
                    if not dry_run:
                        shutil.move(filepath, dest)
                    
                    moved += 1
                    self.log.append(f"{'[DRY] ' if dry_run else ''}Moved: {filepath} -> {dest}")
            except Exception as e:
                errors.append(f"{filepath}: {str(e)}")
        
        return {
            'status': 'success' if not errors else 'partial',
            'files_processed': moved,
            'errors': errors[:10]  # Limit errors
        }
    
    def _execute_delete(self, action: Dict, dry_run: bool) -> Dict:
        """Execute delete action."""
        files = action.get('files', [])
        deleted = 0
        errors = []
        
        for filepath in files:
            try:
                if os.path.exists(filepath):
                    if not dry_run:
                        os.remove(filepath)
                    deleted += 1
                    self.log.append(f"{'[DRY] ' if dry_run else ''}Deleted: {filepath}")
            except Exception as e:
                errors.append(f"{filepath}: {str(e)}")
        
        return {
            'status': 'success' if not errors else 'partial',
            'files_processed': deleted,
            'errors': errors[:10]
        }


# =============================================================================
# 📊 FORMATTING
# =============================================================================

def format_size(size: int) -> str:
    """Format size in human readable form."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"


def format_scan_report(result: Dict) -> str:
    """Format scan result for display with folder analysis."""
    lines = []
    
    lines.append("=" * 70)
    lines.append("🖥️ AI PC ORGANIZER - SMART SCAN REPORT")
    lines.append("=" * 70)
    
    lines.append(f"\n📍 Location: {result.get('location', 'Unknown')}")
    lines.append(f"📅 Scanned: {result.get('timestamp', '')[:19]}")
    
    stats = result.get('stats', {})
    lines.append(f"\n{'─' * 60}")
    lines.append("📊 OVERVIEW")
    lines.append(f"{'─' * 60}")
    lines.append(f"  📄 Total Files: {stats.get('total_files', 0):,}")
    lines.append(f"  📁 Total Folders: {stats.get('total_folders', 0):,}")
    lines.append(f"  📦 Total Size: {format_size(stats.get('total_size', 0))}")
    lines.append(f"  🗑️ Temp Files: {stats.get('temp_files', 0):,}")
    lines.append(f"  📅 Old Files (>1 year): {stats.get('old_files', 0):,}")
    
    # Projects found (Protected)
    projects = result.get('projects', [])
    if projects:
        lines.append(f"\n{'─' * 60}")
        lines.append(f"💻 PROJECTS DETECTED ({len(projects)}) - 🛡️ PROTECTED")
        lines.append(f"{'─' * 60}")
        lines.append("  These folders contain code projects and won't be touched:")
        for proj in projects[:10]:
            proj_name = proj.get('name', os.path.basename(proj['path']))
            lines.append(f"  🔹 {proj['type']}: {proj_name}")
            lines.append(f"     └─ {proj['path']}")
        if len(projects) > 10:
            lines.append(f"  ... and {len(projects) - 10} more projects")
    
    # Folder Purposes (Smart Name Analysis)
    folder_purposes = stats.get('folder_purposes', {})
    if folder_purposes:
        lines.append(f"\n{'─' * 60}")
        lines.append("🧠 FOLDER PURPOSES (Smart Name Analysis)")
        lines.append(f"{'─' * 60}")
        lines.append("  AI detected these folder types by analyzing names:")
        
        sorted_purposes = sorted(folder_purposes.items(), key=lambda x: x[1], reverse=True)
        for purpose, count in sorted_purposes[:10]:
            lines.append(f"  📁 {purpose}: {count} folders")
    
    # Analyzed Folders with high confidence
    analyzed = result.get('analyzed_folders', [])
    interesting_folders = [f for f in analyzed if f.get('confidence', 0) >= 0.7]
    if interesting_folders:
        lines.append(f"\n{'─' * 60}")
        lines.append("📂 FOLDER ANALYSIS (High Confidence)")
        lines.append(f"{'─' * 60}")
        
        for folder in interesting_folders[:15]:
            purpose = folder.get('purpose', 'Unknown')
            name = folder.get('name', 'Unknown')
            confidence = folder.get('confidence', 0)
            hints = folder.get('name_hints', [])
            
            lines.append(f"  📁 {name}")
            lines.append(f"     Purpose: {purpose} (confidence: {confidence:.0%})")
            if hints:
                lines.append(f"     Keywords: {', '.join(hints[:3])}")
            if folder.get('should_organize'):
                lines.append(f"     ⚠️ Needs organization (mixed content)")
    
    # Category breakdown
    cats = stats.get('categories', {})
    if cats:
        lines.append(f"\n{'─' * 60}")
        lines.append("📁 FILE CATEGORIES")
        lines.append(f"{'─' * 60}")
        
        sorted_cats = sorted(cats.items(), key=lambda x: x[1]['count'], reverse=True)
        max_count = sorted_cats[0][1]['count'] if sorted_cats else 1
        
        for cat, cat_stats in sorted_cats:
            count = cat_stats['count']
            size = cat_stats['size']
            bar_len = int((count / max_count) * 25)
            bar = "█" * bar_len + "░" * (25 - bar_len)
            lines.append(f"  {cat}")
            lines.append(f"    [{bar}] {count:,} files ({format_size(size)})")
    
    # Organization plan
    plan = result.get('organization_plan', [])
    if plan:
        lines.append(f"\n{'─' * 60}")
        lines.append(f"📋 ORGANIZATION PLAN ({len(plan)} actions)")
        lines.append(f"{'─' * 60}")
        
        total_files = sum(p.get('file_count', 0) for p in plan)
        total_size = sum(p.get('total_size', 0) for p in plan)
        
        lines.append(f"  📄 Files to organize: {total_files:,}")
        lines.append(f"  📦 Space affected: {format_size(total_size)}")
        lines.append("")
        
        for i, action in enumerate(plan[:10], 1):
            lines.append(f"  {i}. {action.get('description', 'Unknown')}")
            lines.append(f"     └─ {action.get('file_count', 0)} files ({format_size(action.get('total_size', 0))})")
        
        if len(plan) > 10:
            lines.append(f"\n  ... and {len(plan) - 10} more actions")
    
    # Cleanup suggestions
    cleanup = result.get('cleanup_suggestions', [])
    if cleanup:
        lines.append(f"\n{'─' * 60}")
        lines.append(f"🧹 CLEANUP SUGGESTIONS")
        lines.append(f"{'─' * 60}")
        
        for sugg in cleanup:
            lines.append(f"  {sugg.get('icon', '•')} {sugg.get('description', 'Unknown')}")
    
    lines.append(f"\n{'=' * 70}")
    lines.append("💡 Use 'Organize' button to execute the plan (simulation first)")
    
    return "\n".join(lines)


# =============================================================================
# 🚀 MAIN FUNCTIONS
# =============================================================================

def scan_pc_full(drives: List[str] = None, 
                progress_cb: Callable = None,
                skip_system: bool = True) -> Dict:
    """
    Scan entire PC or selected drives.
    
    Args:
        drives: List of drives to scan (None = all)
        progress_cb: Progress callback
        skip_system: Skip system folders
    
    Returns:
        Combined scan result
    """
    scanner = PCScanner(skip_system=skip_system)
    
    if not drives:
        drives = scanner.get_drives()
    
    combined = {
        'drives': drives,
        'timestamp': datetime.now().isoformat(),
        'files': [],
        'projects': [],
        'by_category': defaultdict(list),
        'stats': {
            'total_files': 0,
            'total_size': 0,
            'total_folders': 0,
            'temp_files': 0,
            'old_files': 0,
            'categories': {}
        },
        'organization_plan': [],
        'cleanup_suggestions': []
    }
    
    for drive in drives:
        if progress_cb:
            progress_cb(f"Scanning {drive}...")
        
        result = scanner.scan_location(drive, progress_cb)
        
        # Combine results
        combined['files'].extend(result.get('files', []))
        combined['projects'].extend(result.get('projects', []))
        
        for cat, files in result.get('by_category', {}).items():
            combined['by_category'][cat].extend(files)
        
        # Add stats
        for key in ['total_files', 'total_size', 'total_folders', 'temp_files', 'old_files']:
            combined['stats'][key] += result.get('stats', {}).get(key, 0)
        
        combined['organization_plan'].extend(result.get('organization_plan', []))
        combined['cleanup_suggestions'].extend(result.get('cleanup_suggestions', []))
    
    # Recalculate category stats
    for cat, files in combined['by_category'].items():
        combined['stats']['categories'][cat] = {
            'count': len(files),
            'size': sum(f.get('size', 0) for f in files)
        }
    
    return combined


def organize_files(scan_result: Dict, 
                  base_path: str = None,
                  dry_run: bool = True,
                  progress_cb: Callable = None) -> Dict:
    """
    Organize files based on scan result.
    
    Args:
        scan_result: Result from scan_pc_full
        base_path: Where to create organized folders
        dry_run: Simulation mode
        progress_cb: Progress callback
    
    Returns:
        Organization result
    """
    organizer = FileOrganizer(base_path)
    plan = scan_result.get('organization_plan', [])
    
    return organizer.execute_plan(plan, dry_run, progress_cb)
