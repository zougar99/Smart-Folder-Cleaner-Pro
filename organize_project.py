# -*- coding: utf-8 -*-
"""
Organize project files into proper folder structure.
"""
import os
import shutil

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# Define the new structure
STRUCTURE = {
    "core": {
        "description": "Core application modules",
        "files": [
            "main_gui.py",
            "config.py",
            "settings_manager.py",
            "backup_manager.py",
        ]
    },
    "analyzers": {
        "description": "Analysis and AI modules",
        "files": [
            "ai_categorizer.py",
            "ai_deep_analyzer.py",
            "ai_pc_organizer.py",
            "project_analyzer.py",
            "folder_analyzer.py",
            "mismatch_detector.py",
            "duplicate_detector.py",
            "advanced_algorithms.py",
            "smart_algorithms.py",
        ]
    },
    "tools": {
        "description": "Utility tools",
        "files": [
            "file_tools.py",
            "extra_tools.py",
            "folder_info.py",
            "scanner.py",
            "organizer.py",
            "smart_organizer.py",
            "pc_analyzer.py",
            "system_diagnostics.py",
        ]
    },
    "scripts": {
        "description": "Test and utility scripts",
        "files": [
            "test_scan_d.py",
            "organize_d_drive.py",
            "undo_organization.py",
            "fast_restore.py",
            "deep_restore.py",
            "smart_restore.py",
        ]
    },
}

def main():
    print("=" * 60)
    print("📁 ORGANIZING PROJECT FILES")
    print("=" * 60)
    print()
    
    # Create folders and move files
    for folder_name, folder_info in STRUCTURE.items():
        folder_path = os.path.join(PROJECT_ROOT, folder_name)
        
        print(f"📂 Creating {folder_name}/")
        print(f"   {folder_info['description']}")
        
        os.makedirs(folder_path, exist_ok=True)
        
        # Create __init__.py for Python packages
        init_file = os.path.join(folder_path, "__init__.py")
        if not os.path.exists(init_file):
            with open(init_file, 'w') as f:
                f.write(f'# {folder_info["description"]}\n')
        
        # Move files
        for filename in folder_info['files']:
            src = os.path.join(PROJECT_ROOT, filename)
            dst = os.path.join(folder_path, filename)
            
            if os.path.exists(src):
                shutil.move(src, dst)
                print(f"   ✅ {filename}")
            else:
                print(f"   ⚠️ {filename} (not found)")
        
        print()
    
    # Clean up temp files
    print("🧹 Cleaning up...")
    
    # Remove test result files
    cleanup_files = [
        "d_drive_scan_result.txt",
        ".file_cache.json",
    ]
    
    for filename in cleanup_files:
        filepath = os.path.join(PROJECT_ROOT, filename)
        if os.path.exists(filepath):
            os.remove(filepath)
            print(f"   🗑️ Removed {filename}")
    
    # Clean tmp folder (keep folder, remove old summaries)
    tmp_folder = os.path.join(PROJECT_ROOT, "tmp")
    if os.path.exists(tmp_folder):
        for f in os.listdir(tmp_folder):
            if f.startswith("summary-"):
                os.remove(os.path.join(tmp_folder, f))
        print(f"   🗑️ Cleaned tmp folder")
    
    print()
    print("=" * 60)
    print("✅ PROJECT ORGANIZED!")
    print("=" * 60)
    print()
    print("📁 NEW STRUCTURE:")
    print("""
Smart Folder Cleaner/
│
├── main_gui.py          # Keep in root (entry point)
├── config.py            # Keep in root (configuration)
├── requirements.txt     # Dependencies
├── run.bat              # Launcher
├── .env                 # API keys
│
├── core/                # Core modules
│   ├── settings_manager.py
│   └── backup_manager.py
│
├── analyzers/           # AI & Analysis
│   ├── ai_categorizer.py
│   ├── ai_deep_analyzer.py
│   ├── ai_pc_organizer.py
│   ├── project_analyzer.py
│   ├── folder_analyzer.py
│   ├── mismatch_detector.py
│   ├── duplicate_detector.py
│   ├── advanced_algorithms.py
│   └── smart_algorithms.py
│
├── tools/               # Utilities
│   ├── file_tools.py
│   ├── extra_tools.py
│   ├── folder_info.py
│   ├── scanner.py
│   ├── organizer.py
│   ├── smart_organizer.py
│   ├── pc_analyzer.py
│   └── system_diagnostics.py
│
├── scripts/             # Test scripts
│   ├── test_scan_d.py
│   └── ...
│
└── tmp/                 # Temporary files
""")

if __name__ == "__main__":
    main()
