# -*- coding: utf-8 -*-
"""OJ Helper 入口：高 DPI 初始化 + 全局字体 + 启动 MainWindow。

按模块功能拆分见 app/ 目录：
    constants    全局色板/字体/路径/反查重头文件池
    widgets      Win11 自绘控件
    sidebar      左侧导航栏
    config_page  配置页（OJ 账号、AI、PushPlus、导入导出）
    run_page     运行页（启动/暂停/继续、状态卡）
    log_page     日志页（黑底彩色输出）
    oj_worker    Selenium + AI 主流程（QThread）
    main_window  无边框主窗口
"""

import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication

from app.constants import FONT_FAMILY
from app.main_window import MainWindow


def main():
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


if __name__ == "__main__":
    main()
