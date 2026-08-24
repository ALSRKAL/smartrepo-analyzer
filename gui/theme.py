"""Theme definitions (light/dark) for the SmartRepo GUI.

تعريفات السِمات (نهاري/ليلي) لواجهة SmartRepo.
"""

LIGHT_THEME = {
    "bg": "#f5f6fa",
    "fg": "#1e293b",
    "accent": "#1976d2",
    "button_bg": "#ffffff",
    "button_fg": "#1976d2",
    "entry_bg": "#ffffff",
    "entry_fg": "#1e293b",
    "log_bg": "#ffffff",
    "log_fg": "#334155",
}

DARK_THEME = {
    "bg": "#1e222a",
    "fg": "#e2e8f0",
    "accent": "#90caf9",
    "button_bg": "#2c313c",
    "button_fg": "#90caf9",
    "entry_bg": "#262b35",
    "entry_fg": "#e2e8f0",
    "log_bg": "#16181d",
    "log_fg": "#cbd5e1",
}

current_theme = LIGHT_THEME


def set_theme(mode):
    global current_theme
    current_theme = DARK_THEME if mode == "dark" else LIGHT_THEME


def get_theme():
    return current_theme
