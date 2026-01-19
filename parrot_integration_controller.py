from pathlib import Path
from talon import actions, cron, registry, Context
from talon_init import TALON_USER
from .ui.colors import get_color
from .parrot_integration_paths import (
    get_parrot_integration_path,
    get_patterns_py_path,
    load_patterns,
    build_module_path,
    generate_parrot_integration_hook,
    create_temp_parrot_file,
    remove_temp_parrot_file,
)

patterns_json = {}

tag_ctx = Context()

def enable_parrot_tester_tag():
    tag_ctx.tags = ["user.parrot_tester"]

def disable_parrot_tester_tag():
    tag_ctx.tags = []

def wait_for_ready(callback, attempts=0):
    is_ready = actions.user.parrot_tester_integration_ready()
    if is_ready:
        callback()
    elif attempts < 10:
        cron.after("500ms", lambda: wait_for_ready(callback, attempts + 1))
    else:
        print("Parrot Tester could not initialize after 10 attempts (5 seconds total waited)")

def wait_for_registry_populated(callback, attempts=0):
    parrot_noises = getattr(registry, "parrot_noises", {})
    if parrot_noises:
        callback()
    elif attempts < 10:
        cron.after("500ms", lambda: wait_for_registry_populated(callback, attempts + 1))
    else:
        print("Parrot registry not populated after 10 attempts, continuing anyway...")
        callback()

def parrot_tester_initialize(callback):
    """Initialize Parrot Tester and wrap parrot_integration."""
    print("**** Starting Parrot Tester ****")
    enable_parrot_tester_tag()

    try:
        parrot_integration_path = get_parrot_integration_path().resolve()
        patterns_py_path = get_patterns_py_path().resolve()
        current_path = Path(__file__).resolve()

        current = Path(__file__).parent.resolve()
        target = Path(parrot_integration_path).resolve()
        user_root = Path(TALON_USER).resolve()

        current_rel = current.relative_to(user_root)
        target_rel = target.relative_to(user_root).with_suffix("")

        patterns_data = load_patterns(patterns_py_path)
        set_patterns_json(patterns_data)

        temp_file_created = create_temp_parrot_file(patterns_data)

        def continue_initialization():
            module_path = build_module_path(current_rel, target_rel, user_root)
            generate_parrot_integration_hook(module_path, current_path)

            def on_ready():
                actions.user.parrot_tester_wrap_parrot_integration()
                callback()

            wait_for_ready(on_ready)

        if temp_file_created:
            print("Waiting for Talon to process temporary parrot file...")
            wait_for_registry_populated(continue_initialization)
        else:
            continue_initialization()

    except ValueError as e:
        # This catches our detailed error message about invalid paths
        print(str(e))
        disable_parrot_tester_tag()
        return
    except Exception as e:
        print(f"❌ PARROT TESTER ERROR: Failed to initialize: {e}")
        disable_parrot_tester_tag()
        return

def restore_patterns_paused():
    actions.user.parrot_tester_restore_parrot_integration()
    disable_parrot_tester_tag()

def restore_patterns():
    actions.user.parrot_tester_restore_parrot_integration()
    clear_patterns_json()
    remove_temp_parrot_file()
    disable_parrot_tester_tag()

def get_pattern_color(name: str):
    global_patterns = get_patterns_json()
    try:
        index = list(global_patterns.keys()).index(name)
        return get_color(index)
    except:
        return "#FFFFFF"

def get_pattern_threshold_value(name: str, key: str):
    """Get a specific value from the pattern JSON."""
    global_patterns = get_patterns_json()
    if global_patterns and name in global_patterns:
        return global_patterns[name].get("threshold", {}).get(key, None)
    return None


def get_pattern_json(name: str = None):
    """Get the pattern JSON for a specific name."""
    global_patterns = get_patterns_json()
    # print(f"Pattern JSON: {json.dumps(global_patterns)}")
    # print(f"Getting pattern JSON for name: {name}")
    # print(f"Pattern JSON:", global_patterns)
    if global_patterns:
        return global_patterns.get(name, {})
    return {}

def get_patterns_json():
    """Get the patterns JSON."""
    global patterns_json
    if not patterns_json:
        patterns_py_path = get_patterns_py_path()
        if patterns_py_path:
            patterns_py_path = patterns_py_path.resolve()
            patterns_json = load_patterns(patterns_py_path)
        else:
            patterns_json = {}
    return patterns_json

def clear_patterns_json():
    """Clear the patterns JSON cache."""
    global patterns_json
    patterns_json.clear()

def set_patterns_json(data: dict):
    """Set the patterns JSON data."""
    global patterns_json
    patterns_json = data