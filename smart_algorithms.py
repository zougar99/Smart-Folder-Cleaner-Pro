# -*- coding: utf-8 -*-
"""
Smart Algorithms - Optimized scanning, duplicate detection, and similarity analysis.
"""
import os
import hashlib
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
from difflib import SequenceMatcher
from typing import Callable, Optional, List, Dict, Set
import re

# =============================================================================
# ⚡ PARALLEL FILE SCANNER
# =============================================================================

class ParallelScanner:
    """Fast parallel file scanner with caching."""
    
    def __init__(self, max_workers: int = 8):
        self.max_workers = max_workers
        self._cache = {}
        self._cache_lock = threading.Lock()
    
    def scan_folder(self, folder: str, skip_dirs: Set[str] = None, 
                   progress_cb: Callable = None) -> Dict:
        """
        Scan folder using parallel processing.
        Returns: {files: [...], folders: [...], total_size: int, by_extension: {...}}
        """
        if skip_dirs is None:
            skip_dirs = {
                "node_modules", ".git", "__pycache__", ".venv", "venv",
                "$RECYCLE.BIN", "System Volume Information"
            }
        
        result = {
            "folder": folder,
            "files": [],
            "folders": [],
            "total_size": 0,
            "by_extension": defaultdict(lambda: {"count": 0, "size": 0}),
            "by_size_group": defaultdict(list),  # Group files by size for duplicate detection
        }
        
        # Collect all items first
        items_to_process = []
        
        for root, dirs, files in os.walk(folder):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            
            for f in files:
                items_to_process.append(os.path.join(root, f))
            
            for d in dirs:
                result["folders"].append(os.path.join(root, d))
        
        total = len(items_to_process)
        processed = 0
        
        # Process files in parallel
        def process_file(file_path):
            try:
                stat = os.stat(file_path)
                size = stat.st_size
                mtime = stat.st_mtime
                name = os.path.basename(file_path)
                ext = os.path.splitext(name)[1].lower()
                
                return {
                    "path": file_path,
                    "name": name,
                    "ext": ext,
                    "size": size,
                    "mtime": mtime,
                    "rel_path": os.path.relpath(file_path, folder),
                }
            except:
                return None
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(process_file, f): f for f in items_to_process}
            
            for future in as_completed(futures):
                file_info = future.result()
                if file_info:
                    result["files"].append(file_info)
                    result["total_size"] += file_info["size"]
                    result["by_extension"][file_info["ext"]]["count"] += 1
                    result["by_extension"][file_info["ext"]]["size"] += file_info["size"]
                    
                    # Group by size for duplicate detection
                    result["by_size_group"][file_info["size"]].append(file_info)
                
                processed += 1
                if progress_cb and processed % 100 == 0:
                    progress_cb(f"Scanned {processed}/{total} files...")
        
        result["by_extension"] = dict(result["by_extension"])
        result["file_count"] = len(result["files"])
        result["folder_count"] = len(result["folders"])
        
        return result


# =============================================================================
# 🧠 OPTIMIZED DUPLICATE DETECTION
# =============================================================================

class SmartDuplicateFinder:
    """
    Optimized duplicate finder:
    1. Group by size first (O(n))
    2. Only hash files with same size
    3. Use partial hash for large files first
    """
    
    CHUNK_SIZE = 8192  # 8KB for partial hash
    LARGE_FILE_THRESHOLD = 10 * 1024 * 1024  # 10MB
    
    def __init__(self):
        self._hash_cache = {}
    
    def get_partial_hash(self, file_path: str) -> str:
        """Get hash of first and last chunks (fast check for large files)."""
        try:
            with open(file_path, "rb") as f:
                # Read first chunk
                first_chunk = f.read(self.CHUNK_SIZE)
                
                # Seek to end and read last chunk
                f.seek(0, 2)  # End of file
                size = f.tell()
                
                if size > self.CHUNK_SIZE * 2:
                    f.seek(-self.CHUNK_SIZE, 2)
                    last_chunk = f.read(self.CHUNK_SIZE)
                else:
                    last_chunk = b""
                
                return hashlib.md5(first_chunk + last_chunk).hexdigest()
        except:
            return ""
    
    def get_full_hash(self, file_path: str) -> str:
        """Get full MD5 hash of file."""
        if file_path in self._hash_cache:
            return self._hash_cache[file_path]
        
        try:
            hasher = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    hasher.update(chunk)
            
            hash_val = hasher.hexdigest()
            self._hash_cache[file_path] = hash_val
            return hash_val
        except:
            return ""
    
    def find_duplicates(self, files: List[Dict], progress_cb: Callable = None) -> Dict:
        """
        Find duplicates using optimized algorithm:
        1. Group by size
        2. Filter groups with only 1 file
        3. For remaining, use partial hash
        4. For partial hash matches, verify with full hash
        """
        result = {
            "groups": [],  # List of duplicate groups
            "total_duplicates": 0,
            "wasted_space": 0,
            "scanned_files": len(files),
            "hashed_files": 0,
        }
        
        # Step 1: Group by size
        by_size = defaultdict(list)
        for f in files:
            by_size[f["size"]].append(f)
        
        # Step 2: Filter singles
        potential_duplicates = {size: files for size, files in by_size.items() 
                               if len(files) > 1 and size > 0}
        
        if progress_cb:
            progress_cb(f"Found {len(potential_duplicates)} size groups to check...")
        
        # Step 3: Hash and group
        total_groups = len(potential_duplicates)
        processed_groups = 0
        
        for size, file_list in potential_duplicates.items():
            processed_groups += 1
            
            if progress_cb and processed_groups % 10 == 0:
                progress_cb(f"Checking group {processed_groups}/{total_groups}...")
            
            # For large files, use partial hash first
            if size > self.LARGE_FILE_THRESHOLD:
                # Group by partial hash
                by_partial = defaultdict(list)
                for f in file_list:
                    partial = self.get_partial_hash(f["path"])
                    if partial:
                        by_partial[partial].append(f)
                        result["hashed_files"] += 1
                
                # Only full hash if partial matches
                for partial_hash, partial_list in by_partial.items():
                    if len(partial_list) > 1:
                        self._hash_group(partial_list, result)
            else:
                # Small files: direct full hash
                self._hash_group(file_list, result)
        
        return result
    
    def _hash_group(self, file_list: List[Dict], result: Dict):
        """Hash a group of files and find duplicates."""
        by_hash = defaultdict(list)
        
        for f in file_list:
            full_hash = self.get_full_hash(f["path"])
            if full_hash:
                by_hash[full_hash].append(f)
                result["hashed_files"] += 1
        
        # Find groups with duplicates
        for hash_val, hash_list in by_hash.items():
            if len(hash_list) > 1:
                # Sort by mtime to find original (oldest)
                hash_list.sort(key=lambda x: x.get("mtime", 0))
                
                group = {
                    "hash": hash_val,
                    "size": hash_list[0]["size"],
                    "original": hash_list[0],
                    "duplicates": hash_list[1:],
                }
                
                result["groups"].append(group)
                result["total_duplicates"] += len(hash_list) - 1
                result["wasted_space"] += group["size"] * (len(hash_list) - 1)


# =============================================================================
# 🔍 SIMILAR FILES FINDER (Not Just Exact Duplicates)
# =============================================================================

class SimilarFileFinder:
    """Find files with similar names, content patterns, or that might be versions."""
    
    def find_similar_names(self, files: List[Dict], threshold: float = 0.8,
                          progress_cb: Callable = None) -> List[Dict]:
        """
        Find files with similar names (might be versions or copies).
        Uses sequence matching algorithm.
        """
        results = []
        names = [(f["name"], f) for f in files]
        
        # Group by base name (without numbers/dates)
        base_groups = defaultdict(list)
        
        for name, file_info in names:
            # Remove common version patterns
            base = self._normalize_name(name)
            base_groups[base].append(file_info)
        
        # Find groups with multiple files
        for base, group in base_groups.items():
            if len(group) > 1:
                results.append({
                    "type": "similar_name",
                    "base_name": base,
                    "files": group,
                    "count": len(group),
                })
        
        # Also find fuzzy matches
        checked = set()
        
        for i, (name1, file1) in enumerate(names):
            if progress_cb and i % 100 == 0:
                progress_cb(f"Checking name similarity {i}/{len(names)}...")
            
            for j, (name2, file2) in enumerate(names[i+1:], i+1):
                if (i, j) in checked or (j, i) in checked:
                    continue
                
                # Compare names (without extension)
                base1 = os.path.splitext(name1)[0]
                base2 = os.path.splitext(name2)[0]
                
                similarity = SequenceMatcher(None, base1.lower(), base2.lower()).ratio()
                
                if similarity >= threshold and similarity < 1.0:  # Not exact match
                    results.append({
                        "type": "fuzzy_match",
                        "similarity": similarity,
                        "file1": file1,
                        "file2": file2,
                    })
                    checked.add((i, j))
        
        return results
    
    def _normalize_name(self, name: str) -> str:
        """Remove version numbers, dates, copy indicators from filename."""
        base = os.path.splitext(name)[0].lower()
        
        # Remove common patterns
        patterns = [
            r'\s*\(\d+\)$',           # file (1), file (2)
            r'\s*-\s*copy\s*\d*$',    # file - copy, file - copy 2
            r'\s*copy\s*\d*$',        # file copy, file copy 2
            r'_\d{8,}$',              # file_20240101
            r'_v\d+\.?\d*$',          # file_v1, file_v2.1
            r'\s+v\d+\.?\d*$',        # file v1
            r'_\d+$',                 # file_1, file_2
            r'\s*-\s*\d+$',           # file - 1
        ]
        
        for pattern in patterns:
            base = re.sub(pattern, '', base, flags=re.IGNORECASE)
        
        return base.strip()
    
    def find_potential_backups(self, files: List[Dict], 
                               progress_cb: Callable = None) -> List[Dict]:
        """Find files that look like backups (.bak, .old, ~, etc.)"""
        backup_patterns = [
            (r'\.bak\d*$', 'backup extension'),
            (r'\.old\d*$', 'old extension'),
            (r'\.backup$', 'backup extension'),
            (r'~$', 'tilde backup'),
            (r'\.orig$', 'original backup'),
            (r'_backup\d*\.', 'backup in name'),
            (r'\.save$', 'save file'),
        ]
        
        results = []
        
        for f in files:
            name = f["name"].lower()
            
            for pattern, desc in backup_patterns:
                if re.search(pattern, name):
                    results.append({
                        "file": f,
                        "type": desc,
                        "pattern": pattern,
                    })
                    break
        
        return results


# =============================================================================
# 📊 CONFIDENCE SCORING SYSTEM
# =============================================================================

class ConfidenceScorer:
    """Calculate confidence scores for analysis decisions."""
    
    def score_project_detection(self, folder_info: Dict, detected_type: str) -> Dict:
        """
        Score how confident we are about project type detection.
        Returns: {score: 0-100, reasons: [...], confidence: HIGH/MEDIUM/LOW}
        """
        score = 0
        reasons = []
        extensions = folder_info.get("by_extension", {})
        total_files = folder_info.get("file_count", 0)
        
        if detected_type == "python_project":
            py_count = extensions.get(".py", {}).get("count", 0)
            py_ratio = py_count / max(total_files, 1)
            
            if py_ratio > 0.5:
                score += 30
                reasons.append(f"50%+ Python files ({py_ratio*100:.1f}%)")
            elif py_ratio > 0.2:
                score += 15
                reasons.append(f"20%+ Python files ({py_ratio*100:.1f}%)")
            
            # Check for Python project indicators
            files = [f["name"].lower() for f in folder_info.get("files", [])]
            
            if "requirements.txt" in files:
                score += 25
                reasons.append("Has requirements.txt")
            if "setup.py" in files:
                score += 25
                reasons.append("Has setup.py")
            if "pyproject.toml" in files:
                score += 25
                reasons.append("Has pyproject.toml")
            if "__init__.py" in files:
                score += 15
                reasons.append("Has __init__.py (package)")
            if any("venv" in f or ".venv" in f for f in folder_info.get("folders", [])):
                score += 20
                reasons.append("Has virtual environment")
        
        elif detected_type == "javascript_project":
            js_count = extensions.get(".js", {}).get("count", 0) + extensions.get(".ts", {}).get("count", 0)
            js_ratio = js_count / max(total_files, 1)
            
            if js_ratio > 0.3:
                score += 25
                reasons.append(f"30%+ JS/TS files ({js_ratio*100:.1f}%)")
            
            files = [f["name"].lower() for f in folder_info.get("files", [])]
            
            if "package.json" in files:
                score += 35
                reasons.append("Has package.json")
            if "tsconfig.json" in files:
                score += 20
                reasons.append("Has tsconfig.json (TypeScript)")
            if any("node_modules" in f for f in folder_info.get("folders", [])):
                score += 20
                reasons.append("Has node_modules")
        
        # Determine confidence level
        if score >= 70:
            confidence = "HIGH"
        elif score >= 40:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"
        
        return {
            "score": min(score, 100),
            "confidence": confidence,
            "reasons": reasons,
            "detected_type": detected_type,
        }
    
    def score_file_mismatch(self, file_info: Dict, project_type: str) -> Dict:
        """
        Score how confident we are that a file doesn't belong.
        Returns: {score: 0-100, confidence: HIGH/MEDIUM/LOW, reason: str}
        """
        ext = file_info.get("ext", "").lower()
        name = file_info.get("name", "").lower()
        
        # Define mismatches with confidence
        mismatch_scores = {
            "python_project": {
                ".mp3": (95, "Audio file in code project"),
                ".mp4": (95, "Video file in code project"),
                ".avi": (95, "Video file in code project"),
                ".jpg": (80, "Image file (might be asset, but unusual)"),
                ".png": (60, "Image file (could be icon/asset)"),
                ".doc": (90, "Word document in code project"),
                ".docx": (90, "Word document in code project"),
                ".psd": (90, "Photoshop file in code project"),
            },
            "javascript_project": {
                ".mp3": (95, "Audio file in code project"),
                ".mp4": (95, "Video file in code project"),
                ".py": (70, "Python file (might be build script)"),
                ".doc": (90, "Word document in code project"),
            },
        }
        
        project_mismatches = mismatch_scores.get(project_type, {})
        
        if ext in project_mismatches:
            score, reason = project_mismatches[ext]
            
            # Adjust score based on location
            rel_path = file_info.get("rel_path", "")
            if "assets" in rel_path.lower() or "static" in rel_path.lower():
                score -= 30
                reason += " (but in assets folder)"
            
            if score >= 80:
                confidence = "HIGH"
            elif score >= 50:
                confidence = "MEDIUM"
            else:
                confidence = "LOW"
            
            return {
                "score": score,
                "confidence": confidence,
                "reason": reason,
                "should_flag": score >= 50,
            }
        
        return {
            "score": 0,
            "confidence": "LOW",
            "reason": "File type is acceptable",
            "should_flag": False,
        }


# =============================================================================
# 🤖 ENHANCED AI CONTEXT BUILDER
# =============================================================================

class AIContextBuilder:
    """Build rich context for AI analysis."""
    
    # Files to read for context
    CONTEXT_FILES = {
        "readme": ["README.md", "README.txt", "README", "readme.md"],
        "config": ["package.json", "requirements.txt", "setup.py", "pyproject.toml",
                  "Cargo.toml", "go.mod", "composer.json", "Gemfile", "pom.xml"],
        "manifest": ["manifest.json", "manifest.xml", "AndroidManifest.xml"],
        "docker": ["Dockerfile", "docker-compose.yml", "docker-compose.yaml"],
        "ci": [".github/workflows/*.yml", ".gitlab-ci.yml", "Jenkinsfile", ".travis.yml"],
        "ignore": [".gitignore", ".dockerignore", ".npmignore"],
    }
    
    # Code files to sample
    CODE_EXTENSIONS = {".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs", 
                       ".cpp", ".c", ".cs", ".rb", ".php", ".swift", ".kt"}
    
    MAX_FILE_SIZE = 50000  # 50KB max per file
    MAX_TOTAL_CONTEXT = 200000  # 200KB total context
    
    def build_context(self, folder: str, file_list: List[Dict],
                     progress_cb: Callable = None) -> Dict:
        """Build comprehensive context for AI analysis."""
        context = {
            "folder_name": os.path.basename(folder),
            "folder_path": folder,
            "file_count": len(file_list),
            "file_contents": {},
            "code_samples": [],
            "structure_summary": "",
            "detected_technologies": [],
            "imports_and_dependencies": [],
        }
        
        total_size = 0
        
        # 1. Read important context files
        if progress_cb:
            progress_cb("Reading context files...")
        
        for category, filenames in self.CONTEXT_FILES.items():
            for filename in filenames:
                file_path = os.path.join(folder, filename)
                if os.path.isfile(file_path):
                    content = self._read_file(file_path)
                    if content:
                        context["file_contents"][filename] = content
                        total_size += len(content)
                        
                        # Extract technologies
                        if filename == "package.json":
                            context["detected_technologies"].extend(
                                self._extract_npm_deps(content)
                            )
                        elif filename == "requirements.txt":
                            context["detected_technologies"].extend(
                                self._extract_pip_deps(content)
                            )
                
                if total_size > self.MAX_TOTAL_CONTEXT:
                    break
        
        # 2. Sample code files
        if progress_cb:
            progress_cb("Sampling code files...")
        
        code_files = [f for f in file_list if f.get("ext", "").lower() in self.CODE_EXTENSIONS]
        
        # Sample up to 5 code files
        for f in code_files[:5]:
            if total_size > self.MAX_TOTAL_CONTEXT:
                break
            
            content = self._read_file(f["path"], max_lines=50)
            if content:
                context["code_samples"].append({
                    "file": f["rel_path"],
                    "content": content,
                })
                total_size += len(content)
                
                # Extract imports
                imports = self._extract_imports(content, f.get("ext", ""))
                context["imports_and_dependencies"].extend(imports)
        
        # 3. Build structure summary
        context["structure_summary"] = self._build_structure_summary(file_list)
        
        # Remove duplicates from technologies and imports
        context["detected_technologies"] = list(set(context["detected_technologies"]))
        context["imports_and_dependencies"] = list(set(context["imports_and_dependencies"]))
        
        return context
    
    def _read_file(self, path: str, max_lines: int = None) -> str:
        """Read file content safely."""
        try:
            size = os.path.getsize(path)
            if size > self.MAX_FILE_SIZE:
                return ""
            
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                if max_lines:
                    lines = []
                    for i, line in enumerate(f):
                        if i >= max_lines:
                            break
                        lines.append(line)
                    return "".join(lines)
                return f.read()
        except:
            return ""
    
    def _extract_npm_deps(self, content: str) -> List[str]:
        """Extract dependencies from package.json."""
        try:
            import json
            data = json.loads(content)
            deps = list(data.get("dependencies", {}).keys())
            deps += list(data.get("devDependencies", {}).keys())
            return deps[:20]  # Limit
        except:
            return []
    
    def _extract_pip_deps(self, content: str) -> List[str]:
        """Extract dependencies from requirements.txt."""
        deps = []
        for line in content.split("\n"):
            line = line.strip()
            if line and not line.startswith("#"):
                # Remove version specifiers
                dep = re.split(r'[=<>!~]', line)[0].strip()
                if dep:
                    deps.append(dep)
        return deps[:20]
    
    def _extract_imports(self, content: str, ext: str) -> List[str]:
        """Extract imports from code."""
        imports = []
        
        if ext in {".py"}:
            # Python imports
            for match in re.finditer(r'^(?:from|import)\s+([\w\.]+)', content, re.MULTILINE):
                imports.append(match.group(1).split('.')[0])
        
        elif ext in {".js", ".ts", ".jsx", ".tsx"}:
            # JS/TS imports
            for match in re.finditer(r'(?:import|require)\s*\(?[\'"]([^\'"\)]+)', content):
                imports.append(match.group(1))
        
        return imports[:30]
    
    def _build_structure_summary(self, file_list: List[Dict]) -> str:
        """Build a summary of folder structure."""
        # Count files by top-level directory
        by_dir = defaultdict(int)
        
        for f in file_list:
            rel_path = f.get("rel_path", "")
            parts = rel_path.split(os.sep)
            if len(parts) > 1:
                by_dir[parts[0]] += 1
            else:
                by_dir["(root)"] += 1
        
        # Build summary
        lines = []
        for dir_name, count in sorted(by_dir.items(), key=lambda x: -x[1])[:15]:
            lines.append(f"  {dir_name}/: {count} files")
        
        return "\n".join(lines)


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================

# Global instances for reuse
_scanner = ParallelScanner()
_duplicate_finder = SmartDuplicateFinder()
_similar_finder = SimilarFileFinder()
_confidence_scorer = ConfidenceScorer()
_context_builder = AIContextBuilder()


def fast_scan(folder: str, progress_cb: Callable = None) -> Dict:
    """Fast parallel folder scan."""
    return _scanner.scan_folder(folder, progress_cb=progress_cb)


def find_duplicates_smart(files: List[Dict], progress_cb: Callable = None) -> Dict:
    """Smart duplicate detection."""
    return _duplicate_finder.find_duplicates(files, progress_cb)


def find_similar_files(files: List[Dict], progress_cb: Callable = None) -> List[Dict]:
    """Find similar (not exact) files."""
    return _similar_finder.find_similar_names(files, progress_cb=progress_cb)


def find_backup_files(files: List[Dict], progress_cb: Callable = None) -> List[Dict]:
    """Find backup/temporary files."""
    return _similar_finder.find_potential_backups(files, progress_cb)


def score_project(folder_info: Dict, detected_type: str) -> Dict:
    """Score project detection confidence."""
    return _confidence_scorer.score_project_detection(folder_info, detected_type)


def score_mismatch(file_info: Dict, project_type: str) -> Dict:
    """Score file mismatch confidence."""
    return _confidence_scorer.score_file_mismatch(file_info, project_type)


def build_ai_context(folder: str, files: List[Dict], progress_cb: Callable = None) -> Dict:
    """Build rich context for AI analysis."""
    return _context_builder.build_context(folder, files, progress_cb)
