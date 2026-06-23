# -*- coding: utf-8 -*-
"""左侧导航栏：包含 3 个 SidebarButton（配置 / 运行 / 日志）。"""

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QLabel, QVBoxLayout, QWidget

from app.constants import (
    FONT_FAMILY, SIDEBAR_BG, SIDEBAR_WIDTH, TEXT_SECONDARY, WINDOW_RADIUS,
)
from app.widgets import SidebarButton


class Sidebar(QWidget):
    nav_clicked = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(SIDEBAR_WIDTH)
        self.setStyleSheet(f"""
            background: {SIDEBAR_BG};
            border-top-left-radius: {WINDOW_RADIUS}px;
        """)
        self.current_index = 0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 12, 0, 12)
        layout.setSpacing(2)

        self.nav_items = []

        items = [
            ("⚙️", "配置"),
            ("▶️", "运行"),
            ("📋", "日志"),
        ]

        for i, (icon, text) in enumerate(items):
            btn = SidebarButton(icon, text)
            btn.clicked.connect(lambda checked, idx=i: self._on_click(idx))
            layout.addWidget(btn)
            self.nav_items.append(btn)

        layout.addStretch()

        # 版本信息
        ver_label = QLabel("v1.0 · Win11")
        ver_label.setAlignment(Qt.AlignCenter)
        ver_label.setStyleSheet(f"""
            font-family: "{FONT_FAMILY}";
            font-size: 10px;
            color: {TEXT_SECONDARY};
            padding: 8px;
        """)
        layout.addWidget(ver_label)

        self._set_active(0)

    def _on_click(self, index):
        self._set_active(index)
        self.nav_clicked.emit(index)

    def _set_active(self, index):
        self.current_index = index
        for i, btn in enumerate(self.nav_items):
            btn.set_active(i == index)
