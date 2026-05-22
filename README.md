# 🧹 Smart Folder Cleaner Pro

Intelligent file organization and PC maintenance tool with AI capabilities.

## 🚀 How to Run

```batch
run.bat
```
Or:
```bash
py -3 main_gui.py
```

## 📁 Project Structure

```
Smart Folder Cleaner/
│
├── main_gui.py              # 🖥️ Main application (GUI)
├── config.py                # ⚙️ Configuration & API keys
├── requirements.txt         # 📦 Dependencies
├── run.bat                  # 🚀 Launcher script
├── .env                     # 🔑 API keys (DEEPSEEK_API_KEY)
│
├── 📊 ANALYSIS MODULES:
│   ├── ai_deep_analyzer.py      # 🤖 AI folder analysis
│   ├── ai_pc_organizer.py       # 🖥️ Full PC organization
│   ├── ai_categorizer.py        # 📂 File categorization
│   ├── project_analyzer.py      # 💻 Project detection
│   ├── folder_analyzer.py       # 📁 Folder analysis
│   ├── mismatch_detector.py     # ⚠️ Find mismatched files
│   ├── duplicate_detector.py    # 🔄 Find duplicates
│   ├── advanced_algorithms.py   # ⚡ Optimized algorithms
│   └── smart_algorithms.py      # 🧠 Smart detection
│
├── 🔧 TOOL MODULES:
│   ├── file_tools.py            # 📄 File operations
│   ├── extra_tools.py           # 🔧 Extra utilities
│   ├── folder_info.py           # ℹ️ Folder information
│   ├── scanner.py               # 🔍 File scanner
│   ├── organizer.py             # 📦 File organizer
│   ├── smart_organizer.py       # 🧠 Smart organizer
│   ├── pc_analyzer.py           # 🖥️ PC health check
│   └── system_diagnostics.py    # 🔧 Windows diagnostics
│
├── 💾 MANAGEMENT:
│   ├── settings_manager.py      # ⚙️ User settings
│   └── backup_manager.py        # 💾 Backup & undo
│
└── 📂 FOLDERS:
    ├── .cursor/                 # Cursor IDE settings
    ├── .vscode/                 # VS Code settings
    └── tmp/                     # Temporary files
```

## ✨ Features

### 📊 Analysis Tab
- **Re-analyze** - Basic folder analysis
- **AI Analyze** - Deep AI analysis (reads file contents)
- **Turbo Scan** - Fast parallel scanning
- **Full Report** - Complete 5-phase analysis with health score

### 🖥️ PC Tab
- **Health Scan** - Find junk, large files, old downloads
- **System Check** - Windows errors, services, security
- **Auto-Fix** - Fix detected problems automatically
- **AI Organizer** - Scan & organize entire PC

### 📋 Other Tabs
- **Info** - Folder statistics
- **Search** - File search with wildcards
- **Duplicates** - Find duplicate files
- **Big Files** - Find large files
- **Old Files** - Find old/unused files
- **Empty** - Find empty folders
- **Rename** - Batch rename files
- **Disk** - Disk usage analysis
- **ZIP** - Compress/extract archives
- **Sync** - Folder synchronization
- **Links** - Find broken shortcuts
- **Similar** - Find similar files
- **Settings** - Customize behavior
- **Undo** - Restore moved files

## 🛡️ Safety Features

- **Project Protection** - Detects and protects code projects
- **Smart Name Analysis** - Understands folder/file purposes
- **Simulation Mode** - Preview before executing
- **Full Undo** - Restore any operation
- **Backup System** - Automatic backups before changes

## 📝 Requirements

```
customtkinter
python-dotenv
openai
```

## 🔑 API Key (Optional)

For AI features, add to `.env`:
```
DEEPSEEK_API_KEY=your_key_here
```

Without API key, smart rule-based analysis is used instead.
