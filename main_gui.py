# -*- coding: utf-8 -*-
"""
Smart Folder Cleaner – Complete GUI
Features: Info, Search, Analysis, Duplicates, Big Files, Old Files, Empty Folders, Export
"""
import os
import subprocess
import threading
import time
from datetime import datetime
from tkinter import filedialog, messagebox

import customtkinter as ctk

from config import DEEPSEEK_API_KEY
from folder_info import get_folder_details, generate_folder_report, format_size
from mismatch_detector import find_mismatched_files, get_separation_plan
from smart_organizer import execute_separation, get_undo_logs, undo_separation
from duplicate_detector import find_duplicates, get_duplicate_cleanup_plan
from file_tools import (
    search_files, find_empty_folders, delete_empty_folders,
    find_big_files, find_old_files, export_report, generate_full_report
)
from settings_manager import (
    load_settings, save_settings, reset_settings, format_settings_display
)
from project_analyzer import (
    detect_project_type, find_unrelated_files, get_cleanup_plan, format_analysis_report
)
from backup_manager import (
    get_all_backups, get_backup_details, restore_backup, 
    format_backup_list, quick_restore_last, get_last_backup
)
from ai_deep_analyzer import (
    ai_analyze_folder, format_ai_analysis, get_ai_cleanup_plan
)
from extra_tools import (
    batch_rename_preview, batch_rename_execute, format_rename_preview,
    analyze_disk_usage, format_disk_analysis,
    compress_folder, extract_archive, format_compress_result,
    compare_folders, sync_folders, format_folder_comparison,
    find_broken_shortcuts, delete_broken_shortcuts, format_broken_shortcuts
)
from smart_algorithms import (
    fast_scan, find_duplicates_smart, find_similar_files, find_backup_files,
    score_project, score_mismatch, build_ai_context
)
from pc_analyzer import (
    run_full_pc_analysis, format_pc_analysis, get_disk_info, format_size as pc_format_size
)
from system_diagnostics import (
    run_full_diagnostics, format_diagnostics, fix_problem, fix_all_auto, is_admin
)
from advanced_algorithms import (
    UnifiedAnalyzer, TurboScanner, SmartDuplicateFinder, ProjectDetector,
    analyze_folder_complete, format_analysis_report as format_advanced_report, turbo_scan
)
from ai_pc_organizer import (
    PCScanner, FileOrganizer, scan_pc_full, organize_files,
    format_scan_report, format_size as ai_format_size
)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

WINDOW_SIZE = "1350x980"
TMP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tmp")
os.makedirs(TMP_DIR, exist_ok=True)

# ===== MODERN COLOR SCHEME =====
COLORS = {
    "primary": "#6366f1",       # Indigo
    "primary_hover": "#4f46e5",
    "secondary": "#8b5cf6",     # Purple
    "success": "#10b981",       # Emerald
    "success_hover": "#059669",
    "danger": "#ef4444",        # Red
    "danger_hover": "#dc2626",
    "warning": "#f59e0b",       # Amber
    "info": "#06b6d4",          # Cyan
    "info_hover": "#0891b2",
    "dark": "#1e1e2e",          # Dark bg
    "darker": "#181825",        # Darker bg
    "card": "#313244",          # Card bg
    "text": "#cdd6f4",          # Light text
    "text_dim": "#6c7086",      # Dim text
    "border": "#45475a",        # Border
    "accent1": "#f38ba8",       # Pink
    "accent2": "#a6e3a1",       # Green
    "accent3": "#89b4fa",       # Blue
    "accent4": "#fab387",       # Peach
}


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("🧹 Smart Folder Cleaner Pro")
        self.geometry(WINDOW_SIZE)
        self.configure(fg_color=COLORS["darker"])
        
        # Data storage
        self._folder_info = None
        self._analysis_result = None
        self._mismatched_files = []
        self._duplicate_result = None
        self._big_files = []
        self._old_files = {}
        self._empty_folders = []
        self._search_results = []
        self._settings = load_settings()
        self._ai_analysis = None
        self._complete_analysis = None
        
        # New tools data
        self._rename_preview = []
        self._disk_result = None
        self._sync_result = None
        self._broken_links = []
        self._similar_files = []
        self._backup_files = []
        self._fast_scan_result = None
        
        self._build_ui()
    
    def _build_ui(self):
        # ===== HEADER BANNER =====
        header = ctk.CTkFrame(self, fg_color=COLORS["primary"], corner_radius=0, height=50)
        header.pack(fill="x")
        header.pack_propagate(False)
        
        title_frame = ctk.CTkFrame(header, fg_color="transparent")
        title_frame.pack(side="left", padx=20, pady=10)
        
        ctk.CTkLabel(title_frame, text="🧹", font=("Segoe UI", 24), text_color="white").pack(side="left")
        ctk.CTkLabel(title_frame, text="Smart Folder Cleaner", font=("Segoe UI", 18, "bold"), 
                    text_color="white").pack(side="left", padx=10)
        ctk.CTkLabel(title_frame, text="PRO", font=("Segoe UI", 10, "bold"), text_color=COLORS["warning"],
                    fg_color=COLORS["darker"], corner_radius=5, padx=8, pady=2).pack(side="left")
        
        # Status in header
        self.label_status = ctk.CTkLabel(header, text="● Ready", text_color=COLORS["accent2"], 
                                         font=("Segoe UI", 12, "bold"))
        self.label_status.pack(side="right", padx=20)
        
        # ===== TOP: Folder Selection =====
        top = ctk.CTkFrame(self, fg_color=COLORS["card"], corner_radius=10)
        top.pack(fill="x", padx=15, pady=10)
        
        # Folder input row
        input_row = ctk.CTkFrame(top, fg_color="transparent")
        input_row.pack(fill="x", padx=15, pady=12)
        
        ctk.CTkLabel(input_row, text="📁 Folder:", font=("Segoe UI", 12, "bold"), 
                    text_color=COLORS["text"]).pack(side="left", padx=(0, 10))
        
        self.entry_folder = ctk.CTkEntry(input_row, width=450, height=38,
                                         placeholder_text="Choose a folder to analyze...", 
                                         font=("Segoe UI", 12),
                                         fg_color=COLORS["darker"],
                                         border_color=COLORS["border"],
                                         corner_radius=8)
        self.entry_folder.pack(side="left", padx=5)
        
        ctk.CTkButton(input_row, text="📂 Browse", width=100, height=38, 
                     fg_color=COLORS["dark"], hover_color=COLORS["border"],
                     font=("Segoe UI", 11), corner_radius=8,
                     command=self._browse_folder).pack(side="left", padx=5)
        
        # Action buttons row
        btn_row = ctk.CTkFrame(top, fg_color="transparent")
        btn_row.pack(fill="x", padx=15, pady=(0, 12))
        
        ctk.CTkButton(btn_row, text="🤖 AI Analyze", width=130, height=36,
                     fg_color=COLORS["secondary"], hover_color="#7c3aed",
                     font=("Segoe UI", 11, "bold"), corner_radius=8,
                     command=self._run_ai_analysis).pack(side="left", padx=3)
        
        ctk.CTkButton(btn_row, text="📊 Full Scan", width=120, height=36,
                     fg_color=COLORS["success"], hover_color=COLORS["success_hover"],
                     font=("Segoe UI", 11, "bold"), corner_radius=8,
                     command=self._run_full_scan).pack(side="left", padx=3)
        
        ctk.CTkButton(btn_row, text="⚡ Fast Scan", width=110, height=36,
                     fg_color=COLORS["info"], hover_color=COLORS["info_hover"],
                     font=("Segoe UI", 11, "bold"), corner_radius=8,
                     command=self._run_fast_scan).pack(side="left", padx=3)
        
        ctk.CTkButton(btn_row, text="💾 Export", width=90, height=36,
                     fg_color=COLORS["dark"], hover_color=COLORS["border"],
                     font=("Segoe UI", 11), corner_radius=8,
                     command=self._export_report).pack(side="left", padx=3)
        
        # Quick stats
        self.label_quick_stats = ctk.CTkLabel(btn_row, text="", 
                                              font=("Segoe UI", 10), text_color=COLORS["text_dim"])
        self.label_quick_stats.pack(side="right", padx=10)
        
        # ===== TABS =====
        self.tabview = ctk.CTkTabview(self, width=1300, height=620,
                                      fg_color=COLORS["dark"],
                                      segmented_button_fg_color=COLORS["darker"],
                                      segmented_button_selected_color=COLORS["primary"],
                                      segmented_button_selected_hover_color=COLORS["primary_hover"],
                                      segmented_button_unselected_color=COLORS["darker"],
                                      segmented_button_unselected_hover_color=COLORS["card"],
                                      corner_radius=12)
        self.tabview.pack(fill="both", expand=True, padx=15, pady=10)
        
        # Create tabs with categories
        self.tabview.add("📁 Info")
        self.tabview.add("🔍 Search")
        self.tabview.add("🎯 Analysis")
        self.tabview.add("🖥️ PC")
        self.tabview.add("📋 Duplicates")
        self.tabview.add("🔀 Similar")
        self.tabview.add("📦 Big")
        self.tabview.add("🕐 Old")
        self.tabview.add("🗑️ Empty")
        self.tabview.add("📝 Rename")
        self.tabview.add("📊 Disk")
        self.tabview.add("🗜️ ZIP")
        self.tabview.add("🔄 Sync")
        self.tabview.add("🔗 Links")
        self.tabview.add("⚙️ Settings")
        self.tabview.add("📜 Undo")
        
        self._build_info_tab()
        self._build_search_tab()
        self._build_analysis_tab()
        self._build_pc_tab()
        self._build_duplicates_tab()
        self._build_similar_tab()
        self._build_bigfiles_tab()
        self._build_oldfiles_tab()
        self._build_empty_tab()
        self._build_rename_tab()
        self._build_disk_tab()
        self._build_compress_tab()
        self._build_sync_tab()
        self._build_links_tab()
        self._build_settings_tab()
        self._build_undo_tab()
        
        # ===== BOTTOM: Status Bar =====
        bottom = ctk.CTkFrame(self, fg_color=COLORS["darker"], corner_radius=0, height=35)
        bottom.pack(fill="x", side="bottom")
        bottom.pack_propagate(False)
        
        # Left side - action status
        self.label_action_status = ctk.CTkLabel(bottom, text="", text_color=COLORS["text_dim"], 
                                                font=("Segoe UI", 10))
        self.label_action_status.pack(side="left", padx=15, pady=8)
        
        # Right side - version info
        ctk.CTkLabel(bottom, text="v2.0 Pro", text_color=COLORS["text_dim"],
                    font=("Segoe UI", 9)).pack(side="right", padx=15, pady=8)
        
        # Center - tips
        tips = ["💡 Tip: Use AI Analyze for smart detection", "💡 Tip: Ctrl+S to export report",
                "💡 Tip: Check Similar tab for near-duplicates"]
        import random
        ctk.CTkLabel(bottom, text=random.choice(tips), text_color=COLORS["text_dim"],
                    font=("Segoe UI", 9, "italic")).pack(side="right", padx=50, pady=8)
    
    # ===== STYLE HELPERS =====
    def _create_card(self, parent, title="", icon="📁"):
        """Create a styled card frame."""
        card = ctk.CTkFrame(parent, fg_color=COLORS["card"], corner_radius=12)
        
        if title:
            header = ctk.CTkFrame(card, fg_color="transparent")
            header.pack(fill="x", padx=15, pady=(12, 5))
            
            ctk.CTkLabel(header, text=f"{icon} {title}", 
                        font=("Segoe UI", 13, "bold"),
                        text_color=COLORS["text"]).pack(side="left")
        
        return card
    
    def _create_button(self, parent, text, command, style="default", width=120):
        """Create a styled button."""
        styles = {
            "default": (COLORS["dark"], COLORS["border"]),
            "primary": (COLORS["primary"], COLORS["primary_hover"]),
            "success": (COLORS["success"], COLORS["success_hover"]),
            "danger": (COLORS["danger"], COLORS["danger_hover"]),
            "info": (COLORS["info"], COLORS["info_hover"]),
            "secondary": (COLORS["secondary"], "#7c3aed"),
            "warning": (COLORS["warning"], "#d97706"),
        }
        
        fg, hover = styles.get(style, styles["default"])
        text_color = "black" if style == "warning" else "white"
        
        return ctk.CTkButton(parent, text=text, command=command,
                            width=width, height=34,
                            fg_color=fg, hover_color=hover,
                            font=("Segoe UI", 11), corner_radius=8,
                            text_color=text_color)
    
    def _create_textbox(self, parent):
        """Create a styled textbox."""
        return ctk.CTkTextbox(parent, wrap="word", 
                             font=("JetBrains Mono", 10),
                             fg_color=COLORS["darker"],
                             border_color=COLORS["border"],
                             border_width=1,
                             corner_radius=8,
                             text_color=COLORS["text"])
    
    def _create_entry(self, parent, width=300, placeholder=""):
        """Create a styled entry."""
        return ctk.CTkEntry(parent, width=width, height=36,
                           placeholder_text=placeholder,
                           font=("Segoe UI", 11),
                           fg_color=COLORS["darker"],
                           border_color=COLORS["border"],
                           corner_radius=8)
    
    def _create_label(self, parent, text, style="normal"):
        """Create a styled label."""
        styles = {
            "normal": (COLORS["text"], ("Segoe UI", 11)),
            "title": (COLORS["text"], ("Segoe UI", 14, "bold")),
            "subtitle": (COLORS["text_dim"], ("Segoe UI", 10)),
            "accent": (COLORS["accent3"], ("Segoe UI", 11, "bold")),
            "success": (COLORS["accent2"], ("Segoe UI", 11)),
            "warning": (COLORS["warning"], ("Segoe UI", 11)),
            "danger": (COLORS["danger"], ("Segoe UI", 11)),
        }
        
        color, font = styles.get(style, styles["normal"])
        return ctk.CTkLabel(parent, text=text, text_color=color, font=font)
    
    # ===== TAB BUILDERS =====
    def _build_info_tab(self):
        frame = self.tabview.tab("📁 Info")
        frame.configure(fg_color=COLORS["dark"])
        
        # Stats Card
        stats_card = self._create_card(frame, "Folder Statistics", "📊")
        stats_card.pack(fill="x", padx=10, pady=8)
        
        stats_content = ctk.CTkFrame(stats_card, fg_color="transparent")
        stats_content.pack(fill="x", padx=15, pady=10)
        
        # Stats grid
        self.label_folder_path = self._create_label(stats_content, "📍 Path: Select a folder...", "subtitle")
        self.label_folder_path.pack(anchor="w", pady=2)
        
        stats_row = ctk.CTkFrame(stats_content, fg_color="transparent")
        stats_row.pack(fill="x", pady=8)
        
        # Stat boxes
        for i, (icon, label, var_name) in enumerate([
            ("💾", "Size", "size_stat"),
            ("📄", "Files", "files_stat"),
            ("📁", "Folders", "folders_stat"),
        ]):
            box = ctk.CTkFrame(stats_row, fg_color=COLORS["darker"], corner_radius=8, width=150, height=60)
            box.pack(side="left", padx=5)
            box.pack_propagate(False)
            
            ctk.CTkLabel(box, text=icon, font=("Segoe UI", 20)).pack(pady=(8, 0))
            lbl = ctk.CTkLabel(box, text="—", font=("Segoe UI", 12, "bold"), text_color=COLORS["accent3"])
            lbl.pack()
            ctk.CTkLabel(box, text=label, font=("Segoe UI", 9), text_color=COLORS["text_dim"]).pack()
            setattr(self, f"label_{var_name}", lbl)
        
        # Refresh button
        btn_row = ctk.CTkFrame(stats_content, fg_color="transparent")
        btn_row.pack(fill="x", pady=5)
        self._create_button(btn_row, "🔄 Refresh Info", self._run_folder_info, "info").pack(side="left")
        
        # Results textbox
        self.text_info = self._create_textbox(frame)
        self.text_info.pack(fill="both", expand=True, padx=10, pady=8)
        self.text_info.insert("1.0", "👋 Welcome to Smart Folder Cleaner Pro!\n\n" +
                             "1️⃣ Select a folder using the Browse button\n" +
                             "2️⃣ Click '📊 Full Scan' for complete analysis\n" +
                             "3️⃣ Or use '🤖 AI Analyze' for smart detection\n\n" +
                             "💡 Explore the tabs above for more tools!")
    
    def _build_search_tab(self):
        frame = self.tabview.tab("🔍 Search")
        frame.configure(fg_color=COLORS["dark"])
        
        # Search Card
        search_card = self._create_card(frame, "File Search", "🔍")
        search_card.pack(fill="x", padx=10, pady=8)
        
        search_content = ctk.CTkFrame(search_card, fg_color="transparent")
        search_content.pack(fill="x", padx=15, pady=10)
        
        # Search input row
        input_row = ctk.CTkFrame(search_content, fg_color="transparent")
        input_row.pack(fill="x", pady=5)
        
        self.entry_search = self._create_entry(input_row, 450, "Search files... (supports * and ? wildcards)")
        self.entry_search.pack(side="left", padx=(0, 10))
        self.entry_search.bind("<Return>", lambda e: self._run_search())
        
        self._create_button(input_row, "🔍 Search", self._run_search, "primary").pack(side="left")
        
        self.label_search_count = self._create_label(input_row, "", "accent")
        self.label_search_count.pack(side="left", padx=20)
        
        # Help text
        help_text = "💡 Examples: *.mp3 (all MP3) | report*.pdf (starts with report) | ???.txt (3 chars)"
        self._create_label(search_content, help_text, "subtitle").pack(anchor="w", pady=(10, 0))
        
        # Results
        self.text_search = self._create_textbox(frame)
        self.text_search.pack(fill="both", expand=True, padx=10, pady=8)
        self.text_search.insert("1.0", "🔍 Enter a search term above and press Enter or click Search.\n\n" +
                               "Wildcards:\n" +
                               "  • *     = any characters (photo*.jpg)\n" +
                               "  • ?     = single character (file?.txt)\n" +
                               "  • *.ext = all files with extension")
    
    def _build_analysis_tab(self):
        frame = self.tabview.tab("🎯 Analysis")
        frame.configure(fg_color=COLORS["dark"])
        
        # Analysis Card
        analysis_card = self._create_card(frame, "Project Analysis", "🎯")
        analysis_card.pack(fill="x", padx=10, pady=8)
        
        card_content = ctk.CTkFrame(analysis_card, fg_color="transparent")
        card_content.pack(fill="x", padx=15, pady=10)
        
        # Purpose display with badge
        purpose_row = ctk.CTkFrame(card_content, fg_color="transparent")
        purpose_row.pack(fill="x", pady=3)
        
        self._create_label(purpose_row, "Detected Type:", "normal").pack(side="left")
        self.label_purpose = ctk.CTkLabel(purpose_row, text="Not analyzed", 
                                          font=("Segoe UI", 11, "bold"),
                                          text_color=COLORS["accent4"],
                                          fg_color=COLORS["darker"],
                                          corner_radius=5, padx=10, pady=3)
        self.label_purpose.pack(side="left", padx=10)
        
        # Stats row with colored indicators
        stats_row = ctk.CTkFrame(card_content, fg_color="transparent")
        stats_row.pack(fill="x", pady=8)
        
        self.label_analysis_stats = self._create_label(stats_row, "📊 Run analysis to see results", "subtitle")
        self.label_analysis_stats.pack(side="left")
        
        # Action buttons
        btn_row = ctk.CTkFrame(card_content, fg_color="transparent")
        btn_row.pack(fill="x", pady=5)
        
        self._create_button(btn_row, "🔄 Re-analyze", self._run_analysis, "info").pack(side="left", padx=3)
        self._create_button(btn_row, "🤖 AI Analyze", self._run_ai_analysis, "secondary").pack(side="left", padx=3)
        self._create_button(btn_row, "⚡ Turbo Scan", self._run_turbo_analysis, "success").pack(side="left", padx=3)
        self._create_button(btn_row, "📊 Full Report", self._run_complete_analysis, "warning").pack(side="left", padx=3)
        
        # Results textbox
        self.text_analysis = self._create_textbox(frame)
        self.text_analysis.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Actions Card
        actions_card = self._create_card(frame, "Actions", "⚡")
        actions_card.pack(fill="x", padx=10, pady=8)
        
        actions_content = ctk.CTkFrame(actions_card, fg_color="transparent")
        actions_content.pack(fill="x", padx=15, pady=10)
        
        action_row = ctk.CTkFrame(actions_content, fg_color="transparent")
        action_row.pack(fill="x")
        
        self._create_label(action_row, "Move to:", "normal").pack(side="left", padx=(0, 10))
        self.entry_mismatch_dest = self._create_entry(action_row, 300, "Destination folder...")
        self.entry_mismatch_dest.pack(side="left", padx=5)
        self._create_button(action_row, "📂", lambda: self._browse_to(self.entry_mismatch_dest), "default", 40).pack(side="left", padx=3)
        
        self.var_mismatch_sim = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(action_row, text="Simulation", variable=self.var_mismatch_sim,
                       font=("Segoe UI", 10), text_color=COLORS["text"]).pack(side="left", padx=15)
        self._create_button(action_row, "🚀 Move Files", self._move_mismatched, "primary").pack(side="left", padx=5)
    
    def _build_pc_tab(self):
        """Build the PC Health Analyzer tab."""
        frame = self.tabview.tab("🖥️ PC")
        frame.configure(fg_color=COLORS["dark"])
        
        # Store results
        self._diagnostics_result = None
        self._pc_organizer_result = None
        
        # Header Card
        header_card = self._create_card(frame, "PC Health & AI Organizer", "🖥️")
        header_card.pack(fill="x", padx=10, pady=8)
        
        header_content = ctk.CTkFrame(header_card, fg_color="transparent")
        header_content.pack(fill="x", padx=15, pady=10)
        
        # Admin status
        admin_status = "✅ Administrator" if is_admin() else "⚠️ Not Admin (some fixes unavailable)"
        admin_color = COLORS["accent2"] if is_admin() else COLORS["warning"]
        ctk.CTkLabel(header_content, text=admin_status, font=("Segoe UI", 10, "bold"),
                    text_color=admin_color).pack(anchor="w")
        
        # Disk status boxes (will be updated)
        disk_row = ctk.CTkFrame(header_content, fg_color="transparent")
        disk_row.pack(fill="x", pady=10)
        
        self.pc_disk_frames = []
        for i in range(4):  # Max 4 disks shown
            box = ctk.CTkFrame(disk_row, fg_color=COLORS["darker"], corner_radius=8, width=140, height=70)
            box.pack(side="left", padx=5)
            box.pack_propagate(False)
            self.pc_disk_frames.append(box)
        
        self._update_disk_display()
        
        # Action buttons - ROW 1: Diagnostics
        btn_row1 = ctk.CTkFrame(header_content, fg_color="transparent")
        btn_row1.pack(fill="x", pady=3)
        
        ctk.CTkLabel(btn_row1, text="🔧 Diagnostics:", font=("Segoe UI", 10, "bold"),
                    text_color=COLORS["text"]).pack(side="left", padx=(0, 10))
        self._create_button(btn_row1, "🔍 Health Scan", self._run_pc_analysis, "info", 110).pack(side="left", padx=3)
        self._create_button(btn_row1, "🔧 System Check", self._run_diagnostics, "secondary", 120).pack(side="left", padx=3)
        self._create_button(btn_row1, "🔧 Auto-Fix", self._auto_fix_all, "success", 100).pack(side="left", padx=3)
        
        # Action buttons - ROW 2: AI Organizer
        btn_row2 = ctk.CTkFrame(header_content, fg_color="transparent")
        btn_row2.pack(fill="x", pady=3)
        
        ctk.CTkLabel(btn_row2, text="🤖 AI Organizer:", font=("Segoe UI", 10, "bold"),
                    text_color=COLORS["text"]).pack(side="left", padx=(0, 10))
        self._create_button(btn_row2, "🤖 Scan PC", self._run_ai_pc_scan, "primary", 100).pack(side="left", padx=3)
        self._create_button(btn_row2, "📋 Preview", self._preview_organization, "info", 90).pack(side="left", padx=3)
        self._create_button(btn_row2, "🚀 Organize!", self._execute_organization, "warning", 100).pack(side="left", padx=3)
        
        # Action buttons - ROW 3: Tools
        btn_row3 = ctk.CTkFrame(header_content, fg_color="transparent")
        btn_row3.pack(fill="x", pady=3)
        
        ctk.CTkLabel(btn_row3, text="🧹 Cleanup:", font=("Segoe UI", 10, "bold"),
                    text_color=COLORS["text"]).pack(side="left", padx=(0, 10))
        self._create_button(btn_row3, "🧹 Disk Cleanup", self._run_disk_cleanup, "default", 110).pack(side="left", padx=3)
        self._create_button(btn_row3, "🗑️ Temp Files", self._clean_temp_files, "danger", 100).pack(side="left", padx=3)
        self._create_button(btn_row3, "🔄 Refresh", self._refresh_disk_status, "default", 90).pack(side="left", padx=3)
        
        # Quick stats
        stats_row = ctk.CTkFrame(header_content, fg_color="transparent")
        stats_row.pack(fill="x", pady=5)
        
        self.pc_stats_label = self._create_label(stats_row, "🤖 Click 'Scan PC' for AI-powered organization", "subtitle")
        self.pc_stats_label.pack(side="left")
        
        # Results
        self.text_pc = self._create_textbox(frame)
        self.text_pc.pack(fill="both", expand=True, padx=10, pady=8)
        self.text_pc.insert("1.0", "🖥️ PC Health & AI Organizer\n" +
                           "=" * 60 + "\n\n" +
                           "🔧 DIAGNOSTICS:\n" +
                           "─────────────────────────────────────\n" +
                           "  🔍 Health Scan   - Check junk, large files, old downloads\n" +
                           "  🔧 System Check  - Windows errors, services, security\n" +
                           "  🔧 Auto-Fix      - Fix all detected problems\n\n" +
                           "🤖 AI ORGANIZER:\n" +
                           "─────────────────────────────────────\n" +
                           "  🤖 Scan PC       - AI scans ALL files, categorizes them\n" +
                           "  📋 Preview       - See organization plan before executing\n" +
                           "  🚀 Organize!     - Execute plan (moves files to proper folders)\n\n" +
                           "🧹 CLEANUP:\n" +
                           "─────────────────────────────────────\n" +
                           "  🧹 Disk Cleanup  - Open Windows Disk Cleanup\n" +
                           "  🗑️ Temp Files    - Delete temporary files directly\n\n" +
                           "📁 CATEGORIES (AI auto-detects):\n" +
                           "─────────────────────────────────────\n" +
                           "  💻 Programming   - Code files, projects\n" +
                           "  📄 Documents     - Word, PDF, Excel, Text\n" +
                           "  🖼️ Images        - Photos, Screenshots, Graphics\n" +
                           "  🎵 Music         - MP3, FLAC, WAV\n" +
                           "  🎬 Videos        - Movies, Clips, Recordings\n" +
                           "  📦 Archives      - ZIP, RAR, ISO\n" +
                           "  ⚙️ Applications  - EXE, Installers\n" +
                           "  📊 Data          - JSON, XML, Databases\n\n" +
                           "💡 TIP: AI Organizer creates 'Organized' folder and sorts everything!")
    
    def _update_disk_display(self):
        """Update disk status display boxes."""
        try:
            disks = get_disk_info()
            
            for i, box in enumerate(self.pc_disk_frames):
                # Clear existing
                for widget in box.winfo_children():
                    widget.destroy()
                
                if i < len(disks):
                    disk = disks[i]
                    status_color = COLORS["danger"] if disk["status"] == "critical" else \
                                  COLORS["warning"] if disk["status"] == "warning" else COLORS["accent2"]
                    
                    ctk.CTkLabel(box, text=disk["drive"], font=("Segoe UI", 14, "bold"),
                                text_color=status_color).pack(pady=(8, 0))
                    
                    # Progress bar style
                    pct = disk["usage_percent"]
                    bar_color = "#ef4444" if pct > 90 else "#f59e0b" if pct > 75 else "#10b981"
                    
                    ctk.CTkLabel(box, text=f"{pct:.0f}%", font=("Segoe UI", 11),
                                text_color=COLORS["text"]).pack()
                    
                    ctk.CTkLabel(box, text=f"{pc_format_size(disk['free'])} free", 
                                font=("Segoe UI", 9), text_color=COLORS["text_dim"]).pack()
                else:
                    box.configure(fg_color=COLORS["dark"])
        except Exception as e:
            pass
    
    def _run_pc_analysis(self):
        """Run full PC analysis."""
        self._set_status("🔄 Analyzing PC... This may take a minute...")
        
        def do_analysis():
            results = run_full_pc_analysis(
                lambda msg: self.after(0, lambda: self._set_status(msg))
            )
            
            # Format and display results
            text = format_pc_analysis(results)
            self.after(0, lambda: self._update_textbox(self.text_pc, text))
            
            # Update stats label
            stats = results.get("stats", {})
            problems = stats.get("problem_count", 0)
            warnings = stats.get("warning_count", 0)
            cleanable = stats.get("total_cleanable", 0)
            
            stats_text = f"🔴 {problems} problems | 🟡 {warnings} warnings | 🧹 {pc_format_size(cleanable)} cleanable"
            self.after(0, lambda: self.pc_stats_label.configure(text=stats_text))
            
            # Update disk display
            self.after(0, self._update_disk_display)
            
            status_color = "red" if problems > 0 else "yellow" if warnings > 0 else "green"
            self.after(0, lambda: self._set_status("✅ PC Analysis Complete", status_color))
        
        threading.Thread(target=do_analysis, daemon=True).start()
    
    def _run_diagnostics(self):
        """Run system diagnostics."""
        self._set_status("🔧 Running system diagnostics...")
        
        def do_diagnostics():
            results = run_full_diagnostics(
                lambda msg: self.after(0, lambda: self._set_status(msg))
            )
            self._diagnostics_result = results
            
            # Format and display
            text = format_diagnostics(results)
            self.after(0, lambda: self._update_textbox(self.text_pc, text))
            
            # Update stats
            stats = results.get("stats", {})
            critical = stats.get("critical", 0)
            warning = stats.get("warning", 0)
            fixable = stats.get("auto_fixable", 0)
            
            stats_text = f"🔴 {critical} critical | 🟡 {warning} warnings | 🔧 {fixable} auto-fixable"
            self.after(0, lambda: self.pc_stats_label.configure(text=stats_text))
            
            status_color = "red" if critical > 0 else "yellow" if warning > 0 else "green"
            self.after(0, lambda: self._set_status("✅ Diagnostics complete", status_color))
        
        threading.Thread(target=do_diagnostics, daemon=True).start()
    
    def _auto_fix_all(self):
        """Auto-fix all fixable problems."""
        if not self._diagnostics_result:
            messagebox.showinfo("Info", "Run 'System Diagnostics' first to find problems.")
            return
        
        problems = self._diagnostics_result.get("problems", [])
        fixable = [p for p in problems if p.get("auto_fix")]
        
        if not fixable:
            messagebox.showinfo("Info", "No auto-fixable problems found.")
            return
        
        # Check admin
        needs_admin = [p for p in fixable if p.get("requires_admin")]
        if needs_admin and not is_admin():
            if not messagebox.askyesno("Admin Required", 
                f"{len(needs_admin)} fixes require Administrator.\n\n" +
                "Some fixes will be skipped.\n" +
                "Continue with non-admin fixes?"):
                return
        
        if not messagebox.askyesno("Confirm Auto-Fix", 
            f"Attempt to fix {len(fixable)} problems automatically?\n\n" +
            "🔧 Auto-fixable problems:\n" + 
            "\n".join([f"  • {p['title']}" for p in fixable[:5]]) +
            (f"\n  ... and {len(fixable) - 5} more" if len(fixable) > 5 else "")):
            return
        
        self._set_status("🔧 Fixing problems...")
        
        def do_fix():
            results = fix_all_auto(problems,
                lambda msg: self.after(0, lambda: self._set_status(msg)))
            
            fixed = len(results.get("fixed", []))
            failed = len(results.get("failed", []))
            skipped = len(results.get("skipped", []))
            
            # Show results
            text = "🔧 AUTO-FIX RESULTS\n"
            text += "=" * 50 + "\n\n"
            text += f"✅ Fixed: {fixed}\n"
            text += f"❌ Failed: {failed}\n"
            text += f"⏭️ Skipped: {skipped}\n\n"
            
            if results.get("fixed"):
                text += "✅ FIXED:\n"
                for p in results["fixed"]:
                    text += f"  • {p['title']}\n"
            
            if results.get("failed"):
                text += "\n❌ FAILED:\n"
                for p in results["failed"]:
                    text += f"  • {p['title']}\n"
            
            if results.get("skipped"):
                text += "\n⏭️ SKIPPED (manual fix needed):\n"
                for p in results["skipped"][:10]:
                    text += f"  • {p['title']}\n"
                    text += f"    💡 {p.get('manual_fix', 'N/A')}\n"
            
            self.after(0, lambda: self._update_textbox(self.text_pc, text))
            
            if fixed > 0:
                self.after(0, lambda: self._set_status(f"✅ Fixed {fixed} problems!", "green"))
            else:
                self.after(0, lambda: self._set_status("⚠️ No problems could be fixed", "yellow"))
        
        threading.Thread(target=do_fix, daemon=True).start()
    
    def _run_disk_cleanup(self):
        """Open Windows Disk Cleanup."""
        try:
            subprocess.Popen("cleanmgr", shell=True)
            self._set_status("✅ Disk Cleanup opened", "green")
        except Exception as e:
            messagebox.showerror("Error", f"Could not open Disk Cleanup: {e}")
    
    def _run_ai_pc_scan(self):
        """Run AI-powered PC scan for organization."""
        # Ask user which drives to scan
        scanner = PCScanner()
        drives = scanner.get_drives()
        
        drive_str = ", ".join(drives)
        if not messagebox.askyesno("AI PC Scan", 
            f"This will scan your PC for intelligent organization.\n\n"
            f"Available drives: {drive_str}\n\n"
            f"This may take several minutes.\n"
            f"Projects and system folders will be protected.\n\n"
            f"Continue?"):
            return
        
        self._set_status("🤖 AI scanning your PC...")
        self.text_pc.delete("1.0", "end")
        self.text_pc.insert("1.0", "🤖 AI PC ORGANIZER - SCANNING\n" + "=" * 50 + "\n\n"
            f"Scanning drives: {drive_str}\n\n"
            "This will:\n"
            "  ✓ Find all files on your PC\n"
            "  ✓ Detect projects (won't touch them)\n"
            "  ✓ Categorize files by type\n"
            "  ✓ Create organization plan\n"
            "  ✓ Suggest cleanup actions\n\n"
            "Please wait...")
        
        def do_scan():
            def progress(msg):
                self.after(0, lambda: self._set_status(f"🤖 {msg}"))
                self.after(0, lambda: self.text_pc.insert("end", f"\n{msg}"))
            
            result = scan_pc_full(drives, progress, skip_system=True)
            self._pc_organizer_result = result
            
            # Format and display
            text = format_scan_report(result)
            self.after(0, lambda: self._update_textbox(self.text_pc, text))
            
            # Update stats
            stats = result.get('stats', {})
            plan = result.get('organization_plan', [])
            
            files_to_organize = sum(p.get('file_count', 0) for p in plan)
            stats_text = (f"📄 {stats.get('total_files', 0):,} files | "
                         f"💻 {len(result.get('projects', []))} projects | "
                         f"📋 {files_to_organize:,} to organize")
            
            self.after(0, lambda: self.pc_stats_label.configure(text=stats_text))
            self.after(0, lambda: self._set_status("✅ AI scan complete! Click 'Preview' to see plan", "green"))
        
        threading.Thread(target=do_scan, daemon=True).start()
    
    def _preview_organization(self):
        """Preview the organization plan."""
        if not self._pc_organizer_result:
            messagebox.showinfo("Info", "Run 'Scan PC' first to analyze your files.")
            return
        
        plan = self._pc_organizer_result.get('organization_plan', [])
        cleanup = self._pc_organizer_result.get('cleanup_suggestions', [])
        
        if not plan and not cleanup:
            messagebox.showinfo("Info", "No organization needed - your PC is already organized!")
            return
        
        lines = []
        lines.append("📋 ORGANIZATION PLAN PREVIEW")
        lines.append("=" * 60)
        lines.append("\n⚠️ This is a PREVIEW - no files will be moved yet.\n")
        
        # Organization actions
        if plan:
            total_files = sum(p.get('file_count', 0) for p in plan)
            total_size = sum(p.get('total_size', 0) for p in plan)
            
            lines.append(f"{'─' * 50}")
            lines.append(f"📁 FILES TO ORGANIZE: {total_files:,} ({ai_format_size(total_size)})")
            lines.append(f"{'─' * 50}")
            
            for i, action in enumerate(plan, 1):
                lines.append(f"\n{i}. {action.get('category', 'Unknown')}")
                lines.append(f"   📂 Target: ~/Organized/{action.get('target_folder', 'Other')}/")
                lines.append(f"   📄 Files: {action.get('file_count', 0):,}")
                lines.append(f"   📦 Size: {ai_format_size(action.get('total_size', 0))}")
                
                # Show sample files
                sample_files = action.get('files', [])[:5]
                if sample_files:
                    lines.append("   📋 Sample files:")
                    for f in sample_files:
                        lines.append(f"      • {os.path.basename(f)}")
                    if len(action.get('files', [])) > 5:
                        lines.append(f"      ... and {len(action.get('files', [])) - 5} more")
        
        # Cleanup suggestions
        if cleanup:
            lines.append(f"\n{'─' * 50}")
            lines.append("🧹 CLEANUP SUGGESTIONS")
            lines.append(f"{'─' * 50}")
            
            for sugg in cleanup:
                lines.append(f"\n{sugg.get('icon', '•')} {sugg.get('reason', 'Unknown')}")
                lines.append(f"   {sugg.get('description', '')}")
        
        lines.append(f"\n{'=' * 60}")
        lines.append("💡 Click 'Organize!' to execute this plan")
        lines.append("   (You'll be asked to confirm and can simulate first)")
        
        text = "\n".join(lines)
        self._update_textbox(self.text_pc, text)
        self._set_status("📋 Preview ready - click 'Organize!' to execute", "blue")
    
    def _execute_organization(self):
        """Execute the organization plan."""
        if not self._pc_organizer_result:
            messagebox.showinfo("Info", "Run 'Scan PC' first to analyze your files.")
            return
        
        plan = self._pc_organizer_result.get('organization_plan', [])
        if not plan:
            messagebox.showinfo("Info", "No files to organize.")
            return
        
        total_files = sum(p.get('file_count', 0) for p in plan)
        
        # Ask for simulation first
        result = messagebox.askyesnocancel("Execute Organization",
            f"Ready to organize {total_files:,} files.\n\n"
            f"Files will be moved to: ~/Organized/[Category]/\n\n"
            f"Options:\n"
            f"• YES = Simulate first (recommended)\n"
            f"• NO = Execute immediately\n"
            f"• CANCEL = Abort")
        
        if result is None:  # Cancel
            return
        
        dry_run = result  # True = simulate, False = execute
        
        self._set_status("🚀 Organizing files..." if not dry_run else "📋 Simulating organization...")
        
        def do_organize():
            def progress(msg):
                self.after(0, lambda: self._set_status(msg))
            
            base_path = os.path.expanduser("~")
            result = organize_files(self._pc_organizer_result, base_path, dry_run, progress)
            
            # Format result
            lines = []
            lines.append("🚀 ORGANIZATION " + ("SIMULATION" if dry_run else "COMPLETE"))
            lines.append("=" * 60)
            
            stats = result.get('stats', {})
            lines.append(f"\n📊 RESULTS:")
            lines.append(f"  ✅ Files moved: {stats.get('files_moved', 0):,}")
            lines.append(f"  ❌ Files failed: {stats.get('files_failed', 0):,}")
            lines.append(f"  📦 Space organized: {ai_format_size(stats.get('space_organized', 0))}")
            
            if dry_run:
                lines.append(f"\n⚠️ This was a SIMULATION - no files were actually moved.")
                lines.append(f"   Click 'Organize!' again and select NO to execute for real.")
            else:
                organized_path = os.path.join(base_path, "Organized")
                lines.append(f"\n✅ Files have been moved to:")
                lines.append(f"   {organized_path}")
            
            # Show actions
            lines.append(f"\n{'─' * 50}")
            lines.append("📋 ACTIONS TAKEN:")
            lines.append(f"{'─' * 50}")
            
            for action in result.get('actions', [])[:10]:
                status = action.get('result', {}).get('status', 'unknown')
                icon = "✅" if status == 'success' else "⚠️" if status == 'partial' else "❌"
                lines.append(f"\n{icon} {action.get('description', 'Unknown')}")
                
                act_result = action.get('result', {})
                lines.append(f"   Processed: {act_result.get('files_processed', 0)} files")
                
                errors = act_result.get('errors', [])
                if errors:
                    lines.append(f"   Errors: {len(errors)}")
                    for err in errors[:3]:
                        lines.append(f"      • {err}")
            
            text = "\n".join(lines)
            self.after(0, lambda: self._update_textbox(self.text_pc, text))
            
            status = "✅ Organization complete!" if not dry_run else "📋 Simulation complete"
            self.after(0, lambda: self._set_status(status, "green"))
        
        threading.Thread(target=do_organize, daemon=True).start()
    
    def _clean_temp_files(self):
        """Quick clean temporary files."""
        if not self._pc_organizer_result:
            # Quick temp file scan
            if not messagebox.askyesno("Clean Temp Files",
                "This will scan and delete temporary files.\n\n"
                "Continue?"):
                return
            
            self._set_status("🗑️ Finding temp files...")
            
            def do_clean():
                import tempfile
                temp_dir = tempfile.gettempdir()
                
                deleted = 0
                failed = 0
                size_freed = 0
                
                try:
                    for item in os.listdir(temp_dir):
                        try:
                            path = os.path.join(temp_dir, item)
                            if os.path.isfile(path):
                                size = os.path.getsize(path)
                                os.remove(path)
                                deleted += 1
                                size_freed += size
                        except:
                            failed += 1
                except:
                    pass
                
                self.after(0, lambda: messagebox.showinfo("Temp Cleanup",
                    f"✅ Deleted: {deleted} files\n"
                    f"❌ Failed: {failed} files\n"
                    f"📦 Space freed: {ai_format_size(size_freed)}"))
                self.after(0, lambda: self._set_status(f"✅ Cleaned {deleted} temp files", "green"))
            
            threading.Thread(target=do_clean, daemon=True).start()
        else:
            # Use cleanup suggestions
            cleanup = self._pc_organizer_result.get('cleanup_suggestions', [])
            temp_sugg = [s for s in cleanup if 'temp' in s.get('reason', '').lower()]
            
            if temp_sugg:
                count = temp_sugg[0].get('file_count', 0)
                if messagebox.askyesno("Clean Temp Files",
                    f"Found {count} temporary files.\n\nDelete them?"):
                    self._set_status("🗑️ Cleaning temp files...")
                    # Execute deletion (would need implementation)
                    messagebox.showinfo("Info", "Temp file cleanup - feature in progress")
            else:
                messagebox.showinfo("Info", "No temp files found in scan.")
    
    def _refresh_disk_status(self):
        """Just refresh disk status."""
        self._update_disk_display()
        self._set_status("✅ Disk status updated", "green")
    
    def _build_duplicates_tab(self):
        frame = self.tabview.tab("📋 Duplicates")
        frame.configure(fg_color=COLORS["dark"])
        
        # Header Card with stats
        header_card = self._create_card(frame, "Duplicate Files", "📋")
        header_card.pack(fill="x", padx=10, pady=8)
        
        header_content = ctk.CTkFrame(header_card, fg_color="transparent")
        header_content.pack(fill="x", padx=15, pady=10)
        
        # Stats boxes
        stats_row = ctk.CTkFrame(header_content, fg_color="transparent")
        stats_row.pack(fill="x", pady=5)
        
        for icon, label, color in [("📦", "Groups", COLORS["info"]), 
                                    ("📄", "Duplicates", COLORS["warning"]), 
                                    ("💾", "Wasted", COLORS["danger"])]:
            box = ctk.CTkFrame(stats_row, fg_color=COLORS["darker"], corner_radius=8)
            box.pack(side="left", padx=5, pady=3)
            ctk.CTkLabel(box, text=f"{icon} {label}: —", font=("Segoe UI", 11), 
                        text_color=color, padx=15, pady=8).pack()
        
        self.label_dup_stats = stats_row  # Reference for updates
        
        # Scan button
        btn_row = ctk.CTkFrame(header_content, fg_color="transparent")
        btn_row.pack(fill="x", pady=5)
        self._create_button(btn_row, "🔍 Scan Duplicates", self._run_duplicate_scan, "info", 150).pack(side="left")
        self._create_button(btn_row, "⚡ Smart Scan", lambda: None, "secondary", 120).pack(side="left", padx=5)
        
        # Results
        self.text_duplicates = self._create_textbox(frame)
        self.text_duplicates.pack(fill="both", expand=True, padx=10, pady=5)
        self.text_duplicates.insert("1.0", "🔍 Click 'Scan Duplicates' to find identical files.\n\n" +
                                   "The scanner will:\n" +
                                   "  • Group files by size first (fast)\n" +
                                   "  • Hash only potential duplicates\n" +
                                   "  • Keep the oldest file as 'original'")
        
        # Actions Card
        actions_card = self._create_card(frame, "Cleanup", "🧹")
        actions_card.pack(fill="x", padx=10, pady=8)
        
        actions_content = ctk.CTkFrame(actions_card, fg_color="transparent")
        actions_content.pack(fill="x", padx=15, pady=10)
        
        action_row = ctk.CTkFrame(actions_content, fg_color="transparent")
        action_row.pack(fill="x")
        
        self._create_label(action_row, "Move to:", "normal").pack(side="left", padx=(0, 10))
        self.entry_dup_dest = self._create_entry(action_row, 300, "Folder for duplicates...")
        self.entry_dup_dest.pack(side="left", padx=5)
        self._create_button(action_row, "📂", lambda: self._browse_to(self.entry_dup_dest), "default", 40).pack(side="left", padx=3)
        
        self.var_dup_sim = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(action_row, text="Simulation", variable=self.var_dup_sim,
                       font=("Segoe UI", 10), text_color=COLORS["text"]).pack(side="left", padx=15)
        self._create_button(action_row, "🗑️ Move Duplicates", self._move_duplicates, "danger", 150).pack(side="left", padx=5)
    
    def _build_similar_tab(self):
        """Build the Similar Files tab - finds near-duplicates and backups."""
        frame = self.tabview.tab("🔀 Similar")
        
        header = ctk.CTkFrame(frame)
        header.pack(fill="x", padx=10, pady=8)
        
        ctk.CTkLabel(header, text="🔀 Similar & Backup Files", font=("Segoe UI", 13, "bold"), 
                    text_color="#9b59b6").pack(side="left", padx=10)
        ctk.CTkLabel(header, text="Find files that look like copies, versions, or backups",
                    font=("Segoe UI", 10), text_color="gray").pack(side="left", padx=15)
        
        btn_row = ctk.CTkFrame(frame)
        btn_row.pack(fill="x", padx=10, pady=5)
        ctk.CTkButton(btn_row, text="🔍 Find Similar Names", width=150, 
                     command=self._find_similar_files).pack(side="left", padx=5)
        ctk.CTkButton(btn_row, text="📦 Find Backup Files", width=150, fg_color="#6c757d",
                     command=self._find_backup_files).pack(side="left", padx=5)
        ctk.CTkButton(btn_row, text="⚡ Smart Scan (Fast)", width=140, fg_color="#28a745",
                     command=self._run_fast_scan).pack(side="left", padx=5)
        
        # Info
        info = ctk.CTkFrame(frame)
        info.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(info, 
            text="💡 Similar: file.txt, file (1).txt, file_copy.txt | Backups: file.bak, file.old, file~",
            font=("Segoe UI", 10), text_color="#17a2b8").pack(padx=10, pady=5)
        
        self.text_similar = ctk.CTkTextbox(frame, wrap="word", font=("Consolas", 10))
        self.text_similar.pack(fill="both", expand=True, padx=10, pady=8)
    
    def _build_bigfiles_tab(self):
        frame = self.tabview.tab("📦 Big")
        
        header = ctk.CTkFrame(frame)
        header.pack(fill="x", padx=10, pady=8)
        
        ctk.CTkLabel(header, text="📦 Large Files", font=("Segoe UI", 13, "bold"), text_color="#fd7e14").pack(side="left", padx=10)
        
        ctk.CTkLabel(header, text="Min size (MB):", font=("Segoe UI", 11)).pack(side="left", padx=(20, 5))
        self.entry_min_size = ctk.CTkEntry(header, width=80, placeholder_text="100")
        self.entry_min_size.pack(side="left", padx=5)
        self.entry_min_size.insert(0, "100")
        
        ctk.CTkButton(header, text="🔍 Find Big Files", width=130, command=self._run_bigfiles_scan).pack(side="left", padx=10)
        
        self.label_bigfiles_stats = ctk.CTkLabel(header, text="", font=("Segoe UI", 11))
        self.label_bigfiles_stats.pack(side="left", padx=20)
        
        self.text_bigfiles = ctk.CTkTextbox(frame, wrap="word", font=("Consolas", 10))
        self.text_bigfiles.pack(fill="both", expand=True, padx=10, pady=8)
        self.text_bigfiles.insert("1.0", "Click 'Find Big Files' to find files larger than the specified size.")
    
    def _build_oldfiles_tab(self):
        frame = self.tabview.tab("🕐 Old")
        
        header = ctk.CTkFrame(frame)
        header.pack(fill="x", padx=10, pady=8)
        
        ctk.CTkLabel(header, text="🕐 Old/Unused Files", font=("Segoe UI", 13, "bold"), text_color="#6f42c1").pack(side="left", padx=10)
        
        ctk.CTkLabel(header, text="Older than (days):", font=("Segoe UI", 11)).pack(side="left", padx=(20, 5))
        self.entry_days_old = ctk.CTkEntry(header, width=80, placeholder_text="365")
        self.entry_days_old.pack(side="left", padx=5)
        self.entry_days_old.insert(0, "365")
        
        ctk.CTkButton(header, text="🔍 Find Old Files", width=130, command=self._run_oldfiles_scan).pack(side="left", padx=10)
        
        self.label_oldfiles_stats = ctk.CTkLabel(header, text="", font=("Segoe UI", 11))
        self.label_oldfiles_stats.pack(side="left", padx=20)
        
        self.text_oldfiles = ctk.CTkTextbox(frame, wrap="word", font=("Consolas", 10))
        self.text_oldfiles.pack(fill="both", expand=True, padx=10, pady=8)
        self.text_oldfiles.insert("1.0", "Click 'Find Old Files' to find files not modified in a long time.")
    
    def _build_empty_tab(self):
        frame = self.tabview.tab("🗑️ Empty")
        
        header = ctk.CTkFrame(frame)
        header.pack(fill="x", padx=10, pady=8)
        
        ctk.CTkLabel(header, text="🗑️ Empty Folders", font=("Segoe UI", 13, "bold"), text_color="#dc3545").pack(side="left", padx=10)
        ctk.CTkButton(header, text="🔍 Find Empty Folders", width=150, command=self._run_empty_scan).pack(side="left", padx=10)
        
        self.label_empty_stats = ctk.CTkLabel(header, text="", font=("Segoe UI", 11))
        self.label_empty_stats.pack(side="left", padx=20)
        
        self.text_empty = ctk.CTkTextbox(frame, wrap="word", font=("Consolas", 10))
        self.text_empty.pack(fill="both", expand=True, padx=10, pady=8)
        
        actions = ctk.CTkFrame(frame)
        actions.pack(fill="x", padx=10, pady=8)
        
        self.var_empty_sim = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(actions, text="Simulation (preview only)", variable=self.var_empty_sim).pack(side="left", padx=10)
        ctk.CTkButton(actions, text="🗑️ Delete Empty Folders", width=180, fg_color="#dc3545", command=self._delete_empty).pack(side="left", padx=10)
    
    def _build_settings_tab(self):
        frame = self.tabview.tab("⚙️ Settings")
        
        # Header
        header = ctk.CTkFrame(frame)
        header.pack(fill="x", padx=10, pady=8)
        
        ctk.CTkLabel(header, text="⚙️ Customize Your Settings", font=("Segoe UI", 14, "bold")).pack(side="left", padx=10)
        ctk.CTkButton(header, text="💾 Save", width=80, fg_color="#28a745", command=self._save_settings).pack(side="right", padx=5)
        ctk.CTkButton(header, text="🔄 Reset", width=80, fg_color="#dc3545", command=self._reset_settings).pack(side="right", padx=5)
        ctk.CTkButton(header, text="🔃 Refresh", width=80, command=self._refresh_settings).pack(side="right", padx=5)
        
        # Settings form - left side
        main_frame = ctk.CTkFrame(frame)
        main_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        left_frame = ctk.CTkFrame(main_frame)
        left_frame.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        
        # Thresholds
        thresh_frame = ctk.CTkFrame(left_frame)
        thresh_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(thresh_frame, text="📊 Thresholds", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=10, pady=5)
        
        row1 = ctk.CTkFrame(thresh_frame)
        row1.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(row1, text="Big Files (MB):", width=150).pack(side="left")
        self.entry_set_bigfiles = ctk.CTkEntry(row1, width=100)
        self.entry_set_bigfiles.pack(side="left", padx=10)
        self.entry_set_bigfiles.insert(0, str(self._settings.get("big_files_min_mb", 100)))
        
        row2 = ctk.CTkFrame(thresh_frame)
        row2.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(row2, text="Old Files (days):", width=150).pack(side="left")
        self.entry_set_oldfiles = ctk.CTkEntry(row2, width=100)
        self.entry_set_oldfiles.pack(side="left", padx=10)
        self.entry_set_oldfiles.insert(0, str(self._settings.get("old_files_days", 365)))
        
        # Skip folders
        skip_frame = ctk.CTkFrame(left_frame)
        skip_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(skip_frame, text="🚫 Folders to Skip", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=10, pady=5)
        
        self.text_skip_folders = ctk.CTkTextbox(skip_frame, height=100, font=("Consolas", 10))
        self.text_skip_folders.pack(fill="x", padx=10, pady=5)
        self.text_skip_folders.insert("1.0", "\n".join(self._settings.get("skip_folders", [])))
        
        ctk.CTkLabel(skip_frame, text="(one folder name per line)", text_color="gray", font=("Segoe UI", 10)).pack(anchor="w", padx=10)
        
        # Add custom mismatch rule
        rule_frame = ctk.CTkFrame(left_frame)
        rule_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(rule_frame, text="➕ Add Custom Rule", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=10, pady=5)
        
        row3 = ctk.CTkFrame(rule_frame)
        row3.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(row3, text="Folder type:", width=100).pack(side="left")
        self.entry_rule_folder = ctk.CTkEntry(row3, width=200, placeholder_text="e.g., my_project")
        self.entry_rule_folder.pack(side="left", padx=5)
        
        row4 = ctk.CTkFrame(rule_frame)
        row4.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(row4, text="Don't allow:", width=100).pack(side="left")
        self.entry_rule_exts = ctk.CTkEntry(row4, width=300, placeholder_text=".mp3, .mp4, .exe (comma separated)")
        self.entry_rule_exts.pack(side="left", padx=5)
        
        ctk.CTkButton(rule_frame, text="➕ Add Rule", width=100, command=self._add_custom_rule).pack(anchor="w", padx=10, pady=5)
        
        # Right side - current settings display
        right_frame = ctk.CTkFrame(main_frame)
        right_frame.pack(side="right", fill="both", expand=True, padx=5, pady=5)
        
        ctk.CTkLabel(right_frame, text="📋 Current Settings", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=10, pady=5)
        
        self.text_settings_display = ctk.CTkTextbox(right_frame, font=("Consolas", 10))
        self.text_settings_display.pack(fill="both", expand=True, padx=10, pady=5)
        self._refresh_settings()
        
        # Notes
        notes_frame = ctk.CTkFrame(frame)
        notes_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(notes_frame, text="📝 Your Notes", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=10, pady=5)
        self.text_notes = ctk.CTkEntry(notes_frame, placeholder_text="Add any notes or reminders here...")
        self.text_notes.pack(fill="x", padx=10, pady=5)
        self.text_notes.insert(0, self._settings.get("user_notes", ""))
    
    def _save_settings(self):
        """Save current settings."""
        try:
            self._settings["big_files_min_mb"] = int(self.entry_set_bigfiles.get() or 100)
        except:
            self._settings["big_files_min_mb"] = 100
        
        try:
            self._settings["old_files_days"] = int(self.entry_set_oldfiles.get() or 365)
        except:
            self._settings["old_files_days"] = 365
        
        # Parse skip folders
        skip_text = self.text_skip_folders.get("1.0", "end").strip()
        self._settings["skip_folders"] = [f.strip() for f in skip_text.split("\n") if f.strip()]
        
        # Save notes
        self._settings["user_notes"] = self.text_notes.get().strip()
        
        if save_settings(self._settings):
            self._set_status("✅ Settings saved!", "green")
            messagebox.showinfo("Settings", "Settings saved successfully!")
            self._refresh_settings()
        else:
            self._set_status("❌ Failed to save settings", "red")
    
    def _reset_settings(self):
        """Reset to default settings."""
        if messagebox.askyesno("Reset", "Reset all settings to defaults?"):
            self._settings = reset_settings()
            self.entry_set_bigfiles.delete(0, "end")
            self.entry_set_bigfiles.insert(0, str(self._settings.get("big_files_min_mb", 100)))
            self.entry_set_oldfiles.delete(0, "end")
            self.entry_set_oldfiles.insert(0, str(self._settings.get("old_files_days", 365)))
            self.text_skip_folders.delete("1.0", "end")
            self.text_skip_folders.insert("1.0", "\n".join(self._settings.get("skip_folders", [])))
            self.text_notes.delete(0, "end")
            self._refresh_settings()
            self._set_status("✅ Settings reset!", "green")
    
    def _refresh_settings(self):
        """Refresh settings display."""
        self.text_settings_display.delete("1.0", "end")
        self.text_settings_display.insert("1.0", format_settings_display(self._settings))
    
    def _add_custom_rule(self):
        """Add a custom mismatch rule."""
        folder_type = self.entry_rule_folder.get().strip().lower().replace(" ", "_")
        exts_text = self.entry_rule_exts.get().strip()
        
        if not folder_type or not exts_text:
            messagebox.showwarning("Warning", "Enter folder type and extensions.")
            return
        
        extensions = [e.strip() for e in exts_text.split(",") if e.strip()]
        extensions = [e if e.startswith(".") else f".{e}" for e in extensions]
        
        self._settings["mismatch_rules"][folder_type] = {
            "unexpected": extensions,
            "description": f"Custom rule: {', '.join(extensions)} not allowed"
        }
        
        self._refresh_settings()
        self._set_status(f"✅ Rule added for '{folder_type}'", "green")
        
        # Clear inputs
        self.entry_rule_folder.delete(0, "end")
        self.entry_rule_exts.delete(0, "end")
    
    def _build_undo_tab(self):
        frame = self.tabview.tab("📜 Undo")
        
        # Header with QUICK RESTORE
        header = ctk.CTkFrame(frame)
        header.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(header, text="📜 Backup & Restore", font=("Segoe UI", 14, "bold")).pack(side="left", padx=10)
        
        # BIG QUICK RESTORE BUTTON
        ctk.CTkButton(header, text="⏪ QUICK RESTORE (Undo Last)", width=220, height=40,
                     fg_color="#dc3545", hover_color="#c82333", font=("Segoe UI", 12, "bold"),
                     command=self._quick_restore).pack(side="right", padx=10)
        
        ctk.CTkButton(header, text="🔄 Refresh", width=100, command=self._load_history).pack(side="right", padx=5)
        
        # Info
        info = ctk.CTkFrame(frame)
        info.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(info, 
            text="💡 Backup created automatically before every operation. Click QUICK RESTORE to undo!",
            font=("Segoe UI", 11), text_color="#17a2b8").pack(padx=10, pady=8)
        
        # History
        self.text_history = ctk.CTkTextbox(frame, wrap="word", font=("Consolas", 10), height=200)
        self.text_history.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Manual restore
        restore_frame = ctk.CTkFrame(frame)
        restore_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(restore_frame, text="🔧 Manual Restore:", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=10, pady=5)
        
        row1 = ctk.CTkFrame(restore_frame)
        row1.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(row1, text="Backup ID:").pack(side="left", padx=5)
        self.entry_backup_id = ctk.CTkEntry(row1, width=280, placeholder_text="e.g., backup_20260206_120000")
        self.entry_backup_id.pack(side="left", padx=5)
        ctk.CTkButton(row1, text="⏪ Restore", width=120, fg_color="#6c757d", command=self._restore_specific).pack(side="left", padx=10)
        
        row2 = ctk.CTkFrame(restore_frame)
        row2.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(row2, text="Undo log file:").pack(side="left", padx=5)
        self.entry_undo = ctk.CTkEntry(row2, width=280, placeholder_text="Select undo_log_*.json...")
        self.entry_undo.pack(side="left", padx=5)
        ctk.CTkButton(row2, text="Browse", width=70, command=self._browse_undo).pack(side="left", padx=3)
        ctk.CTkButton(row2, text="⏪ Undo", width=100, command=self._run_undo).pack(side="left", padx=10)
        
        self.label_restore_status = ctk.CTkLabel(restore_frame, text="", font=("Segoe UI", 11))
        self.label_restore_status.pack(anchor="w", padx=10, pady=5)
        
        self._load_history()
    
    # ===== NEW TOOLS TABS =====
    
    def _build_rename_tab(self):
        """Build the Batch Rename tab."""
        frame = self.tabview.tab("📝 Rename")
        
        # Store for rename preview
        self._rename_preview = []
        
        # Header
        header = ctk.CTkFrame(frame)
        header.pack(fill="x", padx=10, pady=8)
        ctk.CTkLabel(header, text="📝 Batch Rename Files", font=("Segoe UI", 14, "bold")).pack(side="left", padx=10)
        
        # Settings
        settings = ctk.CTkFrame(frame)
        settings.pack(fill="x", padx=10, pady=5)
        
        row1 = ctk.CTkFrame(settings)
        row1.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(row1, text="Pattern:").pack(side="left", padx=5)
        self.entry_rename_pattern = ctk.CTkEntry(row1, width=250, placeholder_text="{name}_{n}")
        self.entry_rename_pattern.pack(side="left", padx=5)
        self.entry_rename_pattern.insert(0, "file_{n}")
        
        ctk.CTkLabel(row1, text="Start #:").pack(side="left", padx=10)
        self.entry_rename_start = ctk.CTkEntry(row1, width=60, placeholder_text="1")
        self.entry_rename_start.pack(side="left", padx=5)
        self.entry_rename_start.insert(0, "1")
        
        ctk.CTkLabel(row1, text="Ext filter:").pack(side="left", padx=10)
        self.entry_rename_ext = ctk.CTkEntry(row1, width=80, placeholder_text="*")
        self.entry_rename_ext.pack(side="left", padx=5)
        self.entry_rename_ext.insert(0, "*")
        
        # Help text
        help_frame = ctk.CTkFrame(settings)
        help_frame.pack(fill="x", padx=10, pady=5)
        help_text = "Patterns: {n}=number, {name}=original, {date}=YYYYMMDD, {parent}=folder name"
        ctk.CTkLabel(help_frame, text=help_text, font=("Segoe UI", 10), text_color="gray").pack(padx=10, pady=3)
        
        # Buttons
        btn_row = ctk.CTkFrame(frame)
        btn_row.pack(fill="x", padx=10, pady=5)
        ctk.CTkButton(btn_row, text="👁️ Preview", width=100, command=self._preview_rename).pack(side="left", padx=5)
        ctk.CTkButton(btn_row, text="✅ Execute Rename", width=130, fg_color="#28a745", 
                     hover_color="#218838", command=self._execute_rename).pack(side="left", padx=5)
        
        # Results
        self.text_rename = ctk.CTkTextbox(frame, wrap="word", font=("Consolas", 11))
        self.text_rename.pack(fill="both", expand=True, padx=10, pady=8)
    
    def _build_disk_tab(self):
        """Build the Disk Analyzer tab."""
        frame = self.tabview.tab("📊 Disk")
        
        self._disk_result = None
        
        header = ctk.CTkFrame(frame)
        header.pack(fill="x", padx=10, pady=8)
        ctk.CTkLabel(header, text="📊 Disk Usage Analyzer", font=("Segoe UI", 14, "bold")).pack(side="left", padx=10)
        ctk.CTkButton(header, text="🔍 Analyze Disk Usage", width=160, fg_color="#17a2b8",
                     hover_color="#138496", command=self._run_disk_analysis).pack(side="left", padx=15)
        
        self.text_disk = ctk.CTkTextbox(frame, wrap="word", font=("Consolas", 11))
        self.text_disk.pack(fill="both", expand=True, padx=10, pady=8)
    
    def _build_compress_tab(self):
        """Build the Compress/Extract tab."""
        frame = self.tabview.tab("🗜️ ZIP")
        
        header = ctk.CTkFrame(frame)
        header.pack(fill="x", padx=10, pady=8)
        ctk.CTkLabel(header, text="🗜️ Compress & Extract", font=("Segoe UI", 14, "bold")).pack(side="left", padx=10)
        
        # Compress section
        compress_frame = ctk.CTkFrame(frame)
        compress_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(compress_frame, text="📦 COMPRESS FOLDER TO ZIP", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=10, pady=5)
        
        row1 = ctk.CTkFrame(compress_frame)
        row1.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(row1, text="Output ZIP:").pack(side="left", padx=5)
        self.entry_zip_output = ctk.CTkEntry(row1, width=350, placeholder_text="Leave empty for auto-name")
        self.entry_zip_output.pack(side="left", padx=5)
        ctk.CTkButton(row1, text="🗜️ Compress", width=120, fg_color="#28a745",
                     command=self._compress_folder).pack(side="left", padx=10)
        
        # Extract section
        extract_frame = ctk.CTkFrame(frame)
        extract_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(extract_frame, text="📂 EXTRACT ARCHIVE", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=10, pady=5)
        
        row2 = ctk.CTkFrame(extract_frame)
        row2.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(row2, text="ZIP file:").pack(side="left", padx=5)
        self.entry_zip_input = ctk.CTkEntry(row2, width=350, placeholder_text="Select a .zip file...")
        self.entry_zip_input.pack(side="left", padx=5)
        ctk.CTkButton(row2, text="Browse", width=70, command=self._browse_zip).pack(side="left", padx=3)
        ctk.CTkButton(row2, text="📂 Extract", width=100, fg_color="#17a2b8",
                     command=self._extract_archive).pack(side="left", padx=10)
        
        # Results
        self.text_compress = ctk.CTkTextbox(frame, wrap="word", font=("Consolas", 11))
        self.text_compress.pack(fill="both", expand=True, padx=10, pady=8)
    
    def _build_sync_tab(self):
        """Build the Folder Sync tab."""
        frame = self.tabview.tab("🔄 Sync")
        
        self._sync_result = None
        
        header = ctk.CTkFrame(frame)
        header.pack(fill="x", padx=10, pady=8)
        ctk.CTkLabel(header, text="🔄 Sync Two Folders", font=("Segoe UI", 14, "bold")).pack(side="left", padx=10)
        
        # Folder inputs
        folders_frame = ctk.CTkFrame(frame)
        folders_frame.pack(fill="x", padx=10, pady=10)
        
        row1 = ctk.CTkFrame(folders_frame)
        row1.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(row1, text="📁 Folder 1:").pack(side="left", padx=5)
        self.entry_sync_folder1 = ctk.CTkEntry(row1, width=400, placeholder_text="First folder...")
        self.entry_sync_folder1.pack(side="left", padx=5)
        ctk.CTkButton(row1, text="Browse", width=70, command=lambda: self._browse_to(self.entry_sync_folder1)).pack(side="left", padx=3)
        
        row2 = ctk.CTkFrame(folders_frame)
        row2.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(row2, text="📁 Folder 2:").pack(side="left", padx=5)
        self.entry_sync_folder2 = ctk.CTkEntry(row2, width=400, placeholder_text="Second folder...")
        self.entry_sync_folder2.pack(side="left", padx=5)
        ctk.CTkButton(row2, text="Browse", width=70, command=lambda: self._browse_to(self.entry_sync_folder2)).pack(side="left", padx=3)
        
        # Buttons
        btn_row = ctk.CTkFrame(frame)
        btn_row.pack(fill="x", padx=10, pady=5)
        ctk.CTkButton(btn_row, text="🔍 Compare", width=100, command=self._compare_folders).pack(side="left", padx=5)
        ctk.CTkButton(btn_row, text="➡️ Sync 1→2", width=100, fg_color="#28a745",
                     command=lambda: self._sync_folders("1to2")).pack(side="left", padx=5)
        ctk.CTkButton(btn_row, text="⬅️ Sync 2→1", width=100, fg_color="#17a2b8",
                     command=lambda: self._sync_folders("2to1")).pack(side="left", padx=5)
        ctk.CTkButton(btn_row, text="↔️ Sync Both", width=100, fg_color="#ffc107", text_color="black",
                     command=lambda: self._sync_folders("both")).pack(side="left", padx=5)
        
        # Results
        self.text_sync = ctk.CTkTextbox(frame, wrap="word", font=("Consolas", 11))
        self.text_sync.pack(fill="both", expand=True, padx=10, pady=8)
    
    def _build_links_tab(self):
        """Build the Broken Links tab."""
        frame = self.tabview.tab("🔗 Links")
        
        self._broken_links = []
        
        header = ctk.CTkFrame(frame)
        header.pack(fill="x", padx=10, pady=8)
        ctk.CTkLabel(header, text="🔗 Find Broken Shortcuts", font=("Segoe UI", 14, "bold")).pack(side="left", padx=10)
        
        btn_row = ctk.CTkFrame(frame)
        btn_row.pack(fill="x", padx=10, pady=5)
        ctk.CTkButton(btn_row, text="🔍 Find Broken Links", width=150, command=self._find_broken_links).pack(side="left", padx=5)
        ctk.CTkButton(btn_row, text="🗑️ Delete Broken", width=130, fg_color="#dc3545",
                     hover_color="#c82333", command=self._delete_broken_links).pack(side="left", padx=5)
        
        self.text_links = ctk.CTkTextbox(frame, wrap="word", font=("Consolas", 11))
        self.text_links.pack(fill="both", expand=True, padx=10, pady=8)
    
    # ===== NEW TOOLS HANDLERS =====
    
    def _preview_rename(self):
        folder = self._get_folder()
        if not folder:
            return
        
        pattern = self.entry_rename_pattern.get() or "file_{n}"
        start = int(self.entry_rename_start.get() or "1")
        ext = self.entry_rename_ext.get() or "*"
        
        self._set_status("🔄 Generating preview...")
        
        def do_preview():
            preview = batch_rename_preview(folder, pattern, start, ext, 
                                          lambda msg: self.after(0, lambda: self._set_status(msg)))
            self._rename_preview = preview
            
            text = format_rename_preview(preview)
            self.after(0, lambda: self._update_textbox(self.text_rename, text))
            self.after(0, lambda: self._set_status(f"✅ Preview: {len(preview)} files", "green"))
        
        threading.Thread(target=do_preview, daemon=True).start()
    
    def _execute_rename(self):
        if not self._rename_preview:
            messagebox.showinfo("Info", "Please preview first.")
            return
        
        if not messagebox.askyesno("Confirm", f"Rename {len(self._rename_preview)} files?"):
            return
        
        self._set_status("🔄 Renaming files...")
        
        def do_rename():
            result = batch_rename_execute(self._rename_preview,
                                         lambda msg: self.after(0, lambda: self._set_status(msg)))
            
            text = f"✅ Renamed: {len(result['success'])}\n"
            text += f"⏭️ Skipped: {len(result['skipped'])}\n"
            text += f"❌ Errors: {len(result['errors'])}\n\n"
            
            if result['errors']:
                text += "Errors:\n" + "\n".join(result['errors'][:20])
            
            self._rename_preview = []
            self.after(0, lambda: self._update_textbox(self.text_rename, text))
            self.after(0, lambda: self._set_status(f"✅ Done!", "green"))
        
        threading.Thread(target=do_rename, daemon=True).start()
    
    def _run_disk_analysis(self):
        folder = self._get_folder()
        if not folder:
            return
        
        self._set_status("🔄 Analyzing disk usage...")
        
        def do_analyze():
            result = analyze_disk_usage(folder,
                                       lambda msg: self.after(0, lambda: self._set_status(msg)))
            self._disk_result = result
            
            text = format_disk_analysis(result)
            self.after(0, lambda: self._update_textbox(self.text_disk, text))
            self.after(0, lambda: self._set_status("✅ Analysis complete", "green"))
        
        threading.Thread(target=do_analyze, daemon=True).start()
    
    def _browse_zip(self):
        path = filedialog.askopenfilename(title="Select ZIP file", filetypes=[("ZIP files", "*.zip")])
        if path:
            self.entry_zip_input.delete(0, "end")
            self.entry_zip_input.insert(0, path)
    
    def _compress_folder(self):
        folder = self._get_folder()
        if not folder:
            return
        
        output = self.entry_zip_output.get().strip() or None
        self._set_status("🔄 Compressing...")
        
        def do_compress():
            result = compress_folder(folder, output,
                                    lambda msg: self.after(0, lambda: self._set_status(msg)))
            
            text = format_compress_result(result)
            self.after(0, lambda: self._update_textbox(self.text_compress, text))
            self.after(0, lambda: self._set_status("✅ Compression complete", "green"))
        
        threading.Thread(target=do_compress, daemon=True).start()
    
    def _extract_archive(self):
        zip_path = self.entry_zip_input.get().strip()
        if not zip_path or not os.path.isfile(zip_path):
            messagebox.showwarning("Warning", "Please select a valid ZIP file.")
            return
        
        self._set_status("🔄 Extracting...")
        
        def do_extract():
            result = extract_archive(zip_path, None,
                                    lambda msg: self.after(0, lambda: self._set_status(msg)))
            
            text = format_compress_result(result)
            self.after(0, lambda: self._update_textbox(self.text_compress, text))
            self.after(0, lambda: self._set_status("✅ Extraction complete", "green"))
        
        threading.Thread(target=do_extract, daemon=True).start()
    
    def _compare_folders(self):
        f1 = self.entry_sync_folder1.get().strip()
        f2 = self.entry_sync_folder2.get().strip()
        
        if not f1 or not f2 or not os.path.isdir(f1) or not os.path.isdir(f2):
            messagebox.showwarning("Warning", "Please select two valid folders.")
            return
        
        self._set_status("🔄 Comparing folders...")
        
        def do_compare():
            result = compare_folders(f1, f2,
                                    lambda msg: self.after(0, lambda: self._set_status(msg)))
            self._sync_result = result
            
            text = format_folder_comparison(result)
            self.after(0, lambda: self._update_textbox(self.text_sync, text))
            self.after(0, lambda: self._set_status("✅ Comparison complete", "green"))
        
        threading.Thread(target=do_compare, daemon=True).start()
    
    def _sync_folders(self, direction):
        f1 = self.entry_sync_folder1.get().strip()
        f2 = self.entry_sync_folder2.get().strip()
        
        if not f1 or not f2 or not os.path.isdir(f1) or not os.path.isdir(f2):
            messagebox.showwarning("Warning", "Please select two valid folders.")
            return
        
        if not messagebox.askyesno("Confirm", f"Sync folders ({direction})?"):
            return
        
        self._set_status(f"🔄 Syncing {direction}...")
        
        def do_sync():
            result = sync_folders(f1, f2, direction,
                                 lambda msg: self.after(0, lambda: self._set_status(msg)))
            
            text = f"✅ Sync Complete ({direction})\n\n"
            text += f"Files copied: {len(result.get('copied', []))}\n"
            text += f"Errors: {len(result.get('errors', []))}\n\n"
            
            if result.get('copied'):
                text += "Copied:\n" + "\n".join(result['copied'][:30])
            
            self.after(0, lambda: self._update_textbox(self.text_sync, text))
            self.after(0, lambda: self._set_status("✅ Sync complete", "green"))
        
        threading.Thread(target=do_sync, daemon=True).start()
    
    def _find_similar_files(self):
        folder = self._get_folder()
        if not folder:
            return
        
        self._set_status("🔄 Finding similar files...")
        
        def do_find():
            # First, get all files
            from folder_info import get_folder_details
            info = get_folder_details(folder, lambda msg: self.after(0, lambda: self._set_status(msg)))
            files = info.get("all_files", [])
            
            if not files:
                self.after(0, lambda: self._update_textbox(self.text_similar, "No files found."))
                return
            
            # Find similar files
            results = find_similar_files(files, lambda msg: self.after(0, lambda: self._set_status(msg)))
            self._similar_files = results
            
            # Format results
            lines = []
            lines.append("=" * 60)
            lines.append("🔀 SIMILAR FILES FOUND")
            lines.append("=" * 60)
            lines.append(f"\nTotal groups found: {len(results)}\n")
            
            # Group by type
            name_groups = [r for r in results if r.get("type") == "similar_name"]
            fuzzy_groups = [r for r in results if r.get("type") == "fuzzy_match"]
            
            if name_groups:
                lines.append(f"\n{'─' * 50}")
                lines.append(f"📁 SIMILAR NAMES ({len(name_groups)} groups)")
                lines.append(f"{'─' * 50}")
                
                for group in name_groups[:20]:
                    lines.append(f"\n  📂 Base name: {group['base_name']}")
                    lines.append(f"     Files: {group['count']}")
                    for f in group["files"][:5]:
                        lines.append(f"       • {f['name']}")
                    if len(group["files"]) > 5:
                        lines.append(f"       ... and {len(group['files']) - 5} more")
            
            if fuzzy_groups:
                lines.append(f"\n{'─' * 50}")
                lines.append(f"🔍 FUZZY MATCHES ({len(fuzzy_groups)} pairs)")
                lines.append(f"{'─' * 50}")
                
                for match in fuzzy_groups[:30]:
                    sim = match["similarity"] * 100
                    lines.append(f"\n  {match['file1']['name']}")
                    lines.append(f"  ≈ {match['file2']['name']}")
                    lines.append(f"    Similarity: {sim:.1f}%")
            
            text = "\n".join(lines)
            self.after(0, lambda: self._update_textbox(self.text_similar, text))
            self.after(0, lambda: self._set_status(f"✅ Found {len(results)} groups", "green"))
        
        threading.Thread(target=do_find, daemon=True).start()
    
    def _find_backup_files(self):
        folder = self._get_folder()
        if not folder:
            return
        
        self._set_status("🔄 Finding backup files...")
        
        def do_find():
            from folder_info import get_folder_details
            info = get_folder_details(folder, lambda msg: self.after(0, lambda: self._set_status(msg)))
            files = info.get("all_files", [])
            
            results = find_backup_files(files, lambda msg: self.after(0, lambda: self._set_status(msg)))
            self._backup_files = results
            
            lines = []
            lines.append("=" * 60)
            lines.append("📦 BACKUP FILES FOUND")
            lines.append("=" * 60)
            lines.append(f"\nTotal backup files: {len(results)}\n")
            
            if results:
                # Group by type
                by_type = {}
                for r in results:
                    t = r.get("type", "other")
                    if t not in by_type:
                        by_type[t] = []
                    by_type[t].append(r)
                
                for backup_type, files in by_type.items():
                    lines.append(f"\n{'─' * 50}")
                    lines.append(f"📁 {backup_type.upper()} ({len(files)} files)")
                    lines.append(f"{'─' * 50}")
                    
                    for f in files[:20]:
                        file_info = f["file"]
                        lines.append(f"  • {file_info['rel_path']}")
                    
                    if len(files) > 20:
                        lines.append(f"  ... and {len(files) - 20} more")
            else:
                lines.append("\n✅ No backup files found!")
            
            text = "\n".join(lines)
            self.after(0, lambda: self._update_textbox(self.text_similar, text))
            self.after(0, lambda: self._set_status(f"✅ Found {len(results)} backup files", "green"))
        
        threading.Thread(target=do_find, daemon=True).start()
    
    def _run_fast_scan(self):
        folder = self._get_folder()
        if not folder:
            return
        
        self._set_status("⚡ Running fast parallel scan...")
        
        def do_scan():
            result = fast_scan(folder, lambda msg: self.after(0, lambda: self._set_status(msg)))
            self._fast_scan_result = result
            
            lines = []
            lines.append("=" * 60)
            lines.append("⚡ FAST SCAN RESULTS")
            lines.append("=" * 60)
            
            lines.append(f"\n📁 Folder: {result['folder']}")
            lines.append(f"📄 Files: {result['file_count']:,}")
            lines.append(f"📂 Folders: {result['folder_count']:,}")
            
            # Format size
            size = result['total_size']
            for unit in ["B", "KB", "MB", "GB"]:
                if size < 1024:
                    lines.append(f"💾 Size: {size:.1f} {unit}")
                    break
                size /= 1024
            
            # Extension breakdown
            lines.append(f"\n{'─' * 50}")
            lines.append("📊 BY EXTENSION")
            lines.append(f"{'─' * 50}")
            
            ext_sorted = sorted(result['by_extension'].items(), 
                               key=lambda x: -x[1]['count'])[:15]
            
            for ext, data in ext_sorted:
                ext_name = ext if ext else "(no ext)"
                lines.append(f"  {ext_name:12} {data['count']:>6} files")
            
            # Potential duplicates hint
            dup_candidates = sum(1 for size, files in result['by_size_group'].items() 
                                if len(files) > 1 and size > 0)
            lines.append(f"\n💡 {dup_candidates} file sizes have potential duplicates")
            
            text = "\n".join(lines)
            self.after(0, lambda: self._update_textbox(self.text_similar, text))
            self.after(0, lambda: self._set_status("✅ Fast scan complete", "green"))
        
        threading.Thread(target=do_scan, daemon=True).start()
    
    def _find_broken_links(self):
        folder = self._get_folder()
        if not folder:
            return
        
        self._set_status("🔄 Finding broken links...")
        
        def do_find():
            result = find_broken_shortcuts(folder,
                                          lambda msg: self.after(0, lambda: self._set_status(msg)))
            self._broken_links = result.get("broken", [])
            
            text = format_broken_shortcuts(result)
            self.after(0, lambda: self._update_textbox(self.text_links, text))
            self.after(0, lambda: self._set_status(f"✅ Found {len(self._broken_links)} broken", "green"))
        
        threading.Thread(target=do_find, daemon=True).start()
    
    def _delete_broken_links(self):
        if not self._broken_links:
            messagebox.showinfo("Info", "No broken links found. Run scan first.")
            return
        
        if not messagebox.askyesno("Confirm", f"Delete {len(self._broken_links)} broken shortcuts?"):
            return
        
        self._set_status("🔄 Deleting broken links...")
        
        def do_delete():
            result = delete_broken_shortcuts(self._broken_links,
                                            lambda msg: self.after(0, lambda: self._set_status(msg)))
            
            text = f"✅ Deleted: {len(result['deleted'])}\n"
            text += f"❌ Errors: {len(result['errors'])}\n"
            
            self._broken_links = []
            self.after(0, lambda: self._update_textbox(self.text_links, text))
            self.after(0, lambda: self._set_status("✅ Cleanup complete", "green"))
        
        threading.Thread(target=do_delete, daemon=True).start()
    
    def _update_textbox(self, textbox, text):
        """Helper to update a textbox."""
        textbox.delete("1.0", "end")
        textbox.insert("1.0", text)
    
    # ===== HELPER FUNCTIONS =====
    def _browse_folder(self):
        path = filedialog.askdirectory(title="Choose folder")
        if path:
            self.entry_folder.delete(0, "end")
            self.entry_folder.insert(0, path)
    
    def _browse_to(self, entry_widget):
        path = filedialog.askdirectory(title="Choose destination")
        if path:
            entry_widget.delete(0, "end")
            entry_widget.insert(0, path)
    
    def _browse_undo(self):
        path = filedialog.askopenfilename(title="Select undo log", initialdir=TMP_DIR, filetypes=[("JSON", "*.json")])
        if path:
            self.entry_undo.delete(0, "end")
            self.entry_undo.insert(0, path)
    
    def _get_folder(self):
        folder = (self.entry_folder.get() or "").strip()
        if not folder or not os.path.isdir(folder):
            messagebox.showwarning("Warning", "Please choose a valid folder.")
            return None
        return folder
    
    def _set_status(self, text, color="yellow"):
        """Set status with colored indicator."""
        # Map colors to new scheme
        color_map = {
            "yellow": COLORS["warning"],
            "green": COLORS["accent2"],
            "red": COLORS["danger"],
            "blue": COLORS["info"],
            "gray": COLORS["text_dim"],
        }
        actual_color = color_map.get(color, color)
        
        # Add indicator dot
        if "✅" in text or color == "green":
            indicator = "●"
            actual_color = COLORS["accent2"]
        elif "❌" in text or color == "red":
            indicator = "●"
            actual_color = COLORS["danger"]
        elif "🔄" in text or "⚡" in text:
            indicator = "◐"
            actual_color = COLORS["warning"]
        else:
            indicator = "●"
        
        self.label_status.configure(text=f"{indicator} {text}", text_color=actual_color)
    
    # ===== FULL SCAN =====
    def _run_full_scan(self):
        folder = self._get_folder()
        if not folder:
            return
        
        self._set_status("🔄 Running full scan...")
        
        def do_scan():
            self.after(0, lambda: self._set_status("🔄 Getting folder info..."))
            self._folder_info = get_folder_details(folder)
            self.after(0, self._update_info_tab)
            
            self.after(0, lambda: self._set_status("🔄 Detecting project type..."))
            self._analysis_result = find_unrelated_files(folder, use_ai=bool(DEEPSEEK_API_KEY))
            self._mismatched_files = self._analysis_result.get("unrelated_files", [])
            self.after(0, self._update_analysis_tab)
            
            self.after(0, lambda: self._set_status("🔄 Finding duplicates..."))
            self._duplicate_result = find_duplicates(folder)
            self.after(0, self._update_duplicates_tab)
            
            self.after(0, lambda: self._set_status("🔄 Finding big files..."))
            min_mb = self._settings.get("big_files_min_mb", 100)
            self._big_files = find_big_files(folder, min_size_mb=min_mb)
            self.after(0, self._update_bigfiles_tab)
            
            self.after(0, lambda: self._set_status("🔄 Finding old files..."))
            days = self._settings.get("old_files_days", 365)
            self._old_files = find_old_files(folder, days_old=days)
            self.after(0, self._update_oldfiles_tab)
            
            self.after(0, lambda: self._set_status("🔄 Finding empty folders..."))
            self._empty_folders = find_empty_folders(folder)
            self.after(0, self._update_empty_tab)
            
            self.after(0, lambda: self._set_status("✅ Full scan complete!", "green"))
        
        threading.Thread(target=do_scan, daemon=True).start()
    
    # ===== INFO TAB =====
    def _run_folder_info(self):
        folder = self._get_folder()
        if not folder:
            return
        
        self._set_status("🔄 Getting folder info...")
        
        def do_info():
            self._folder_info = get_folder_details(folder)
            self.after(0, self._update_info_tab)
            self.after(0, lambda: self._set_status("✅ Done!", "green"))
        
        threading.Thread(target=do_info, daemon=True).start()
    
    def _update_info_tab(self):
        if not self._folder_info or "error" in self._folder_info:
            return
        
        info = self._folder_info
        self.label_folder_path.configure(text=f"📍 Path: {info['folder_path']}")
        self.label_folder_stats.configure(
            text=f"💾 {format_size(info['total_size'])} | 📄 {info['total_files']:,} files | 📁 {info['total_subdirs']:,} folders"
        )
        
        report = generate_folder_report(info)
        self.text_info.delete("1.0", "end")
        self.text_info.insert("1.0", report)
    
    # ===== SEARCH TAB =====
    def _run_search(self):
        folder = self._get_folder()
        if not folder:
            return
        
        query = self.entry_search.get().strip()
        if not query:
            messagebox.showinfo("Info", "Enter a search term.")
            return
        
        self._set_status(f"🔍 Searching for '{query}'...")
        self.text_search.delete("1.0", "end")
        self.text_search.insert("1.0", "Searching...")
        
        def do_search():
            self._search_results = search_files(folder, query)
            self.after(0, self._update_search_tab)
        
        threading.Thread(target=do_search, daemon=True).start()
    
    def _update_search_tab(self):
        count = len(self._search_results)
        self.label_search_count.configure(text=f"Found: {count} files")
        self._set_status(f"✅ Found {count} files", "green")
        
        self.text_search.delete("1.0", "end")
        
        if not self._search_results:
            self.text_search.insert("1.0", "No files found matching your search.")
            return
        
        lines = [f"Found {count} files:\n"]
        for f in self._search_results[:200]:
            lines.append(f"📄 {f['name']}")
            lines.append(f"   📍 {f['rel_path']}")
            lines.append(f"   💾 {format_size(f['size'])} | 📅 {f['modified']}\n")
        
        if count > 200:
            lines.append(f"\n... and {count - 200} more files")
        
        self.text_search.insert("1.0", "\n".join(lines))
    
    # ===== AI DEEP ANALYSIS =====
    def _run_ai_analysis(self):
        """Run AI deep analysis - reads folder completely before deciding."""
        folder = self._get_folder()
        if not folder:
            return
        
        self._set_status("🤖 AI is reading the entire folder...", "yellow")
        self.tabview.set("🎯 Analysis")
        self.text_analysis.delete("1.0", "end")
        self.text_analysis.insert("1.0", "🤖 AI is analyzing...\n\n"
            "• Reading folder structure\n"
            "• Reading file contents\n"
            "• Understanding project purpose\n"
            "• Deciding what belongs and what doesn't\n\n"
            "Please wait...")
        
        def do_ai_analysis():
            def progress(msg):
                self.after(0, lambda: self._set_status(f"🤖 {msg}", "yellow"))
            
            result = ai_analyze_folder(folder, progress_cb=progress)
            self._ai_analysis = result
            self._mismatched_files = result.get("unrelated_files", [])
            self.after(0, lambda: self._update_ai_analysis_tab(result))
        
        threading.Thread(target=do_ai_analysis, daemon=True).start()
    
    def _update_ai_analysis_tab(self, result):
        """Update analysis tab with AI results."""
        if "error" in result:
            self._set_status(f"❌ Error: {result['error']}", "red")
            return
        
        # Update header
        should_sep = result.get("should_separate", "MAYBE")
        confidence = result.get("confidence", "LOW")
        folder_type = result.get("folder_type", "Unknown")
        
        if should_sep == "YES":
            decision = "✅ YES - Separate files"
            self._set_status(f"🤖 AI says: Separate {len(self._mismatched_files)} files", "green")
        elif should_sep == "NO":
            decision = "❌ NO - All files belong"
            self._set_status("🤖 AI says: All files belong here!", "green")
        else:
            decision = "⚠️ MAYBE - Review needed"
            self._set_status("🤖 AI says: Some files are questionable", "yellow")
        
        self.label_purpose.configure(text=f"🤖 {folder_type}")
        self.label_analysis_stats.configure(
            text=f"Decision: {decision} | Confidence: {confidence} | Unrelated: {len(self._mismatched_files)}"
        )
        
        # Show full AI analysis
        self.text_analysis.delete("1.0", "end")
        report = format_ai_analysis(result)
        self.text_analysis.insert("1.0", report)
    
    # ===== ANALYSIS TAB =====
    def _run_analysis(self):
        folder = self._get_folder()
        if not folder:
            return
        
        self._set_status("🔄 Detecting project type...")
        
        def do_analysis():
            # Use smart project analyzer
            self._analysis_result = find_unrelated_files(folder, use_ai=bool(DEEPSEEK_API_KEY))
            self._mismatched_files = self._analysis_result.get("unrelated_files", [])
            self.after(0, self._update_analysis_tab)
            self.after(0, lambda: self._set_status("✅ Done!", "green"))
        
        threading.Thread(target=do_analysis, daemon=True).start()
    
    def _update_analysis_tab(self):
        if not self._analysis_result:
            return
        
        r = self._analysis_result
        proj_type = r.get("project_description", r.get("project_type", "Unknown"))
        confidence = r.get("confidence", "unknown").upper()
        
        self.label_purpose.configure(text=f"🎯 {proj_type} (Confidence: {confidence})")
        self.label_analysis_stats.configure(
            text=f"Total: {r.get('total_files', 0)} | ✅ Related: {r.get('related_count', 0)} | ❌ Unrelated: {r.get('unrelated_count', 0)}"
        )
        
        self.text_analysis.delete("1.0", "end")
        
        # Use formatted report
        report = format_analysis_report(r)
        self.text_analysis.insert("1.0", report)
    
    def _run_turbo_analysis(self):
        """Run fast parallel scan with advanced algorithms."""
        folder = self._get_folder()
        if not folder:
            return
        
        self._set_status("⚡ Running Turbo Scan...")
        self.tabview.set("🎯 Analysis")
        self.text_analysis.delete("1.0", "end")
        self.text_analysis.insert("1.0", "⚡ TURBO SCAN\n" + "=" * 50 + "\n\n"
            "Using parallel processing for maximum speed...\n\n"
            "• Multi-threaded file scanning\n"
            "• Smart caching for repeated scans\n"
            "• Optimized hash algorithms\n\n"
            "Please wait...")
        
        def do_turbo():
            start = time.time()
            scanner = TurboScanner()
            
            def progress(msg):
                self.after(0, lambda: self._set_status(f"⚡ {msg}"))
            
            result = scanner.scan_folder(folder, progress)
            
            # Detect project
            detector = ProjectDetector()
            project = detector.detect(result)
            
            elapsed = time.time() - start
            
            # Format results
            lines = []
            lines.append("⚡ TURBO SCAN COMPLETE")
            lines.append("=" * 60)
            lines.append(f"\n📁 Folder: {folder}")
            lines.append(f"⏱️ Time: {elapsed:.2f}s")
            lines.append(f"\n{'─' * 50}")
            lines.append("📊 SCAN RESULTS")
            lines.append(f"{'─' * 50}")
            lines.append(f"  📄 Total files: {result['total_files']:,}")
            lines.append(f"  📁 Total folders: {result['total_folders']:,}")
            lines.append(f"  📦 Total size: {format_size(result['total_size'])}")
            
            lines.append(f"\n{'─' * 50}")
            lines.append("🎯 PROJECT DETECTION")
            lines.append(f"{'─' * 50}")
            lines.append(f"  🏷️ Type: {project['type']}")
            lines.append(f"  📊 Confidence: {project['confidence']:.0%}")
            lines.append(f"  🔍 Is Project: {'✅ Yes' if project['is_project'] else '❌ No'}")
            
            if project['indicators']:
                lines.append(f"\n  📋 Indicators:")
                for ind in project['indicators'][:8]:
                    lines.append(f"     ✓ {ind}")
            
            if project['secondary_types']:
                lines.append(f"\n  🔀 Also detected: {', '.join(project['secondary_types'])}")
            
            lines.append(f"\n{'─' * 50}")
            lines.append("📂 FILE TYPES BREAKDOWN")
            lines.append(f"{'─' * 50}")
            
            # Sort by count
            by_ext = result['by_extension']
            sorted_exts = sorted(by_ext.items(), key=lambda x: len(x[1]), reverse=True)[:15]
            
            max_count = len(sorted_exts[0][1]) if sorted_exts else 1
            for ext, files in sorted_exts:
                ext_name = ext if ext else "(no ext)"
                bar_len = int((len(files) / max_count) * 30)
                bar = "█" * bar_len + "░" * (30 - bar_len)
                lines.append(f"  {ext_name:12} [{bar}] {len(files):,}")
            
            lines.append(f"\n{'=' * 60}")
            lines.append("💡 Use 'Full Report' for complete analysis with duplicates.")
            
            text = "\n".join(lines)
            self.after(0, lambda: self._update_textbox(self.text_analysis, text))
            self.after(0, lambda: self.label_purpose.configure(text=f"🎯 {project['type']} ({project['confidence']:.0%})"))
            self.after(0, lambda: self._set_status(f"✅ Turbo scan done in {elapsed:.2f}s", "green"))
        
        threading.Thread(target=do_turbo, daemon=True).start()
    
    def _run_complete_analysis(self):
        """Run complete unified analysis with all checks."""
        folder = self._get_folder()
        if not folder:
            return
        
        self._set_status("📊 Running complete analysis...")
        self.tabview.set("🎯 Analysis")
        self.text_analysis.delete("1.0", "end")
        self.text_analysis.insert("1.0", "📊 COMPLETE FOLDER ANALYSIS\n" + "=" * 50 + "\n\n"
            "Running 5-phase comprehensive analysis:\n\n"
            "  Phase 1: 🔍 Fast parallel scan\n"
            "  Phase 2: 🎯 Project detection\n"
            "  Phase 3: 🔄 Duplicate detection\n"
            "  Phase 4: ⚠️ Mismatch analysis\n"
            "  Phase 5: 🔗 Similar file detection\n\n"
            "Please wait...")
        
        def do_complete():
            def progress(msg):
                self.after(0, lambda: self._set_status(msg))
            
            analyzer = UnifiedAnalyzer()
            result = analyzer.full_analysis(folder, progress)
            
            # Store for later use
            self._complete_analysis = result
            self._mismatched_files = [m[0] for m in result.get('mismatches', {}).get('mismatched', [])]
            
            # Format report
            text = format_advanced_report(result)
            
            # Add extra details
            lines = [text]
            
            # Duplicate details
            dupes = result.get('duplicates', {})
            if dupes.get('groups'):
                lines.append("\n" + "─" * 60)
                lines.append("🔄 DUPLICATE GROUPS (top 5)")
                lines.append("─" * 60)
                
                for i, group in enumerate(dupes['groups'][:5], 1):
                    lines.append(f"\n  Group {i}:")
                    for f in group[:3]:
                        lines.append(f"    • {os.path.basename(f)}")
                    if len(group) > 3:
                        lines.append(f"    ... and {len(group) - 3} more")
            
            # Mismatch details
            mism = result.get('mismatches', {})
            if mism.get('mismatched'):
                lines.append("\n" + "─" * 60)
                lines.append("⚠️ MISMATCHED FILES (top 10)")
                lines.append("─" * 60)
                
                for filepath, reason, conf in mism['mismatched'][:10]:
                    lines.append(f"  • {os.path.basename(filepath)}")
                    lines.append(f"    └─ {reason} (confidence: {conf:.0%})")
            
            # Similar files
            similar = result.get('similar', [])
            if similar:
                lines.append("\n" + "─" * 60)
                lines.append("🔗 SIMILAR FILE GROUPS (top 5)")
                lines.append("─" * 60)
                
                for grp in similar[:5]:
                    lines.append(f"\n  📁 {grp['normalized_name']}")
                    lines.append(f"     Type: {grp['similarity_type']} | Confidence: {grp['confidence']:.0%}")
                    for f in grp['files'][:3]:
                        lines.append(f"     • {os.path.basename(f)}")
            
            full_text = "\n".join(lines)
            self.after(0, lambda: self._update_textbox(self.text_analysis, full_text))
            
            # Update UI
            summary = result.get('summary', {})
            health = summary.get('health_score', 0)
            proj_type = summary.get('project_type', 'Unknown')
            
            self.after(0, lambda: self.label_purpose.configure(
                text=f"🎯 {proj_type} | Health: {health}/100"))
            self.after(0, lambda: self.label_analysis_stats.configure(
                text=f"📄 {summary.get('total_files', 0)} files | "
                     f"🔄 {summary.get('duplicate_files', 0)} dupes | "
                     f"⚠️ {summary.get('mismatched_files', 0)} mismatched"))
            self.after(0, lambda: self._set_status(f"✅ Analysis complete - Health: {health}/100", "green"))
        
        threading.Thread(target=do_complete, daemon=True).start()
    
    def _move_mismatched(self):
        if not self._mismatched_files:
            messagebox.showinfo("Info", "No unrelated files to move.\n\nRun 🤖 AI Analyze first!")
            return
        
        dest = self.entry_mismatch_dest.get().strip()
        if not dest:
            dest = filedialog.askdirectory(title="Destination for unrelated files")
            if dest:
                self.entry_mismatch_dest.delete(0, "end")
                self.entry_mismatch_dest.insert(0, dest)
        if not dest:
            return
        
        # Use AI cleanup plan if available
        if self._ai_analysis:
            plan = get_ai_cleanup_plan(self._ai_analysis, dest)
        else:
            plan = get_cleanup_plan(self._mismatched_files, dest)
        
        sim = self.var_mismatch_sim.get()
        
        if not sim and not messagebox.askyesno("Confirm", 
            f"Move {len(plan)} unrelated files to:\n{dest}\n\n"
            f"Files will be organized by type (images/, audio/, etc.)\n\n"
            f"💡 A backup will be created automatically."):
            return
        
        self._execute_plan(plan, sim, "unrelated files")
    
    # ===== DUPLICATES TAB =====
    def _run_duplicate_scan(self):
        folder = self._get_folder()
        if not folder:
            return
        
        self._set_status("🔄 Finding duplicates...")
        
        def do_scan():
            self._duplicate_result = find_duplicates(folder)
            self.after(0, self._update_duplicates_tab)
            self.after(0, lambda: self._set_status("✅ Done!", "green"))
        
        threading.Thread(target=do_scan, daemon=True).start()
    
    def _update_duplicates_tab(self):
        if not self._duplicate_result:
            return
        
        r = self._duplicate_result
        groups = r.get("duplicate_groups", 0)
        files = r.get("total_duplicate_files", 0)
        size = r.get("total_duplicate_size_mb", 0)
        
        self.label_dup_stats.configure(text=f"Groups: {groups} | Duplicates: {files} | Wasted: {size:.1f} MB")
        
        self.text_duplicates.delete("1.0", "end")
        
        if not r.get("groups"):
            self.text_duplicates.insert("1.0", "✅ No duplicate files found!")
            return
        
        lines = [f"Found {groups} groups of duplicates ({files} files, {size:.1f} MB wasted)\n"]
        lines.append("─" * 50 + "\n")
        
        for i, g in enumerate(r.get("groups", [])[:30], 1):
            orig = g.get("original", {})
            dups = g.get("duplicates", [])
            
            lines.append(f"\n📦 Group {i} ({len(dups)} duplicates)")
            lines.append(f"   ✅ ORIGINAL: {orig.get('name', '')}")
            lines.append(f"      {orig.get('path', '')}")
            
            for d in dups:
                lines.append(f"   ❌ COPY: {d.get('name', '')}")
                lines.append(f"      {d.get('path', '')}")
        
        self.text_duplicates.insert("1.0", "\n".join(lines))
    
    def _move_duplicates(self):
        if not self._duplicate_result or not self._duplicate_result.get("groups"):
            messagebox.showinfo("Info", "No duplicates to move.")
            return
        
        dest = self.entry_dup_dest.get().strip()
        if not dest:
            dest = filedialog.askdirectory(title="Destination")
            if dest:
                self.entry_dup_dest.delete(0, "end")
                self.entry_dup_dest.insert(0, dest)
        if not dest:
            return
        
        plan = get_duplicate_cleanup_plan(self._duplicate_result, dest)
        sim = self.var_dup_sim.get()
        
        if not sim and not messagebox.askyesno("Confirm", f"Move {len(plan)} duplicate files?\nOriginals will be kept."):
            return
        
        self._execute_plan(plan, sim, "duplicates")
    
    # ===== BIG FILES TAB =====
    def _run_bigfiles_scan(self):
        folder = self._get_folder()
        if not folder:
            return
        
        try:
            min_size = float(self.entry_min_size.get() or "100")
        except:
            min_size = 100
        
        self._set_status(f"🔄 Finding files > {min_size} MB...")
        
        def do_scan():
            self._big_files = find_big_files(folder, min_size_mb=min_size)
            self.after(0, self._update_bigfiles_tab)
            self.after(0, lambda: self._set_status("✅ Done!", "green"))
        
        threading.Thread(target=do_scan, daemon=True).start()
    
    def _update_bigfiles_tab(self):
        count = len(self._big_files)
        total_size = sum(f["size"] for f in self._big_files)
        
        self.label_bigfiles_stats.configure(text=f"Found: {count} files ({format_size(total_size)})")
        
        self.text_bigfiles.delete("1.0", "end")
        
        if not self._big_files:
            self.text_bigfiles.insert("1.0", "No large files found.")
            return
        
        lines = [f"Found {count} large files (Total: {format_size(total_size)})\n"]
        lines.append("─" * 50 + "\n")
        
        for f in self._big_files[:100]:
            lines.append(f"📦 {f['size_str']:>10}  {f['name']}")
            lines.append(f"              📍 {f['rel_path']}")
            lines.append(f"              📅 {f['modified']}\n")
        
        self.text_bigfiles.insert("1.0", "\n".join(lines))
    
    # ===== OLD FILES TAB =====
    def _run_oldfiles_scan(self):
        folder = self._get_folder()
        if not folder:
            return
        
        try:
            days = int(self.entry_days_old.get() or "365")
        except:
            days = 365
        
        self._set_status(f"🔄 Finding files older than {days} days...")
        
        def do_scan():
            self._old_files = find_old_files(folder, days_old=days)
            self.after(0, self._update_oldfiles_tab)
            self.after(0, lambda: self._set_status("✅ Done!", "green"))
        
        threading.Thread(target=do_scan, daemon=True).start()
    
    def _update_oldfiles_tab(self):
        if not self._old_files:
            return
        
        count = self._old_files.get("count", 0)
        size = self._old_files.get("total_size_str", "0 B")
        
        self.label_oldfiles_stats.configure(text=f"Found: {count} files ({size})")
        
        self.text_oldfiles.delete("1.0", "end")
        
        files = self._old_files.get("files", [])
        if not files:
            self.text_oldfiles.insert("1.0", "No old files found.")
            return
        
        lines = [f"Found {count} old files (Total: {size})\n"]
        lines.append("─" * 50 + "\n")
        
        for f in files[:100]:
            lines.append(f"🕐 {f['age_days']} days old  {f['name']}")
            lines.append(f"   📍 {f['rel_path']}")
            lines.append(f"   💾 {f['size_str']} | 📅 Last modified: {f['modified']}\n")
        
        self.text_oldfiles.insert("1.0", "\n".join(lines))
    
    # ===== EMPTY FOLDERS TAB =====
    def _run_empty_scan(self):
        folder = self._get_folder()
        if not folder:
            return
        
        self._set_status("🔄 Finding empty folders...")
        
        def do_scan():
            self._empty_folders = find_empty_folders(folder)
            self.after(0, self._update_empty_tab)
            self.after(0, lambda: self._set_status("✅ Done!", "green"))
        
        threading.Thread(target=do_scan, daemon=True).start()
    
    def _update_empty_tab(self):
        count = len(self._empty_folders)
        self.label_empty_stats.configure(text=f"Found: {count} empty folders")
        
        self.text_empty.delete("1.0", "end")
        
        if not self._empty_folders:
            self.text_empty.insert("1.0", "✅ No empty folders found!")
            return
        
        lines = [f"Found {count} empty folders:\n"]
        lines.append("─" * 50 + "\n")
        
        for f in self._empty_folders[:100]:
            lines.append(f"🗑️ {f.get('rel_path', f.get('path', ''))}")
        
        self.text_empty.insert("1.0", "\n".join(lines))
    
    def _delete_empty(self):
        if not self._empty_folders:
            messagebox.showinfo("Info", "No empty folders to delete.")
            return
        
        sim = self.var_empty_sim.get()
        
        if not sim and not messagebox.askyesno("Confirm", f"Delete {len(self._empty_folders)} empty folders?"):
            return
        
        result = delete_empty_folders(self._empty_folders, simulation=sim)
        
        deleted = len(result.get("deleted", []))
        errors = len(result.get("errors", []))
        
        if sim:
            self.label_action_status.configure(text=f"📋 Simulation: {deleted} folders would be deleted", text_color="cyan")
        else:
            self.label_action_status.configure(text=f"✅ Deleted {deleted} folders", text_color="green")
            self._run_empty_scan()  # Refresh
    
    # ===== UNDO TAB =====
    def _load_history(self):
        self.text_history.delete("1.0", "end")
        
        # Show backups first
        backups = get_all_backups()
        
        if backups:
            text = format_backup_list(backups)
            self.text_history.insert("1.0", text)
        else:
            # Legacy undo logs
            logs = get_undo_logs()
            if not logs:
                self.text_history.insert("1.0", "No backups found.\n\n💡 Backups are created automatically when you move files.\nUse QUICK RESTORE to undo!")
                return
            
            lines = ["📜 Legacy Undo Logs:\n"]
            for log in logs[:20]:
                lines.append(f"📄 {log['name']}")
                lines.append(f"   Time: {log['timestamp']} | Files: {log['count']}\n")
            self.text_history.insert("1.0", "\n".join(lines))
    
    def _quick_restore(self):
        """One-click restore last operation."""
        last = get_last_backup()
        
        if not last:
            messagebox.showinfo("No Backup", "No backup found.\n\nBackups are created when you move files.")
            return
        
        backup_id = last.get("id", "")
        op_count = len(last.get("operations", []))
        desc = last.get("description", "")
        
        if not messagebox.askyesno("⏪ Quick Restore", 
            f"Restore last operation?\n\n"
            f"📦 {backup_id}\n"
            f"📝 {desc}\n"
            f"📄 {op_count} files to restore\n\n"
            f"All files will return to original locations."):
            return
        
        self._set_status("🔄 Restoring...")
        self.label_restore_status.configure(text="🔄 Restoring...", text_color="yellow")
        
        def do_restore():
            result = restore_backup(backup_id)
            self.after(0, lambda: self._finish_restore(result))
        
        threading.Thread(target=do_restore, daemon=True).start()
    
    def _restore_specific(self):
        """Restore specific backup by ID."""
        backup_id = self.entry_backup_id.get().strip()
        
        if not backup_id:
            messagebox.showwarning("Warning", "Enter a backup ID from the list above.")
            return
        
        details = get_backup_details(backup_id)
        if "error" in details:
            messagebox.showerror("Error", f"Backup not found: {backup_id}")
            return
        
        op_count = len(details.get("operations", []))
        
        if not messagebox.askyesno("Restore", f"Restore '{backup_id}'?\n\n{op_count} files will be moved back."):
            return
        
        self._set_status("🔄 Restoring...")
        self.label_restore_status.configure(text="🔄 Restoring...", text_color="yellow")
        
        def do_restore():
            result = restore_backup(backup_id)
            self.after(0, lambda: self._finish_restore(result))
        
        threading.Thread(target=do_restore, daemon=True).start()
    
    def _finish_restore(self, result):
        """Handle restore completion."""
        if "error" in result:
            self._set_status(f"❌ {result['error']}", "red")
            self.label_restore_status.configure(text=f"❌ {result['error']}", text_color="red")
            return
        
        restored = len(result.get("restored", []))
        errors = len(result.get("errors", []))
        
        msg = f"✅ Restored {restored} files!"
        if errors:
            msg += f" ({errors} errors)"
        
        self._set_status(msg, "green")
        self.label_restore_status.configure(text=msg, text_color="green")
        
        messagebox.showinfo("✅ Restore Complete", f"Restored {restored} files to original locations!")
        self._load_history()
    
    def _run_undo(self):
        log_path = self.entry_undo.get().strip()
        if not log_path or not os.path.isfile(log_path):
            messagebox.showwarning("Warning", "Select a valid undo log file.")
            return
        
        if not messagebox.askyesno("Confirm", "Restore files to original locations?"):
            return
        
        self._set_status("🔄 Restoring...")
        
        def do_undo():
            result = undo_separation(log_path)
            restored = len(result.get("restored", []))
            self.after(0, lambda: self._set_status(f"✅ Restored {restored} files", "green"))
            self.after(0, lambda: messagebox.showinfo("Done", f"Restored {restored} files."))
        
        threading.Thread(target=do_undo, daemon=True).start()
    
    # ===== EXPORT =====
    def _export_report(self):
        folder = self._get_folder()
        if not folder:
            return
        
        path = filedialog.asksaveasfilename(
            title="Save Report",
            defaultextension=".txt",
            filetypes=[("Text", "*.txt"), ("JSON", "*.json")],
            initialfile=f"folder_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        
        if not path:
            return
        
        self._set_status("🔄 Generating report...")
        
        def do_export():
            data = {
                "folder_info": self._folder_info,
                "mismatched_files": self._mismatched_files,
                "duplicates": self._duplicate_result,
                "big_files": self._big_files,
                "old_files": self._old_files,
                "empty_folders": self._empty_folders,
            }
            
            fmt = "json" if path.endswith(".json") else "txt"
            result = export_report(data, path, format_type=fmt)
            
            self.after(0, lambda: self._set_status(f"✅ Saved to {path}", "green"))
            self.after(0, lambda: messagebox.showinfo("Export", f"Report saved:\n{path}"))
        
        threading.Thread(target=do_export, daemon=True).start()
    
    # ===== COMMON EXECUTE =====
    def _execute_plan(self, plan, simulation, desc):
        self._set_status(f"🔄 Processing {desc}...")
        
        def do_execute():
            result = execute_separation(plan, simulation=simulation)
            success = len(result.get("success", []))
            
            if simulation:
                self.after(0, lambda: self.label_action_status.configure(
                    text=f"📋 Simulation: {success} files would be moved", text_color="cyan"))
            else:
                self.after(0, lambda: self.label_action_status.configure(
                    text=f"✅ Moved {success} files", text_color="green"))
                self.after(0, self._load_history)
                if result.get("undo_log"):
                    self.after(0, lambda: messagebox.showinfo("Done", f"Moved {success} files.\nUndo log saved."))
            
            self.after(0, lambda: self._set_status("✅ Done!", "green"))
        
        threading.Thread(target=do_execute, daemon=True).start()


if __name__ == "__main__":
    app = App()
    app.mainloop()
