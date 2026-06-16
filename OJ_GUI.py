# -*- coding: utf-8 -*-
"""
OJ Helper GUI — 仿 Windows 11 风格的 PyQt5 桌面应用
使用 Selenium 自动化 + DeepSeek API 解决东华大学 OJ 题目
"""

import sys
import os
import re
import time
import json

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QFrame,
    QStackedWidget, QPlainTextEdit, QScrollArea,
    QGraphicsDropShadowEffect
)
from PyQt5.QtCore import (
    Qt, QRect, QRectF, pyqtSignal,
    QPoint, QThread
)
from PyQt5.QtGui import (
    QColor, QFont, QPainter, QPen,
    QTextCursor, QTextCharFormat, QPainterPath
)

# ============================================================
# 导入 Selenium 与 AI 依赖
# ============================================================
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from openai import OpenAI
import requests

# ============================================================
# 全局配置
# ============================================================
FONT_FAMILY = "Microsoft YaHei UI"
ICON_COLOR = "#1A1A1A"
ACCENT_BLUE = "#005FB8"
ACCENT_BLUE_HOVER = "#004C93"
TITLE_BG = "#F3F3F3"
WINDOW_BG = "#FAFAFA"
SIDEBAR_BG = "#F3F3F3"
BORDER_COLOR = "#E5E5E5"
TEXT_PRIMARY = "#1A1A1A"
TEXT_SECONDARY = "#666666"
TEXT_PLACEHOLDER = "#999999"
INPUT_BG = "#FFFFFF"
INPUT_BORDER = "#D1D1D1"
INPUT_BORDER_FOCUS = "#005FB8"
BTN_HOVER_BG = "#E5E5E5"
BTN_PRIMARY_BG = "#005FB8"
BTN_PRIMARY_HOVER = "#004C93"
SUCCESS_GREEN = "#0FA958"
ERROR_RED = "#E81123"
WARNING_ORANGE = "#FF8C00"
LOG_BG = "#1E1E1E"
SIDEBAR_WIDTH = 200
TITLEBAR_HEIGHT = 36
WINDOW_RADIUS = 8
SHADOW_MARGIN = 10


# ============================================================
# 工具函数 —— 用 QPainter 绘制窗口按钮图标
# ============================================================
def draw_minimize_icon(painter, rect, color):
    painter.setPen(QPen(QColor(color), 1.5))
    cx, cy = rect.center().x(), rect.center().y()
    # 短横线居中：16px 宽
    painter.drawLine(cx - 8, cy, cx + 8, cy)


def draw_maximize_icon(painter, rect, color, is_maximized=False):
    painter.setPen(QPen(QColor(color), 1.5))
    cx, cy = rect.center().x(), rect.center().y()
    if not is_maximized:
        # 最大化图标: 12×12 □ 居中
        painter.drawRect(cx - 6, cy - 6, 12, 12)
    else:
        # 还原图标: 两个 10×10 矩形错位重叠
        # 后层（偏左上）
        painter.drawRect(cx - 6, cy - 4, 10, 10)
        # 前层（偏右下）
        painter.drawRect(cx - 2, cy - 8, 10, 10)


def draw_close_icon(painter, rect, color):
    pen = QPen(QColor(color), 1.8)
    pen.setCapStyle(Qt.RoundCap)
    painter.setPen(pen)
    cx, cy = rect.center().x(), rect.center().y()
    offset = 6
    painter.drawLine(cx - offset, cy - offset, cx + offset, cy + offset)
    painter.drawLine(cx + offset, cy - offset, cx - offset, cy + offset)


# ============================================================
# 自定义标题栏按钮
# ============================================================
class TitleBarButton(QPushButton):
    def __init__(self, parent=None, btn_type='close'):
        super().__init__(parent)
        self.btn_type = btn_type
        self.hovered = False
        self.setFixedSize(46, TITLEBAR_HEIGHT)
        self.setCursor(Qt.ArrowCursor)
        self.setStyleSheet("background: transparent; border: none;")

    def enterEvent(self, event):
        self.hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.hovered = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect()

        if self.hovered:
            if self.btn_type == 'close':
                painter.fillRect(rect, QColor(ERROR_RED))
            else:
                painter.fillRect(rect, QColor(BTN_HOVER_BG))

        icon_color = "#FFFFFF" if (self.hovered and self.btn_type == 'close') else ICON_COLOR
        if self.btn_type == 'minimize':
            draw_minimize_icon(painter, rect, icon_color)
        elif self.btn_type == 'maximize':
            parent_win = self.window()
            is_max = parent_win.isMaximized() if parent_win else False
            draw_maximize_icon(painter, rect, icon_color, is_max)
        elif self.btn_type == 'close':
            draw_close_icon(painter, rect, icon_color)


# ============================================================
# 自定义窗口（无边框、圆角、阴影、可拖动）
# ============================================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowMinimizeButtonHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumSize(960, 680)

        self._is_maximized = False
        self._drag_pos = QPoint()
        self._resizing = False
        self._resize_dir = 0
        self._drag_start_global = QPoint()
        self._drag_start_rect = QRect()

        # 中央容器
        self.central_container = QFrame(self)
        self.central_container.setObjectName("centralContainer")
        self.central_container.setStyleSheet(f"""
            #centralContainer {{
                background: {WINDOW_BG};
                border-radius: {WINDOW_RADIUS}px;
            }}
        """)

        # 主布局
        self.main_layout = QVBoxLayout(self.central_container)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # 阴影
        self.shadow = QGraphicsDropShadowEffect(self.central_container)
        self.shadow.setBlurRadius(40)
        self.shadow.setColor(QColor(0, 0, 0, 60))
        self.shadow.setOffset(0, 4)
        self.central_container.setGraphicsEffect(self.shadow)

        # 构建界面
        self.build_title_bar()
        self.build_body()

        self.setCentralWidget(self.central_container)

    def build_title_bar(self):
        self.title_bar = QWidget()
        self.title_bar.setFixedHeight(TITLEBAR_HEIGHT)
        self.title_bar.setStyleSheet(f"background: transparent; border-top-left-radius: {WINDOW_RADIUS}px; border-top-right-radius: {WINDOW_RADIUS}px;")

        title_layout = QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(16, 0, 0, 0)
        title_layout.setSpacing(0)

        # 标题图标 + 文字
        icon_label = QLabel("⚡")
        icon_label.setStyleSheet("font-size: 14px; color: #005FB8;")
        icon_label.setFixedWidth(20)

        self.title_label = QLabel("OJ Helper")
        self.title_label.setStyleSheet(f"""
            font-family: "{FONT_FAMILY}";
            font-size: 12px;
            font-weight: 600;
            color: {TEXT_PRIMARY};
        """)

        title_layout.addWidget(icon_label)
        title_layout.addSpacing(6)
        title_layout.addWidget(self.title_label)
        title_layout.addStretch()

        # 窗口按钮
        self.btn_min = TitleBarButton(btn_type='minimize')
        self.btn_max = TitleBarButton(btn_type='maximize')
        self.btn_close = TitleBarButton(btn_type='close')

        self.btn_min.clicked.connect(self.showMinimized)
        self.btn_max.clicked.connect(self.toggle_maximize)
        self.btn_close.clicked.connect(self.close)

        self.btn_max.enterEvent = self._on_max_enter
        self.btn_max.leaveEvent = self._on_max_leave

        title_layout.addWidget(self.btn_min)
        title_layout.addWidget(self.btn_max)
        title_layout.addWidget(self.btn_close)

        self.main_layout.addWidget(self.title_bar)

    def _on_max_enter(self, event):
        self.btn_max.hovered = True
        self.btn_max.update()
        TitleBarButton.enterEvent(self.btn_max, event)

    def _on_max_leave(self, event):
        self.btn_max.hovered = False
        self.btn_max.update()
        TitleBarButton.leaveEvent(self.btn_max, event)

    def toggle_maximize(self):
        if self._is_maximized:
            self.showNormal()
            self._is_maximized = False
        else:
            self.showMaximized()
            self._is_maximized = True
        self.btn_max.update()

    def changeEvent(self, event):
        if event.type() == event.WindowStateChange:
            self._is_maximized = self.isMaximized()
            self.btn_max.update()
        super().changeEvent(event)

    def build_body(self):
        self.body_widget = QWidget()
        self.body_widget.setStyleSheet(f"background: {WINDOW_BG};")
        body_layout = QHBoxLayout(self.body_widget)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        # 侧边栏
        self.sidebar = Sidebar(self)
        body_layout.addWidget(self.sidebar)

        # 分割线
        divider = QFrame()
        divider.setFixedWidth(1)
        divider.setStyleSheet(f"background: {BORDER_COLOR};")
        body_layout.addWidget(divider)

        # 内容区
        self.content_stack = QStackedWidget()
        self.content_stack.setStyleSheet(f"background: {WINDOW_BG};")

        self.page_config = ConfigPage(self)
        self.page_run = RunPage(self)
        self.page_logs = LogPage(self)

        self.content_stack.addWidget(self.page_config)
        self.content_stack.addWidget(self.page_run)
        self.content_stack.addWidget(self.page_logs)

        body_layout.addWidget(self.content_stack, 1)

        self.main_layout.addWidget(self.body_widget, 1)

        # 连接侧边栏导航
        self.sidebar.nav_clicked.connect(self.on_nav_clicked)

    def on_nav_clicked(self, index):
        self.content_stack.setCurrentIndex(index)

    # ---- 窗口拖动与缩放 ----
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            pos = event.pos()
            # 检查是否在标题栏区域
            title_bar_rect = self.title_bar.geometry()
            # 排除按钮区域
            btn_rect = self.btn_min.geometry().united(self.btn_max.geometry()).united(self.btn_close.geometry())
            if title_bar_rect.contains(pos) and not btn_rect.contains(self.title_bar.mapFrom(self, pos)):
                self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
                event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and not self._drag_pos.isNull():
            if not self._is_maximized:
                self.move(event.globalPos() - self._drag_pos)
            else:
                # 从最大化状态拖拽时先还原
                ratio = event.pos().x() / self.width()
                self.showNormal()
                self._is_maximized = False
                self.btn_max.update()
                new_x = event.globalPos().x() - int(self.width() * ratio)
                self.move(new_x, event.globalPos().y() - 20)
                self._drag_pos = QPoint(int(self.width() * ratio), 20)
            event.accept()

    def mouseDoubleClickEvent(self, event):
        if self.title_bar.geometry().contains(event.pos()):
            self.toggle_maximize()

    def resizeEvent(self, event):
        self.central_container.setGeometry(SHADOW_MARGIN, SHADOW_MARGIN,
                                           self.width() - 2 * SHADOW_MARGIN,
                                           self.height() - 2 * SHADOW_MARGIN)
        super().resizeEvent(event)

    def closeEvent(self, event):
        """关闭窗口时确保清理 worker 线程和浏览器驱动"""
        run_page = self.page_run if hasattr(self, 'page_run') else None
        if run_page and run_page.worker and run_page.worker.isRunning():
            run_page.worker.stop()
            if not run_page.worker.wait(5000):
                run_page.worker.terminate()
                run_page.worker.wait()
        super().closeEvent(event)


# ============================================================
# 侧边栏
# ============================================================
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


class SidebarButton(QPushButton):
    def __init__(self, icon, text, parent=None):
        super().__init__(parent)
        self._active = False
        self._hovered = False
        self.icon_text = icon
        self.btn_text = text
        self.setFixedHeight(44)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("background: transparent; border: none; text-align: left;")

    def set_active(self, active):
        self._active = active
        self.update()

    def enterEvent(self, event):
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect()

        # 背景
        bg_color = None
        if self._active:
            bg_color = QColor(0, 95, 184, 20)
        elif self._hovered:
            bg_color = QColor(0, 0, 0, 8)

        if bg_color:
            path = QPainterPath()
            path.addRoundedRect(QRectF(rect.adjusted(8, 2, -8, -2)), 6, 6)
            painter.fillPath(path, bg_color)

        # 左侧指示条
        if self._active:
            painter.fillRect(QRect(0, 8, 3, rect.height() - 16), QColor(ACCENT_BLUE))

        # 图标
        icon_rect = QRect(20, 0, 24, rect.height())
        painter.setPen(QColor(TEXT_PRIMARY))
        icon_font = QFont("Segoe UI Emoji", 12)
        painter.setFont(icon_font)
        painter.drawText(icon_rect, Qt.AlignCenter, self.icon_text)

        # 文字
        text_rect = QRect(48, 0, rect.width() - 56, rect.height())
        text_font = QFont(FONT_FAMILY, 10)
        text_font.setWeight(QFont.Medium if self._active else QFont.Normal)
        painter.setFont(text_font)
        painter.setPen(QColor(TEXT_PRIMARY))
        painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, self.btn_text)


# ============================================================
# 内容页面 - 配置
# ============================================================
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "oj_config.json")


class ConfigPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(0)

        # 标题
        title = QLabel("设置")
        title.setStyleSheet(f"""
            font-family: "{FONT_FAMILY}";
            font-size: 20px;
            font-weight: 600;
            color: {TEXT_PRIMARY};
        """)
        layout.addWidget(title)

        subtitle = QLabel("配置 OJ 账号与 AI 参数")
        subtitle.setStyleSheet(f"""
            font-family: "{FONT_FAMILY}";
            font-size: 11px;
            color: {TEXT_SECONDARY};
            margin-bottom: 20px;
        """)
        layout.addWidget(subtitle)

        # 表单区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(f"""
            QScrollArea {{ background: transparent; border: none; }}
            QScrollBar:vertical {{ width: 6px; background: transparent; }}
            QScrollBar::handle:vertical {{ background: #C0C0C0; border-radius: 3px; min-height: 30px; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        """)

        form_widget = QWidget()
        form_widget.setStyleSheet("background: transparent;")
        form_layout = QVBoxLayout(form_widget)
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setSpacing(16)

        # ====== OJ 配置 ======
        section1 = QLabel("OJ 平台")
        section1.setStyleSheet(f"""
            font-family: "{FONT_FAMILY}";
            font-size: 12px;
            font-weight: 600;
            color: {ACCENT_BLUE};
            margin-top: 8px;
        """)
        form_layout.addWidget(section1)

        self.input_oj_url = Win11LineEdit("OJ 地址", "http://oj.dhu.edu.cn")
        self.input_username = Win11LineEdit("用户名", "weishi_corroding@163.com")
        self.input_password = Win11LineEdit("密码", "Dh_411411", is_password=True)

        form_layout.addWidget(self.input_oj_url)
        form_layout.addWidget(self.input_username)
        form_layout.addWidget(self.input_password)

        # ====== AI 配置 ======
        section2 = QLabel("AI 接口")
        section2.setStyleSheet(f"""
            font-family: "{FONT_FAMILY}";
            font-size: 12px;
            font-weight: 600;
            color: {ACCENT_BLUE};
            margin-top: 16px;
        """)
        form_layout.addWidget(section2)

        self.input_api_key = Win11LineEdit("API Key", "sk-e00efab0672a406e9a1bf9b865145064")
        self.input_api_url = Win11LineEdit("API 地址", "https://api.deepseek.com")
        self.input_model = Win11LineEdit("模型", "deepseek-chat")

        form_layout.addWidget(self.input_api_key)
        form_layout.addWidget(self.input_api_url)
        form_layout.addWidget(self.input_model)

        form_layout.addStretch()
        scroll.setWidget(form_widget)
        layout.addWidget(scroll, 1)

        # ====== 底部按钮栏 ======
        btn_bar = QHBoxLayout()
        btn_bar.setContentsMargins(0, 12, 0, 0)
        btn_bar.addStretch()

        self.btn_save = Win11Button("💾 保存配置", primary=True, small=False)
        self.btn_save.setFixedWidth(140)
        self.btn_save.clicked.connect(self.save_config)
        btn_bar.addWidget(self.btn_save)

        layout.addLayout(btn_bar)

        # 启动时加载已有配置
        self.load_config()

    def get_config(self):
        return {
            "oj_url": self.input_oj_url.text(),
            "username": self.input_username.text(),
            "password": self.input_password.text(),
            "api_key": self.input_api_key.text(),
            "api_url": self.input_api_url.text(),
            "model": self.input_model.text(),
        }

    def set_config(self, cfg):
        """用字典填充各输入框"""
        self.input_oj_url.setText(cfg.get("oj_url", ""))
        self.input_username.setText(cfg.get("username", ""))
        self.input_password.setText(cfg.get("password", ""))
        self.input_api_key.setText(cfg.get("api_key", ""))
        self.input_api_url.setText(cfg.get("api_url", ""))
        self.input_model.setText(cfg.get("model", ""))

    def load_config(self):
        """从 JSON 文件读取配置"""
        if not os.path.exists(CONFIG_FILE):
            return
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            self.set_config(cfg)
        except Exception as e:
            print(f"加载配置文件失败: {e}")

    def save_config(self):
        """将当前配置写入 JSON 文件"""
        try:
            cfg = self.get_config()
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
            # 显示成功提示（通过主窗口的日志系统或状态提示）
            main_win = self.window()
            if hasattr(main_win, 'page_logs'):
                main_win.page_logs.append_log("配置已保存", "success")
                main_win.page_logs.append_log(f"配置文件: {CONFIG_FILE}", "info")
        except Exception as e:
            main_win = self.window()
            if hasattr(main_win, 'page_logs'):
                main_win.page_logs.append_log(f"保存配置失败: {e}", "error")


# ============================================================
# Win11 风格输入框
# ============================================================
class Win11LineEdit(QWidget):
    def __init__(self, label, default_text="", is_password=False, parent=None):
        super().__init__(parent)
        self.label_text = label
        self._focused = False
        self.setFixedHeight(60)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(4)

        # 标签
        self.label = QLabel(label)
        self.label.setStyleSheet(f"""
            font-family: "{FONT_FAMILY}";
            font-size: 10px;
            font-weight: 500;
            color: {TEXT_SECONDARY};
            padding-left: 2px;
        """)
        layout.addWidget(self.label)

        # 输入框
        self.edit = QLineEdit()
        self.edit.setText(default_text)
        if is_password:
            self.edit.setEchoMode(QLineEdit.Password)

        self.edit.setFixedHeight(34)
        self.edit.setStyleSheet(f"""
            QLineEdit {{
                font-family: "{FONT_FAMILY}";
                font-size: 11px;
                color: {TEXT_PRIMARY};
                background: {INPUT_BG};
                border: 1px solid {INPUT_BORDER};
                border-radius: 4px;
                padding: 4px 10px;
                selection-background-color: {ACCENT_BLUE};
                selection-color: white;
            }}
            QLineEdit:focus {{
                border: 1.5px solid {INPUT_BORDER_FOCUS};
                background: {INPUT_BG};
            }}
        """)
        self.edit.textChanged.connect(self.on_text_changed)
        layout.addWidget(self.edit)

        # 底部提示线（聚焦时变色）
        self.focus_line = QFrame()
        self.focus_line.setFixedHeight(2)
        self.focus_line.setStyleSheet(f"background: transparent; border-radius: 1px;")
        layout.addWidget(self.focus_line)

        self.edit.installEventFilter(self)

    def on_text_changed(self, text):
        pass

    def eventFilter(self, obj, event):
        if obj == self.edit:
            if event.type() == event.FocusIn:
                self._focused = True
                self.focus_line.setStyleSheet(f"background: {ACCENT_BLUE}; border-radius: 1px;")
                self.label.setStyleSheet(f"""
                    font-family: "{FONT_FAMILY}";
                    font-size: 10px;
                    font-weight: 500;
                    color: {ACCENT_BLUE};
                    padding-left: 2px;
                """)
            elif event.type() == event.FocusOut:
                self._focused = False
                self.focus_line.setStyleSheet("background: transparent; border-radius: 1px;")
                self.label.setStyleSheet(f"""
                    font-family: "{FONT_FAMILY}";
                    font-size: 10px;
                    font-weight: 500;
                    color: {TEXT_SECONDARY};
                    padding-left: 2px;
                """)
        return super().eventFilter(obj, event)

    def text(self):
        return self.edit.text()

    def setText(self, text):
        self.edit.setText(text)


# ============================================================
# Win11 风格按钮
# ============================================================
class Win11Button(QPushButton):
    def __init__(self, text, primary=True, small=False, parent=None):
        super().__init__(text, parent)
        self._primary = primary
        self._hovered = False
        self._pressed = False

        self.setCursor(Qt.PointingHandCursor)

        if small:
            self.setFixedHeight(30)
            font_size = 10
        else:
            self.setFixedHeight(36)
            font_size = 11

        self.setStyleSheet(f"""
            QPushButton {{
                font-family: "{FONT_FAMILY}";
                font-size: {font_size}px;
                font-weight: 500;
                border: none;
                border-radius: 4px;
                padding: 0 20px;
                background: {BTN_PRIMARY_BG if primary else "transparent"};
                color: {"#FFFFFF" if primary else TEXT_PRIMARY};
            }}
            QPushButton:hover {{
                background: {BTN_PRIMARY_HOVER if primary else BTN_HOVER_BG};
            }}
            QPushButton:pressed {{
                background: {BTN_PRIMARY_HOVER if primary else "#D0D0D0"};
            }}
            QPushButton:disabled {{
                background: {"#C0C0C0" if primary else "transparent"};
                color: {"#FFFFFF" if primary else TEXT_PLACEHOLDER};
            }}
        """)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect()

        bg = QColor(BTN_PRIMARY_BG) if self._primary else QColor(0, 0, 0, 0)
        if self._hovered:
            bg = QColor(BTN_PRIMARY_HOVER) if self._primary else QColor(0, 0, 0, 20)
        if not self.isEnabled():
            bg = QColor(192, 192, 192) if self._primary else QColor(0, 0, 0, 0)

        path = QPainterPath()
        path.addRoundedRect(QRectF(rect), 4, 4)
        painter.fillPath(path, bg)

        if not self._primary:
            border_path = QPainterPath()
            r = QRectF(rect)
            border_path.addRoundedRect(r.adjusted(0.5, 0.5, -0.5, -0.5), 4, 4)
            painter.setPen(QPen(QColor(BORDER_COLOR), 1))
            painter.drawPath(border_path)

        text_color = QColor("#FFFFFF") if (self._primary or not self.isEnabled()) else QColor(TEXT_PRIMARY) if self.isEnabled() else QColor(TEXT_PLACEHOLDER)
        painter.setPen(text_color)
        font = QFont(FONT_FAMILY, 11 if self.height() > 32 else 10)
        font.setWeight(QFont.Medium)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignCenter, self.text())

    def enterEvent(self, event):
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self._pressed = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        self._pressed = True
        self.update()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self._pressed = False
        self.update()
        super().mouseReleaseEvent(event)


# ============================================================
# 日志页面
# ============================================================
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


# ============================================================
# 运行页面
# ============================================================
class RunPage(QWidget):
    log_signal = pyqtSignal(str, str)
    status_signal = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker = None
        self.running = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(0)

        # 标题
        title = QLabel("运行")
        title.setStyleSheet(f"""
            font-family: "{FONT_FAMILY}";
            font-size: 20px;
            font-weight: 600;
            color: {TEXT_PRIMARY};
        """)
        layout.addWidget(title)

        subtitle = QLabel("一键启动 OJ 自动答题流程")
        subtitle.setStyleSheet(f"""
            font-family: "{FONT_FAMILY}";
            font-size: 11px;
            color: {TEXT_SECONDARY};
            margin-bottom: 24px;
        """)
        layout.addWidget(subtitle)

        # 状态卡片
        self.status_card = QFrame()
        self.status_card.setStyleSheet(f"""
            background: #F0F6FF;
            border: 1px solid #D6E8FF;
            border-radius: 8px;
            padding: 16px;
        """)
        status_layout = QHBoxLayout(self.status_card)
        status_layout.setContentsMargins(16, 12, 16, 12)

        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet(f"color: {TEXT_PLACEHOLDER}; font-size: 16px;")
        status_layout.addWidget(self.status_dot)

        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet(f"""
            font-family: "{FONT_FAMILY}";
            font-size: 12px;
            font-weight: 500;
            color: {TEXT_SECONDARY};
        """)
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()

        layout.addWidget(self.status_card)
        layout.addSpacing(20)

        # 控制按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        self.btn_toggle = Win11Button("▶ 开始运行", primary=True)
        self.btn_toggle.setFixedWidth(140)
        self.btn_toggle.clicked.connect(self.toggle_oj)

        btn_layout.addWidget(self.btn_toggle)
        btn_layout.addStretch()

        layout.addLayout(btn_layout)
        layout.addSpacing(16)

        # 延迟提交设置
        delay_row = QHBoxLayout()
        delay_row.setSpacing(8)
        delay_label = QLabel("提交延迟:")
        delay_label.setStyleSheet(f"""
            font-family: "{FONT_FAMILY}";
            font-size: 11px;
            font-weight: 500;
            color: {TEXT_PRIMARY};
        """)
        self.input_delay = QLineEdit("0")
        self.input_delay.setFixedWidth(80)
        self.input_delay.setFixedHeight(32)
        self.input_delay.setStyleSheet(f"""
            QLineEdit {{
                font-family: "{FONT_FAMILY}";
                font-size: 11px;
                color: {TEXT_PRIMARY};
                background: {INPUT_BG};
                border: 1px solid {INPUT_BORDER};
                border-radius: 4px;
                padding: 4px 8px;
            }}
            QLineEdit:focus {{
                border: 1.5px solid {INPUT_BORDER_FOCUS};
            }}
        """)
        delay_unit = QLabel("秒")
        delay_unit.setStyleSheet(f"""
            font-family: "{FONT_FAMILY}";
            font-size: 11px;
            color: {TEXT_SECONDARY};
        """)
        self.delay_hint = QLabel("（留空为立即提交）")
        self.delay_hint.setStyleSheet(f"""
            font-family: "{FONT_FAMILY}";
            font-size: 10px;
            color: {TEXT_PLACEHOLDER};
        """)
        delay_row.addWidget(delay_label)
        delay_row.addWidget(self.input_delay)
        delay_row.addWidget(delay_unit)
        delay_row.addSpacing(8)
        delay_row.addWidget(self.delay_hint)
        delay_row.addStretch()
        layout.addLayout(delay_row)
        layout.addSpacing(20)

        # 运行参数摘要
        summary_frame = QFrame()
        summary_frame.setStyleSheet(f"""
            background: {WINDOW_BG};
            border: 1px solid {BORDER_COLOR};
            border-radius: 8px;
        """)
        summary_layout = QVBoxLayout(summary_frame)
        summary_layout.setContentsMargins(16, 14, 16, 14)
        summary_layout.setSpacing(8)

        summary_title = QLabel("当前配置摘要")
        summary_title.setStyleSheet(f"""
            font-family: "{FONT_FAMILY}";
            font-size: 11px;
            font-weight: 600;
            color: {TEXT_PRIMARY};
        """)
        summary_layout.addWidget(summary_title)

        self.summary_text = QLabel("加载配置中...")
        self.summary_text.setWordWrap(True)
        self.summary_text.setStyleSheet(f"""
            font-family: "{FONT_FAMILY}";
            font-size: 10px;
            color: {TEXT_SECONDARY};
            line-height: 1.6;
        """)
        summary_layout.addWidget(self.summary_text)

        layout.addWidget(summary_frame)
        layout.addStretch()

        # 信号连接
        self.log_signal.connect(self._on_log)
        self.status_signal.connect(self._on_status)

    def showEvent(self, event):
        super().showEvent(event)
        self._update_summary()

    def _update_summary(self):
        main_win = self.window()
        if hasattr(main_win, 'page_config'):
            cfg = main_win.page_config.get_config()
            masked_key = cfg["api_key"][:8] + "****" if len(cfg["api_key"]) > 8 else "****"
            self.summary_text.setText(
                f"OJ: {cfg['oj_url']}  |  账号: {cfg['username']}\n"
                f"AI: {cfg['model']} @ {cfg['api_url']}  |  Key: {masked_key}"
            )

    def toggle_oj(self):
        if self.running:
            self.stop_oj()
        else:
            self.start_oj()

    def start_oj(self):
        if self.worker and self.worker.isRunning():
            self.log_signal.emit("已有进程在运行中", "warning")
            return

        main_win = self.window()
        cfg = main_win.page_config.get_config()
        os.environ['DEEPSEEK_API_KEY'] = cfg["api_key"]

        self.running = True
        self.btn_toggle.setText("■ 停止")
        self.btn_toggle._primary = False
        self.btn_toggle.update()
        self.status_dot.setStyleSheet(f"color: {SUCCESS_GREEN}; font-size: 16px;")
        self.status_label.setText("运行中...")
        self.status_label.setStyleSheet(f"""
            font-family: "{FONT_FAMILY}";
            font-size: 12px;
            font-weight: 500;
            color: {SUCCESS_GREEN};
        """)

        self.log_signal.emit("启动 OJ 自动化流程...", "system")
        self.log_signal.emit(f"目标 OJ: {cfg['oj_url']}", "info")
        self.log_signal.emit(f"当前用户: {cfg['username']}", "info")

        try:
            delay_seconds = int(self.input_delay.text()) if self.input_delay.text().strip() else 0
        except ValueError:
            delay_seconds = 0
            self.log_signal.emit("延迟时间格式错误，使用默认值0秒", "warning")

        self.worker = OJWorker(cfg, delay_seconds)
        self.worker.log_signal.connect(lambda msg, lv: self.log_signal.emit(msg, lv))
        self.worker.finished.connect(self._on_worker_finished)
        self.worker.start()

    def stop_oj(self):
        if self.worker and self.worker.isRunning():
            self.log_signal.emit("正在停止...", "warning")
            self.worker.stop()  # 设置停止标志 + 立即关闭浏览器
            if not self.worker.wait(3000):
                self.log_signal.emit("强制终止", "error")
                self.worker.terminate()
                self.worker.wait()
            # 确保 UI 恢复（terminate 时 finished 信号不会触发）
            self._on_worker_finished()

    def _on_worker_finished(self):
        self.running = False
        self.btn_toggle.setText("▶ 开始运行")
        self.btn_toggle._primary = True
        self.btn_toggle.update()
        self.status_dot.setStyleSheet(f"color: {TEXT_PLACEHOLDER}; font-size: 16px;")
        self.status_label.setText("已停止")
        self.status_label.setStyleSheet(f"""
            font-family: "{FONT_FAMILY}";
            font-size: 12px;
            font-weight: 500;
            color: {TEXT_SECONDARY};
        """)

    def _on_log(self, text, level):
        main_win = self.window()
        if hasattr(main_win, 'page_logs'):
            main_win.page_logs.append_log(text, level)

    def _on_status(self, text):
        self.status_label.setText(text)


# ============================================================
# OJ 工作线程
# ============================================================
class OJWorker(QThread):
    log_signal = pyqtSignal(str, str)
    finished = pyqtSignal()

    def __init__(self, config, delay_seconds=0, parent=None):
        super().__init__(parent)
        self.config = config
        self.delay_seconds = delay_seconds
        self._stop_flag = False
        self.driver = None

    def stop(self):
        self._stop_flag = True
        # 立即关闭浏览器，打断 Selenium 阻塞操作
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass

    def log(self, msg, level="info"):
        self.log_signal.emit(msg, level)

    def run(self):
        try:
            self._run_oj()
        except Exception as e:
            self.log(f"程序异常: {e}", "error")
        finally:
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
            self.finished.emit()

    def _handle_draw_modal(self, driver):
        """处理抽题弹窗：检测弹窗 → 选第一个选项 → 点击抽题（含JS回退 + portal检测）"""
        try:
            modal = driver.find_elements(By.CSS_SELECTOR, ".n-card.n-modal")
            if not modal:
                modal = driver.find_elements(By.CSS_SELECTOR, ".n-dialog")
                if not modal:
                    return False

            self.log("检测到抽题弹窗，自动选择第一个选项...", "system")
            try:
                radio_label = driver.find_element(By.XPATH, "//div[contains(text(), '切换到题目类别')]")
                radio_label.click()
            except:
                pass

            wait_and_click = self._make_wait_click(driver)

            # 点击选择框（若被拦截则用 JS 回退）
            try:
                sel = driver.find_element(By.CSS_SELECTOR, ".n-select .n-base-selection")
                sel.click()
            except:
                driver.execute_script("arguments[0].click();", sel)
            time.sleep(0.3)

            # 获取选项（含 portal 模式 fallback）
            options = driver.find_elements(By.CSS_SELECTOR, ".n-base-select-option__content")
            if not options:
                # 可能渲染到 portal 中
                options = driver.find_elements(By.XPATH,
                    "//div[contains(@class, 'n-base-select-option')]")
            if not options:
                # 可能是 n-select-menu 里的
                options = driver.find_elements(By.CSS_SELECTOR, ".n-select-menu .n-base-select-option")

            if options:
                self.log(f"选择: {options[0].text}", "info")
                try:
                    options[0].click()
                except:
                    driver.execute_script("arguments[0].click();", options[0])
            else:
                self.log("未找到任何选项", "warning")

            time.sleep(0.3)
            draw_btn = wait_and_click(By.XPATH, "//button[span[contains(text(), '我要抽题')]]")
            if not draw_btn:
                # JS 回退
                btns = driver.find_elements(By.XPATH, "//button[span[contains(text(), '我要抽题')]]")
                if btns:
                    driver.execute_script("arguments[0].click();", btns[0])

            time.sleep(2)

            # 检查是否弹窗已关闭
            still_modal = driver.find_elements(By.CSS_SELECTOR, ".n-card.n-modal")
            if still_modal:
                self.log("抽题后弹窗未关闭（可能类别选择无效），继续尝试...", "warning")
            else:
                self.log("抽题弹窗已关闭", "success")
            return True
        except Exception as e:
            self.log(f"抽题弹窗处理异常: {e}", "warning")
            return False

    def _fill_code_editor(self, code):
        """填入代码到编辑器，使用多种方法回退"""
        # ---- 方法 1: 点击编辑器容器激活 + JS 注入 ----
        try:
            # 找所有 .cm-editor，筛选可见的那个
            all_editors = self.driver.find_elements(By.CSS_SELECTOR, ".cm-editor")
            editor_outer = None
            for e in all_editors:
                if e.is_displayed() and e.size['width'] > 0 and e.size['height'] > 0:
                    editor_outer = e
                    break
            if not editor_outer:
                editor_outer = all_editors[0] if all_editors else None
            if not editor_outer:
                raise Exception("未找到 .cm-editor 元素")

            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", editor_outer)
            time.sleep(0.5)

            try:
                editor_outer.click()
                time.sleep(0.3)
            except:
                self.driver.execute_script("arguments[0].click();", editor_outer)
                time.sleep(0.3)

            # 找可见的 .cm-content
            all_contents = self.driver.find_elements(By.CSS_SELECTOR, ".cm-content")
            cm_content = None
            for c in all_contents:
                if c.is_displayed() and c.size['width'] > 0:
                    cm_content = c
                    break
            if not cm_content:
                cm_content = all_contents[0] if all_contents else None
            if not cm_content:
                raise Exception("未找到 .cm-content 元素")

            self.driver.execute_script("""
                var el = arguments[0];
                el.innerText = arguments[1];
                el.dispatchEvent(new Event('input', {bubbles: true, cancelable: true}));
            """, cm_content, code)
            self.log("代码填入成功 (方法1: JS注入)", "success")
            return True
        except Exception as e:
            self.log(f"方法1失败: {e}", "warning")

        # ---- 方法 2: pyperclip 剪贴板粘贴 ----
        try:
            import pyperclip
            pyperclip.copy(code)
            editor_outer = self.driver.find_element(By.CSS_SELECTOR, ".cm-editor")
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", editor_outer)
            editor_outer.click()
            time.sleep(0.3)
            ActionChains(self.driver).key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL).perform()
            time.sleep(0.2)
            ActionChains(self.driver).key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
            time.sleep(0.3)
            self.log("代码填入成功 (方法2: 剪贴板)", "success")
            return True
        except Exception as e:
            self.log(f"方法2失败: {e}", "warning")

        # ---- 方法 3: 直接 send_keys ----
        try:
            content = WebDriverWait(self.driver, 3).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".cm-content"))
            )
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", content)
            content.click()
            content.send_keys(Keys.CONTROL, 'a')
            content.send_keys(code)
            self.log("代码填入成功 (方法3: send_keys)", "success")
            return True
        except Exception as e:
            self.log(f"方法3失败: {e}", "warning")

        return False

    def _make_wait_click(self, driver):
        """返回一个绑定到指定 driver 的 wait_and_click 闭包（带 scrollIntoView + 异常防护）"""
        def wc(by, value, timeout=10):
            try:
                element = WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((by, value)))
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                time.sleep(0.2)
                element.click()
                return element
            except Exception as e:
                self.log(f"点击失败 ({value}): {e}", "warning")
                return None
        return wc

    def _make_wait_input(self, driver):
        """返回一个绑定到指定 driver 的 wait_and_input 闭包"""
        def wi(by, value, text, timeout=10):
            element = WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, value)))
            element.clear()
            element.send_keys(text)
        return wi

    def _get_problem_via_api(self):
        """使用 requests 调用 OJ REST API 获取题目数据，返回带 sourceCode 的 prompt"""
        try:
            url = self.driver.current_url
            exam_id = 410
            problem_id = re.search(r'problems/(\d+)', url).group(1)
            class_id = 263

            # 获取 Token
            token_raw = self.driver.execute_script(
                "return localStorage.getItem('DHU_OJ_ACCESS_TOKEN_USER');"
            )
            if not token_raw:
                self.log("未能获取 Token", "error")
                return None

            try:
                token_data = json.loads(token_raw)
                token_value = token_data.get("value")
            except:
                token_value = token_raw

            # 获取 JSESSIONID
            all_cookies = self.driver.get_cookies()
            jsessionid = next(
                (c['value'] for c in all_cookies if c['name'] == 'JSESSIONID'), ""
            )

            headers = {
                "Accept": "application/json, text/plain, */*",
                "Authorization": token_value,
                "Content-Type": "application/json",
                "Origin": "https://oj.dhu.edu.cn",
                "Referer": "https://oj.dhu.edu.cn/",
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/143.0.0.0 Safari/537.36 Edg/143.0.0.0"
                ),
            }
            cookies = {"JSESSIONID": jsessionid}
            payload = {
                "examId": str(exam_id),
                "id": str(problem_id),
                "classId": class_id,
            }

            self.log("正在通过 API 获取题目数据...", "system")
            resp = requests.post(
                "https://oj.dhu.edu.cn/api/problems/getProblemByIdAndExamIdAndClassId",
                headers=headers,
                cookies=cookies,
                json=payload,
                timeout=15,
            )
            resp.raise_for_status()
            res_json = resp.json()

            if res_json.get("code") == 0:
                data = res_json.get("data", {})
                self.log(f"题目: {data.get('title')}", "info")

                source_code = data.get("sourceCode", "")
                problem_prompt = (
                    f"标题: {data.get('title')}\n"
                    f"描述: {data.get('description')}\n"
                    f"输入要求: {data.get('inputRequirement')}\n"
                    f"输出要求: {data.get('outputRequirement')}\n"
                    f"样例输入: {data.get('sampleInput')}\n"
                    f"样例输出: {data.get('sampleOuput')}"
                )
                if source_code:
                    problem_prompt += (
                        f"\n参考题解:\n{source_code}\n"
                        f"[注] 以上解答仅供参考，保留核心功能即可，无需包含注释。"
                    )
                    self.log("已包含参考题解", "info")

                return problem_prompt
            else:
                self.log(f"API 返回异常: {res_json}", "error")
                return None

        except Exception as e:
            self.log(f"API 获取题目失败: {e}", "error")
            return None

    def _run_oj(self):
        # 初始化 DeepSeek 客户端
        client = OpenAI(
            api_key=self.config["api_key"],
            base_url=self.config["api_url"]
        )

        self.log("正在启动 Edge 浏览器...", "system")
        self.driver = webdriver.Edge()
        self.driver.maximize_window()

        wait_and_click = self._make_wait_click(self.driver)
        wait_and_input = self._make_wait_input(self.driver)

        def get_ai_solution(prompt_content, current_code=None, error_msg=None):
            system_prompt = "你是一个C++算法竞赛专家。请直接输出可编译的完整C++代码(使用MinGW标准)，不要包含markdown标记(如```cpp)，不要包含任何解释性文字，不要输出注释。参考题解仅供思路参考，保留核心功能即可，不要照搬其结构。"
            user_content = prompt_content
            if error_msg:
                user_content = f"我之前的代码如下：\n{current_code}\n\n报错信息如下：\n{error_msg}\n\n请根据报错修正代码，直接输出修正后的完整代码。"
            try:
                response = client.chat.completions.create(
                    model=self.config["model"],
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content},
                    ],
                    stream=False
                )
                content = response.choices[0].message.content
                content = content.replace("```cpp", "").replace("```", "").strip()
                return content
            except Exception as e:
                self.log(f"AI 调用失败: {e}", "error")
                return None

        # ---- 主流程 ----
        if self._stop_flag:
            return

        self.driver.get(self.config["oj_url"])

        # 检查页面是否正常加载（检测 502 / 空白页等异常）
        try:
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.XPATH, "//input[@placeholder='登录账号']"))
            )
        except:
            page_source = self.driver.page_source[:300] if self.driver.page_source else "(空)"
            current_title = self.driver.title
            self.log(f"页面加载异常 — 标题: '{current_title}'", "error")
            self.log(f"页面内容片段: {page_source}", "error")
            if "502" in page_source or "Bad Gateway" in page_source:
                self.log(
                    "OJ 服务器返回 502 Bad Gateway，可能是服务器维护或网络问题。\n"
                    "请尝试：1. 手动打开 http://oj.dhu.edu.cn 检查是否可访问\n"
                    "      2. 等待一段时间后重试",
                    "error"
                )
            elif "404" in page_source or "Not Found" in page_source:
                self.log("OJ 地址不可达（404），请检查 OJ_URL 配置", "error")
            else:
                self.log("登录页面未能正常加载，请手动检查", "error")
            self.log("请在浏览器中手动检查页面状态，然后按回车继续或关闭窗口...", "warning")
            # 给用户机会手动处理
            for _ in range(60):
                if self._stop_flag:
                    return
                time.sleep(1)
                try:
                    # 检测用户是否已手动到达登录页
                    self.driver.find_element(By.XPATH, "//input[@placeholder='登录账号']")
                    self.log("检测到登录页，继续执行...", "success")
                    break
                except:
                    continue
            else:
                self.log("等待超时，终止流程", "error")
                return

        self.log("正在登录...", "info")
        wait_and_input(By.XPATH, "//input[@placeholder='登录账号']", self.config["username"])
        password_input = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//input[@placeholder='请输入密码']"))
        )
        password_input.clear()
        password_input.send_keys(self.config["password"])
        time.sleep(0.5)
        password_input.send_keys(Keys.ENTER)
        self.log("登录提交完成", "success")

        if self._stop_flag:
            return

        # 进入考试列表
        try:
            wait_and_click(By.XPATH, "//a[@href='#/user/exam-list']", timeout=5)
        except:
            self.driver.get(f"{self.config['oj_url']}/#/user/exam-list")
        time.sleep(1)

        # 点击第一个"参加"按钮
        self.log("正在参加考试...", "info")
        try:
            buttons = WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located((By.XPATH, "//button[span[contains(text(), '参加')]]"))
            )
            buttons[0].click()
        except Exception as e:
            self.log(f"点击参加按钮失败: {e}", "error")
            return

        # 点击"参加"后必定转到考试概览页，直接点击"开始做题"
        self.log("点击【开始做题】...", "info")
        try:
            wait_and_click(By.XPATH, "//button[span[contains(text(), '开始做题')]]")
            time.sleep(3)
        except Exception as e:
            self.log(f"点击开始做题失败: {e}", "error")
            return

        # 进入后处理可能出现的抽题弹窗
        if not self._handle_draw_modal(self.driver):
            self.log("无抽题弹窗，已有题目", "info")

        # ---- 循环做题 ----
        while not self._stop_flag:
            # 每次新题目前检查抽题弹窗（非首次已在 break 前处理）
            if self._stop_flag:
                break

            # 获取题目（通过 API）
            self.log("正在获取题目详情...", "info")
            problem_prompt = self._get_problem_via_api()
            if not problem_prompt:
                self.log("API 获取题目失败，跳过", "error")
                break

            self.log("正在请求 AI 生成代码...", "system")
            code = get_ai_solution(problem_prompt)
            if not code:
                self.log("AI 生成失败，重试...", "error")
                continue

            current_code = code
            self.log("AI 代码生成完成", "success")

            if self._stop_flag:
                break

            # 填入代码（多方法回退）
            if not self._fill_code_editor(current_code):
                self.log("所有填入代码方法均失败", "error")

            # 选择语言 MinGW
            try:
                selections = self.driver.find_elements(By.CSS_SELECTOR, ".n-base-selection")
                for sel in selections:
                    try:
                        sel.click()
                        time.sleep(0.2)
                        mingw_opt = self.driver.find_elements(By.XPATH, "//div[contains(text(), 'MinGW')]")
                        if mingw_opt:
                            mingw_opt[0].click()
                            break
                    except:
                        continue
            except:
                pass

            # 延迟提交（提交前等待指定秒数，可中途取消）
            if self.delay_seconds > 0:
                self.log(f"⏳ 等待 {self.delay_seconds} 秒后提交...", "system")
                for _ in range(self.delay_seconds):
                    if self._stop_flag:
                        return
                    time.sleep(1)
                self.log("延迟结束，准备提交", "info")

            # 循环提交
            solved = False
            submitted = False
            while not solved and not self._stop_flag:
                # ---- 提交（仅在首次或修复后执行） ----
                if not submitted:
                    self.log("提交代码中...", "system")
                    submit_btn = wait_and_click(By.XPATH, "//button[span[contains(text(), '提交代码')]]")
                    if not submit_btn:
                        self.log("提交按钮未找到", "error")
                        break

                    # 确认弹窗
                    try:
                        confirm = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, "//div[@class='n-dialog__action']//button[span[contains(text(), '提交')]]"))
                        )
                        confirm.click()
                    except:
                        pass

                    # 抄袭警告
                    try:
                        warning = WebDriverWait(self.driver, 2).until(
                            EC.element_to_be_clickable((By.XPATH, "//button[span[contains(text(), '坚持提交')]]"))
                        )
                        warning.click()
                    except:
                        pass

                    submitted = True
                    # 标记首次检查需要用长超时等待"已AC但未提交"弹窗
                    _ac_wait_done = False

                # ---- 等待判题 ----
                self.log("等待判题结果...", "info")
                time.sleep(3)

                # ---- 结果检查 ----

                # 1. "已AC但未提交"确认弹窗（AC后先弹此窗，提交后才出现"我要抽题"）
                #    首次检查用30s长超时，后续用瞬时检查避免每次循环都空等30s
                ac_timeout = 30 if not _ac_wait_done else 3
                ac_submit_btn = wait_and_click(By.XPATH,
                    "//div[contains(@class, 'n-dialog__action')]//button[span[contains(text(), '提交')]]",
                    timeout=ac_timeout)
                _ac_wait_done = True

                if ac_submit_btn:
                    self.log("检测到'已AC但未提交'弹窗 → 已点击提交", "system")
                    time.sleep(2)

                    # 点击提交后可能出现抄袭警告
                    try:
                        warn = WebDriverWait(self.driver, 3).until(
                            EC.element_to_be_clickable((By.XPATH, "//button[span[contains(text(), '坚持提交')]]"))
                        )
                        warn.click()
                        self.log("已点击'坚持提交'", "success")
                        time.sleep(1)
                    except:
                        pass

                # 2. "我要抽题"按钮（通关弹窗）
                next_btn = self.driver.find_elements(By.XPATH, "//button[span[contains(text(), '我要抽题')]]")
                if next_btn and next_btn[0].is_displayed():
                    self.log("✅ 题目通过 (AC)！进入下一题...", "success")
                    next_btn[0].click()
                    solved = True
                    time.sleep(2)
                    # 通关弹窗关闭后可能出现抽题弹窗
                    self._handle_draw_modal(self.driver)
                    break

                # 3. "已通关"（全部题目完成）
                cleared = self.driver.find_elements(By.XPATH, "//div[contains(text(), '已通关')]")
                if cleared:
                    self.log("🎉 已通关所有题目！", "success")
                    solved = True
                    break

                # 4. 仍在排队/判题中 → 继续等待
                try:
                    result_tab = self.driver.find_element(By.XPATH, "//div[@data-name='result']")
                    result_tab.click()
                    time.sleep(1)
                    status_elem = self.driver.find_elements(By.XPATH, "//td[@data-col-key='status']")
                    if status_elem:
                        status_text = status_elem[0].text.lower()
                        if 'queue' in status_text or '等待' in status_text or 'judg' in status_text:
                            self.log(f"判题排队中 ({status_elem[0].text})，继续等待...", "info")
                            continue
                except:
                    pass

                # 5. 未通过，获取错误信息进行 AI 修复
                self.log("未通过，获取错误信息...", "warning")
                try:
                    result_tab = self.driver.find_element(By.XPATH, "//div[@data-name='result']")
                    result_tab.click()
                except:
                    pass

                try:
                    time.sleep(1)
                    status_elem = self.driver.find_elements(By.XPATH, "//td[@data-col-key='status']")
                    if status_elem:
                        status_text = status_elem[0].text
                        self.log(f"运行状态: {status_text}", "warning")

                    error_area = self.driver.find_elements(By.XPATH, "//div[contains(text(), '详细信息')]/following-sibling::div//textarea")
                    error_msg = ""
                    if error_area:
                        error_msg = error_area[0].get_attribute('value')
                    if not error_msg and status_elem:
                        error_msg = f"运行状态: {status_elem[0].text} (请检查逻辑)"
                    elif not error_msg:
                        error_msg = "未知错误"

                    self.log(f"错误信息: {error_msg[:80]}...", "error")

                    self.log("请求 AI 修复代码...", "system")
                    new_code = get_ai_solution(problem_prompt, current_code, error_msg)
                    if new_code:
                        current_code = new_code
                        editor = self.driver.find_element(By.CSS_SELECTOR, ".cm-content")
                        action = ActionChains(self.driver)
                        action.click(editor).key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL).send_keys(Keys.BACK_SPACE).perform()
                        self.driver.execute_script("arguments[0].innerText = arguments[1];", editor, current_code)
                        editor.send_keys(" ")
                        editor.send_keys(Keys.BACK_SPACE)
                        submitted = False  # 修复后重新提交
                    continue
                except Exception as e:
                    self.log(f"获取错误结果失败: {e}", "error")
                    break

        self.log("运行结束", "system")


# ============================================================
# 应用入口
# ============================================================
if __name__ == "__main__":
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # 全局字体
    font = QFont(FONT_FAMILY, 9)
    font.setStyleStrategy(QFont.PreferAntialias)
    app.setFont(font)

    window = MainWindow()
    window.resize(1100, 750)
    window.show()

    sys.exit(app.exec_())
