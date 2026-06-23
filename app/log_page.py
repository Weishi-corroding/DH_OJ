# -*- coding: utf-8 -*-
"""日志页面：黑底彩色日志显示 + 清空按钮。"""

import time

from PyQt5.QtGui import QColor, QTextCharFormat, QTextCursor
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QPlainTextEdit, QVBoxLayout, QWidget

from app.constants import (
    ACCENT_BLUE, ERROR_RED, FONT_FAMILY, LOG_BG, SUCCESS_GREEN,
    TEXT_PRIMARY, WARNING_ORANGE,
)
from app.widgets import Win11Button


class LogPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        # 标题栏
        header = QHBoxLayout()
        title = QLabel("运行日志")
        title.setStyleSheet(f"""
            font-family: "{FONT_FAMILY}";
            font-size: 18px;
            font-weight: 600;
            color: {TEXT_PRIMARY};
        """)
        header.addWidget(title)
        header.addStretch()

        self.btn_clear_log = Win11Button("清空日志", primary=False, small=True)
        self.btn_clear_log.setFixedWidth(100)
        self.btn_clear_log.clicked.connect(self.clear_log)
        header.addWidget(self.btn_clear_log)

        layout.addLayout(header)

        # 日志显示区域
        self.log_output = QPlainTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setStyleSheet(f"""
            QPlainTextEdit {{
                font-family: "Cascadia Code", "Consolas", "Courier New";
                font-size: 11px;
                background: {LOG_BG};
                color: #D4D4D4;
                border: none;
                border-radius: 6px;
                padding: 12px;
                selection-background-color: {ACCENT_BLUE};
            }}
            QScrollBar:vertical {{
                width: 8px;
                background: #2A2A2A;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background: #555555;
                border-radius: 4px;
                min-height: 30px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
        """)
        layout.addWidget(self.log_output, 1)

    def append_log(self, text, level="info"):
        cursor = self.log_output.textCursor()
        cursor.movePosition(QTextCursor.End)

        fmt = QTextCharFormat()
        if level == "error":
            fmt.setForeground(QColor(ERROR_RED))
        elif level == "success":
            fmt.setForeground(QColor(SUCCESS_GREEN))
        elif level == "warning":
            fmt.setForeground(QColor(WARNING_ORANGE))
        elif level == "system":
            fmt.setForeground(QColor(ACCENT_BLUE))
        else:
            fmt.setForeground(QColor("#D4D4D4"))

        cursor.insertText(f"[{time.strftime('%H:%M:%S')}] {text}\n", fmt)
        self.log_output.setTextCursor(cursor)
        self.log_output.ensureCursorVisible()

    def clear_log(self):
        self.log_output.clear()
