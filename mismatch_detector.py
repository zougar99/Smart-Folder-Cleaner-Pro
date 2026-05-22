# -*- coding: utf-8 -*-
"""
Mismatch Detector - Find files that DON'T BELONG in a folder.
Uses folder analysis to identify out-of-place files.
"""
import os
import json
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
from folder_analyzer import analyze_folder_purpose, get_all_files_deep


def find_mismatched_files(folder_path: str, use_ai: bool = True) -> dict:
    """
    Analyze folder and find files that don't belong.
    Returns: analysis + list of mismatched files with reasons.
    """
    # First, analyze the folder purpose
    analysis = analyze_folder_purpose(folder_path)
    if "error" in analysis:
        return analysis
    
    # Get all files
    all_files = get_all_files_deep(folder_path)
    
    expected_exts = set(analysis.get("expected_extensions", []))
    unexpected_exts = set(analysis.get("unexpected_extensions", []))
    category = analysis.get("category", "unknown")
    
    matched_files = []
    mismatched_files = []
    
    for f in all_files:
        ext = f.get("ext", "").lower()
        name = f.get("name", "").lower()
        
        # Skip common files that belong everywhere
        if name in [".gitignore", ".env", "license", "license.md", "license.txt", 
                    "readme.md", "readme.txt", "changelog.md", ".editorconfig"]:
            matched_files.append({**f, "status": "common_file"})
            continue
        
        # Check if extension is expected or unexpected
        is_expected = ext in expected_exts if expected_exts else None
        is_unexpected = ext in unexpected_exts if unexpected_exts else False
        
        if is_unexpected:
            mismatched_files.append({
                **f,
                "status": "mismatched",
                "reason": f"Extension {ext} doesn't belong in {category} folder"
            })
        elif is_expected:
            matched_files.append({**f, "status": "matched"})
        elif expected_exts:  # Has expectations but this ext not in list
            # Could be mismatched, need AI to decide
            mismatched_files.append({
                **f,
                "status": "possibly_mismatched",
                "reason": f"Extension {ext} is unusual for {category} folder"
            })
        else:
            matched_files.append({**f, "status": "unknown"})
    
    # If AI is enabled, refine the mismatch detection
    if use_ai and DEEPSEEK_API_KEY and mismatched_files:
        mismatched_files = _refine_with_ai(analysis, mismatched_files)
    
    return {
        "folder_path": folder_path,
        "folder_name": analysis.get("folder_name"),
        "purpose": analysis.get("purpose"),
        "category": category,
        "description": analysis.get("description"),
        "total_files": len(all_files),
        "matched_count": len(matched_files),
        "mismatched_count": len(mismatched_files),
        "matched_files": matched_files,
        "mismatched_files": mismatched_files,
    }


def _refine_with_ai(analysis: dict, mismatched_files: list) -> list:
    """Use AI to confirm/refine mismatch detection."""
    if not mismatched_files:
        return mismatched_files
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
        
        # Sample files for AI (limit to 30)
        sample = mismatched_files[:30]
        file_list = "\n".join([f"- {f['rel_path']}" for f in sample])
        
        prompt = f"""This folder is: {analysis.get('purpose', 'unknown')}
Category: {analysis.get('category', 'unknown')}

These files were flagged as possibly NOT belonging here:
{file_list}

For each file, tell me:
1. Does it REALLY not belong here? (yes/no/maybe)
2. Why?

Reply in JSON format:
{{
    "file_path": {{"belongs": "yes/no/maybe", "reason": "explanation"}},
    ...
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
        
        ai_results = json.loads(text)
        
        # Update mismatched files with AI assessment
        refined = []
        for f in mismatched_files:
            rel_path = f.get("rel_path", "")
            ai_info = ai_results.get(rel_path, {})
            
            belongs = ai_info.get("belongs", "maybe")
            if belongs == "yes":
                f["status"] = "ai_approved"
                f["reason"] = ai_info.get("reason", "AI says it belongs here")
            elif belongs == "no":
                f["status"] = "ai_confirmed_mismatch"
                f["reason"] = ai_info.get("reason", f["reason"])
                refined.append(f)
            else:
                f["status"] = "possibly_mismatched"
                refined.append(f)
        
        return refined
        
    except Exception:
        return mismatched_files


def analyze_multiple_folders(parent_path: str) -> list:
    """Analyze all subfolders in a directory."""
    results = []
    parent_path = os.path.abspath(parent_path)
    
    if not os.path.isdir(parent_path):
        return [{"error": "Not a valid directory"}]
    
    for item in os.listdir(parent_path):
        folder_path = os.path.join(parent_path, item)
        if os.path.isdir(folder_path):
            # Skip system folders
            if item.lower() in ["$recycle.bin", "system volume information", ".git"]:
                continue
            result = find_mismatched_files(folder_path, use_ai=True)
            result["folder_name"] = item
            results.append(result)
    
    return results


def get_separation_plan(mismatched_files: list, dest_folder: str) -> list:
    """
    Create a plan to move mismatched files to a destination folder.
    Preserves relative structure.
    """
    plan = []
    dest_folder = os.path.abspath(dest_folder)
    
    for f in mismatched_files:
        src = f.get("path", "")
        if not src or not os.path.isfile(src):
            continue
        
        # Create destination path
        name = f.get("name", os.path.basename(src))
        ext = f.get("ext", "").lower()
        
        # Organize by type in destination
        if ext in [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"]:
            sub = "images"
        elif ext in [".mp3", ".wav", ".flac", ".m4a", ".ogg"]:
            sub = "audio"
        elif ext in [".mp4", ".avi", ".mkv", ".mov", ".webm"]:
            sub = "videos"
        elif ext in [".doc", ".docx", ".pdf", ".xlsx", ".pptx", ".txt"]:
            sub = "documents"
        elif ext in [".exe", ".msi", ".dll"]:
            sub = "executables"
        elif ext in [".zip", ".rar", ".7z", ".tar", ".gz"]:
            sub = "archives"
        else:
            sub = "other"
        
        dest_path = os.path.join(dest_folder, sub, name)
        
        plan.append({
            "src": src,
            "dest": dest_path,
            "reason": f.get("reason", "Doesn't belong"),
            "size": f.get("size", 0),
        })
    
    return plan
