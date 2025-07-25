LIGHT_THEME = {
    'bg': '#f5f5f5',
    'fg': '#222',
    'accent': '#1976d2',
    'button_bg': '#fff',
    'button_fg': '#1976d2',
    'entry_bg': '#fff',
    'entry_fg': '#222',
}
DARK_THEME = {
    'bg': '#23272e',
    'fg': '#fff',
    'accent': '#90caf9',
    'button_bg': '#2c313c',
    'button_fg': '#90caf9',
    'entry_bg': '#23272e',
    'entry_fg': '#fff',
}

current_theme = LIGHT_THEME

def set_theme(mode):
    global current_theme
    if mode == 'dark':
        current_theme = DARK_THEME
    else:
        current_theme = LIGHT_THEME

def get_theme():
    return current_theme 