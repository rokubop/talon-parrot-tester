from talon import actions
import json
import os
from .colors import (
    SECONDARY_COLOR,
    ACCENT_COLOR,
    BORDER_COLOR,
    BG_DARKEST,
)

def get_version():
    manifest_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "manifest.json")
    )
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("version", "unknown")
    except Exception:
        return "unknown"

def page_about():
    div, text, table, tr, td, style, icon, link = actions.user.ui_elements(
        ["div", "text", "table", "tr", "td", "style", "icon", "link"]
    )

    style({
        "td": {
            "padding": 8,
        },
        "text": {
            "font_size": 18,
        }
    })

    return div(flex_direction="row", padding=16, gap=16, height="100%")[
        div(background_color=BG_DARKEST, flex=1, border_radius=4, padding=16, border_width=1, border_color=BORDER_COLOR)[
            table()[
                tr()[
                    td()[text("Parrot Tester version", color=SECONDARY_COLOR)],
                    td()[text(get_version())],
                ],
                tr()[
                    td()[text("Parrot Tester GitHub", color=SECONDARY_COLOR)],
                    td()[
                        link(
                            url="https://github.com/rokubop/talon-parrot-tester",
                            minimize_on_click=True,
                            flex_direction="row",
                            gap=8,
                            align_items="center"
                        )[
                            text("https://github.com/rokubop/talon-parrot-tester", color=ACCENT_COLOR),
                            icon("external_link", size=16, color=ACCENT_COLOR),
                        ],
                    ],
                ],
                tr()[
                    td()[text("Talon UI Elements", color=SECONDARY_COLOR)],
                    td()[
                        link(
                            url="https://github.com/rokubop/talon-ui-elements",
                            minimize_on_click=True,
                            flex_direction="row",
                            gap=8,
                            align_items="center"
                        )[
                            text("https://github.com/rokubop/talon-ui-elements", color=ACCENT_COLOR),
                            icon("external_link", size=16, color=ACCENT_COLOR),
                        ],
                    ],
                ],
                tr()[
                    td()[text("Parrot.py GitHub", color=SECONDARY_COLOR)],
                    td()[
                        link(
                            url="https://github.com/chaosparrot/parrot.py",
                            minimize_on_click=True,
                            flex_direction="row",
                            gap=8,
                            align_items="center"
                        )[
                            text("https://github.com/chaosparrot/parrot.py", color=ACCENT_COLOR),
                            icon("external_link", size=16, color=ACCENT_COLOR),
                        ],
                    ],
                ],
                tr()[
                    td()[text("Author", color=SECONDARY_COLOR)],
                    td()[text("Rokubop")],
                ],
            ],
        ]
    ]