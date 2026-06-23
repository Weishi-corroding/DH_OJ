# -*- coding: utf-8 -*-
"""Win11 风格的自绘控件集合。

包含：
    - TitleBarButton   标题栏的最小化/最大化/关闭按钮（QPainter 绘制）
    - SidebarButton    侧边栏导航按钮（带激活指示条）
    - Win11LineEdit    顶部标签 + QLineEdit + 焦点线 的复合输入框
    - Win11ComboBox    与 Win11LineEdit 结构对齐的下拉框
    - Win11Button      圆角主/次按钮（QPainter 绘制，支持 set_bg 运行时换色）
    - Win11CheckBox    自绘的方框对勾复选框
"""

from PyQt5.QtCore import Qt, QRect, QRectF, pyqtSignal
from PyQt5.QtGui import (
    QColor, QFont, QFontMetrics, QPainter, QPainterPath, QPen,
)
from PyQt5.QtWidgets import (
    QComboBox, QFrame, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget,
)

from app.constants import (
    ACCENT_BLUE, ACCENT_BLUE_HOVER, BORDER_COLOR, BTN_HOVER_BG,
    BTN_PRIMARY_BG, BTN_PRIMARY_HOVER, ERROR_RED, FONT_FAMILY, ICON_COLOR,
    INPUT_BG, INPUT_BORDER, INPUT_BORDER_FOCUS, TEXT_PLACEHOLDER,
    TEXT_PRIMARY, TEXT_SECONDARY, TITLEBAR_HEIGHT,
)
from app.draw_icons import (
    draw_close_icon, draw_maximize_icon, draw_minimize_icon,
)


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
# 侧边栏导航按钮
# ============================================================
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
# Win11 风格下拉框
# ============================================================
class Win11ComboBox(QWidget):
    """复合控件：顶部 label + 中间 QComboBox + 底部 focus line，结构与 Win11LineEdit 对齐。"""

    def __init__(self, label="", parent=None):
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

        # 下拉框
        self._combo = QComboBox()
        self._combo.setFixedHeight(34)
        self._combo.setStyleSheet(f"""
            QComboBox {{
                font-family: "{FONT_FAMILY}";
                font-size: 11px;
                color: {TEXT_PRIMARY};
                background: {INPUT_BG};
                border: 1px solid {INPUT_BORDER};
                border-radius: 4px;
                padding: 4px 10px;
            }}
            QComboBox:focus {{
                border: 1.5px solid {INPUT_BORDER_FOCUS};
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 24px;
                border: none;
            }}
            QComboBox QAbstractItemView {{
                font-family: "{FONT_FAMILY}";
                font-size: 11px;
                color: {TEXT_PRIMARY};
                background: {INPUT_BG};
                border: 1px solid {INPUT_BORDER};
                border-radius: 4px;
                selection-background-color: {BTN_HOVER_BG};
                selection-color: {TEXT_PRIMARY};
                outline: none;
                padding: 2px 0;
            }}
            QComboBox QAbstractItemView::item {{
                min-height: 28px;
                padding: 4px 12px;
            }}
        """)
        layout.addWidget(self._combo)

        # 底部提示线
        self.focus_line = QFrame()
        self.focus_line.setFixedHeight(2)
        self.focus_line.setStyleSheet("background: transparent; border-radius: 1px;")
        layout.addWidget(self.focus_line)

        self._combo.installEventFilter(self)

        # 信号转发
        self.currentIndexChanged = self._combo.currentIndexChanged

    def eventFilter(self, obj, event):
        if obj is self._combo:
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

    # 委托给内部 QComboBox 的常用方法
    def addItem(self, text, userData=None):
        if userData is None:
            self._combo.addItem(text)
        else:
            self._combo.addItem(text, userData)

    def clear(self):
        self._combo.clear()

    def setCurrentIndex(self, idx):
        self._combo.setCurrentIndex(idx)

    def currentIndex(self):
        return self._combo.currentIndex()

    def count(self):
        return self._combo.count()

    def currentText(self):
        return self._combo.currentText()

    def setItemText(self, idx, text):
        self._combo.setItemText(idx, text)


# ============================================================
# Win11 风格按钮
# ============================================================
class Win11Button(QPushButton):
    def __init__(self, text, primary=True, small=False, bg_color=None, hover_color=None, parent=None):
        super().__init__(text, parent)
        self._primary = primary
        self._hovered = False
        self._pressed = False
        # 自定义主色（仅 primary=True 时生效，None 表示使用默认蓝色）
        self._bg_color = bg_color
        self._hover_color = hover_color

        self.setCursor(Qt.PointingHandCursor)

        if small:
            self.setFixedHeight(30)
            font_size = 10
        else:
            self.setFixedHeight(36)
            font_size = 11

        self._font_size = font_size
        self._apply_stylesheet()

    def _apply_stylesheet(self):
        bg = self._bg_color if (self._primary and self._bg_color) else BTN_PRIMARY_BG
        hover = self._hover_color if (self._primary and self._hover_color) else BTN_PRIMARY_HOVER
        self.setStyleSheet(f"""
            QPushButton {{
                font-family: "{FONT_FAMILY}";
                font-size: {self._font_size}px;
                font-weight: 500;
                border: none;
                border-radius: 4px;
                padding: 0 20px;
                background: {bg if self._primary else "transparent"};
                color: {"#FFFFFF" if self._primary else TEXT_PRIMARY};
            }}
            QPushButton:hover {{
                background: {hover if self._primary else BTN_HOVER_BG};
            }}
            QPushButton:pressed {{
                background: {hover if self._primary else "#D0D0D0"};
            }}
            QPushButton:disabled {{
                background: {"#C0C0C0" if self._primary else "transparent"};
                color: {"#FFFFFF" if self._primary else TEXT_PLACEHOLDER};
            }}
        """)

    def set_bg(self, bg_color, hover_color):
        """运行时切换主色（用于按钮三态切换）。传 None 恢复默认蓝色。"""
        self._bg_color = bg_color
        self._hover_color = hover_color
        self._apply_stylesheet()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect()

        # 主色：自定义优先，否则用默认蓝
        primary_bg = QColor(self._bg_color) if self._bg_color else QColor(BTN_PRIMARY_BG)
        primary_hover = QColor(self._hover_color) if self._hover_color else QColor(BTN_PRIMARY_HOVER)

        bg = primary_bg if self._primary else QColor(0, 0, 0, 0)
        if self._hovered:
            bg = primary_hover if self._primary else QColor(0, 0, 0, 20)
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
# Win11 风格复选框
# ============================================================
class Win11CheckBox(QWidget):
    """自绘 Win11 风格复选框：16×16 方框 + 蓝色填充 + 白色对勾。
    支持 toggled 信号、setChecked/isChecked、setToolTip（PyQt5 内置）。
    """
    toggled = pyqtSignal(bool)

    def __init__(self, text="", parent=None):
        super().__init__(parent)
        self._text = text
        self._checked = False
        self._hovered = False
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(28)
        self.setMouseTracking(True)
        # 初步宽度估算（实际由父布局拉伸）
        font = QFont(FONT_FAMILY, 11)
        fm = QFontMetrics(font)
        self.setMinimumWidth(20 + 8 + fm.horizontalAdvance(text) + 4)

    def setChecked(self, value: bool):
        if self._checked != bool(value):
            self._checked = bool(value)
            self.update()
            self.toggled.emit(self._checked)

    def isChecked(self):
        return self._checked

    def setText(self, text: str):
        self._text = text
        self.update()

    def text(self):
        return self._text

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.setChecked(not self._checked)
        super().mousePressEvent(event)

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

        box_size = 16
        box_x = 2
        box_y = (self.height() - box_size) // 2
        box_rect = QRectF(box_x, box_y, box_size, box_size)

        if self._checked:
            # 填充蓝色 + 白勾
            fill = QColor(ACCENT_BLUE)
            if self._hovered:
                fill = QColor(ACCENT_BLUE_HOVER)
            path = QPainterPath()
            path.addRoundedRect(box_rect, 3, 3)
            painter.fillPath(path, fill)
            # 对勾
            pen = QPen(QColor("#FFFFFF"), 1.8)
            pen.setCapStyle(Qt.RoundCap)
            pen.setJoinStyle(Qt.RoundJoin)
            painter.setPen(pen)
            cx = box_x + box_size / 2
            cy = box_y + box_size / 2
            painter.drawLine(int(cx - 4), int(cy), int(cx - 1), int(cy + 3))
            painter.drawLine(int(cx - 1), int(cy + 3), int(cx + 4), int(cy - 3))
        else:
            # 空心方框
            border_color = QColor(ACCENT_BLUE) if self._hovered else QColor("#666666")
            pen = QPen(border_color, 1.2)
            painter.setPen(pen)
            path = QPainterPath()
            path.addRoundedRect(box_rect, 3, 3)
            painter.drawPath(path)

        # 文本
        if self._text:
            painter.setPen(QColor(TEXT_PRIMARY))
            font = QFont(FONT_FAMILY, 11)
            painter.setFont(font)
            text_rect = QRect(box_x + box_size + 8, 0, self.width() - (box_x + box_size + 8), self.height())
            painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, self._text)
