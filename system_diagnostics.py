# -*- coding: utf-8 -*-
"""
System Diagnostics - Deep Windows system health check.
Detects hardware, Windows, and software problems with auto-fix options.
"""
import os
import subprocess
import platform
import ctypes
import winreg
from datetime import datetime, timedelta
from typing import Callable, Dict, List, Optional
import json

# =============================================================================
# 🔍 SYSTEM CHECKS
# =============================================================================

def is_admin() -> bool:
    """Check if running as administrator."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except:
        return False


def run_command(cmd: str, timeout: int = 30) -> tuple:
    """Run a Windows command and return output."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except Exception as e:
        return -1, "", str(e)


# =============================================================================
# 💾 DISK HEALTH
# =============================================================================

def check_disk_health(progress_cb: Callable = None) -> List[Dict]:
    """Check disk health using WMIC."""
    problems = []
    
    if progress_cb:
        progress_cb("Checking disk health...")
    
    # Check disk status using WMIC
    code, output, err = run_command('wmic diskdrive get status,model,size', 10)
    
    if code == 0 and output:
        lines = [l.strip() for l in output.strip().split('\n') if l.strip()]
        for line in lines[1:]:  # Skip header
            if "OK" not in line.upper() and line:
                problems.append({
                    "type": "disk_health",
                    "severity": "critical",
                    "icon": "💾",
                    "title": "Disk Health Warning",
                    "description": f"Disk may have issues: {line}",
                    "auto_fix": False,
                    "manual_fix": "Run 'chkdsk /f' in Administrator Command Prompt",
                })
    
    # Check for disk errors in Event Log
    code, output, err = run_command(
        'wevtutil qe System /q:"*[System[Provider[@Name=\'disk\'] and (Level=2 or Level=3)]]" /c:5 /f:text',
        15
    )
    
    if code == 0 and "Event" in output:
        problems.append({
            "type": "disk_errors",
            "severity": "warning",
            "icon": "💾",
            "title": "Disk Errors in Event Log",
            "description": "Recent disk errors found in Windows Event Log",
            "auto_fix": False,
            "manual_fix": "Check Event Viewer > Windows Logs > System for disk errors",
        })
    
    return problems


def check_disk_space_critical(progress_cb: Callable = None) -> List[Dict]:
    """Check for critically low disk space."""
    import shutil
    import string
    
    problems = []
    
    if progress_cb:
        progress_cb("Checking disk space...")
    
    drives = [f"{d}:\\" for d in string.ascii_uppercase if os.path.exists(f"{d}:\\")]
    
    for drive in drives:
        try:
            total, used, free = shutil.disk_usage(drive)
            free_gb = free / (1024**3)
            free_pct = (free / total) * 100
            
            if free_pct < 5 or free_gb < 1:
                problems.append({
                    "type": "disk_space_critical",
                    "severity": "critical",
                    "icon": "🔴",
                    "title": f"Drive {drive} Critically Low!",
                    "description": f"Only {free_gb:.1f} GB ({free_pct:.1f}%) free",
                    "auto_fix": True,
                    "fix_command": "cleanmgr",
                    "fix_args": f"/d {drive[0]}",
                    "manual_fix": f"Run Disk Cleanup on {drive} or delete files",
                })
            elif free_pct < 15:
                problems.append({
                    "type": "disk_space_low",
                    "severity": "warning",
                    "icon": "🟡",
                    "title": f"Drive {drive} Low Space",
                    "description": f"{free_gb:.1f} GB ({free_pct:.1f}%) free",
                    "auto_fix": True,
                    "fix_command": "cleanmgr",
                    "fix_args": f"/d {drive[0]}",
                    "manual_fix": f"Consider cleaning up {drive}",
                })
        except:
            pass
    
    return problems


# =============================================================================
# 🪟 WINDOWS SYSTEM CHECKS
# =============================================================================

def check_windows_update(progress_cb: Callable = None) -> List[Dict]:
    """Check Windows Update status."""
    problems = []
    
    if progress_cb:
        progress_cb("Checking Windows Update...")
    
    # Check if Windows Update service is running
    code, output, err = run_command('sc query wuauserv', 10)
    
    if code == 0:
        if "STOPPED" in output:
            problems.append({
                "type": "windows_update_stopped",
                "severity": "warning",
                "icon": "🪟",
                "title": "Windows Update Service Stopped",
                "description": "Windows Update service is not running",
                "auto_fix": True,
                "fix_command": "net",
                "fix_args": "start wuauserv",
                "requires_admin": True,
                "manual_fix": "Run 'services.msc' and start Windows Update service",
            })
    
    return problems


def check_system_files(progress_cb: Callable = None) -> List[Dict]:
    """Check for corrupted system files."""
    problems = []
    
    if progress_cb:
        progress_cb("This check requires running SFC (may take time)...")
    
    # Note: Full SFC scan takes too long, just check if it's been run recently
    # We'll recommend running it instead
    
    problems.append({
        "type": "sfc_recommendation",
        "severity": "info",
        "icon": "🔧",
        "title": "System File Check",
        "description": "Recommend running System File Checker to find corrupted files",
        "auto_fix": True,
        "fix_command": "sfc",
        "fix_args": "/scannow",
        "requires_admin": True,
        "manual_fix": "Run 'sfc /scannow' in Administrator Command Prompt",
    })
    
    return problems


def check_windows_services(progress_cb: Callable = None) -> List[Dict]:
    """Check critical Windows services."""
    problems = []
    
    critical_services = [
        ("wuauserv", "Windows Update"),
        ("WinDefend", "Windows Defender"),
        ("BITS", "Background Intelligent Transfer"),
        ("Dnscache", "DNS Client"),
        ("Dhcp", "DHCP Client"),
        ("EventLog", "Windows Event Log"),
        ("Schedule", "Task Scheduler"),
    ]
    
    if progress_cb:
        progress_cb("Checking Windows services...")
    
    for service_name, display_name in critical_services:
        code, output, err = run_command(f'sc query {service_name}', 5)
        
        if code == 0:
            if "STOPPED" in output:
                problems.append({
                    "type": "service_stopped",
                    "severity": "warning",
                    "icon": "⚙️",
                    "title": f"{display_name} Stopped",
                    "description": f"Service '{service_name}' is not running",
                    "auto_fix": True,
                    "fix_command": "net",
                    "fix_args": f"start {service_name}",
                    "requires_admin": True,
                    "manual_fix": f"Run 'net start {service_name}' as Administrator",
                })
        elif code != 0 and "1060" not in err:  # 1060 = service doesn't exist
            pass  # Service might not exist on this Windows version
    
    return problems


def check_event_log_errors(progress_cb: Callable = None) -> List[Dict]:
    """Check Windows Event Log for recent critical errors."""
    problems = []
    
    if progress_cb:
        progress_cb("Checking Windows Event Log...")
    
    # Check for critical and error events in last 24 hours
    queries = [
        ("System", "Critical system errors", "*[System[(Level=1 or Level=2) and TimeCreated[timediff(@SystemTime) <= 86400000]]]"),
        ("Application", "Application crashes", "*[System[(Level=1 or Level=2) and TimeCreated[timediff(@SystemTime) <= 86400000]]]"),
    ]
    
    for log_name, desc, query in queries:
        code, output, err = run_command(
            f'wevtutil qe {log_name} /q:"{query}" /c:10 /f:text',
            15
        )
        
        if code == 0 and "Event[" in output.replace(" ", ""):
            # Count events
            event_count = output.count("Event[")
            if event_count > 0:
                problems.append({
                    "type": f"event_log_{log_name.lower()}",
                    "severity": "warning" if event_count < 5 else "critical",
                    "icon": "📋",
                    "title": f"{desc}",
                    "description": f"{event_count} errors in {log_name} log (last 24h)",
                    "auto_fix": False,
                    "manual_fix": f"Open Event Viewer > Windows Logs > {log_name} to see details",
                })
    
    return problems


def check_startup_impact(progress_cb: Callable = None) -> List[Dict]:
    """Check startup programs with high impact."""
    problems = []
    
    if progress_cb:
        progress_cb("Checking startup programs...")
    
    # Check Task Manager startup items via registry
    startup_keys = [
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run"),
    ]
    
    startup_count = 0
    startup_items = []
    
    for hive, key_path in startup_keys:
        try:
            key = winreg.OpenKey(hive, key_path)
            i = 0
            while True:
                try:
                    name, value, _ = winreg.EnumValue(key, i)
                    startup_items.append(name)
                    startup_count += 1
                    i += 1
                except WindowsError:
                    break
            winreg.CloseKey(key)
        except:
            pass
    
    if startup_count > 10:
        problems.append({
            "type": "too_many_startup",
            "severity": "warning",
            "icon": "🚀",
            "title": "Many Startup Programs",
            "description": f"{startup_count} programs run at startup, may slow boot",
            "auto_fix": False,
            "manual_fix": "Open Task Manager > Startup tab to disable unnecessary programs",
            "details": startup_items[:10],
        })
    
    return problems


# =============================================================================
# 🌐 NETWORK CHECKS
# =============================================================================

def check_network(progress_cb: Callable = None) -> List[Dict]:
    """Check network connectivity and DNS."""
    problems = []
    
    if progress_cb:
        progress_cb("Checking network...")
    
    # Ping test
    code, output, err = run_command('ping -n 1 8.8.8.8', 10)
    
    if code != 0 or "TTL=" not in output:
        problems.append({
            "type": "no_internet",
            "severity": "critical",
            "icon": "🌐",
            "title": "No Internet Connection",
            "description": "Cannot reach internet (ping 8.8.8.8 failed)",
            "auto_fix": True,
            "fix_command": "ipconfig",
            "fix_args": "/renew",
            "manual_fix": "Check network cable/WiFi, or run 'ipconfig /renew'",
        })
    else:
        # DNS test
        code, output, err = run_command('ping -n 1 google.com', 10)
        
        if code != 0:
            problems.append({
                "type": "dns_problem",
                "severity": "warning",
                "icon": "🌐",
                "title": "DNS Problem",
                "description": "Internet works but DNS resolution fails",
                "auto_fix": True,
                "fix_command": "ipconfig",
                "fix_args": "/flushdns",
                "manual_fix": "Run 'ipconfig /flushdns' or change DNS to 8.8.8.8",
            })
    
    return problems


# =============================================================================
# 🛡️ SECURITY CHECKS
# =============================================================================

def check_security(progress_cb: Callable = None) -> List[Dict]:
    """Check Windows security status."""
    problems = []
    
    if progress_cb:
        progress_cb("Checking security...")
    
    # Check Windows Defender status
    code, output, err = run_command('sc query WinDefend', 5)
    
    if code == 0 and "STOPPED" in output:
        problems.append({
            "type": "defender_stopped",
            "severity": "critical",
            "icon": "🛡️",
            "title": "Windows Defender Not Running",
            "description": "Your PC may be unprotected",
            "auto_fix": True,
            "fix_command": "net",
            "fix_args": "start WinDefend",
            "requires_admin": True,
            "manual_fix": "Open Windows Security and enable Real-time protection",
        })
    
    # Check Windows Firewall
    code, output, err = run_command('netsh advfirewall show allprofiles state', 10)
    
    if code == 0 and "OFF" in output.upper():
        problems.append({
            "type": "firewall_off",
            "severity": "warning",
            "icon": "🔥",
            "title": "Windows Firewall Disabled",
            "description": "One or more firewall profiles are OFF",
            "auto_fix": True,
            "fix_command": "netsh",
            "fix_args": "advfirewall set allprofiles state on",
            "requires_admin": True,
            "manual_fix": "Open Windows Firewall settings and enable it",
        })
    
    return problems


# =============================================================================
# 🔧 AUTO-FIX FUNCTIONS
# =============================================================================

def fix_problem(problem: Dict, progress_cb: Callable = None) -> Dict:
    """Attempt to auto-fix a problem."""
    result = {
        "success": False,
        "message": "",
        "problem": problem,
    }
    
    if not problem.get("auto_fix"):
        result["message"] = "This problem cannot be auto-fixed"
        return result
    
    if problem.get("requires_admin") and not is_admin():
        result["message"] = "This fix requires Administrator privileges"
        return result
    
    cmd = problem.get("fix_command", "")
    args = problem.get("fix_args", "")
    
    if not cmd:
        result["message"] = "No fix command available"
        return result
    
    if progress_cb:
        progress_cb(f"Fixing: {problem['title']}...")
    
    full_cmd = f"{cmd} {args}".strip()
    code, output, err = run_command(full_cmd, 60)
    
    if code == 0:
        result["success"] = True
        result["message"] = f"Fixed: {problem['title']}"
    else:
        result["message"] = f"Fix failed: {err or output}"
    
    return result


def fix_all_auto(problems: List[Dict], progress_cb: Callable = None) -> Dict:
    """Fix all auto-fixable problems."""
    results = {
        "fixed": [],
        "failed": [],
        "skipped": [],
    }
    
    for problem in problems:
        if not problem.get("auto_fix"):
            results["skipped"].append(problem)
            continue
        
        if problem.get("requires_admin") and not is_admin():
            results["skipped"].append(problem)
            continue
        
        fix_result = fix_problem(problem, progress_cb)
        
        if fix_result["success"]:
            results["fixed"].append(problem)
        else:
            results["failed"].append(problem)
    
    return results


# =============================================================================
# 📊 FULL DIAGNOSTICS
# =============================================================================

def run_full_diagnostics(progress_cb: Callable = None) -> Dict:
    """Run all diagnostic checks."""
    results = {
        "timestamp": datetime.now().isoformat(),
        "is_admin": is_admin(),
        "problems": [],
        "stats": {
            "critical": 0,
            "warning": 0,
            "info": 0,
            "auto_fixable": 0,
        },
    }
    
    checks = [
        ("Disk Space", check_disk_space_critical),
        ("Disk Health", check_disk_health),
        ("Windows Services", check_windows_services),
        ("Windows Update", check_windows_update),
        ("Event Log Errors", check_event_log_errors),
        ("Startup Programs", check_startup_impact),
        ("Network", check_network),
        ("Security", check_security),
    ]
    
    for name, check_func in checks:
        if progress_cb:
            progress_cb(f"Running: {name}...")
        
        try:
            problems = check_func(progress_cb)
            results["problems"].extend(problems)
        except Exception as e:
            results["problems"].append({
                "type": "check_error",
                "severity": "info",
                "icon": "⚠️",
                "title": f"{name} Check Failed",
                "description": str(e),
                "auto_fix": False,
            })
    
    # Count by severity
    for p in results["problems"]:
        sev = p.get("severity", "info")
        results["stats"][sev] = results["stats"].get(sev, 0) + 1
        
        if p.get("auto_fix"):
            results["stats"]["auto_fixable"] += 1
    
    return results


def format_diagnostics(results: Dict) -> str:
    """Format diagnostics results for display."""
    lines = []
    
    lines.append("=" * 70)
    lines.append("🔧 SYSTEM DIAGNOSTICS REPORT")
    lines.append("=" * 70)
    lines.append(f"\n📅 {results['timestamp'][:19]}")
    lines.append(f"🔑 Admin Mode: {'✅ Yes' if results['is_admin'] else '❌ No (some fixes unavailable)'}")
    
    stats = results.get("stats", {})
    lines.append(f"\n{'─' * 60}")
    lines.append("📊 SUMMARY")
    lines.append(f"{'─' * 60}")
    lines.append(f"  🔴 Critical: {stats.get('critical', 0)}")
    lines.append(f"  🟡 Warning: {stats.get('warning', 0)}")
    lines.append(f"  ℹ️ Info: {stats.get('info', 0)}")
    lines.append(f"  🔧 Auto-fixable: {stats.get('auto_fixable', 0)}")
    
    if stats.get('critical', 0) == 0 and stats.get('warning', 0) == 0:
        lines.append(f"\n  ✅ No critical problems found!")
    
    # Group by severity
    critical = [p for p in results["problems"] if p.get("severity") == "critical"]
    warnings = [p for p in results["problems"] if p.get("severity") == "warning"]
    info = [p for p in results["problems"] if p.get("severity") == "info"]
    
    if critical:
        lines.append(f"\n{'─' * 60}")
        lines.append("🔴 CRITICAL PROBLEMS")
        lines.append(f"{'─' * 60}")
        
        for p in critical:
            auto = "🔧" if p.get("auto_fix") else "📝"
            admin = "👑" if p.get("requires_admin") else ""
            lines.append(f"\n  {p['icon']} {p['title']} {auto}{admin}")
            lines.append(f"     {p['description']}")
            lines.append(f"     💡 Fix: {p.get('manual_fix', 'N/A')}")
    
    if warnings:
        lines.append(f"\n{'─' * 60}")
        lines.append("🟡 WARNINGS")
        lines.append(f"{'─' * 60}")
        
        for p in warnings:
            auto = "🔧" if p.get("auto_fix") else "📝"
            admin = "👑" if p.get("requires_admin") else ""
            lines.append(f"\n  {p['icon']} {p['title']} {auto}{admin}")
            lines.append(f"     {p['description']}")
            lines.append(f"     💡 Fix: {p.get('manual_fix', 'N/A')}")
    
    if info:
        lines.append(f"\n{'─' * 60}")
        lines.append("ℹ️ INFORMATION")
        lines.append(f"{'─' * 60}")
        
        for p in info:
            lines.append(f"\n  {p['icon']} {p['title']}")
            lines.append(f"     {p['description']}")
    
    # Legend
    lines.append(f"\n{'─' * 60}")
    lines.append("📖 LEGEND")
    lines.append(f"{'─' * 60}")
    lines.append("  🔧 = Auto-fixable")
    lines.append("  📝 = Manual fix required")
    lines.append("  👑 = Requires Administrator")
    
    lines.append(f"\n{'=' * 70}")
    
    return "\n".join(lines)
