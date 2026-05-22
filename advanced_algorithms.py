# -*- coding: utf-8 -*-
"""
Advanced Algorithms - High-performance scanning and analysis.
Optimizations: Caching, parallel processing, smart hashing, incremental scans.
"""
import os
import hashlib
import json
import time
import threading
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
from collections import defaultdict
from typing import Callable, Dict, List, Optional, Set, Tuple
import re

# =============================================================================
# 📦 SMART CACHE SYSTEM
# =============================================================================

class FileCache:
    """Intelligent file metadata cache with auto-expiry."""
    
    def __init__(self, cache_file: str = ".file_cache.json", max_age_hours: int = 24):
        self.cache_file = cache_file
        self.max_age = timedelta(hours=max_age_hours)
        self.cache: Dict[str, dict] = {}
        self._lock = threading.Lock()
        self._load_cache()
    
    def _load_cache(self):
        """Load cache from disk."""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Filter out expired entries
                    now = datetime.now().timestamp()
                    self.cache = {
                        k: v for k, v in data.items()
                        if now - v.get('cached_at', 0) < self.max_age.total_seconds()
                    }
        except:
            self.cache = {}
    
    def _save_cache(self):
        """Save cache to disk."""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f)
        except:
            pass
    
    def get(self, filepath: str, mtime: float) -> Optional[dict]:
        """Get cached data if still valid."""
        with self._lock:
            key = filepath
            if key in self.cache:
                cached = self.cache[key]
                # Valid if file hasn't changed
                if cached.get('mtime') == mtime:
                    return cached
            return None
    
    def set(self, filepath: str, mtime: float, data: dict):
        """Cache file data."""
        with self._lock:
            self.cache[filepath] = {
                **data,
                'mtime': mtime,
                'cached_at': datetime.now().timestamp()
            }
    
    def save(self):
        """Persist cache to disk."""
        with self._lock:
            self._save_cache()
    
    def clear(self):
        """Clear all cache."""
        with self._lock:
            self.cache = {}
            try:
                os.remove(self.cache_file)
            except:
                pass


# Global cache instance
_file_cache = FileCache()


# =============================================================================
# ⚡ OPTIMIZED HASHING
# =============================================================================

def quick_hash(filepath: str, chunk_size: int = 8192) -> str:
    """
    Ultra-fast hash using first + middle + last chunks.
    Good for quick duplicate detection before full hash.
    """
    try:
        file_size = os.path.getsize(filepath)
        
        if file_size == 0:
            return "empty"
        
        hasher = hashlib.md5()
        
        with open(filepath, 'rb') as f:
            # First chunk
            hasher.update(f.read(chunk_size))
            
            if file_size > chunk_size * 3:
                # Middle chunk
                f.seek(file_size // 2)
                hasher.update(f.read(chunk_size))
                
                # Last chunk
                f.seek(-chunk_size, 2)
                hasher.update(f.read(chunk_size))
            elif file_size > chunk_size:
                # Just read rest for small files
                hasher.update(f.read())
        
        # Include size in hash for extra accuracy
        hasher.update(str(file_size).encode())
        
        return hasher.hexdigest()
    except:
        return ""


def full_hash_chunked(filepath: str, chunk_size: int = 1024 * 1024) -> str:
    """
    Memory-efficient full file hash using streaming.
    Processes 1MB at a time instead of loading entire file.
    """
    try:
        hasher = hashlib.md5()
        
        with open(filepath, 'rb') as f:
            while chunk := f.read(chunk_size):
                hasher.update(chunk)
        
        return hasher.hexdigest()
    except:
        return ""


def smart_hash(filepath: str, use_cache: bool = True) -> Tuple[str, str]:
    """
    Smart hashing with caching.
    Returns (quick_hash, full_hash) - full_hash may be None if not needed.
    """
    try:
        mtime = os.path.getmtime(filepath)
        
        # Check cache
        if use_cache:
            cached = _file_cache.get(filepath, mtime)
            if cached and 'quick_hash' in cached:
                return cached.get('quick_hash'), cached.get('full_hash')
        
        # Calculate quick hash
        qhash = quick_hash(filepath)
        
        # Cache it
        if use_cache:
            _file_cache.set(filepath, mtime, {'quick_hash': qhash})
        
        return qhash, None
    except:
        return "", None


# =============================================================================
# 🔍 PARALLEL SCANNER
# =============================================================================

class TurboScanner:
    """
    High-performance parallel file scanner.
    Uses thread pool for I/O-bound operations.
    """
    
    def __init__(self, max_workers: int = 8, skip_patterns: List[str] = None):
        self.max_workers = max_workers
        self.skip_patterns = skip_patterns or [
            'node_modules', '.git', '__pycache__', '.venv', 'venv',
            '$RECYCLE.BIN', 'System Volume Information', 'Windows',
            'Program Files', 'Program Files (x86)', 'AppData'
        ]
        self._stop_flag = threading.Event()
    
    def stop(self):
        """Signal scanner to stop."""
        self._stop_flag.set()
    
    def _should_skip(self, path: str) -> bool:
        """Check if path should be skipped."""
        name = os.path.basename(path)
        return name in self.skip_patterns or name.startswith('.')
    
    def scan_folder(self, folder_path: str, 
                   progress_cb: Callable = None,
                   collect_hashes: bool = False) -> Dict:
        """
        Scan folder with parallel processing.
        
        Returns:
            {
                'files': [(path, size, mtime, ext), ...],
                'folders': [path, ...],
                'by_extension': {'.py': [files], ...},
                'by_size': {size: [files], ...},  # For duplicate detection
                'total_size': int,
                'total_files': int,
                'total_folders': int,
                'scan_time': float
            }
        """
        start_time = time.time()
        
        result = {
            'files': [],
            'folders': [],
            'by_extension': defaultdict(list),
            'by_size': defaultdict(list),
            'total_size': 0,
            'total_files': 0,
            'total_folders': 0,
            'scan_time': 0
        }
        
        if not os.path.isdir(folder_path):
            return result
        
        # Collect all directories first
        dirs_to_scan = []
        
        for root, dirs, files in os.walk(folder_path):
            if self._stop_flag.is_set():
                break
            
            # Filter out skip directories
            dirs[:] = [d for d in dirs if not self._should_skip(d)]
            
            dirs_to_scan.append((root, files))
            result['total_folders'] += 1
            result['folders'].append(root)
        
        # Process files in parallel
        def process_file(args):
            root, filename = args
            filepath = os.path.join(root, filename)
            
            try:
                stat = os.stat(filepath)
                size = stat.st_size
                mtime = stat.st_mtime
                ext = os.path.splitext(filename)[1].lower()
                
                return (filepath, size, mtime, ext, filename)
            except:
                return None
        
        # Flatten file list
        all_files = []
        for root, files in dirs_to_scan:
            for f in files:
                all_files.append((root, f))
        
        # Process with thread pool
        processed = 0
        total = len(all_files)
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(process_file, args): args for args in all_files}
            
            for future in as_completed(futures):
                if self._stop_flag.is_set():
                    break
                
                file_data = future.result()
                if file_data:
                    filepath, size, mtime, ext, filename = file_data
                    
                    result['files'].append((filepath, size, mtime, ext))
                    result['by_extension'][ext].append(filepath)
                    result['by_size'][size].append(filepath)
                    result['total_size'] += size
                    result['total_files'] += 1
                
                processed += 1
                if progress_cb and processed % 100 == 0:
                    progress_cb(f"Scanned {processed}/{total} files...")
        
        result['scan_time'] = time.time() - start_time
        
        return result


# =============================================================================
# 🔄 SMART DUPLICATE FINDER
# =============================================================================

class SmartDuplicateFinder:
    """
    3-phase duplicate detection:
    1. Group by size (instant)
    2. Quick hash comparison (fast)
    3. Full hash verification (accurate)
    """
    
    def __init__(self, min_size: int = 1):
        self.min_size = min_size
    
    def find_duplicates(self, scan_result: Dict, 
                       progress_cb: Callable = None) -> Dict:
        """
        Find duplicates using optimized 3-phase approach.
        
        Returns:
            {
                'groups': [[file1, file2, ...], ...],  # Each group has same content
                'total_duplicates': int,
                'wasted_space': int,
                'by_hash': {hash: [files]},
                'originals': [files],  # Oldest file in each group
                'duplicates': [files]  # All non-original duplicates
            }
        """
        result = {
            'groups': [],
            'total_duplicates': 0,
            'wasted_space': 0,
            'by_hash': {},
            'originals': [],
            'duplicates': []
        }
        
        by_size = scan_result.get('by_size', {})
        
        # Phase 1: Filter to only sizes with multiple files
        potential_dupes = {
            size: files for size, files in by_size.items()
            if len(files) > 1 and size >= self.min_size
        }
        
        if progress_cb:
            progress_cb(f"Phase 1: {len(potential_dupes)} size groups to check...")
        
        # Phase 2: Quick hash comparison
        quick_hash_groups = defaultdict(list)
        
        for size, files in potential_dupes.items():
            for filepath in files:
                qhash = quick_hash(filepath)
                if qhash:
                    quick_hash_groups[(size, qhash)].append(filepath)
        
        # Filter to groups with potential duplicates
        potential_dupes_2 = {
            k: v for k, v in quick_hash_groups.items()
            if len(v) > 1
        }
        
        if progress_cb:
            progress_cb(f"Phase 2: {len(potential_dupes_2)} quick-hash groups to verify...")
        
        # Phase 3: Full hash verification
        full_hash_groups = defaultdict(list)
        
        total_to_hash = sum(len(v) for v in potential_dupes_2.values())
        hashed = 0
        
        for (size, qhash), files in potential_dupes_2.items():
            for filepath in files:
                fhash = full_hash_chunked(filepath)
                if fhash:
                    full_hash_groups[fhash].append((filepath, size))
                
                hashed += 1
                if progress_cb and hashed % 50 == 0:
                    progress_cb(f"Phase 3: Verified {hashed}/{total_to_hash} files...")
        
        # Build final result
        for fhash, files_with_size in full_hash_groups.items():
            if len(files_with_size) > 1:
                # Sort by mtime to find original (oldest)
                files_sorted = sorted(
                    files_with_size,
                    key=lambda x: os.path.getmtime(x[0]) if os.path.exists(x[0]) else 0
                )
                
                file_paths = [f[0] for f in files_sorted]
                file_size = files_sorted[0][1]
                
                result['groups'].append(file_paths)
                result['by_hash'][fhash] = file_paths
                result['originals'].append(file_paths[0])
                result['duplicates'].extend(file_paths[1:])
                result['total_duplicates'] += len(file_paths) - 1
                result['wasted_space'] += file_size * (len(file_paths) - 1)
        
        return result


# =============================================================================
# 🎯 INTELLIGENT PROJECT DETECTOR
# =============================================================================

class ProjectDetector:
    """
    Advanced project detection with confidence scoring.
    Uses file patterns, structure analysis, and content sampling.
    """
    
    # Project signatures with weighted indicators
    SIGNATURES = {
        'python_project': {
            'files': ['requirements.txt', 'setup.py', 'pyproject.toml', 'Pipfile', 'main.py', 'app.py'],
            'extensions': ['.py', '.pyw', '.pyx'],
            'config_files': ['.env', '.flake8', '.pylintrc', 'pytest.ini', 'tox.ini'],
            'weight': 1.0
        },
        'nodejs_project': {
            'files': ['package.json', 'package-lock.json', 'yarn.lock', 'tsconfig.json'],
            'extensions': ['.js', '.jsx', '.ts', '.tsx', '.mjs'],
            'config_files': ['.eslintrc', '.prettierrc', '.babelrc', 'webpack.config.js'],
            'weight': 1.0
        },
        'web_project': {
            'files': ['index.html', 'index.htm'],
            'extensions': ['.html', '.htm', '.css', '.scss'],
            'config_files': [],
            'weight': 0.8
        },
        'java_project': {
            'files': ['pom.xml', 'build.gradle', 'gradlew'],
            'extensions': ['.java', '.jar', '.class'],
            'config_files': [],
            'weight': 1.0
        },
        'csharp_project': {
            'files': [],
            'extensions': ['.cs', '.csproj', '.sln'],
            'config_files': [],
            'weight': 1.0
        },
        'rust_project': {
            'files': ['Cargo.toml', 'Cargo.lock'],
            'extensions': ['.rs'],
            'config_files': [],
            'weight': 1.0
        },
        'go_project': {
            'files': ['go.mod', 'go.sum'],
            'extensions': ['.go'],
            'config_files': [],
            'weight': 1.0
        },
        'cpp_project': {
            'files': ['CMakeLists.txt', 'Makefile'],
            'extensions': ['.cpp', '.c', '.h', '.hpp', '.cc'],
            'config_files': [],
            'weight': 1.0
        },
        'docker_project': {
            'files': ['Dockerfile', 'docker-compose.yml', 'docker-compose.yaml'],
            'extensions': [],
            'config_files': ['.dockerignore'],
            'weight': 0.7
        }
    }
    
    # Files that indicate ANY project
    UNIVERSAL_PROJECT_INDICATORS = [
        '.git', '.gitignore', '.gitattributes',
        'README.md', 'README.txt', 'README',
        'LICENSE', 'LICENSE.md', 'LICENSE.txt',
        'CHANGELOG.md', 'CONTRIBUTING.md',
        '.editorconfig', '.env.example'
    ]
    
    def detect(self, scan_result: Dict) -> Dict:
        """
        Detect project type with confidence score.
        
        Returns:
            {
                'type': str,  # Best match or 'mixed' or 'unknown'
                'confidence': float,  # 0.0 to 1.0
                'scores': {type: score},  # All scores
                'indicators': [str],  # What was detected
                'is_project': bool,
                'expected_extensions': [str],
                'secondary_types': [str]  # Other detected types
            }
        """
        files = scan_result.get('files', [])
        by_ext = scan_result.get('by_extension', {})
        
        # Get all filenames (lowercase)
        filenames = set()
        for filepath, _, _, _ in files:
            filenames.add(os.path.basename(filepath).lower())
        
        # Check universal indicators
        has_universal = any(
            ind.lower() in filenames or 
            any(ind.lower() in f.lower() for f in filenames)
            for ind in self.UNIVERSAL_PROJECT_INDICATORS
        )
        
        # Score each project type
        scores = {}
        indicators = []
        
        for proj_type, signature in self.SIGNATURES.items():
            score = 0.0
            type_indicators = []
            
            # Check indicator files
            for ind_file in signature['files']:
                if ind_file.lower() in filenames:
                    score += 0.3
                    type_indicators.append(f"Found {ind_file}")
            
            # Check extensions
            type_exts = signature['extensions']
            if type_exts:
                ext_count = sum(
                    len(by_ext.get(ext, []))
                    for ext in type_exts
                )
                total_files = len(files)
                
                if total_files > 0:
                    ext_ratio = ext_count / total_files
                    score += ext_ratio * 0.5
                    
                    if ext_ratio > 0.3:
                        type_indicators.append(f"{ext_count} {'/'.join(type_exts)} files ({ext_ratio:.0%})")
            
            # Check config files
            for cfg in signature['config_files']:
                if cfg.lower() in filenames:
                    score += 0.1
                    type_indicators.append(f"Config: {cfg}")
            
            # Apply weight
            score *= signature['weight']
            
            scores[proj_type] = score
            if type_indicators:
                indicators.extend(type_indicators)
        
        # Find best match
        if scores:
            best_type = max(scores, key=scores.get)
            best_score = scores[best_type]
        else:
            best_type = 'unknown'
            best_score = 0.0
        
        # Determine confidence
        if best_score >= 0.5:
            confidence = min(1.0, best_score)
        elif has_universal:
            confidence = 0.4
        else:
            confidence = best_score
        
        # Find secondary types (score > 0.2)
        secondary = [
            t for t, s in scores.items()
            if s > 0.2 and t != best_type
        ]
        
        # Is it a project?
        is_project = confidence >= 0.3 or has_universal
        
        # Get expected extensions
        expected_exts = []
        if best_type in self.SIGNATURES:
            expected_exts = self.SIGNATURES[best_type]['extensions']
        
        return {
            'type': best_type if confidence >= 0.3 else ('mixed' if secondary else 'unknown'),
            'confidence': confidence,
            'scores': scores,
            'indicators': indicators,
            'is_project': is_project,
            'expected_extensions': expected_exts,
            'secondary_types': secondary
        }


# =============================================================================
# 📊 SMART MISMATCH ANALYZER
# =============================================================================

class MismatchAnalyzer:
    """
    Intelligent file mismatch detection.
    Considers context, common patterns, and project structure.
    """
    
    # Files that belong in ANY project
    UNIVERSAL_PROJECT_FILES = {
        '.gitignore', '.gitattributes', '.editorconfig',
        'readme.md', 'readme.txt', 'readme',
        'license', 'license.md', 'license.txt',
        'changelog.md', 'contributing.md',
        '.env', '.env.example', '.env.local', '.env.sample',
        'dockerfile', 'docker-compose.yml',
        'makefile', 'cmakelists.txt',
        '.prettierrc', '.eslintrc', '.babelrc'
    }
    
    # Extensions that are common in projects
    PROJECT_EXTENSIONS = {
        '.md', '.txt', '.json', '.yaml', '.yml', '.toml',
        '.xml', '.ini', '.cfg', '.conf', '.config',
        '.sh', '.bat', '.cmd', '.ps1',
        '.log', '.lock', '.example', '.sample', '.template',
        '.exe', '.dll', '.so', '.dylib',  # Build outputs
        '.png', '.jpg', '.ico', '.svg', '.gif',  # Assets
        '.woff', '.woff2', '.ttf', '.eot',  # Fonts
    }
    
    # Truly unrelated personal files
    PERSONAL_MEDIA = {
        '.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma',  # Music
        '.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv',  # Videos
        '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',  # Office
        '.pdf',  # Documents (sometimes OK in projects)
    }
    
    def analyze(self, scan_result: Dict, project_info: Dict) -> Dict:
        """
        Analyze files for mismatches.
        
        Returns:
            {
                'mismatched': [(filepath, reason, confidence), ...],
                'total_mismatched': int,
                'categories': {reason: [files]},
                'should_separate': bool,
                'recommendation': str
            }
        """
        files = scan_result.get('files', [])
        project_type = project_info.get('type', 'unknown')
        expected_exts = set(project_info.get('expected_extensions', []))
        is_project = project_info.get('is_project', False)
        
        mismatched = []
        categories = defaultdict(list)
        
        for filepath, size, mtime, ext in files:
            filename = os.path.basename(filepath).lower()
            parent_dir = os.path.basename(os.path.dirname(filepath)).lower()
            
            # Skip universal project files
            if filename in self.UNIVERSAL_PROJECT_FILES:
                continue
            
            # Skip common project extensions
            if ext in self.PROJECT_EXTENSIONS:
                continue
            
            # Check if it's in an assets/resources folder
            asset_folders = {'assets', 'images', 'img', 'icons', 'fonts', 'media', 'resources', 'static', 'public'}
            if parent_dir in asset_folders:
                continue
            
            # Check for personal media in projects
            if is_project and ext in self.PERSONAL_MEDIA:
                # High confidence mismatch
                reason = f"Personal media ({ext}) in {project_type}"
                mismatched.append((filepath, reason, 0.9))
                categories['personal_media'].append(filepath)
                continue
            
            # Check for truly unexpected extensions in projects
            if is_project and expected_exts:
                if ext and ext not in expected_exts and ext not in self.PROJECT_EXTENSIONS:
                    # Medium confidence - might be intentional
                    reason = f"Unusual extension ({ext}) for {project_type}"
                    mismatched.append((filepath, reason, 0.5))
                    categories['unusual_extension'].append(filepath)
        
        # Determine if separation is needed
        high_confidence = [m for m in mismatched if m[2] >= 0.7]
        
        if len(high_confidence) >= 10:
            should_separate = True
            recommendation = f"Found {len(high_confidence)} files that clearly don't belong. Recommend separation."
        elif len(high_confidence) >= 3:
            should_separate = None  # Maybe
            recommendation = f"Found {len(high_confidence)} possibly mismatched files. Review recommended."
        else:
            should_separate = False
            recommendation = "Folder looks clean. No action needed."
        
        return {
            'mismatched': mismatched,
            'total_mismatched': len(mismatched),
            'categories': dict(categories),
            'should_separate': should_separate,
            'recommendation': recommendation
        }


# =============================================================================
# 🔗 SIMILAR FILE FINDER (Improved)
# =============================================================================

class SimilarFileFinder:
    """
    Find similar files using multiple strategies:
    1. Name similarity (fuzzy matching)
    2. Size similarity
    3. Content sampling
    """
    
    # Patterns indicating copies/versions
    COPY_PATTERNS = [
        r'[\s_\-]?copy[\s_\-]?\d*',
        r'[\s_\-]?\(\d+\)',
        r'[\s_\-]?v\d+',
        r'[\s_\-]?\d{8,}',  # Date stamps
        r'[\s_\-]?backup',
        r'[\s_\-]?old',
        r'[\s_\-]?new',
        r'[\s_\-]?final',
        r'[\s_\-]?revised',
    ]
    
    def __init__(self, similarity_threshold: float = 0.8):
        self.threshold = similarity_threshold
        self._compiled_patterns = [re.compile(p, re.IGNORECASE) for p in self.COPY_PATTERNS]
    
    def _normalize_name(self, filename: str) -> str:
        """Remove copy/version indicators from filename."""
        name = os.path.splitext(filename)[0]
        
        for pattern in self._compiled_patterns:
            name = pattern.sub('', name)
        
        return name.lower().strip()
    
    def _similarity_ratio(self, s1: str, s2: str) -> float:
        """Calculate string similarity using difflib."""
        from difflib import SequenceMatcher
        return SequenceMatcher(None, s1, s2).ratio()
    
    def find_similar(self, scan_result: Dict, 
                    progress_cb: Callable = None) -> List[Dict]:
        """
        Find groups of similar files.
        
        Returns:
            [
                {
                    'files': [filepath, ...],
                    'normalized_name': str,
                    'similarity_type': str,  # 'name', 'size', 'content'
                    'confidence': float
                },
                ...
            ]
        """
        files = scan_result.get('files', [])
        by_size = scan_result.get('by_size', {})
        
        similar_groups = []
        
        # Strategy 1: Name-based similarity
        name_groups = defaultdict(list)
        
        for filepath, size, mtime, ext in files:
            filename = os.path.basename(filepath)
            normalized = self._normalize_name(filename)
            
            if len(normalized) >= 3:  # Skip very short names
                name_groups[normalized].append((filepath, filename, ext))
        
        # Find groups with similar names
        for norm_name, group_files in name_groups.items():
            if len(group_files) > 1:
                similar_groups.append({
                    'files': [f[0] for f in group_files],
                    'normalized_name': norm_name,
                    'similarity_type': 'exact_normalized',
                    'confidence': 0.95
                })
        
        # Strategy 2: Fuzzy name matching
        processed_names = list(name_groups.keys())
        fuzzy_matches = []
        
        for i, name1 in enumerate(processed_names):
            for name2 in processed_names[i+1:]:
                ratio = self._similarity_ratio(name1, name2)
                
                if ratio >= self.threshold:
                    files1 = name_groups[name1]
                    files2 = name_groups[name2]
                    
                    # Avoid duplicating exact matches
                    if name1 != name2:
                        fuzzy_matches.append({
                            'files': [f[0] for f in files1 + files2],
                            'normalized_name': f"{name1} ~ {name2}",
                            'similarity_type': 'fuzzy_name',
                            'confidence': ratio
                        })
        
        similar_groups.extend(fuzzy_matches)
        
        # Strategy 3: Same size, same extension (potential duplicates)
        for size, size_files in by_size.items():
            if len(size_files) > 1 and size > 1024:  # Skip tiny files
                # Group by extension
                by_ext = defaultdict(list)
                for fp in size_files:
                    ext = os.path.splitext(fp)[1].lower()
                    by_ext[ext].append(fp)
                
                for ext, ext_files in by_ext.items():
                    if len(ext_files) > 1:
                        similar_groups.append({
                            'files': ext_files,
                            'normalized_name': f"Same size ({size} bytes) {ext}",
                            'similarity_type': 'size_match',
                            'confidence': 0.7
                        })
        
        return similar_groups


# =============================================================================
# 🎯 UNIFIED ANALYZER
# =============================================================================

class UnifiedAnalyzer:
    """
    Combines all analysis tools into a single, efficient pipeline.
    """
    
    def __init__(self):
        self.scanner = TurboScanner()
        self.duplicate_finder = SmartDuplicateFinder()
        self.project_detector = ProjectDetector()
        self.mismatch_analyzer = MismatchAnalyzer()
        self.similar_finder = SimilarFileFinder()
    
    def full_analysis(self, folder_path: str, 
                     progress_cb: Callable = None) -> Dict:
        """
        Run complete folder analysis.
        
        Returns comprehensive analysis result.
        """
        result = {
            'folder': folder_path,
            'timestamp': datetime.now().isoformat(),
            'scan': None,
            'project': None,
            'duplicates': None,
            'mismatches': None,
            'similar': None,
            'summary': {}
        }
        
        # Phase 1: Scan
        if progress_cb:
            progress_cb("Phase 1/5: Scanning folder...")
        
        result['scan'] = self.scanner.scan_folder(folder_path, progress_cb)
        
        # Phase 2: Project detection
        if progress_cb:
            progress_cb("Phase 2/5: Detecting project type...")
        
        result['project'] = self.project_detector.detect(result['scan'])
        
        # Phase 3: Duplicate detection
        if progress_cb:
            progress_cb("Phase 3/5: Finding duplicates...")
        
        result['duplicates'] = self.duplicate_finder.find_duplicates(result['scan'], progress_cb)
        
        # Phase 4: Mismatch analysis
        if progress_cb:
            progress_cb("Phase 4/5: Analyzing mismatches...")
        
        result['mismatches'] = self.mismatch_analyzer.analyze(result['scan'], result['project'])
        
        # Phase 5: Similar files
        if progress_cb:
            progress_cb("Phase 5/5: Finding similar files...")
        
        result['similar'] = self.similar_finder.find_similar(result['scan'], progress_cb)
        
        # Build summary
        scan = result['scan']
        dupes = result['duplicates']
        proj = result['project']
        mism = result['mismatches']
        
        result['summary'] = {
            'total_files': scan['total_files'],
            'total_size': scan['total_size'],
            'scan_time': scan['scan_time'],
            'project_type': proj['type'],
            'project_confidence': proj['confidence'],
            'is_project': proj['is_project'],
            'duplicate_groups': len(dupes['groups']),
            'duplicate_files': dupes['total_duplicates'],
            'wasted_space': dupes['wasted_space'],
            'mismatched_files': mism['total_mismatched'],
            'should_separate': mism['should_separate'],
            'similar_groups': len(result['similar']),
            'health_score': self._calculate_health(result)
        }
        
        return result
    
    def _calculate_health(self, result: Dict) -> int:
        """Calculate folder health score (0-100)."""
        score = 100
        
        scan = result['scan']
        dupes = result['duplicates']
        mism = result['mismatches']
        
        total_files = scan['total_files'] or 1
        
        # Penalize duplicates
        dupe_ratio = dupes['total_duplicates'] / total_files
        score -= int(dupe_ratio * 30)
        
        # Penalize mismatches
        mism_ratio = mism['total_mismatched'] / total_files
        score -= int(mism_ratio * 20)
        
        # Penalize unorganized (many similar files)
        similar_ratio = len(result['similar']) / total_files if total_files > 0 else 0
        score -= int(similar_ratio * 10)
        
        return max(0, min(100, score))


def format_analysis_report(result: Dict) -> str:
    """Format analysis result for display."""
    lines = []
    
    lines.append("=" * 70)
    lines.append("📊 ADVANCED FOLDER ANALYSIS")
    lines.append("=" * 70)
    
    summary = result.get('summary', {})
    scan = result.get('scan', {})
    proj = result.get('project', {})
    
    # Basic info
    lines.append(f"\n📁 Folder: {result.get('folder', 'Unknown')}")
    lines.append(f"📅 Analyzed: {result.get('timestamp', '')[:19]}")
    lines.append(f"⏱️ Scan time: {scan.get('scan_time', 0):.2f}s")
    
    # Health score
    health = summary.get('health_score', 0)
    health_bar = "█" * (health // 10) + "░" * (10 - health // 10)
    health_emoji = "🟢" if health >= 80 else "🟡" if health >= 50 else "🔴"
    
    lines.append(f"\n{'─' * 60}")
    lines.append(f"🏥 HEALTH SCORE: {health_emoji} {health}/100 [{health_bar}]")
    lines.append(f"{'─' * 60}")
    
    # Stats
    def fmt_size(b):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if b < 1024:
                return f"{b:.1f} {unit}"
            b /= 1024
        return f"{b:.1f} TB"
    
    lines.append(f"\n📊 STATISTICS")
    lines.append(f"  📄 Files: {summary.get('total_files', 0):,}")
    lines.append(f"  📦 Size: {fmt_size(summary.get('total_size', 0))}")
    lines.append(f"  📁 Folders: {scan.get('total_folders', 0):,}")
    
    # Project info
    lines.append(f"\n🎯 PROJECT DETECTION")
    lines.append(f"  🏷️ Type: {proj.get('type', 'Unknown')}")
    lines.append(f"  📊 Confidence: {proj.get('confidence', 0):.0%}")
    
    if proj.get('indicators'):
        lines.append(f"  📋 Indicators:")
        for ind in proj['indicators'][:5]:
            lines.append(f"     • {ind}")
    
    # Duplicates
    dupes = result.get('duplicates', {})
    lines.append(f"\n🔄 DUPLICATES")
    lines.append(f"  📦 Groups: {len(dupes.get('groups', []))}")
    lines.append(f"  📄 Files: {dupes.get('total_duplicates', 0)}")
    lines.append(f"  💾 Wasted: {fmt_size(dupes.get('wasted_space', 0))}")
    
    # Mismatches
    mism = result.get('mismatches', {})
    lines.append(f"\n⚠️ MISMATCHES")
    lines.append(f"  📄 Found: {mism.get('total_mismatched', 0)}")
    lines.append(f"  💡 {mism.get('recommendation', 'N/A')}")
    
    # Similar files
    similar = result.get('similar', [])
    lines.append(f"\n🔗 SIMILAR FILES")
    lines.append(f"  📦 Groups: {len(similar)}")
    
    if similar:
        lines.append(f"  📋 Top groups:")
        for grp in similar[:3]:
            lines.append(f"     • {grp['normalized_name']} ({len(grp['files'])} files)")
    
    lines.append("\n" + "=" * 70)
    
    return "\n".join(lines)


# =============================================================================
# 🔧 CONVENIENCE FUNCTIONS
# =============================================================================

def turbo_scan(folder_path: str, progress_cb: Callable = None) -> Dict:
    """Quick folder scan using parallel processing."""
    scanner = TurboScanner()
    return scanner.scan_folder(folder_path, progress_cb)


def find_duplicates_fast(folder_path: str, progress_cb: Callable = None) -> Dict:
    """Find duplicates using optimized 3-phase algorithm."""
    scan = turbo_scan(folder_path, progress_cb)
    finder = SmartDuplicateFinder()
    return finder.find_duplicates(scan, progress_cb)


def analyze_folder_complete(folder_path: str, progress_cb: Callable = None) -> Dict:
    """Run complete unified analysis."""
    analyzer = UnifiedAnalyzer()
    return analyzer.full_analysis(folder_path, progress_cb)


# Save cache on exit
import atexit
atexit.register(_file_cache.save)
