import ast

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
        tree = ast.parse(content, filename=str(parrot_integration_path))

        def eval_path_expr(node):
            # Handles Path(...), str(...), and BinOp (e.g., TALON_HOME / 'user' / ...)
            if isinstance(node, ast.Call):
                func_id = getattr(node.func, "id", None)
                if func_id == "Path":
                    parts = [eval_path_expr(a) for a in node.args]
                    return str(Path(*parts))
                if func_id == "str":
                    return eval_path_expr(node.args[0])
            elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
                # Handle pathlib 'Path(folder) / file' syntax
                left = eval_path_expr(node.left)
                right = eval_path_expr(node.right)
                if isinstance(left, Path):
                    return left / right
                return Path(left) / right
            elif isinstance(node, ast.Constant):
                return node.value
            elif isinstance(node, ast.Name):
                if node.id == "TALON_HOME":
                    return TALON_HOME
            return None

        pattern_path_value = None
        parrot_home_value = None

        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        if target.id == "PARROT_HOME":
                            try:
                                parrot_home_value = eval_path_expr(node.value)
                            except Exception as e:
                                logger.debug(f"Failed to evaluate PARROT_HOME: {node.value}")
                        elif target.id == "pattern_path":
                            try:
                                pattern_path_value = eval_path_expr(node.value)
                            except Exception as e:
                                logger.debug(f"Failed to evaluate pattern_path: {node.value}")

        if pattern_path_value:
            logger.debug(f"   Found pattern_path: {pattern_path_value}")
            return str(pattern_path_value)

        if parrot_home_value:
            full_path_json = Path(parrot_home_value) / "patterns.json"
            logger.debug(f"   Checking for patterns.json: {full_path_json}")
            if full_path_json.exists():
                logger.debug(f"   Found patterns.json: {full_path_json}")
                return str(full_path_json)
            full_path_py = Path(parrot_home_value) / "patterns.py"
            logger.debug(f"   Checking for patterns.py: {full_path_py}")
            if full_path_py.exists():
                logger.debug(f"   Found patterns.py: {full_path_py}")
                return str(full_path_py)

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
    if path.suffix == ".json":
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return data
        except Exception as e:
            print(f"❌ Failed to load patterns from {path}: {e}")
            return {}
    elif path.suffix == ".py":
        try:
            spec = importlib.util.spec_from_file_location("patterns", path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module.parrot_patterns
        except Exception as e:
            print(f"❌ Failed to load patterns, ensure a variable named 'parrot_patterns' exists from {path}: {e}")
            return {}
    else:
        print(f"❌ Unsupported file type for patterns: {path}")
        return {}

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

    code = f'''

module_name  = "{module_name}"
fake_pkg    = "{fake_pkg}"

# Load module from system modules if already imported before

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
    import sys
    import os
    import importlib.machinery
{generate_import_code(Path(import_path).resolve(), ["parrot_delegate"], indent="    ")}

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
