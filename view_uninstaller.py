from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QListWidget, QListWidgetItem, QLineEdit, QMessageBox)
from PyQt6.QtCore import Qt, QSize
from workers import WingetListWorker, UninstallWorker

class AppItemWidget(QWidget):
    def __init__(self, name, app_id, parent_view):
        super().__init__()
        self.app_id = app_id
        self.parent_view = parent_view
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        
        info_layout = QVBoxLayout()
        name_lbl = QLabel(name)
        name_lbl.setStyleSheet("font-weight: bold; font-size: 15px;")
        id_lbl = QLabel(app_id)
        id_lbl.setStyleSheet("color: #888888; font-size: 12px;")
        info_layout.addWidget(name_lbl)
        info_layout.addWidget(id_lbl)
        
        layout.addLayout(info_layout)
        layout.addStretch()
        
        btn = QPushButton("Uninstall")
        btn.setObjectName("Danger") # Použije červený styl
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(self.on_uninstall)
        layout.addWidget(btn)

    def on_uninstall(self):
        self.parent_view.confirm_uninstall(self.app_id)

class UninstallerPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Header
        header = QHBoxLayout()
        title = QLabel("Odinstalace aplikací")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        header.addWidget(title)
        header.addStretch()
        
        self.search = QLineEdit()
        self.search.setPlaceholderText("Hledat aplikaci...")
        self.search.setFixedWidth(300)
        self.search.textChanged.connect(self.filter_items)
        header.addWidget(self.search)
        
        layout.addLayout(header)
        
        # Refresh Button
        self.refresh_btn = QPushButton("Načíst nainstalované aplikace")
        self.refresh_btn.setObjectName("Primary")
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.clicked.connect(self.load_apps)
        layout.addWidget(self.refresh_btn)
        
        # List
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("background-color: #252526; border-radius: 5px;")
        self.list_widget.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        layout.addWidget(self.list_widget)
        
        # Status
        self.status = QLabel("Připraveno.")
        self.status.setStyleSheet("color: #888888;")
        layout.addWidget(self.status)

        self.all_items = [] # Cache pro filtrování

    def load_apps(self):
        self.list_widget.clear()
        self.all_items = []
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setText("Skenuji systém...")
        self.status.setText("Probíhá skenování aplikací (Winget)...")
        
        self.worker = WingetListWorker()
        self.worker.finished.connect(self.on_loaded)
        self.worker.error.connect(lambda e: self.status.setText(f"Chyba: {e}"))
        self.worker.start()

    def on_loaded(self, apps):
        self.list_widget.setUpdatesEnabled(False) # Zrychlení vykreslování
        
        for app in apps:
            item = QListWidgetItem(self.list_widget)
            item.setSizeHint(QSize(0, 60))
            
            widget = AppItemWidget(app['name'], app['id'], self)
            self.list_widget.setItemWidget(item, widget)
            
            # Uložíme si data pro vyhledávání
            self.all_items.append((item, widget, app['name'].lower()))
            
        self.list_widget.setUpdatesEnabled(True)
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText("Načíst nainstalované aplikace")
        self.status.setText(f"Nalezeno {len(apps)} aplikací.")

    def filter_items(self, text):
        text = text.lower()
        for item, widget, name in self.all_items:
            item.setHidden(text not in name)

    def confirm_uninstall(self, app_id):
        reply = QMessageBox.question(self, "Potvrzení", f"Odinstalovat {app_id}?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.start_uninstall(app_id)

    def start_uninstall(self, app_id):
        self.status.setText(f"Odinstalovávám {app_id}...")
        self.u_worker = UninstallWorker(app_id)
        self.u_worker.log.connect(lambda s: self.status.setText(s))
        self.u_worker.finished.connect(lambda: [self.status.setText("Hotovo."), self.load_apps()])
        self.u_worker.start()