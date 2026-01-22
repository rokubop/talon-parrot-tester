from talon import actions
from ..parrot_integration_controller import (
    get_pattern_json,
    get_pattern_color,
)
from .colors import (
    ACCENT_COLOR,
    BG_INPUT,
    BORDER_COLOR_LIGHTER,
    BORDER_COLOR,
    DETECTED_COLOR,
    GRACE_COLOR,
    GRAY_SOFT,
    SECONDARY_COLOR,
    THROTTLE_COLOR,
)

LABEL_FONT = "consolas"
LABEL_WEIGHT = None
LABEL_FONT_SIZE = 16
NUMBER_FONT = "consolas"

def last_detection(size="small"):
    div, text, state = actions.user.ui_elements(["div", "text", "state"])
    detection_current_log_frames = state.get("detection_current_log_frames", [])

    last_frame = detection_current_log_frames[-1] if detection_current_log_frames else None

    if not last_frame or not last_frame.winner:
        return div(flex_direction="column", gap=12, width=200, align_items="center", padding=8)[
            text("-", font_size=30 if size == "small" else 50, color=GRAY_SOFT)
        ]

    return div(flex_direction="column", gap=12 if size == "small" else 24, width=200, align_items="center", padding=8)[
        text(
            last_frame.winner["name"] if last_frame else "-",
            font_size=30 if size == "small" else 50,
            color=ACCENT_COLOR
        ),
        div(flex_direction="row", gap=8, align_items="center")[
            text(
                last_frame.format(last_frame.power, 2) if last_frame else "",
                font_size=14 if size == "small" else 24,
            ),
            text("/"),
            text(
                last_frame.format(last_frame.winner["probability"], 3) if last_frame else "",
                font_size=14 if size == "small" else 24,
            ),
        ],
        power_ratio_bar(
            last_frame.power,
            last_frame.patterns,
            last_frame.winner_grace_power_threshold if last_frame.grace_detected else \
                last_frame.winner_power_threshold if last_frame.detected else None
        )
    ]

def legend():
    div, text, icon = actions.user.ui_elements(["div", "text", "icon"])

    return div(flex_direction="row", gap=32, padding=8, align_items="flex_end")[
        div(flex_direction="row", gap=8, align_items="center")[
            text("Detected"),
            icon("check", size=14, color="73BF69", stroke_width=3),
        ],
        div(flex_direction="row", gap=8, align_items="center")[
            text("Throttled"),
            icon("clock", size=14, color="FFCC00"),
        ],
        div(flex_direction="row", gap=8, align_items="center")[
            text("Grace detected"),
            tilda_icon(),
        ],
        div(flex_direction="row", gap=8, align_items="center")[
            text("Not detected"),
            text("-", color="999999"),
        ],
    ]

def rect_color(color, size=20, **props):
    div = actions.user.ui_elements("div")
    svg, rect = actions.user.ui_elements_svg(["svg", "rect"])

    return div(**props)[
        svg(size=size)[
            rect(x=0, y=0, width=24, height=24, fill=color)
        ]
    ]

def subtitle(text_value):
    text = actions.user.ui_elements("text")
    return text(
        text_value,
        margin=8,
        padding_top=6,
        padding_bottom=8,
        border_bottom=1,
        color=GRAY_SOFT,
        border_color=BORDER_COLOR_LIGHTER,
        min_width=320
    )

def number(value, **kwargs):
    text = actions.user.ui_elements("text")
    return text(value, font_family=NUMBER_FONT, **kwargs)

def number_threshold(value, **kwargs):
    text = actions.user.ui_elements("text")
    return text(f">{value}", font_family=NUMBER_FONT, color=SECONDARY_COLOR, **kwargs)

def status_cell(status: str, graceperiod: bool = False):
    text, icon = actions.user.ui_elements(["text", "icon"])

    s = None

    if status =="grace_detected":
        s = tilda_icon()
    elif status == "detected":
        s = icon("check", size=16, color=DETECTED_COLOR, stroke_width=3)
    elif status == "throttled":
        s = icon("clock", size=16, color=THROTTLE_COLOR)
    return s if s else text("-", color="#999999")

def power_ratio_bar(power: float, patterns: list, power_threshold: float = None):
    div = actions.user.ui_elements("div")
    power_percent = min(30, power) / 30
    power_threshold_percent = min(30, power_threshold) / 30 if power_threshold else 0
    full_bar_width = 150
    bar_width = int(full_bar_width * power_percent)
    power_threshold_left = int(power_threshold_percent * full_bar_width) if power_threshold else None

    return div(position="relative", flex_direction="row", width=bar_width, background_color="555555", height=9)[
        *[div(width=int(pattern["probability"] * bar_width), background_color=pattern["color"]) for pattern in patterns],
        div(position="absolute", left=power_threshold_left - 1.5, width=1.5, top=0, bottom=0, background_color="#920000") if power_threshold else None,
    ]

def table_controls():
    div, text, icon, button, checkbox, style = actions.user.ui_elements(["div", "text", "icon", "button", "checkbox", "style"])
    state = actions.user.ui_elements("state")
    double_pop_pause, set_double_pop_pause = state.use("double_pop_pause", False)
    disable_actions, set_disable_actions = state.use("disable_actions", False)
    show_formants, set_show_formants = state.use("show_formants", False)
    show_thresholds, set_show_thresholds = state.use("show_thresholds", True)
    debug_power, set_debug_power = state.use("debug_power", False)
    debug_probability, set_debug_probability = state.use("debug_probability", False)
    tab = state.get("tab")

    checkbox_props = {
        "background_color": BG_INPUT,
        "border_color": BORDER_COLOR,
        "border_width": 1,
        "border_radius": 2,
    }

    return div(flex_direction="row", gap=24, margin_right=8)[
        # div(flex_direction="row", gap=8, align_items="center")[
        #     checkbox(checkbox_props, id="disable_actions", checked=disable_actions, on_change=lambda e: set_disable_actions(e.checked)),
        #     text("Disable actions", for_id="disable_actions"),
        # ],
        # div(flex_direction="row", gap=8, align_items="center")[
        #     checkbox(checkbox_props, id="double_pop_pause", checked=double_pop_pause, on_change=lambda e: set_double_pop_pause(e.checked)),
        #     text("Double pop to pause", for_id="double_pop_pause"),
        # ],
        div(flex_direction="row", gap=8, align_items="center")[
            checkbox(checkbox_props, id="show_formants", checked=show_formants, on_change=lambda e: set_show_formants(e.checked)),
            text("Show F0, F1, F2", for_id="show_formants"),
        ],
        div(flex_direction="row", gap=8, align_items="center")[
            checkbox(checkbox_props, id="show_thresholds", checked=show_thresholds, on_change=lambda e: set_show_thresholds(e.checked)),
            text("Show thresholds", for_id="show_thresholds"),
        ] if tab == "detection_log" else None,
        # div(flex_direction="row", gap=8, align_items="center")[
        #     checkbox(checkbox_props, id="debug_power", checked=debug_power, on_change=lambda e: set_debug_power(e.checked)),
        #     text("Debug power (>1.0)", for_id="debug_power"),
        # ],
        # div(flex_direction="row", gap=8, align_items="center")[
        #     checkbox(checkbox_props, id="debug_probability", checked=debug_probability, on_change=lambda e: set_debug_probability(e.checked)),
        #     text("Debug prob. (>0.10)", for_id="debug_probability"),
        # ],
        # button(padding=8, padding_left=12, padding_right=12, flex_direction="row", align_items="center", gap=4, border_color=BORDER_COLOR, border_width=2, border_radius=4)[
        #     text("Capture time"),
        #     icon("chevron_down", size=14),
        # ],
        # button(padding=8, padding_left=12, padding_right=12, flex_direction="row", align_items="center", gap=4, border_color=BORDER_COLOR, border_width=2, border_radius=4)[
        #     text("Filters"),
        #     icon("chevron_down", size=14),
        # ],
        # button(padding=8, padding_left=12, padding_right=12, flex_direction="row", align_items="center", gap=4, background_color="#292A2F", border_color=BORDER_COLOR, border_width=1, border_radius=4)[
        #     text("Columns"),
        #     icon("chevron_down", size=14),
        # ],
    ]

def tilda_icon():
    svg, path = actions.user.ui_elements_svg(["svg", "path"])
    return svg(size=14, stroke=GRACE_COLOR, stroke_width=4)[
        path(d="M4 14 Q8 10, 12 14 T20 14")
    ]

def pattern(props):
    div, text, icon, button, state = actions.user.ui_elements(["div", "text", "icon", "button", "state"])
    table, tr, td, style = actions.user.ui_elements(["table", "tr", "td", "style"])

    pattern_name = props["name"]
    highlight_when_active = props.get("highlight_when_active", False)
    show_throttles = props.get("show_throttles", True)
    show_grace = props.get("show_grace", True)
    small = props.get("small", False)
    view = props.get("view", "full")
    # edit = props.get("edit", True)

    if view != "full":
        show_throttles = False
        show_grace = False

    pattern_data = get_pattern_json(pattern_name)
    pattern_color = get_pattern_color(pattern_name)

    style({
        "th": {
            "padding": 5,
            "padding_right": 7,
            "flex_direction": "row",
            "align_items": "center",
        },
        "td": {
            "padding": 5,
            "padding_right": 7,
            "flex_direction": "row",
            "align_items": "center",
        },
    })

    if show_throttles:
        throttle_items = list(pattern_data.get("throttle", {}).items())
        throttle_groups = [throttle_items[i:i + 2] for i in range(0, len(throttle_items), 2)]
    else:
        throttle_groups = []

    if show_grace:
        grace_period = pattern_data.get("graceperiod", "")
        grace_threshold_items = list(pattern_data.get("grace_threshold", {}).items())
        grace_threshold_groups = [grace_threshold_items[i:i + 2] for i in range(0, len(grace_threshold_items), 2)]
    else:
        grace_period = ""
        grace_threshold_groups = []

    pattern_props = {
        "padding": 16,
        "padding_top": 12,
        "padding_bottom": 12,
        "flex_direction": "column",
        "gap": 8,
    }

    if highlight_when_active:
        pattern_props["id"] = f"pattern_{pattern_name}"

    thresholds = pattern_data.get("threshold", {})

    ordered_thresholds = []
    if ">power" in thresholds:
        ordered_thresholds.append((">power", thresholds[">power"]))
    if ">probability" in thresholds:
        ordered_thresholds.append((">probability", thresholds[">probability"]))

    for key, value in thresholds.items():
        if key not in [">power", ">probability"]:
            ordered_thresholds.append((key, value))

    threshold_groups = [ordered_thresholds[i:i + 2] for i in range(0, len(ordered_thresholds), 2)]

    if view == "compact":
        return div(pattern_props)[
            div(flex_direction="row", gap=8, align_items="center", padding_bottom=8, justify_content="space_between")[
                div(flex_direction="row", gap=8, align_items="center")[
                    rect_color(pattern_color, size=14),
                    text(pattern_name, font_size=18),
                ],
            ],
        ]

    if small:
        return div(pattern_props)[
            div(flex_direction="row", gap=8, align_items="center", justify_content="space_between")[
                div(flex_direction="row", gap=8, align_items="center")[
                    rect_color(pattern_color, size=12),
                    text(pattern_name, font_size=15),
                ],
            ],
            div(flex_direction="row", border_left=1, border_color=BORDER_COLOR_LIGHTER)[
                table()[
                    *[
                        tr()[
                            *[
                                item
                                for k, v in group
                                for item in [
                                    td()[
                                        text(k, font_size=LABEL_FONT_SIZE, color=ACCENT_COLOR, font_weight=LABEL_WEIGHT, font_family=LABEL_FONT),
                                    ],
                                    td(margin_right=16)[
                                        number(v),
                                    ],
                                ]
                            ] + ([None, None] if len(group) == 1 else [])  # Pad single items
                        ]
                        for group in threshold_groups
                    ] if threshold_groups else [
                        tr()[
                            td(position="relative")[
                                text(">power", font_size=LABEL_FONT_SIZE, color=ACCENT_COLOR, font_weight=LABEL_WEIGHT, font_family=LABEL_FONT),
                            ],
                            td(margin_right=16, position="relative")[
                                number("0"),
                            ],
                            td()[text(">probability", font_size=LABEL_FONT_SIZE, color=ACCENT_COLOR, font_weight=LABEL_WEIGHT, font_family=LABEL_FONT)],
                            td(margin_right=16)[number("0")],
                        ]
                    ]
                ],
            ],
        ]

    return div(pattern_props)[
        div(flex_direction="row", gap=8, align_items="center", padding_bottom=8, justify_content="space_between")[
            div(flex_direction="row", gap=8, align_items="center")[
                rect_color(pattern_color, size=14),
                text(pattern_name, font_size=18),
            ],
            # button(on_click=lambda e: state.set("edit_pattern", pattern_name))[
            #     icon("edit", size=16, color=ACCENT_COLOR, stroke_width=3),
            # ] if edit else None,
        ],
        div(align_items="flex_start", border_left=1, border_color=BORDER_COLOR_LIGHTER)[
            div(flex_direction="row", gap=8, margin_left=15, align_items="center")[
                text("sounds", font_size=LABEL_FONT_SIZE, color=ACCENT_COLOR, font_weight=LABEL_WEIGHT, font_family=LABEL_FONT),
                text(",".join(pattern_data.get("sounds", []))),
            ] if not small else None,
            table(padding=8, padding_bottom=0)[
                *[
                    tr()[
                        *[
                            item
                            for k, v in group
                            for item in [
                                td(position="relative")[
                                    text(k, font_size=LABEL_FONT_SIZE, color=ACCENT_COLOR, font_weight=LABEL_WEIGHT, font_family=LABEL_FONT),
                                ],
                                td(margin_right=16, position="relative")[
                                    number(v),
                                ],
                            ]
                        ] + ([None, None] if len(group) == 1 else [])  # Pad single items
                    ]
                    for group in threshold_groups
                ] if threshold_groups else [
                    tr()[
                        td(position="relative")[
                            text(">power", font_size=LABEL_FONT_SIZE, color=ACCENT_COLOR, font_weight=LABEL_WEIGHT, font_family=LABEL_FONT),
                        ],
                        td(margin_right=16, position="relative")[
                            number("0"),
                        ],
                        td()[text(">probability", font_size=LABEL_FONT_SIZE, color=ACCENT_COLOR, font_weight=LABEL_WEIGHT, font_family=LABEL_FONT)],
                        td(margin_right=16)[number("0")],
                    ]
                ],
                *[
                    tr()[
                        *[
                            item
                            for k, v in group
                            for item in [
                                td()[
                                    div(flex_direction="row", gap=4, align_items="center")[
                                        icon("clock", size=14, color="FFCC00"),
                                        text(k, font_size=LABEL_FONT_SIZE, color=ACCENT_COLOR, font_weight=LABEL_WEIGHT, font_family=LABEL_FONT),
                                    ]
                                ],
                                td(margin_right=16)[number(v)],
                            ]
                        ]
                    ]
                    for group in throttle_groups
                ]
            ],
            div(flex_direction="row", gap=8, margin_left=15, align_items="center", margin_top=8)[
                text("graceperiod", color=GRACE_COLOR, font_weight=LABEL_WEIGHT, font_family=LABEL_FONT),
                number(grace_period),
            ] if grace_period else None,
            table(padding=8, padding_bottom=0)[
                *[
                    tr()[
                        *[
                            item
                            for k, v in group
                            for item in [
                                td()[
                                    div(flex_direction="row", gap=4, align_items="center")[
                                        text(k, color=GRACE_COLOR, font_weight=LABEL_WEIGHT, font_family=LABEL_FONT),
                                    ]
                                ],
                                td(margin_right=16)[number(v)],
                            ]
                        ]
                    ]
                    for group in grace_threshold_groups
                ]
            ] if grace_threshold_groups else None,
        ]
    ]

# def removable_pill(name):
#     div, text, icon = actions.user.ui_elements(["div", "text", "icon"])

#     return div(flex_direction="row", border_width=1, border_color="555555", background_color=f"55555533", padding=4, border_radius=4)[
#         text(name),
#         icon("close", size=14, color="555555", stroke_width=3, margin_left=8),
#     ]

# def pattern_pill(name):
#     div, text = actions.user.ui_elements(["div", "text"])

#     if name in get_patterns_json():
#         pattern_color = get_pattern_color(name)
#     else:
#         pattern_color = "555555"
#     return div(border_width=1, border_color=pattern_color, background_color=f"{pattern_color}33", padding=4, border_radius=4)[
#         text(f"+ {name}")
#     ]