from talon import actions
from .colors import (
    BORDER_COLOR,
    ACTIVE_COLOR,
    BG_INPUT,
)
from .components import (
    pattern
)
from ..parrot_integration_wrapper import (
    get_patterns_json,
)

view_map = {
    "full": "Full",
    "medium": "Medium",
    "compact": "Compact",
}

def view_tabs():
    div, button, text, state = actions.user.ui_elements(["div", "button", "text", "state"])
    tab_state, set_tab = state.use("patterns_view", "medium")

    return div(
        flex_direction="row",
        align_items="flex_end",
        background_color=BG_INPUT,
        border_color=BORDER_COLOR,
        border_width=1,
    )[
        *[button(
            on_click=lambda e, id=tab: set_tab(id),
            padding=16,
            padding_top=10,
            padding_bottom=10,
            position="relative",
        )[
            text(view_map[tab], font_size=16, color="FFFFFF"),
            div(
                position="absolute",
                bottom=0,
                background_color=ACTIVE_COLOR,
                height=3,
                width="100%",
                border_radius=2,
            ) if tab_state == tab else None
        ] for tab in view_map.keys()]
    ]

def page_patterns():
    div, component, table, tr, td = actions.user.ui_elements(["div", "component", "table", "tr", "td"])
    text, button, state, style = actions.user.ui_elements(["text", "button", "state", "style"])
    patterns = get_patterns_json()
    pattern_items = list(patterns.items())
    view = state.get("patterns_view", "medium")
    num_patterns_horizontal = 6 if view == "compact" else 3
    pattern_groups = [pattern_items[i:i + num_patterns_horizontal] for i in range(0, len(pattern_items), num_patterns_horizontal)]

    style({
        "td": {
            "padding": 8,
        },
    })

    return div(flex_direction="column", padding=8, height="100%", align_items="center")[
        view_tabs(),
        div(height="100%", overflow_y="scroll", width="100%")[
            table()[
                *[tr()[
                    *[td()[
                        div(background_color="#36393E", border_radius=4, border_width=1, border_color=BORDER_COLOR)[
                            component(pattern, props={
                                "name": name,
                                "highlight_when_active": True,
                                "view": view,
                            }),
                        ]
                    ] for name, _ in group]
                ] for group in pattern_groups]
            ]
        ],
    ]