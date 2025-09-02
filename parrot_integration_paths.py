from pathlib import Path
import importlib.util
import os
import sys
import json
import re
import logging
from talon_init import TALON_HOME

DEBUG_PATH_DISCOVERY = False

logger = logging.getLogger(__name__)
if DEBUG_PATH_DISCOVERY:
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s')
handler.setFormatter(formatter)
if not logger.hasHandlers():
    logger.addHandler(handler)

def extract_pattern_path_from_parrot_integration(parrot_integration_path: Path) -> str | None:
    logger.debug(f"Parsing parrot_integration.py: {parrot_integration_path}")
    try:
        with parrot_integration_path.open("r", encoding="utf-8") as f:
            content = f.read()

        # Look for pattern_path = str(...) pattern
        pattern_path_match = re.search(r'^\s*pattern_path\s*=\s*str\(([^)]+)\)', content, re.MULTILINE)
        if pattern_path_match:
            path_expr = pattern_path_match.group(1).strip()
            logger.debug(f"   Found pattern_path = str({path_expr})")

            # Look for PARROT_HOME definition
            parrot_home_match = re.search(r'^\s*PARROT_HOME\s*=\s*TALON_HOME\s*/\s*[\'"]?([^\'")\s]+)[\'"]?', content, re.MULTILINE)
            if parrot_home_match and 'PARROT_HOME' in path_expr:
                parrot_subpath = parrot_home_match.group(1)
                logger.debug(f"   Found PARROT_HOME = TALON_HOME / '{parrot_subpath}'")
                full_path = TALON_HOME / parrot_subpath / "patterns.json"
                logger.debug(f"   Constructed path: {full_path}")
                return str(full_path)

        # Alternative: look for direct pattern_path assignment
        direct_match = re.search(r'^\s*pattern_path\s*=\s*[\'"]([^\'"]+)[\'"]', content, re.MULTILINE)
        if direct_match:
            path = direct_match.group(1)
            logger.debug(f"   Found direct pattern_path = '{path}'")
            return path

        logger.debug("   No pattern_path found in file")

    except Exception as e:
        logger.error(f"   Failed to parse: {e}")

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
    logger.debug(f"🔍 Searching for parrot_integration.py in: {talon_user_path}")

    matches = list(Path(talon_user_path).rglob("parrot_integration.py"))

    if matches:
        logger.debug(f"   Found {len(matches)} parrot_integration.py files:")
        for i, path in enumerate(matches):
            logger.debug(f"     {i+1}. {path}")
    else:
        logger.debug("   No parrot_integration.py files found")

    return matches[0] if matches else None

def get_patterns_py_path():
    """Get the path to the patterns.json file using 3-stage fallback."""

    logger.debug("Starting patterns.json discovery process...")

    # Stage 1: Try to parse parrot_integration.py to extract pattern_path
    logger.debug("Stage 1: Parsing parrot_integration.py")
    try:
        parrot_integration_path = get_parrot_integration_path()
        if parrot_integration_path:
            logger.debug(f"   Using parrot_integration.py: {parrot_integration_path}")
            pattern_path = extract_pattern_path_from_parrot_integration(parrot_integration_path)
            if pattern_path:
                path_obj = Path(pattern_path)
                if path_obj.exists():
                    logger.info(f"Stage 1 SUCCESS: {pattern_path}")
                    return path_obj
                else:
                    logger.debug(f"Stage 1: Path doesn't exist: {pattern_path}")
            else:
                logger.debug("Stage 1: No pattern_path extracted")
        else:
            logger.debug("Stage 1: No parrot_integration.py found")
    except Exception as e:
        logger.error(f"Stage 1 failed: {e}")

    # Stage 2: Try common location /talon/parrot/patterns.json
    logger.debug("Stage 2: Checking common parrot location")
    try:
        parrot_patterns_path = TALON_HOME / "parrot" / "patterns.json"
        logger.debug(f"   Checking: {parrot_patterns_path}")
        if parrot_patterns_path.exists():
            logger.info(f"Stage 2 SUCCESS: {parrot_patterns_path}")
            return parrot_patterns_path
        else:
            logger.debug("Stage 2: File doesn't exist")
    except Exception as e:
        logger.error(f"Stage 2 failed: {e}")

    # Stage 3: Fall back to searching within talon user directory
    logger.debug("Stage 3: Searching in user directory")
    try:
        talon_user_path = get_talon_user_path()
        logger.debug(f"   Searching in: {talon_user_path}")
        matches = list(Path(talon_user_path).rglob("patterns.json"))

        if matches:
            logger.debug(f"   Found {len(matches)} matches:")
            for i, path in enumerate(matches):
                logger.debug(f"     {i+1}. {path}")
        else:
            logger.debug("   No matches found")

        if matches:
            chosen = matches[0]
            logger.info(f"Stage 3 SUCCESS: Using first match: {chosen}")
            return chosen
        else:
            logger.debug("Stage 3: No patterns.json found in user directory")
    except Exception as e:
        logger.error(f"Stage 3 failed: {e}")

    logger.warning("ALL STAGES FAILED: Could not find patterns.json")
    return None

def load_patterns(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception as e:
        logger.error(f"❌ Failed to load patterns from {path}: {e}")
        return {}

def build_relative_import_path(current_file: Path, target_file: Path) -> str:
    # Check for invalid Python identifiers (like dashes) in the path
    invalid_parts = [part for part in target_file.parts if not part.isidentifier()]
    if invalid_parts:
        error_msg = f"""
PARROT TESTER LIMITATION: Cannot work with your current parrot_integration.py path

Issue: Parrot Tester has a technical limitation with folder names containing dashes or special characters.
Your file: {target_file}
Problematic parts: {', '.join(invalid_parts)}

Why: Parrot Tester uses Python import statements internally, which require valid identifiers
(letters, numbers, underscores only).

To use Parrot Tester: Rename folders containing dashes to use underscores, or move the parrot_integration.py elsewhere.

Example rename: {str(target_file).replace('-', '_')}

Your folder naming is perfectly valid - this is just a technical constraint of this tool.
"""
        raise ValueError(error_msg)

    up_levels = len(current_file.parts)
    dot_prefix = "." * up_levels if up_levels > 0 else "."
    target_module = ".".join(target_file.parts)

    return f"{dot_prefix}.{target_module}"

def generate_import_code(
    file_path: str,
    symbols: list[str],
    fake_pkg: str | None = None,
    indent: str = ""
) -> str:
    """
    Generate Python code that imports a module from a file path, assigns the given symbols,
    and supports relative imports even if the real path contains dashes.

    :param file_path: Absolute path to the .py file to import
    :param symbols: List of attribute names to import from that module
    :param fake_pkg: Optional fake package name; defaults to parent directory's stem
    :param indent: String to prepend to each line (e.g. '    ' for 4 spaces)
    """
    p = Path(file_path)
    if fake_pkg is None:
        fake_pkg = p.parent.stem

    module_name = p.stem
    assigns = "\n".join(f"{sym} = module.{sym}" for sym in symbols)

    code = f'''import sys
import importlib.util
import importlib.machinery

module_name  = "{module_name}"
fake_pkg    = "{fake_pkg}"

# Load module from system modules if already imported before
import os

module = None
target_path = os.path.abspath(r"{file_path}")
for mod in sys.modules.values():
    if hasattr(mod, "__file__") and mod.__file__:
        if os.path.abspath(mod.__file__) == target_path:
            module = mod
            break
if module is None:
    spec = importlib.util.spec_from_file_location(
        f"{fake_pkg}.{module_name}",
        r"{file_path}"
    )
    module = importlib.util.module_from_spec(spec)
    module.__package__ = fake_pkg

    # Create fake package in sys.modules
    pkg_module = importlib.util.module_from_spec(
        importlib.machinery.ModuleSpec(fake_pkg, loader=None)
    )
    pkg_module.__path__ = [r"{str(Path(file_path).parent)}"]
    sys.modules[fake_pkg] = pkg_module

    # Register submodule
    sys.modules[f"{{fake_pkg}}.{module_name}"] = module

    spec.loader.exec_module(module)

{assigns}
'''

    # Apply indentation to all non-empty lines
    return "\n".join(f"{indent}{line}" if line.strip() else line for line in code.splitlines())


def generate_parrot_integration_hook(import_path: str, current_file: Path) -> bool:
    """
    Generate the parrot_integration_hook.py file.
    Returns True if this is the first time generating the file, False otherwise.
    """
    target_dir = current_file.parent
    hook_file = target_dir / "parrot_integration_hook.py"

    code = f"""\
# AUTO-GENERATED: Do not edit manually.
# This provides Talon access to parrot_delegate via actions,
# while preserving the integrity of the original source.
try:
    from talon import Context
    import importlib.util
    import traceback
{generate_import_code(import_path, ["parrot_delegate"], indent="    ")}

{generate_import_code(target_dir / "parrot_integration_wrapper.py", [
        "parrot_tester_wrap_parrot_integration",
        "parrot_tester_restore_parrot_integration",
    ], "parrot_tester", indent="    ")}

    ctx = Context()

    @ctx.action_class("user")
    class Actions:
        def parrot_tester_integration_ready():
            print("Hook checks as initialised")
            return True

        def parrot_tester_wrap_parrot_integration():
            parrot_tester_wrap_parrot_integration(parrot_delegate)

        def parrot_tester_restore_parrot_integration():
            parrot_tester_restore_parrot_integration(parrot_delegate)
except ImportError as e:
    print("Error initialising hook: ", e)
    print(traceback.format_exc())
"""

    hook_file.write_text(code)
    print(f"Generated file: {hook_file}")
