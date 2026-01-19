from talon import actions, cron
from talon.experimental.parrot import ParrotFrame
from math import floor
from .ui.colors import get_color
from .parrot_integration_controller import (
    get_patterns_json,
)
from .parrot_integration_controller import (
    restore_patterns_paused,
)

def truncate_stringify(x: float, decimals: int = 3) -> str:
    factor = 10 ** decimals
    truncated = floor(x * factor) / factor
    return f"{truncated:.{decimals}f}"

STATUS_ORDER = {
    "detected": 0,
    "grace_detected": 1,
    "throttled": 2,
    "": 3
}

def format(value: float, decimals: int = 3) -> str:
    if value is None:
        return ""
    return truncate_stringify(value, decimals)

class ParrotTesterFrame:
    THRESHOLD_PROBABILITY = 0.1

    def __init__(self, frame: ParrotFrame):
        self.id = None
        self.index = None
        self.ts = frame.ts
        self.ts_delta = None
        self.ts_zero_based = None
        self.power = frame.power
        self.f0 = frame.f0
        self.f1 = frame.f1
        self.f2 = frame.f2
        self.patterns = []
        self.pattern_names = set()
        self.detected = False
        self.grace_detected = False
        self.log_id = None
        self.capture_id = None

    def add_pattern(self, name: str, sounds: set[str], probability: float, detected: bool, throttled: bool, graceperiod: bool, color: str, grace_detected=bool):
        if probability > self.THRESHOLD_PROBABILITY:
            if detected:
                self.detected = True
            if grace_detected:
                self.grace_detected = True
            self.pattern_names.add(name)
            self.patterns.append({
                "name": name,
                "sounds": sounds,
                "probability": probability,
                "status": "grace_detected" if grace_detected else "detected" if detected else "throttled" if throttled else "",
                "graceperiod": graceperiod,
                "color": color,
            })

    def freeze(self):
        self.patterns = sorted(
            self.patterns,
            key=lambda x: (
                STATUS_ORDER.get(x["status"], 99),  # sort by status first
                -x["probability"]                   # then by probability descending
            )
        )

    def format(self, value: float, decimals: int = 3) -> str:
        if value is None:
            return ""
        return truncate_stringify(value, decimals)

    @property
    def winner(self):
        return self.patterns[0] if self.patterns else {}

    @property
    def winner_name(self):
        return self.winner.get("name", "")

    @property
    def winner_power_threshold(self):
        name = self.winner_name
        global_patterns = get_patterns_json()
        return global_patterns.get(name, {}).get("threshold", {}).get(">power", None)

    @property
    def winner_grace_power_threshold(self):
        name = self.winner_name
        global_patterns = get_patterns_json()
        return global_patterns.get(name, {}).get("grace_threshold", {}).get(">power", None)

    @property
    def winner_probability(self):
        return self.winner.get("probability", 0.0)

    @property
    def winner_status(self):
        return self.winner.get("status", "")

class Buffer:
    def __init__(self, size: int = 5):
        self.size = size
        self.buffer: list[ParrotTesterFrame] = []
        self.buffer_last: list[ParrotTesterFrame] = []
        self.get_time_window = 0.3

    def add(self, item):
        if len(self.buffer) > self.size:
            self.buffer_last = self.buffer.copy()
            self.buffer = []
        self.buffer.append(item)

    def get(self, current_ts: float) -> list[ParrotTesterFrame]:
        all = self.buffer_last + self.buffer
        # but dont include the last one
        all = all[:-1]
        # look at each frame.ts and get the last 0.3 seconds
        return [frame for frame in all if current_ts - frame.ts < self.get_time_window]

    def clear(self):
        """Clear the buffer."""
        self.buffer = []
        self.buffer_last = []

buffer = Buffer()

def create_id_from_frame(frame: ParrotTesterFrame) -> str:
    """Create a unique ID from the frame's timestamp and winner name."""
    return f"{frame.format(frame.ts, 3)} {frame.winner_name}" if frame else None

class Capture:
    def __init__(self, detect_frame: ParrotTesterFrame):
        self.id = create_id_from_frame(detect_frame)
        self.frames = buffer.get(detect_frame.ts)
        self.frames.append(detect_frame)
        detect_frame.capture_id = self.id
        detect_frame_index = len(self.frames) - 1
        self._detect_frames = [(detect_frame, detect_frame_index)]
        self.pattern_names = set()
        for frame in self.frames:
            self.pattern_names.update(frame.pattern_names)

    @property
    def detect_frames(self):
        return [frame[0] for frame in self._detect_frames]

    @property
    def detected_pattern_names(self):
        patterns = []
        seen = set()

        for frame in self.detect_frames:
            for p in frame.patterns:
                name = p["name"]
                if name not in seen:
                    patterns.append(name)
                    seen.add(name)

        return patterns

    @property
    def other_pattern_names(self):
        return self.pattern_names - set(self.detected_pattern_names)

    def add_frame(self, frame: ParrotTesterFrame):
        self.frames.append(frame)
        self.pattern_names.update(frame.pattern_names)

    def add_detect_frame(self, frame: ParrotTesterFrame):
        self.frames.append(frame)
        frame.capture_id = self.id
        detect_frame_index = len(self.frames) - 1
        self._detect_frames.append((frame, detect_frame_index))
        self.pattern_names.update(frame.pattern_names)

    def detected_two_pops(self) -> bool:
        pop_count = sum(1 for frame in self.detect_frames if "pop" == frame.winner_name)
        return pop_count >= 2

    def complete(self):
        for i, frame in enumerate(self.frames):
            frame.ts_delta = frame.ts - self.detect_frames[0].ts
            frame.ts_zero_based = frame.ts - self.frames[0].ts
            frame.id = i + 1
            frame.index = i

class CaptureCollection:
    capture_timeout = "350ms"
    max_frames_per_capture = 50

    def __init__(self):
        self.current_capture: Capture | None = None
        self.captures: list[Capture] = []
        self.end_current_capture_job = None

    def add(self, frame: ParrotTesterFrame, active: set[str]):
        new_capture = False
        if self.current_capture and len(self.current_capture.frames) >= self.max_frames_per_capture:
            self.end_current_capture()

        if active:
            if self.current_capture is None:
                new_capture = True
                self.current_capture = Capture(frame)
                self.captures.append(self.current_capture)
            else:
                self.current_capture.add_detect_frame(frame)
            if self.end_current_capture_job is not None:
                cron.cancel(self.end_current_capture_job)
            self.end_current_capture_job = cron.after(self.capture_timeout, self.end_current_capture)
        elif self.current_capture is not None:
            self.current_capture.add_frame(frame)

        if new_capture and actions.user.ui_elements_get_state("tab") == "frames":
            actions.user.ui_elements_set_state("capture_updating", True)

    def end_current_capture(self):
        if self.current_capture is not None:
            self.current_capture.complete()

            self.current_capture = None
            if self.end_current_capture_job is not None:
                cron.cancel(self.end_current_capture_job)
            self.end_current_capture_job = None
            last_capture = self.captures[-1] if self.captures else None
            tab = actions.user.ui_elements_get_state("tab")
            if tab == "frames":
                actions.user.ui_elements_set_state("capture_updating", False)

            # double pop pause
            if actions.user.ui_elements_get_state("double_pop_pause") and last_capture and last_capture.detected_two_pops():
                actions.user.ui_elements_set_state("play", False)
                actions.user.ui_elements_toggle_hints(True)
                restore_patterns_paused()
            elif tab == "frames":
                actions.user.ui_elements_set_state("last_capture", last_capture)

    def clear(self):
        self.captures = []
        self.current_capture = None
        if self.end_current_capture_job is not None:
            cron.cancel(self.end_current_capture_job)
            self.end_current_capture_job = None

class DetectionLog:
    def __init__(self):
        self.frames: list[ParrotTesterFrame] = []

    def add(self, frame: ParrotTesterFrame):
        self.frames.append(frame)

    def clear(self):
        self.frames = []

    def id(self):
        return create_id_from_frame(self.frames[0]) if self.frames else None

class DetectionLogCollection:
    def __init__(self):
        self.collection: list[DetectionLog] = []
        self.current_log: DetectionLog | None = None

    def add(self, frame: ParrotTesterFrame):
        if self.current_log is None or len(self.current_log.frames) >= 20:
            self.current_log = DetectionLog()
            self.collection.append(self.current_log)
        self.current_log.add(frame)
        frame.log_id = self.current_log.id()

    def history(self):
        return [log.id() for log in self.collection]

    def current_log_frames(self) -> list[ParrotTesterFrame]:
        """Get the frames of the current detection log."""
        if self.current_log:
            return list(self.current_log.frames)
        return []

    def get_log_by_id(self, log_id: str) -> DetectionLog | None:
        for log in self.collection:
            if log.id() == log_id:
                return log
        return None

    def clear(self):
        self.collection = []
        self.current_log = None

class PatternsStats:
    def __init__(self):
        self.stats = {}
        self.total_frames = {}
        # Initialize stats structure from patterns in get_patterns_json
        global_patterns = get_patterns_json()
        # print("Initializing PatternsStats with patterns:", global_patterns.keys())
        for pattern_name in global_patterns.keys():
            self._initialize_pattern_stats(pattern_name)

    def _initialize_pattern_stats(self, pattern_name):
        """Initialize statistics structure for a new pattern."""
        if pattern_name not in self.stats:
            self.stats[pattern_name] = {
                "count": 0,
                "power": {"min": float('inf'), "sum": 0, "max": float('-inf')},
                "probability": {"min": float('inf'), "sum": 0, "max": float('-inf')},
                "f0": {"min": float('inf'), "sum": 0, "max": float('-inf')},
                "f1": {"min": float('inf'), "sum": 0, "max": float('-inf')},
                "f2": {"min": float('inf'), "sum": 0, "max": float('-inf')}
            }
            self.total_frames[pattern_name] = 0

    def _update_metric(self, pattern_name, metric_name, value):
        """Update min, sum, and max for a given metric."""
        if value is None:
            return

        stats = self.stats[pattern_name][metric_name]
        stats["min"] = min(stats["min"], value)
        stats["sum"] += value
        stats["max"] = max(stats["max"], value)

    def add_frame(self, frame):
        """Add a single frame's statistics."""
        if not frame.patterns:
            return

        # Update stats for the winning pattern (most confident detection)
        winner = frame.winner
        if not winner:
            return

        pattern_name = winner.get("name")
        if not pattern_name:
            return

        self._initialize_pattern_stats(pattern_name)

        # Update counts
        self.stats[pattern_name]["count"] += 1
        self.total_frames[pattern_name] += 1

        # Update metrics
        self._update_metric(pattern_name, "power", frame.power)
        self._update_metric(pattern_name, "probability", winner.get("probability"))
        self._update_metric(pattern_name, "f0", frame.f0)
        self._update_metric(pattern_name, "f1", frame.f1)
        self._update_metric(pattern_name, "f2", frame.f2)

    def generate(self, log_collection):
        """Generate statistics from a log collection."""
        # Reset stats while keeping the structure
        # print("log_collection.collection:", log_collection.collection)
        # print("log_collection.current_log:", log_collection.current_log)
        for pattern in list(self.stats.keys()):
            self.stats[pattern]["count"] = 0
            for metric in ["power", "probability", "f0", "f1", "f2"]:
                self.stats[pattern][metric]["min"] = float('inf')
                self.stats[pattern][metric]["sum"] = 0
                self.stats[pattern][metric]["max"] = float('-inf')
        self.total_frames = {pattern: 0 for pattern in self.stats}

        # Process all frames
        for log in log_collection.collection:
            for frame in log.frames:
                # print("adding frame to stats:", frame.id, frame.ts, frame.winner_name)
                self.add_frame(frame)

        return self.get_stats()

    def get_stats(self):
        """Get the current statistics with averages calculated."""
        result = {}
        for pattern_name, stats in self.stats.items():
            result[pattern_name] = {
                "name": pattern_name,
                "count": stats["count"],
                "power": {
                    "min": stats["power"]["min"] if stats["power"]["min"] != float('inf') else 0,
                    "average": stats["power"]["sum"] / self.total_frames[pattern_name] if self.total_frames[pattern_name] > 0 else 0,
                    "max": stats["power"]["max"] if stats["power"]["max"] != float('-inf') else 0
                },
                "probability": {
                    "min": stats["probability"]["min"] if stats["probability"]["min"] != float('inf') else 0,
                    "average": stats["probability"]["sum"] / self.total_frames[pattern_name] if self.total_frames[pattern_name] > 0 else 0,
                    "max": stats["probability"]["max"] if stats["probability"]["max"] != float('-inf') else 0
                },
                "f0": {
                    "min": stats["f0"]["min"] if stats["f0"]["min"] != float('inf') else 0,
                    "average": stats["f0"]["sum"] / self.total_frames[pattern_name] if self.total_frames[pattern_name] > 0 else 0,
                    "max": stats["f0"]["max"] if stats["f0"]["max"] != float('-inf') else 0
                },
                "f1": {
                    "min": stats["f1"]["min"] if stats["f1"]["min"] != float('inf') else 0,
                    "average": stats["f1"]["sum"] / self.total_frames[pattern_name] if self.total_frames[pattern_name] > 0 else 0,
                    "max": stats["f1"]["max"] if stats["f1"]["max"] != float('-inf') else 0
                },
                "f2": {
                    "min": stats["f2"]["min"] if stats["f2"]["min"] != float('inf') else 0,
                    "average": stats["f2"]["sum"] / self.total_frames[pattern_name] if self.total_frames[pattern_name] > 0 else 0,
                    "max": stats["f2"]["max"] if stats["f2"]["max"] != float('-inf') else 0
                }
            }

        return result

    def clear(self):
        """Clear all statistics."""
        self.stats = {}
        self.total_frames = {}
        # Re-initialize with patterns from get_patterns_json
        global_patterns = get_patterns_json()
        for pattern_name in global_patterns:
            self._initialize_pattern_stats(pattern_name)

capture_collection = CaptureCollection()
detection_log_collection = DetectionLogCollection()
patterns_stats = None
detected_log = []
log_events = False

def init_stats():
    """Initialize the patterns statistics."""
    global patterns_stats, detection_log_collection
    if not patterns_stats:
        patterns_stats = PatternsStats()
    s = patterns_stats.generate(detection_log_collection)
    # print("Generated patterns stats:", s)
    actions.user.ui_elements_set_state("patterns_stats", s)

def add_frame_to_stats(frame: ParrotTesterFrame):
    """Add a frame to the patterns statistics."""
    global patterns_stats
    if patterns_stats is None:
        init_stats()
    patterns_stats.add_frame(frame)

def get_stats():
    """Get the current patterns statistics."""
    global patterns_stats
    if patterns_stats is None:
        init_stats()
    return patterns_stats.get_stats()

def get_stats_pretty_print(name: str = None) -> str:
    if name:
        return format_stats_multiline(get_stats().get(name, {}))
    # do all
    stats = get_stats()
    return "\n".join(format_stats_multiline(entry) for entry in stats.values() if entry["count"] > 0)

def reset_stats():
    """Reset the patterns statistics."""
    global patterns_stats
    if patterns_stats:
        patterns_stats.clear()

def update_stats_state():
    """Update the Talon UI state with the current patterns statistics."""
    global patterns_stats
    if patterns_stats is None:
        init_stats()
    actions.user.ui_elements_set_state("patterns_stats", patterns_stats.get_stats())

def format_stats_multiline(entry: dict) -> str:
    lines = [f"{entry['name']} (count: {entry['count']})"]
    for key in ["power", "probability", "f0", "f1", "f2"]:
        values = entry[key]
        lines.append(f"  {key}: min={values['min']}, avg={values['average']}, max={values['max']}")
    return "\n".join(lines)

def reset_capture_collection():
    global log_events, patterns_stats
    buffer.clear()
    capture_collection.clear()
    detected_log.clear()
    detection_log_collection.clear()
    if patterns_stats:
        patterns_stats.clear()
        patterns_stats = None
    log_events = False

def listen_log_events(enable: bool):
    global log_events
    log_events = enable

def determine_grace_detected(detect: bool, uses_grace_thresholds: bool, power: float, probability: float, pattern: dict) -> bool:
    if not detect:
        return False

    power_threshold = pattern.lowest_power_thresholds[0]
    grace_power_threshold = pattern.lowest_power_thresholds[1]
    if 0 < grace_power_threshold < power < power_threshold:
        return True

    return False

def is_grace_detected(pattern, frame) -> bool:
    grace_detected = False
    if pattern.timestamps.graceperiod_until and frame.ts < pattern.timestamps.graceperiod_until:
        if pattern.is_active(frame.ts) and pattern.match_pattern(pattern, frame, pattern.timestamps.graceperiod_until):
            grace_detected = True
    return grace_detected

def is_using_grace_thresholds_for_detection(pattern, frame):
    return frame.ts < pattern.timestamps.graceperiod_until

def force_normal_threshold_detection(pattern, frame):
    return pattern.match_pattern(pattern, frame, graceperiod_until=0)

def detect(pattern, frame):
    detected = pattern.detect(frame)
    grace_detected = False
    if detected and pattern.timestamps.graceperiod_until and \
            is_using_grace_thresholds_for_detection(pattern, frame):
        detection_normal = force_normal_threshold_detection(pattern, frame)
        if not detection_normal:
            grace_detected = True

    return detected, grace_detected

def wrap_pattern_match(parrot_delegate):
    pattern_index = {
        name: index for index, name in enumerate(parrot_delegate.patterns.keys())
    }

    def wrapper(frame: ParrotFrame):
        active: set[str] = set()
        parrot_tester_frame = ParrotTesterFrame(frame)
        buffer.add(parrot_tester_frame)

        for pattern in parrot_delegate.patterns.values():
            detected, grace_detected = detect(pattern, frame)
            graceperiod = pattern.timestamps.graceperiod_until > frame.ts
            probability = sum(frame.classes.get(label, 0) for label in pattern.labels)
            parrot_tester_frame.add_pattern(
                name=pattern.name,
                sounds=pattern.labels,
                probability=probability,
                detected=detected,
                grace_detected=grace_detected,
                throttled=pattern.timestamps.throttled_at > 0 and \
                    pattern.timestamps.throttled_until > frame.ts,
                graceperiod=graceperiod,
                color=get_color(pattern_index[pattern.name]),
            )

            if detected:
                active.add(pattern.name)
                throttles = pattern.get_throttles()
                parrot_delegate.throttle_patterns(throttles, frame.ts)
                detection_log_collection.add(parrot_tester_frame)

        parrot_tester_frame.freeze()
        capture_collection.add(parrot_tester_frame, active)

        if active:
            tab = actions.user.ui_elements_get_state("tab")
            if tab == "patterns":
                for name in active:
                    actions.user.ui_elements_highlight_briefly(f"pattern_{name}")
            elif tab == "detection_log" or tab == "activity" or actions.user.ui_elements_get_state("minimized"):
                populate_detection_log_state()
            elif tab == "stats":
                add_frame_to_stats(parrot_tester_frame)
                update_stats_state()

        return active
    return wrapper

def set_detection_log_state_by_id(log_id: str):
    """Set the detection log state based on the log ID."""
    actions.user.ui_elements_set_state("detection_current_log_id", log_id)
    if detection_log_collection.current_log and detection_log_collection.current_log.id() == log_id:
        actions.user.ui_elements_set_state("detection_current_log_frames", detection_log_collection.current_log_frames())
    else:
        log = detection_log_collection.get_log_by_id(log_id)
        actions.user.ui_elements_set_state("detection_current_log_frames", log.frames if log else [])

def populate_detection_log_state():
    actions.user.ui_elements_set_state("detection_log_history", detection_log_collection.history())
    log_id = detection_log_collection.current_log.id() if detection_log_collection.current_log else None
    set_detection_log_state_by_id(log_id)

original_pattern_match = None

def get_current_log_by_id(log_id: str) -> DetectionLog | None:
    """Get the current detection log by ID."""
    return detection_log_collection.get_log_by_id(log_id)

def parrot_tester_wrap_parrot_integration(parrot_delegate):
    global original_pattern_match
    if original_pattern_match is None:
        original_pattern_match = parrot_delegate.pattern_match
        parrot_delegate.pattern_match = wrap_pattern_match(parrot_delegate)
        print("parrot_integration.py wrapped")

def parrot_tester_restore_parrot_integration(parrot_delegate, reset_ui_state=True):
    global original_pattern_match
    if original_pattern_match is not None:
        parrot_delegate.pattern_match = original_pattern_match
        original_pattern_match = None

    if reset_ui_state:
        reset_capture_collection()
    print("parrot_integration.py restored")
