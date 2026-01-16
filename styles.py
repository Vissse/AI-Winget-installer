from config import COLORS

def get_stylesheet():
    return f"""
    QMainWindow {{
        background-color: {COLORS['bg_main']};
    }}
    QWidget {{
        color: {COLORS['fg']};
        font-family: 'Segoe UI', sans-serif;
        font-size: 14px;
    }}
    /* Sidebar */
    QListWidget#Sidebar {{
        background-color: {COLORS['bg_sidebar']};
        border: none;
        outline: none;
        font-size: 16px;
    }}
    QListWidget#Sidebar::item {{
        height: 50px;
        padding-left: 10px;
        border-left: 3px solid transparent;
    }}
    QListWidget#Sidebar::item:selected {{
        background-color: {COLORS['item_hover']};
        border-left: 3px solid {COLORS['accent']};
        color: white;
    }}
    QListWidget#Sidebar::item:hover {{
        background-color: {COLORS['item_hover']};
    }}
    
    /* Buttons */
    QPushButton {{
        background-color: {COLORS['item_bg']};
        border: 1px solid {COLORS['border']};
        border-radius: 5px;
        padding: 6px 12px;
    }}
    QPushButton:hover {{
        background-color: {COLORS['item_hover']};
        border-color: {COLORS['accent']};
    }}
    QPushButton#Primary {{
        background-color: {COLORS['accent']};
        border: none;
        font-weight: bold;
    }}
    QPushButton#Primary:hover {{
        background-color: {COLORS['accent_hover']};
    }}
    QPushButton#Danger {{
        background-color: {COLORS['danger']};
        border: none;
        font-weight: bold;
    }}
    
    /* Inputs */
    QLineEdit {{
        background-color: {COLORS['item_bg']};
        border: 1px solid {COLORS['border']};
        border-radius: 4px;
        padding: 5px;
        color: white;
    }}
    QLineEdit:focus {{
        border: 1px solid {COLORS['accent']};
    }}

    /* Scrollbar */
    QScrollBar:vertical {{
        border: none;
        background: {COLORS['bg_main']};
        width: 10px;
        margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: #424242;
        min-height: 20px;
        border-radius: 5px;
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    """