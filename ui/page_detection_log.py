from talon import actions
from .components import (
    legend,
    number,
    status_cell,
    power_ratio_bar,
    table_controls,
    subtitle,
)
from .colors import (
    SECONDARY_COLOR,
    BORDER_COLOR,
    BG_DARKEST,
    BG_DARK,
    ACTIVE_COLOR,
    BG_GRAY,
)
from ..parrot_integration_controller import (
    get_pattern_threshold_value,
)
from ..parrot_integration_wrapper import (
    populate_detection_log_state,
    set_detection_log_state_by_id,
)

def table_log():
    div, text, icon, style = actions.user.ui_elements(["div", "text", "icon", "style"])
    table, th, tr, td = actions.user.ui_elements(["table", "th", "tr", "td"])
    state = actions.user.ui_elements(["state"])
    detection_current_log_frames = state.get("detection_current_log_frames", [])
    show_formants = state.get("show_formants", False)
    show_thresholds = state.get("show_thresholds", False)

    style({
        "th": {
            "padding": 10,
            "padding_left": 12,
            "padding_right": 12,
            "align_items": "flex_start",
            "border_bottom": 1,
        },
        "td": {
            "padding": 8,
            "padding_left": 12,
            "padding_right": 12,
            "align_items": "flex_end",
            "border_bottom": 1,
        },
    })

    return table(height="100%", overflow_y="scroll", padding=16, padding_top=0)[
        tr()[
            th(align_items="flex_end")[text("ts", color=SECONDARY_COLOR)],
            th()[text("Pattern", color=SECONDARY_COLOR)],
            # th()[text("Sounds", color=SECONDARY_COLOR)],
            th(align_items="flex_end")[text("Power", color=SECONDARY_COLOR)],
            th(align_items="flex_end")[text("> Pow", color=SECONDARY_COLOR)] if show_thresholds else None,
            th(align_items="flex_end")[text("Prob.", color=SECONDARY_COLOR)],
            th(align_items="flex_end")[text("> Prob.", color=SECONDARY_COLOR)] if show_thresholds else None,
            *[
                th(align_items="flex_end", justify_content="center")[
                    text("F0", color=SECONDARY_COLOR),
                ],
                th(align_items="flex_end", justify_content="center")[
                    text("F1", color=SECONDARY_COLOR),
                ],
                th(align_items="flex_end", justify_content="center")[
                    text("F2", color=SECONDARY_COLOR),
                ],
            ] if show_formants else [],
            th(align_items="center")[text("Status", color=SECONDARY_COLOR)],
            th(align_items="flex_start")[div(flex_direction="row", gap=2)[
                text("Power", color=SECONDARY_COLOR),
                icon("multiply", size=11, stroke_width=3, color=SECONDARY_COLOR),
                text("Prob.", color=SECONDARY_COLOR),
            ]],
        ],
        *[
            tr()[
                td()[number(frame.format(frame.ts, 3))],
                td(align_items="flex_start")[div(gap=8, min_width=60)[
                    text(frame.winner["name"])
                ]],
                # td(align_items="flex_start")[div(gap=8)[
                #     *[text(", ".join(p["sounds"])) for p in frame.patterns]
                # ]],
                td(align_items="flex_end")[number(frame.format(frame.power, 2))],
                td(align_items="flex_end")[
                    number(get_pattern_threshold_value(frame.winner["name"], ">power"))
                ] if show_thresholds else None,
                td(align_items="flex_end")[number(frame.format(frame.winner["probability"], 4))],
                td(align_items="flex_end")[
                    number(get_pattern_threshold_value(frame.winner["name"], ">probability"))
                ] if show_thresholds else None,
                *[
                    td(align_items="flex_end", justify_content="center")[
                        number(str(round(frame.f0))),
                    ],
                    td(align_items="flex_end", justify_content="center")[
                        number(str(round(frame.f1))),
                    ],
                    td(align_items="flex_end", justify_content="center")[
                        number(str(round(frame.f2))),
                    ],
                ] if show_formants else [],
                td(align_items="center")[div(gap=8, align_items="center")[
                    status_cell(frame.winner["status"], frame.winner["graceperiod"])
                ]],
                td(align_items="flex_start", justify_content="center")[
                    power_ratio_bar(
                        frame.power,
                        frame.patterns,
                        frame.winner_grace_power_threshold if frame.grace_detected else \
                            frame.winner_power_threshold if frame.detected else None
                    )
                ],
            ] for frame in detection_current_log_frames
        ],
    ]

def page_detection_log():
    div, component, text, state, button = actions.user.ui_elements(
        ["div", "component", "text", "state", "button"]
    )
    effect = actions.user.ui_elements("effect")
    detection_log_history = state.get("detection_log_history", [])
    current_log_id, set_current_log_id = state.use("detection_current_log_id", None)

    def on_mount(e):
        if not detection_log_history:
            populate_detection_log_state()

    effect(on_mount, [])

    return div(background_color=BG_DARKEST, flex_direction="row", height=750)[
        div(flex_direction="column", background_color=BG_GRAY, height=750, border_right=1, border_color=BORDER_COLOR, overflow_y="scroll")[
            subtitle("Detection Log History"),
            *[button(
                margin=1,
                margin_left=8,
                margin_right=8,
                padding=9,
                border_radius=4,
                background_color=ACTIVE_COLOR if log_id == current_log_id else BG_GRAY,
                on_click=lambda e, log_id=log_id: (
                    set_current_log_id(log_id),
                    set_detection_log_state_by_id(log_id),
                ),
            )[
                number(log_id)
            ] for log_id in detection_log_history],
        ],
        div(flex_direction="column", gap=16, flex=1)[
            div(position="relative", flex=1)[
                div(background_color=BG_DARK, border_color=BORDER_COLOR, border_bottom=1)[
                    div(flex_direction="row", padding=8, justify_content="space_between", align_items="center")[
                        text("Detection Log", font_size=16),
                        component(table_controls),
                    ],
                ],
                div(position="relative", flex=1)[
                    component(table_log),
                ],
                div(
                    position="absolute",
                    bottom=0,
                    right=0,
                    flex_direction="row",
                    justify_content="flex_end",
                    background_color=BG_DARK,
                )[
                    legend(),
                ],
            ],
        ],
    ]