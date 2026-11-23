import os
import re
from pathlib import Path
from difflib import SequenceMatcher


def normalize_name(name):
    """Normalize a filename/path for comparison: lowercase, remove all spaces and punctuation."""
    if not name:
        return ""
    name = name.lower()
    # Remove all non-alphanumeric characters for aggressive fuzzy matching
    name = re.sub(r'[^a-z0-9]', '', name)
    return name


def similarity_ratio(a, b):
    """Calculate similarity between two strings (0 to 1)."""
    return SequenceMatcher(None, a, b).ratio()


def find_file_fuzzy(filename, search_paths=None, max_depth=3):
    """
    Find files with fuzzy matching.
    Searches in common directories and handles variations in case and punctuation.
    Returns a list of best matching files.
    """
    if search_paths is None:
        user_profile = os.path.expanduser("~")
        search_paths = [
            os.path.join(user_profile, "Downloads"),
            os.path.join(user_profile, "Documents"),
            os.path.join(user_profile, "Desktop"),
            os.path.join(user_profile, "Pictures"),
            os.path.join(user_profile, "Videos"),
            os.path.join(user_profile, "Music"),
            os.path.join(user_profile, "OneDrive", "Documents"),
            os.path.join(user_profile, "OneDrive", "Desktop"),
            os.path.join(user_profile, "OneDrive", "Pictures"),
            os.getcwd(),
        ]
        
        # Add all available drives except C (to avoid scanning entire system drive)
        import string
        for d in string.ascii_uppercase:
            if d == 'C':
                continue
            drive = f"{d}:\\"
            if os.path.exists(drive):
                search_paths.append(drive)

    normalized_target = normalize_name(filename)
    best_matches = []
    best_score = 0
    
    for base_path in search_paths:
        if not os.path.exists(base_path):
            continue

        base_depth = base_path.rstrip(os.path.sep).count(os.path.sep)

        try:
            for root, dirs, files in os.walk(base_path):
                current_depth = root.rstrip(os.path.sep).count(os.path.sep)
                if current_depth - base_depth >= max_depth:
                    # Don't go deeper
                    dirs[:] = []
                
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        normalized_file = normalize_name(file)
                        name_no_ext = os.path.splitext(file)[0]
                        normalized_base = normalize_name(name_no_ext)
                        
                        # Untuk pencarian 1-2 huruf, butuh pencocokan persis
                        if len(normalized_target) <= 2:
                            if normalized_target not in (normalized_base, normalized_file):
                                continue
                                
                        score_full = similarity_ratio(normalized_target, normalized_file)
                        score_base = similarity_ratio(normalized_target, normalized_base)
                        score = max(score_full, score_base)

                        if score > best_score:
                            best_score = score
                            best_matches = [file_path]
                        elif score == best_score and score > 0:
                            if file_path not in best_matches:
                                best_matches.append(file_path)

                    except (PermissionError, OSError):
                        continue
        except (PermissionError, OSError):
            continue

    # Lower threshold to 0.4 for aggressive partial matches
    return best_matches if best_score > 0.4 else []


def find_folder_fuzzy(folder_name, search_paths=None):
    """Find a folder with fuzzy matching (fast, non-recursive)."""
    normalized_target = normalize_name(folder_name)
    
    # Quick check for common system folders
    common_folders = {
        "documents": os.path.expanduser("~\\Documents"),
        "desktop": os.path.expanduser("~\\Desktop"),
        "downloads": os.path.expanduser("~\\Downloads"),
        "pictures": os.path.expanduser("~\\Pictures"),
        "music": os.path.expanduser("~\\Music"),
        "videos": os.path.expanduser("~\\Videos"),
    }
    
    for common_name, common_path in common_folders.items():
        score = similarity_ratio(normalized_target, common_name)
        if score > 0.8 and os.path.exists(common_path):
            return common_path
    
    if search_paths is None:
        search_paths = [
            os.path.expanduser("~\\Documents"),
            os.path.expanduser("~\\Desktop"),
            os.path.expanduser("~\\Downloads"),
        ]

    best_match = None
    best_score = 0

    for base_path in search_paths:
        if not os.path.exists(base_path):
            continue

        try:
            # Only check immediate subdirectories, no recursion
            items = os.listdir(base_path)
            # Limit to first 500 items for performance
            for item in items[:500]:
                item_path = os.path.join(base_path, item)
                try:
                    if os.path.isdir(item_path):
                        normalized_dir = normalize_name(item)
                        score = similarity_ratio(normalized_target, normalized_dir)

                        if score > best_score:
                            best_score = score
                            best_match = item_path

                        if score == 1.0:
                            return best_match
                except (PermissionError, OSError):
                    continue
        except (PermissionError, OSError):
            continue

    return best_match if best_score > 0.7 else None


def find_application(app_name):
    """Find an application by name (handles variations). Optimized for speed."""
    app_variants = [
        app_name,
        app_name + ".exe",
        app_name + ".lnk",
        app_name.lower(),
        app_name.lower() + ".exe",
        app_name.lower() + ".lnk",
    ]
    
    # Quick check: is this in PATH or current directory?
    for variant in app_variants:
        if os.path.isfile(variant) or os.path.isfile(f"{variant}.exe") or os.path.isfile(f"{variant}.lnk"):
            return variant
    
    user_profile = os.path.expanduser("~")
    common_app_paths = [
        os.path.join(user_profile, "Desktop"),
        os.path.join(user_profile, "OneDrive", "Desktop"),
        "C:\\Users\\Public\\Desktop",
        "C:\\ProgramData\\Microsoft\\Windows\\Start Menu\\Programs",
        os.path.join(user_profile, "AppData", "Roaming", "Microsoft", "Windows", "Start Menu", "Programs"),
        "C:\\Windows\\System32",
        os.path.join(user_profile, "AppData", "Local", "Programs"),
        "C:\\Program Files",
        "C:\\Program Files (x86)",
    ]

    normalized_target = normalize_name(app_name)
    best_match = None
    best_score = 0
    
    for base_path in common_app_paths:
        if not os.path.exists(base_path):
            continue
            
        base_depth = base_path.rstrip(os.path.sep).count(os.path.sep)
        # Use deeper search for Start Menu/Desktop, shallower for Program Files
        max_depth = 3 if "Start Menu" in base_path or "Desktop" in base_path else 2
        
        try:
            for root, dirs, files in os.walk(base_path):
                current_depth = root.rstrip(os.path.sep).count(os.path.sep)
                if current_depth - base_depth >= max_depth:
                    dirs[:] = []
                    
                for file in files:
                    file_lower = file.lower()
                    if file_lower.endswith('.exe') or file_lower.endswith('.lnk'):
                        normalized_file = normalize_name(file)
                        name_no_ext = os.path.splitext(file)[0]
                        normalized_base = normalize_name(name_no_ext)
                        
                        # Untuk pencarian 1-2 huruf, butuh pencocokan persis
                        if len(normalized_target) <= 2:
                            if normalized_target not in (normalized_base, normalized_file):
                                continue
                                
                        score_full = similarity_ratio(normalized_target, normalized_file)
                        score_base = similarity_ratio(normalized_target, normalized_base)
                        score = max(score_full, score_base)
                        
                        if score > best_score:
                            best_score = score
                            best_match = os.path.join(root, file)
                            
                        if score == 1.0:
                            return best_match
        except (PermissionError, OSError):
            continue
            
    return best_match if best_score > 0.6 else None


def parse_path_or_url(text):
    """
    Parse user input to determine if it's a file, folder, URL, or app name.
    Returns a dict with 'type' and 'value'.
    Optimized order: URL → common folder → file (with ext) → app → file (single word only) → folder
    """
    text = text.strip()

    if text.startswith("http://") or text.startswith("https://"):
        return {"type": "url", "value": text}

    # Quick check for common system folders FIRST (very fast, 0ms)
    normalized_target = normalize_name(text)
    common_folders = {
        "documents": os.path.expanduser("~\\Documents"),
        "desktop": os.path.expanduser("~\\Desktop"),
        "downloads": os.path.expanduser("~\\Downloads"),
        "pictures": os.path.expanduser("~\\Pictures"),
        "music": os.path.expanduser("~\\Music"),
        "videos": os.path.expanduser("~\\Videos"),
    }
    for common_name, common_path in common_folders.items():
        score = similarity_ratio(normalized_target, common_name)
        if score > 0.8 and os.path.exists(common_path):
            return {"type": "folder", "value": common_path}

    # Check for file WITH known extensions (fast, ~20ms)
    if "." in text:
        result = find_file_fuzzy(text)
        if result:
            return {"type": "file", "value": result}

    # Check for app (fast if not found, ~3s if app exists)
    result = find_application(text)
    if result:
        return {"type": "app", "value": result}

    # Check for file WITHOUT extension
    # We allow multi-word inputs to be fuzzy-matched against files
    result = find_file_fuzzy(text)
    if result:
        return {"type": "file", "value": result}

    # Folder search last (slower)
    result = find_folder_fuzzy(text)
    if result:
        return {"type": "folder", "value": result}

    return {"type": "unknown", "value": text}
