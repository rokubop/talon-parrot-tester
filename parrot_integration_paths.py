from pathlib import Path
import os
import sys
import json
import re
from talon_init import TALON_HOME

DEBUG_PATH_DISCOVERY = False

def extract_pattern_path_from_parrot_integration(parrot_integration_path: Path) -> str | None:
    if DEBUG_PATH_DISCOVERY:
        print(f"Parsing parrot_integration.py: {parrot_integration_path}")

    try:
        with parrot_integration_path.open("r", encoding="utf-8") as f:
            content = f.read()

        # Look for pattern_path = str(...) pattern
        pattern_path_match = re.search(r'^\s*pattern_path\s*=\s*str\(([^)]+)\)', content, re.MULTILINE)
        if pattern_path_match:
            path_expr = pattern_path_match.group(1).strip()
            if DEBUG_PATH_DISCOVERY:
                print(f"   Found pattern_path = str({path_expr})")

            # Look for PARROT_HOME definition
            parrot_home_match = re.search(r'^\s*PARROT_HOME\s*=\s*TALON_HOME\s*/\s*[\'"]?([^\'")\s]+)[\'"]?', content, re.MULTILINE)
            if parrot_home_match and 'PARROT_HOME' in path_expr:
                parrot_subpath = parrot_home_match.group(1)
                if DEBUG_PATH_DISCOVERY:
                    print(f"   Found PARROT_HOME = TALON_HOME / '{parrot_subpath}'")
                full_path = TALON_HOME / parrot_subpath / "patterns.json"
                if DEBUG_PATH_DISCOVERY:
                    print(f"   Constructed path: {full_path}")
                return str(full_path)

        # Alternative: look for direct pattern_path assignment
        direct_match = re.search(r'^\s*pattern_path\s*=\s*[\'"]([^\'"]+)[\'"]', content, re.MULTILINE)
        if direct_match:
            path = direct_match.group(1)
            if DEBUG_PATH_DISCOVERY:
                print(f"   Found direct pattern_path = '{path}'")
            return path

        if DEBUG_PATH_DISCOVERY:
            print("   No pattern_path found in file")

    except Exception as e:
        if DEBUG_PATH_DISCOVERY:
            print(f"   Failed to parse: {e}")

    return None

def get_talon_user_path():
    """Get the talon user path based on the platform."""
    if sys.platform == "win32":
        return os.path.join(os.getenv("APPDATA"), "talon", "user")
    else:
        return os.path.join(os.getenv("HOME"), ".talon", "user")

def get_parrot_integration_path():
    """Get the path to the parrot_integration.py file."""
    talon_user_path = get_talon_user_path()
    if DEBUG_PATH_DISCOVERY:
        print(f"🔍 Searching for parrot_integration.py in: {talon_user_path}")

    matches = list(Path(talon_user_path).rglob("parrot_integration.py"))

    if DEBUG_PATH_DISCOVERY:
        if matches:
            print(f"   Found {len(matches)} parrot_integration.py files:")
            for i, path in enumerate(matches):
                print(f"     {i+1}. {path}")
        else:
            print("   No parrot_integration.py files found")

    return matches[0] if matches else None

def get_patterns_py_path():
    """Get the path to the patterns.json file using 3-stage fallback."""

    if DEBUG_PATH_DISCOVERY:
        print("Starting patterns.json discovery process...")

    # Stage 1: Try to parse parrot_integration.py to extract pattern_path
    if DEBUG_PATH_DISCOVERY:
        print("Stage 1: Parsing parrot_integration.py")
    try:
        parrot_integration_path = get_parrot_integration_path()
        if parrot_integration_path:
            if DEBUG_PATH_DISCOVERY:
                print(f"   Using parrot_integration.py: {parrot_integration_path}")
            pattern_path = extract_pattern_path_from_parrot_integration(parrot_integration_path)
            if pattern_path:
                path_obj = Path(pattern_path)
                if path_obj.exists():
                    if DEBUG_PATH_DISCOVERY:
                        print(f"Stage 1 SUCCESS: {pattern_path}")
                    return path_obj
                else:
                    if DEBUG_PATH_DISCOVERY:
                        print(f"Stage 1: Path doesn't exist: {pattern_path}")
            else:
                if DEBUG_PATH_DISCOVERY:
                    print("Stage 1: No pattern_path extracted")
        else:
            if DEBUG_PATH_DISCOVERY:
                print("Stage 1: No parrot_integration.py found")
    except Exception as e:
        if DEBUG_PATH_DISCOVERY:
            print(f"Stage 1 failed: {e}")

    # Stage 2: Try common location /talon/parrot/patterns.json
    if DEBUG_PATH_DISCOVERY:
        print("Stage 2: Checking common parrot location")
    try:
        parrot_patterns_path = TALON_HOME / "parrot" / "patterns.json"
        if DEBUG_PATH_DISCOVERY:
            print(f"   Checking: {parrot_patterns_path}")
        if parrot_patterns_path.exists():
            if DEBUG_PATH_DISCOVERY:
                print(f"Stage 2 SUCCESS: {parrot_patterns_path}")
            return parrot_patterns_path
        else:
            if DEBUG_PATH_DISCOVERY:
                print("Stage 2: File doesn't exist")
    except Exception as e:
        if DEBUG_PATH_DISCOVERY:
            print(f"Stage 2 failed: {e}")

    # Stage 3: Fall back to searching within talon user directory
    if DEBUG_PATH_DISCOVERY:
        print("Stage 3: Searching in user directory")
    try:
        talon_user_path = get_talon_user_path()
        if DEBUG_PATH_DISCOVERY:
            print(f"   Searching in: {talon_user_path}")
        matches = list(Path(talon_user_path).rglob("patterns.json"))

        if DEBUG_PATH_DISCOVERY:
            if matches:
                print(f"   Found {len(matches)} matches:")
                for i, path in enumerate(matches):
                    print(f"     {i+1}. {path}")
            else:
                print("   No matches found")

        if matches:
            chosen = matches[0]
            if DEBUG_PATH_DISCOVERY:
                print(f"Stage 3 SUCCESS: Using first match: {chosen}")
            return chosen
        else:
            if DEBUG_PATH_DISCOVERY:
                print("Stage 3: No patterns.json found in user directory")
    except Exception as e:
        if DEBUG_PATH_DISCOVERY:
            print(f"Stage 3 failed: {e}")

    if DEBUG_PATH_DISCOVERY:
        print("ALL STAGES FAILED: Could not find patterns.json")
    return None

def load_patterns(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"❌ Failed to load patterns from {path}: {e}")
        return {}

def build_module_path(current_file: Path, target_file: Path, user_root: Path) -> Path:
    """
    Build the absolute path to the target module file.
    Uses importlib to load modules directly from file paths,
    bypassing Python identifier restrictions.
    """
    # target_file is relative to user_root without .py extension
    full_path = user_root / target_file.with_suffix(".py")

    if not full_path.exists():
        raise ValueError(f"Target parrot_integration.py not found at: {full_path}")

    return full_path

def generate_parrot_integration_hook(module_path: Path, current_file: Path) -> bool:
    """
    Generate the parrot_integration_hook.py file using importlib for module loading.
    This allows importing from paths with dashes or other special characters.
    """
    target_dir = current_file.parent
    hook_file = target_dir / "parrot_integration_hook.py"

    # Escape backslashes for Windows paths in the generated Python code
    module_path_str = str(module_path).replace("\\", "\\\\")

    code = f"""\
# AUTO-GENERATED: Do not edit manually.
# This provides Talon access to parrot_delegate via actions,
# while preserving the integrity of the original source.
try:
    from talon import Context
    import importlib.util
    import sys
    from pathlib import Path
    from .parrot_integration_wrapper import (
        parrot_tester_wrap_parrot_integration,
        parrot_tester_restore_parrot_integration
    )

    def _get_parrot_delegate():
        # Find the ACTUAL parrot_integration module that Talon already loaded
        # by searching sys.modules for the one loaded from this specific path
        _module_path = Path(r"{module_path_str}")

        # Search sys.modules for a module loaded from this file path
        for module_name, module in list(sys.modules.items()):
            if module is None:
                continue
            try:
                if hasattr(module, '__file__') and module.__file__:
                    module_file = Path(module.__file__).resolve()
                    if module_file == _module_path and hasattr(module, 'parrot_delegate'):
                        return module.parrot_delegate
            except Exception:
                pass
        
        # If not found in sys.modules, load it fresh (first run scenario)
        _spec = importlib.util.spec_from_file_location("parrot_integration_for_tester", _module_path)
        if _spec is None:
            raise ImportError(f"Cannot load module spec from {{_module_path}}")
        
        _module = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_module)
        
        if not hasattr(_module, 'parrot_delegate'):
            raise AttributeError(f"Module {{_module_path}} has no 'parrot_delegate' attribute")
        
        return _module.parrot_delegate

    ctx = Context()

    @ctx.action_class("user")
    class Actions:
        def parrot_tester_integration_ready():
            return True

        def parrot_tester_wrap_parrot_integration():
            parrot_delegate = _get_parrot_delegate()
            parrot_tester_wrap_parrot_integration(parrot_delegate)

        def parrot_tester_restore_parrot_integration():
            parrot_delegate = _get_parrot_delegate()
            parrot_tester_restore_parrot_integration(parrot_delegate)
except Exception as e:
    print(f"Parrot Tester Hook Error: {{e}}")
    import traceback
    traceback.print_exc()
"""

    hook_file.write_text(code)
