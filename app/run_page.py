# -*- coding: utf-8 -*-
"""运行页面：状态卡、开始/暂停/继续/停止按钮、提交延迟、坚持提交开关、配置摘要。

页面创建 OJWorker（QThread）并桥接它的信号到主窗口的日志页。
"""

import os

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QLineEdit, QStyle, QSystemTrayIcon,
    QVBoxLayout, QWidget,
)

from app.constants import (
    BORDER_COLOR, FONT_FAMILY, INPUT_BG, INPUT_BORDER, INPUT_BORDER_FOCUS,
    SUCCESS_GREEN, TEXT_PLACEHOLDER, TEXT_PRIMARY, TEXT_SECONDARY,
    WARNING_ORANGE, WINDOW_BG,
)
from app.oj_worker import OJWorker
from app.widgets import Win11Button, Win11CheckBox


class RunPage(QWidget):
    log_signal = pyqtSignal(str, str)
    status_signal = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker = None
        self.running = False
        self.paused = False

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
        layout.addSpacing(12)

        # 是否坚持提交（默认勾选；取消勾选时遇到抄袭警告会暂停）
        self.chk_persist_submit = Win11CheckBox("是否坚持提交")
        self.chk_persist_submit.setChecked(True)
        self.chk_persist_submit.setToolTip(
            "勾选：检测到抄袭警告时自动点击\"坚持提交\"。\n"
            "不勾选：检测到抄袭警告时暂停程序，由您手动处理\n"
            "（包括改写代码、自行点击提交等），然后点击\"继续\"恢复自动流程。"
        )
        layout.addWidget(self.chk_persist_submit)
        layout.addSpacing(16)

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
            cfg = main_win.page_config.get_active_config()
            masked_key = cfg["api_key"][:8] + "****" if len(cfg["api_key"]) > 8 else "****"
            self.summary_text.setText(
                f"OJ: {cfg['oj_url']}  |  账号: {cfg['username']}\n"
                f"AI: {cfg['model']} @ {cfg['api_url']}  |  Key: {masked_key}"
            )

    def toggle_oj(self):
        if not self.running:
            self.start_oj()
        elif self.paused:
            self.resume_oj()
        else:
            self.stop_oj()

    def start_oj(self):
        if self.worker and self.worker.isRunning():
            self.log_signal.emit("已有进程在运行中", "warning")
            return

        main_win = self.window()
        cfg = main_win.page_config.get_active_config()

        # 检查必要配置
        missing = [k for k in ["api_key", "username", "password"] if not cfg.get(k)]
        if missing:
            self.log_signal.emit(f"配置不完整，请先在设置页填写: {', '.join(missing)}", "error")
            return

        os.environ['DEEPSEEK_API_KEY'] = cfg["api_key"]

        self.running = True
        self.paused = False
        self.btn_toggle.setText("■ 停止")
        self.btn_toggle._primary = False
        self.btn_toggle.set_bg(None, None)  # 恢复默认色
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
        self.worker.set_persist_submit(self.chk_persist_submit.isChecked())
        self.worker.log_signal.connect(lambda msg, lv: self.log_signal.emit(msg, lv))
        self.worker.finished.connect(self._on_worker_finished)
        self.worker.paused_signal.connect(self._on_worker_paused)

        # 系统托盘通知（当 PushPlus 未启用时作为兜底）
        if not hasattr(self, '_tray_icon') or self._tray_icon is None:
            self._tray_icon = QSystemTrayIcon(self)
            icon = self.style().standardIcon(QStyle.SP_MessageBoxInformation)
            self._tray_icon.setIcon(icon)
            self._tray_icon.setToolTip("OJ Helper")
        try:
            self._tray_icon.show()
            self.worker.notify_signal.connect(
                lambda title, msg: self._tray_icon.showMessage(
                    title, msg, QSystemTrayIcon.Information, 10000
                )
            )
        except Exception:
            self.log_signal.emit("系统托盘通知不可用（环境不支持）", "warning")

        # 复选框热更新到 worker
        try:
            self.chk_persist_submit.toggled.disconnect()
        except TypeError:
            pass
        self.chk_persist_submit.toggled.connect(self._on_persist_submit_toggled)
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

    def resume_oj(self):
        """从暂停状态恢复运行"""
        if not (self.worker and self.worker.isRunning()):
            return
        self.log_signal.emit("继续运行...", "system")
        self.paused = False
        self.btn_toggle.setText("■ 停止")
        self.btn_toggle._primary = False
        self.btn_toggle.set_bg(None, None)  # 恢复默认（非 primary 状态下颜色无关，但保险起见清掉）
        self.btn_toggle.update()
        self.status_dot.setStyleSheet(f"color: {SUCCESS_GREEN}; font-size: 16px;")
        self.status_label.setText("运行中...")
        self.status_label.setStyleSheet(f"""
            font-family: "{FONT_FAMILY}";
            font-size: 12px;
            font-weight: 500;
            color: {SUCCESS_GREEN};
        """)
        self.worker.resume()

    def _on_worker_paused(self):
        """worker 进入暂停时，更新按钮为橙色'继续'"""
        self.paused = True
        self.btn_toggle.setText("▶ 继续")
        self.btn_toggle._primary = True
        self.btn_toggle.set_bg(WARNING_ORANGE, "#E67E00")
        self.btn_toggle.update()
        self.status_dot.setStyleSheet(f"color: {WARNING_ORANGE}; font-size: 16px;")
        self.status_label.setText("已暂停")
        self.status_label.setStyleSheet(f"""
            font-family: "{FONT_FAMILY}";
            font-size: 12px;
            font-weight: 500;
            color: {WARNING_ORANGE};
        """)

    def _on_persist_submit_toggled(self, value: bool):
        if self.worker and self.worker.isRunning():
            self.worker.set_persist_submit(value)

    def _on_worker_finished(self):
        self.running = False
        self.paused = False
        self.btn_toggle.setText("▶ 开始运行")
        self.btn_toggle._primary = True
        self.btn_toggle.set_bg(None, None)  # 恢复默认蓝色
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
