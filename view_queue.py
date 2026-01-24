import os
import json
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QListWidget, QListWidgetItem, 
                             QMessageBox, QFileDialog, QFrame, QLineEdit)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QPixmap, QColor, QPainter

from config import COLORS
from install_manager import InstallationDialog
from view_installer import HoverButton, AppTableWidget, InstallationOptionsDialog 

# --- TABULKOVÝ ŘÁDEK FRONTY ---
class QueueTableWidget(AppTableWidget):
    def __init__(self, data, parent_controller, queue_page_ref, cached_icon=None):
        super().__init__(data, parent_controller, queue_page_ref)
        if cached_icon:
            self.icon_lbl.setPixmap(cached_icon.scaled(24, 24, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            self.icon_lbl.setText("")

    def toggle_queue(self, state):
        pass

# --- HLAVNÍ STRÁNKA FRONTY ---
class QueuePage(QWidget):
    def __init__(self):
        super().__init__()
        self.queue_data = {} 
        self.installer_page_ref = None
        self.installation_options = {}

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # === A. HORNÍ LIŠTA ===
        top_bar = QWidget()
        top_bar.setStyleSheet(f"background-color: {COLORS['bg_main']}; border-bottom: 1px solid {COLORS['border']};")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(20, 15, 20, 15)
        top_layout.setSpacing(10)

        lbl_title = QLabel("Instalační fronta")
        lbl_title.setStyleSheet("font-size: 14pt; font-weight: bold; color: white; border: none;")
        top_layout.addWidget(lbl_title)
        top_layout.addSpacing(20)

        self.search_container = QFrame()
        self.search_container.setFixedWidth(700)
        self.search_container.setFixedHeight(38)
        self.search_container.setStyleSheet(f"QFrame {{ background-color: {COLORS['input_bg']}; border: 1px solid {COLORS['border']}; border-radius: 6px; }} QFrame:focus-within {{ border: 1px solid {COLORS['accent']}; }}")
        
        search_cont_layout = QHBoxLayout(self.search_container)
        search_cont_layout.setContentsMargins(10, 0, 5, 0)
        search_cont_layout.setSpacing(0)

        self.local_search_input = QLineEdit()
        self.local_search_input.setPlaceholderText("Hledat v seznamu fronty...")
        self.local_search_input.setStyleSheet("border: none; background: transparent; color: white; font-size: 10pt;")
        self.local_search_input.textChanged.connect(self.filter_queue)
        
        self.btn_search_icon = HoverButton("", "images/magnifying-glass-thin.png", "fg")
        self.btn_search_icon.setFixedSize(32, 32)
        self.btn_search_icon.setIconSize(QSize(18, 18))
        self.btn_search_icon.setStyleSheet("background: transparent; border: none; padding: 0;")

        search_cont_layout.addWidget(self.local_search_input)
        search_cont_layout.addWidget(self.btn_search_icon)
        
        top_layout.addWidget(self.search_container)
        top_layout.addStretch()
        main_layout.addWidget(top_bar)

        # === B. ACTION BAR ===
        action_bar = QWidget()
        action_bar.setStyleSheet(f"background-color: {COLORS['bg_main']};")
        action_layout = QHBoxLayout(action_bar)
        action_layout.setContentsMargins(20, 10, 20, 10)
        action_layout.setSpacing(10)

        # IDENTICKÝ SPLIT BUTTON JAKO V INSTALLERU
        split_container = QFrame()
        split_container.setFixedHeight(34)
        split_container.setStyleSheet(f"QFrame {{ background-color: {COLORS['item_bg']}; border: 1px solid {COLORS['border']}; border-radius: 6px; }} QFrame:hover {{ border-color: {COLORS['accent']}; }}")
        split_layout = QHBoxLayout(split_container)
        split_layout.setContentsMargins(0, 0, 0, 0)
        split_layout.setSpacing(0)

        self.btn_install_main = QPushButton("  Nainstalovat vybrané")
        self.btn_install_main.setIcon(QIcon("images/download-simple-thin.png"))
        self.btn_install_main.setFixedHeight(32)
        # Fixní zaoblení pouze vlevo
        self.btn_install_main.setStyleSheet(f"QPushButton {{ background: transparent; border: none; color: white; padding: 0 15px; font-weight: bold; font-size: 10pt; border-top-left-radius: 5px; border-bottom-left-radius: 5px; border-top-right-radius: 0px; border-bottom-right-radius: 0px; }} QPushButton:hover {{ background-color: {COLORS['item_hover']}; }}")
        self.btn_install_main.clicked.connect(self.run_installation)

        mid_line = QFrame()
        mid_line.setFixedWidth(1)
        mid_line.setStyleSheet(f"background-color: {COLORS['border']}; border: none;")

        self.btn_settings_quick = QPushButton()
        self.btn_settings_quick.setFixedSize(32, 32)
        self.btn_settings_quick.setIcon(self.get_colored_icon("images/gear-six-thin.png", COLORS['fg']))
        self.btn_settings_quick.setIconSize(QSize(18, 18))
        # Fixní zaoblení pouze vpravo
        self.btn_settings_quick.setStyleSheet(f"QPushButton {{ background: transparent; border: none; border-top-right-radius: 5px; border-bottom-right-radius: 5px; border-top-left-radius: 0px; border-bottom-left-radius: 0px; }} QPushButton:hover {{ background-color: {COLORS['item_hover']}; }}")
        self.btn_settings_quick.clicked.connect(self.open_options_dialog)

        split_layout.addWidget(self.btn_install_main)
        split_layout.addWidget(mid_line)
        split_layout.addWidget(self.btn_settings_quick)
        action_layout.addWidget(split_container)

        self.add_separator(action_layout)

        

        self.btn_new = HoverButton(" Nová", "images/plus-thin.png", "fg", self)
        self.btn_new.clicked.connect(self.clear_queue)
        action_layout.addWidget(self.btn_new)

        self.btn_open = HoverButton(" Otevřít", "images/folder-open-thin.png", "fg", self)
        self.btn_open.clicked.connect(self.load_from_json)
        action_layout.addWidget(self.btn_open)

        self.btn_save = HoverButton(" Uložit", "images/floppy-disk-thin.png", "fg", self)
        self.btn_save.clicked.connect(self.save_to_json)
        action_layout.addWidget(self.btn_save)

        self.add_separator(action_layout)

        self.btn_ps1 = HoverButton(" Skript", "images/terminal-window-thin.png", "fg", self)
        self.btn_ps1.clicked.connect(self.save_powershell_script)
        action_layout.addWidget(self.btn_ps1)

        self.add_separator(action_layout)

        self.btn_remove_selected = HoverButton(" Odebrat vybrané", "images/trash-thin.png", "fg", self)
        self.btn_remove_selected.clicked.connect(self.remove_selected_items)
        action_layout.addWidget(self.btn_remove_selected)

        action_layout.addStretch()

        self.btn_help = HoverButton(" Nápověda", "images/question-thin.png", "sub_text")
        self.btn_help.setIconSize(QSize(20, 20))
        self.btn_help.clicked.connect(self.show_help)
        action_layout.addWidget(self.btn_help)

        main_layout.addWidget(action_bar)

        # Hlavička (Identická s InstallerPage)
        header_widget = QWidget()
        header_widget.setStyleSheet(f"background-color: {COLORS['bg_sidebar']}; border: none; font-size: 9pt;")
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(35, 8, 35, 8)
        header_layout.setSpacing(15)

        h_headers = [("", 30), ("", 24), ("NÁZEV BALÍČKU", 0), ("ID BALÍČKU", 0), ("VERZE", 100), ("ZDROJ", 80)]
        for i, (text, width) in enumerate(h_headers):
            lbl = QLabel(text)
            lbl.setStyleSheet("font-weight: bold; color: white; border: none;")
            if width > 0: lbl.setFixedWidth(width)
            stretch = 4 if i == 2 else (3 if i == 3 else 0)
            header_layout.addWidget(lbl, stretch=stretch)
        main_layout.addWidget(header_widget)

        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(f"QListWidget {{ background-color: {COLORS['bg_main']}; border: none; outline: none; padding: 0 30px; }} QListWidget::item {{ border-bottom: 1px solid {COLORS['border']}; padding: 0px; }} QListWidget::item:hover {{ background-color: {COLORS['item_hover']}; }}")
        self.list_widget.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        main_layout.addWidget(self.list_widget)

    # --- LOGIKA ---
    def remove_selected_items(self):
        if not self.queue_data:
            QMessageBox.warning(self, "Prázdná fronta", "V seznamu nejsou žádné balíčky k odebrání.")
            return
        to_remove = [self.list_widget.itemWidget(self.list_widget.item(i)).data['id'] 
                     for i in range(self.list_widget.count()) 
                     if self.list_widget.itemWidget(self.list_widget.item(i)).chk.isChecked()]
        if not to_remove:
            QMessageBox.information(self, "Žádný výběr", "Nejdříve zaškrtněte balíčky k odebrání.")
            return
        if QMessageBox.question(self, "Smazat vybrané", f"Odebrat {len(to_remove)} balíčků?") == QMessageBox.StandardButton.Yes:
            for app_id in to_remove: self.remove_item_by_id(app_id)

    def run_installation(self):
        if not self.queue_data:
            QMessageBox.warning(self, "Prázdná fronta", "Nejdříve přidejte balíčky.")
            return
        selected = [self.list_widget.itemWidget(self.list_widget.item(i)).data 
                    for i in range(self.list_widget.count()) 
                    if self.list_widget.itemWidget(self.list_widget.item(i)).chk.isChecked()]
        if not selected:
            QMessageBox.information(self, "Žádný výběr", "Označte alespoň jeden balíček, který chcete nainstalovat.")
            return
        InstallationDialog(selected, self).exec()

    def save_to_json(self):
        if not self.queue_data:
            QMessageBox.warning(self, "Prázdná fronta", "Není co uložit. Nejdřív přidejte balíčky")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Uložit frontu", "fronta.json", "JSON (*.json)")
        if path:
            with open(path, "w", encoding="utf-8") as f: json.dump(list(self.queue_data.values()), f, indent=4, ensure_ascii=False)

    def save_powershell_script(self):
        if not self.queue_data:
            QMessageBox.warning(self, "Prázdná fronta", "Nelze vytvořit skript pro prázdnou frontu.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Vytvořit skript", "install.ps1", "PowerShell (*.ps1)")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write("# Winget Auto-Install\n")
                for app in self.queue_data.values():
                    f.write(f"winget install --id '{app['id']}' -e --accept-source-agreements --accept-package-agreements\n")

    def filter_queue(self, text):
        search_text = text.lower()
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            widget = self.list_widget.itemWidget(item)
            if isinstance(widget, QueueTableWidget):
                item.setHidden(search_text not in widget.data['name'].lower() and search_text not in widget.data['id'].lower())

    def clear_queue(self):
        if self.queue_data and QMessageBox.question(self, "Nová fronta", "Opravdu chcete vyčistit celou frontu?") == QMessageBox.StandardButton.Yes:
            self.queue_data.clear(); self.list_widget.clear()
            if self.installer_page_ref: self.installer_page_ref.refresh_checkboxes()

    def show_help(self):
        help_text = ("Nápověda k ovládání fronty:\n\n"
                     "• Checkbox: Vybere balíček pro instalaci nebo odebrání.\n"
                     "• Nainstalovat vybrané: Spustí proces instalace pro označené položky.\n"
                     "• Odebrat vybrané: Trvale odstraní označené balíčky z tohoto seznamu.\n"
                     "• Otevřít/Uložit: Správa fronty jako JSON souboru.\n"
                     "• Skript: Vygeneruje PowerShell (.ps1) soubor pro automatizaci.")
        QMessageBox.information(self, "Nápověda", help_text)

    def load_from_json(self):
        path, _ = QFileDialog.getOpenFileName(self, "Načíst frontu", "", "JSON (*.json)")
        if path:
            try:
                with open(path, "r", encoding="utf-8") as f: apps = json.load(f)
                self.queue_data.clear(); self.list_widget.clear()
                for app in apps: self.add_to_queue(app)
                if self.installer_page_ref: self.installer_page_ref.refresh_checkboxes()
            except: pass

    def add_to_queue(self, data, icon=None):
        app_id = data['id']
        if app_id in self.queue_data: return
        self.queue_data[app_id] = data
        item = QListWidgetItem(self.list_widget); item.setSizeHint(QSize(0, 50))
        item.setData(Qt.ItemDataRole.UserRole, app_id)
        widget = QueueTableWidget(data, self, self, cached_icon=icon)
        widget.chk.setChecked(True)
        self.list_widget.setItemWidget(item, widget)

    def remove_item_by_id(self, app_id):
        if app_id in self.queue_data: del self.queue_data[app_id]
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item and item.data(Qt.ItemDataRole.UserRole) == app_id:
                self.list_widget.takeItem(i); break
        if self.installer_page_ref: self.installer_page_ref.refresh_checkboxes()

    def open_options_dialog(self):
        dlg = InstallationOptionsDialog(self, self.installation_options)
        if dlg.exec(): self.installation_options = dlg.get_options()

    def get_colored_icon(self, path, color_hex):
        if not os.path.exists(path): return QIcon()
        pixmap = QPixmap(path); colored = QPixmap(pixmap.size()); colored.fill(Qt.GlobalColor.transparent)
        p = QPainter(colored); p.drawPixmap(0, 0, pixmap); p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn); p.fillRect(colored.rect(), QColor(color_hex)); p.end()
        return QIcon(colored)

    def add_separator(self, layout):
        sep = QFrame(); sep.setFrameShape(QFrame.Shape.VLine); sep.setFixedWidth(1); sep.setFixedHeight(18); sep.setStyleSheet(f"background: {COLORS['border']}; border: none;"); layout.addWidget(sep)

    def set_installer_ref(self, ref): self.installer_page_ref = ref