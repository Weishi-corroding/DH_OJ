# -*- coding: utf-8 -*-
"""无边框、圆角、阴影、可拖动的 Win11 风格主窗口。

承载标题栏（图标 + 标题 + 3 个 TitleBarButton）和正文（Sidebar + QStackedWidget 的
3 个页面）。提供窗口拖动、双击最大化、退出时清理 worker 的逻辑。
"""

from PyQt5.QtCore import Qt, QPoint, QRect
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QFrame, QGraphicsDropShadowEffect, QHBoxLayout, QLabel, QMainWindow,
    QStackedWidget, QVBoxLayout, QWidget,
)

from app.config_page import ConfigPage
from app.constants import (
    BORDER_COLOR, FONT_FAMILY, SHADOW_MARGIN, TEXT_PRIMARY,
    TITLEBAR_HEIGHT, WINDOW_BG, WINDOW_RADIUS,
)
from app.log_page import LogPage
from app.run_page import RunPage
from app.sidebar import Sidebar
from app.widgets import TitleBarButton


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
