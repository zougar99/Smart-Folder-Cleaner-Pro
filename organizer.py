# -*- coding: utf-8 -*-
"""
Organize files: by type (documents, images, ...) and/or by AI-suggested folder.
Supports move, copy, and simulation (no actual move/copy).
"""
import os
import shutil
from scanner import get_summary_by_category, EXT_CATEGORIES, _category_for_ext
from ai_categorizer import categorize_with_ai


def organize_files(
    files: list,
    dest_dir: str,
    by_type: bool = True,
    by_ai: bool = False,
    move: bool = True,
    simulation: bool = False,
    progress_cb=None,
):
    """
    Organize files into dest_dir.
    - by_type: create subdirs like documents/, images/, pdf/, ...
    - by_ai: use AI to suggest subfolder per file (e.g. invoices, vacation_photos)
    - move: True = move, False = copy
    - simulation: if True, don't actually move/copy; return planned actions.
    Returns list of dicts: { action, src, dest, error? }.
    """
    dest_dir = os.path.abspath(dest_dir)
    results = []
    os.makedirs(dest_dir, exist_ok=True)

    # AI categories for file names (batch)
    ai_map = {}
    if by_ai and files:
        names = [os.path.basename(f.get("path", "")) for f in files]
        ai_map = categorize_with_ai(names)

    for i, f in enumerate(files):
        src = f.get("path") or f.get("path", "")
        if not src or not os.path.isfile(src):
            continue
        name = f.get("name") or os.path.basename(src)
        category = f.get("category", "other")

        # Target subdir
        if by_ai and name in ai_map:
            sub = ai_map[name]
        elif by_type:
            sub = category
        else:
            sub = "other"
        sub = (sub or "other").strip().replace(" ", "_")
        target_dir = os.path.join(dest_dir, sub)
        dest_path = os.path.join(target_dir, name)

        # Deduplicate dest_path if file exists
        if os.path.exists(dest_path) and not simulation:
            base, ext = os.path.splitext(name)
            n = 1
            while os.path.exists(dest_path):
                dest_path = os.path.join(target_dir, f"{base}_{n}{ext}")
                n += 1

        action = "move" if move else "copy"
        if simulation:
            results.append({"action": action, "src": src, "dest": dest_path, "simulation": True})
        else:
            try:
                os.makedirs(target_dir, exist_ok=True)
                if move:
                    shutil.move(src, dest_path)
                else:
                    shutil.copy2(src, dest_path)
                results.append({"action": action, "src": src, "dest": dest_path})
            except Exception as e:
                results.append({"action": action, "src": src, "dest": dest_path, "error": str(e)})
        if progress_cb:
            progress_cb(i + 1, len(files))
    return results
