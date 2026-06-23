# -*- coding: utf-8 -*-
"""标题栏按钮图标（最小化 / 最大化 / 关闭）—— 直接由 QPainter 绘制。"""

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QPen


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
