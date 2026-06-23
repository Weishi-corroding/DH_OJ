# -*- coding: utf-8 -*-
"""配置页面：OJ 账号、AI 接口、PushPlus 通知、导入/导出/保存。

支持多账号、多 AI profile 的下拉切换，`+` 按钮新增空条目。`get_active_config()`
返回当前选中条目展开后的扁平 dict 供 OJWorker 消费。
"""

import json
import os

from PyQt5.QtWidgets import (
    QFileDialog, QFrame, QGraphicsOpacityEffect, QHBoxLayout, QLabel,
    QMessageBox, QScrollArea, QVBoxLayout, QWidget,
)

from app.constants import (
    ACCENT_BLUE, BASE_DIR, CONFIG_FILE, FONT_FAMILY, TEXT_PRIMARY,
    TEXT_SECONDARY,
)
from app.widgets import (
    Win11Button, Win11CheckBox, Win11ComboBox, Win11LineEdit,
)


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

        self.input_oj_url = Win11LineEdit("OJ 地址", "https://oj.dhu.edu.cn/#/user/index")
        form_layout.addWidget(self.input_oj_url)

        # 账号下拉 + 新增按钮
        account_row = QHBoxLayout()
        account_row.setContentsMargins(0, 0, 0, 0)
        account_row.setSpacing(8)
        self.combo_account = Win11ComboBox("选择账号")
        account_row.addWidget(self.combo_account, 1)
        self.btn_add_account = Win11Button("＋", primary=False, small=True)
        self.btn_add_account.setFixedSize(34, 34)
        self.btn_add_account.setStyleSheet(self.btn_add_account.styleSheet() + " QPushButton { padding: 0; }")
        self.btn_add_account.setToolTip("新增一个账号")
        account_row.addWidget(self.btn_add_account)
        form_layout.addLayout(account_row)

        self.input_username = Win11LineEdit("用户名", "")
        self.input_password = Win11LineEdit("密码", "", is_password=True)

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

        # AI 配置下拉 + 新增按钮
        ai_row = QHBoxLayout()
        ai_row.setContentsMargins(0, 0, 0, 0)
        ai_row.setSpacing(8)
        self.combo_ai = Win11ComboBox("选择 AI 配置")
        ai_row.addWidget(self.combo_ai, 1)
        self.btn_add_ai = Win11Button("＋", primary=False, small=True)
        self.btn_add_ai.setFixedSize(34, 34)
        self.btn_add_ai.setStyleSheet(self.btn_add_ai.styleSheet() + " QPushButton { padding: 0; }")
        self.btn_add_ai.setToolTip("新增一个 AI 配置")
        ai_row.addWidget(self.btn_add_ai)
        form_layout.addLayout(ai_row)

        self.input_api_key = Win11LineEdit("API Key", "")
        self.input_api_url = Win11LineEdit("API 地址", "")
        self.input_model = Win11LineEdit("模型", "")

        form_layout.addWidget(self.input_api_key)
        form_layout.addWidget(self.input_api_url)
        form_layout.addWidget(self.input_model)

        # ====== PushPlus 通知 ======
        section3 = QLabel("通知")
        section3.setStyleSheet(f"""
            font-family: "{FONT_FAMILY}";
            font-size: 12px;
            font-weight: 600;
            color: {ACCENT_BLUE};
            margin-top: 16px;
        """)
        form_layout.addWidget(section3)

        # PushPlus 勾选框
        self.chk_pushplus = Win11CheckBox("启用 PushPlus 通知")
        self.chk_pushplus.setToolTip(
            "勾选后，在需要您人工操作（如抄袭警告、连续两次提交失败）时\n"
            "通过 PushPlus 推送通知到您的微信。"
        )
        form_layout.addWidget(self.chk_pushplus)

        # PushPlus Token 输入（勾选后才可用）
        self.input_pushplus_token = Win11LineEdit("PushPlus Token", "")
        self._set_pushplus_input_enabled(False)
        form_layout.addWidget(self.input_pushplus_token)

        # 勾选/取消时切换输入框可用状态
        self.chk_pushplus.toggled.connect(self._on_pushplus_toggled)

        form_layout.addStretch()
        scroll.setWidget(form_widget)
        layout.addWidget(scroll, 1)

        # ====== 底部按钮栏 ======
        btn_bar = QHBoxLayout()
        btn_bar.setContentsMargins(0, 12, 0, 0)
        btn_bar.addStretch()

        self.btn_import = Win11Button("📂 导入配置", primary=False, small=False)
        self.btn_import.setFixedWidth(120)
        self.btn_import.setToolTip("从外部 JSON 文件导入配置（覆盖当前表单）")
        self.btn_import.clicked.connect(self.import_config)
        btn_bar.addWidget(self.btn_import)

        self.btn_export = Win11Button("💾 导出配置", primary=False, small=False)
        self.btn_export.setFixedWidth(120)
        self.btn_export.setToolTip("将当前表单配置导出为 JSON 文件")
        self.btn_export.clicked.connect(self.export_config)
        btn_bar.addWidget(self.btn_export)

        self.btn_save = Win11Button("💾 保存配置", primary=True, small=False)
        self.btn_save.setFixedWidth(140)
        self.btn_save.clicked.connect(self.save_config)
        btn_bar.addWidget(self.btn_save)

        layout.addLayout(btn_bar)

        # ====== 多账号 / 多 AI 配置状态 ======
        self._accounts = []
        self._ai_profiles = []
        self._loading = False

        # 信号连接
        self.combo_account.currentIndexChanged.connect(self._on_account_changed)
        self.combo_ai.currentIndexChanged.connect(self._on_ai_changed)
        self.input_username.edit.textChanged.connect(self._on_username_changed)
        self.input_password.edit.textChanged.connect(self._on_password_changed)
        self.input_api_key.edit.textChanged.connect(self._on_api_key_changed)
        self.input_api_url.edit.textChanged.connect(self._on_api_url_changed)
        self.input_model.edit.textChanged.connect(self._on_model_changed)
        self.btn_add_account.clicked.connect(self._add_account)
        self.btn_add_ai.clicked.connect(self._add_ai)

        # 启动时加载已有配置
        self.load_config()

    def _set_pushplus_input_enabled(self, enabled: bool):
        """切换 PushPlus Token 输入框的可用状态"""
        self.input_pushplus_token.setEnabled(enabled)
        # 视觉上置灰
        opacity = 1.0 if enabled else 0.4
        self.input_pushplus_token.setGraphicsEffect(
            None if enabled else QGraphicsOpacityEffect(opacity=opacity)
        )

    def _on_pushplus_toggled(self, checked: bool):
        """勾选状态变化时同步输入框可用性"""
        self._set_pushplus_input_enabled(checked)

    # -------------------- 多账号 / 多 AI 配置 内部逻辑 --------------------

    @staticmethod
    def _normalize_cfg(cfg):
        """兼容旧扁平 schema：把顶层 username/password/api_key/... 折叠到 accounts/ai_profiles。"""
        cfg = dict(cfg or {})
        # 账号
        if "accounts" not in cfg:
            if any(k in cfg for k in ("username", "password")):
                cfg["accounts"] = [{
                    "username": cfg.get("username", ""),
                    "password": cfg.get("password", ""),
                }]
                cfg.setdefault("active_account", 0)
            else:
                cfg["accounts"] = []
        # AI 配置
        if "ai_profiles" not in cfg:
            if any(k in cfg for k in ("api_key", "api_url", "model")):
                cfg["ai_profiles"] = [{
                    "api_key": cfg.get("api_key", ""),
                    "api_url": cfg.get("api_url", ""),
                    "model": cfg.get("model", ""),
                }]
                cfg.setdefault("active_ai", 0)
            else:
                cfg["ai_profiles"] = []
        cfg.setdefault("active_account", 0)
        cfg.setdefault("active_ai", 0)
        cfg.setdefault("oj_url", "")
        cfg.setdefault("pushplus_enabled", False)
        cfg.setdefault("pushplus_token", "")
        return cfg

    def _on_account_changed(self, idx):
        if self._loading:
            return
        if 0 <= idx < len(self._accounts):
            self._loading = True
            self.input_username.setText(self._accounts[idx].get("username", ""))
            self.input_password.setText(self._accounts[idx].get("password", ""))
            self._loading = False

    def _on_ai_changed(self, idx):
        if self._loading:
            return
        if 0 <= idx < len(self._ai_profiles):
            self._loading = True
            self.input_api_key.setText(self._ai_profiles[idx].get("api_key", ""))
            self.input_api_url.setText(self._ai_profiles[idx].get("api_url", ""))
            self.input_model.setText(self._ai_profiles[idx].get("model", ""))
            self._loading = False

    def _on_username_changed(self, text):
        if self._loading:
            return
        idx = self.combo_account.currentIndex()
        if 0 <= idx < len(self._accounts):
            self._accounts[idx]["username"] = text
            self.combo_account.setItemText(idx, text or "(空)")

    def _on_password_changed(self, text):
        if self._loading:
            return
        idx = self.combo_account.currentIndex()
        if 0 <= idx < len(self._accounts):
            self._accounts[idx]["password"] = text

    def _on_api_key_changed(self, text):
        if self._loading:
            return
        idx = self.combo_ai.currentIndex()
        if 0 <= idx < len(self._ai_profiles):
            self._ai_profiles[idx]["api_key"] = text

    def _on_api_url_changed(self, text):
        if self._loading:
            return
        idx = self.combo_ai.currentIndex()
        if 0 <= idx < len(self._ai_profiles):
            self._ai_profiles[idx]["api_url"] = text

    def _on_model_changed(self, text):
        if self._loading:
            return
        idx = self.combo_ai.currentIndex()
        if 0 <= idx < len(self._ai_profiles):
            self._ai_profiles[idx]["model"] = text
            self.combo_ai.setItemText(idx, text or "(空)")

    def _add_account(self):
        self._accounts.append({"username": "", "password": ""})
        new_idx = len(self._accounts) - 1
        self._loading = True
        self.combo_account.addItem("(空)")
        self._loading = False
        self.combo_account.setCurrentIndex(new_idx)  # 触发 _on_account_changed 把空值填到输入框

    def _add_ai(self):
        self._ai_profiles.append({"api_key": "", "api_url": "", "model": ""})
        new_idx = len(self._ai_profiles) - 1
        self._loading = True
        self.combo_ai.addItem("(空)")
        self._loading = False
        self.combo_ai.setCurrentIndex(new_idx)

    def _ensure_default_state(self):
        """无配置文件 / 解析失败时，给 UI 种一条空账号 + 空 AI profile。"""
        self._loading = True
        self._accounts = [{"username": "", "password": ""}]
        self._ai_profiles = [{"api_key": "", "api_url": "", "model": ""}]
        self.combo_account.clear()
        self.combo_account.addItem("(空)")
        self.combo_account.setCurrentIndex(0)
        self.combo_ai.clear()
        self.combo_ai.addItem("(空)")
        self.combo_ai.setCurrentIndex(0)
        self.input_username.setText("")
        self.input_password.setText("")
        self.input_api_key.setText("")
        self.input_api_url.setText("")
        self.input_model.setText("")
        self._loading = False

    # -------------------- 对外接口 --------------------

    def get_config(self):
        return {
            "oj_url": self.input_oj_url.text(),
            "active_account": self.combo_account.currentIndex(),
            "accounts": self._accounts,
            "active_ai": self.combo_ai.currentIndex(),
            "ai_profiles": self._ai_profiles,
            "pushplus_enabled": self.chk_pushplus.isChecked(),
            "pushplus_token": self.input_pushplus_token.text(),
        }

    def get_active_config(self):
        """返回当前选中条目展开后的扁平 dict，供 OJWorker 等消费方使用。"""
        cfg = self.get_config()
        accounts = cfg["accounts"] or [{}]
        ai_profiles = cfg["ai_profiles"] or [{}]
        ai_idx = max(0, min(cfg["active_ai"], len(ai_profiles) - 1))
        acc_idx = max(0, min(cfg["active_account"], len(accounts) - 1))
        acc = accounts[acc_idx] if accounts else {}
        ai = ai_profiles[ai_idx] if ai_profiles else {}
        return {
            "oj_url": cfg["oj_url"],
            "username": acc.get("username", ""),
            "password": acc.get("password", ""),
            "api_key": ai.get("api_key", ""),
            "api_url": ai.get("api_url", ""),
            "model": ai.get("model", ""),
            "pushplus_enabled": cfg["pushplus_enabled"],
            "pushplus_token": cfg["pushplus_token"],
        }

    def set_config(self, cfg):
        """用 dict 填充 UI；兼容旧扁平 schema。"""
        self._loading = True
        cfg = self._normalize_cfg(cfg)

        self.input_oj_url.setText(cfg.get("oj_url", ""))

        # 账号
        self._accounts = list(cfg.get("accounts", []))
        if not self._accounts:
            self._accounts = [{"username": "", "password": ""}]
        self.combo_account.clear()
        for acc in self._accounts:
            self.combo_account.addItem(acc.get("username", "") or "(空)")
        active_acc = cfg.get("active_account", 0)
        if not (0 <= active_acc < len(self._accounts)):
            active_acc = 0
        self.combo_account.setCurrentIndex(active_acc)
        self.input_username.setText(self._accounts[active_acc].get("username", ""))
        self.input_password.setText(self._accounts[active_acc].get("password", ""))

        # AI 配置
        self._ai_profiles = list(cfg.get("ai_profiles", []))
        if not self._ai_profiles:
            self._ai_profiles = [{"api_key": "", "api_url": "", "model": ""}]
        self.combo_ai.clear()
        for prof in self._ai_profiles:
            self.combo_ai.addItem(prof.get("model", "") or "(空)")
        active_ai = cfg.get("active_ai", 0)
        if not (0 <= active_ai < len(self._ai_profiles)):
            active_ai = 0
        self.combo_ai.setCurrentIndex(active_ai)
        self.input_api_key.setText(self._ai_profiles[active_ai].get("api_key", ""))
        self.input_api_url.setText(self._ai_profiles[active_ai].get("api_url", ""))
        self.input_model.setText(self._ai_profiles[active_ai].get("model", ""))

        # PushPlus
        pushplus_enabled = cfg.get("pushplus_enabled", False)
        self.chk_pushplus.setChecked(pushplus_enabled)
        self.input_pushplus_token.setText(cfg.get("pushplus_token", ""))
        self._set_pushplus_input_enabled(pushplus_enabled)

        self._loading = False

    def load_config(self):
        """从 JSON 文件读取配置"""
        if not os.path.exists(CONFIG_FILE):
            self._ensure_default_state()
            return
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            self.set_config(cfg)
        except Exception as e:
            print(f"加载配置文件失败: {e}")
            self._ensure_default_state()

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

    def import_config(self):
        """从外部 JSON 文件导入配置，覆盖当前表单"""
        path, _ = QFileDialog.getOpenFileName(
            self, "选择配置文件", BASE_DIR, "JSON 配置文件 (*.json);;所有文件 (*.*)"
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except json.JSONDecodeError as e:
            QMessageBox.critical(self, "导入失败", f"文件不是有效的 JSON：\n{e}")
            return
        except Exception as e:
            QMessageBox.critical(self, "导入失败", f"读取文件失败：\n{e}")
            return

        # 兼容旧版/外部配置：只读取已知字段，缺失字段保持默认
        known = {
            "oj_url", "username", "password",
            "api_key", "api_url", "model",
            "pushplus_enabled", "pushplus_token",
            "accounts", "ai_profiles", "active_account", "active_ai",
        }
        cfg = {k: v for k, v in cfg.items() if k in known}
        if not cfg:
            QMessageBox.warning(self, "导入失败", "文件中未找到可识别的配置字段。")
            return

        self.set_config(cfg)
        main_win = self.window()
        if hasattr(main_win, 'page_logs'):
            main_win.page_logs.append_log(f"已从外部文件导入配置: {path}", "success")
            main_win.page_logs.append_log("点击「保存配置」可将其写入默认配置文件。", "info")

        reply = QMessageBox.question(
            self, "导入成功",
            f"已加载配置：\n{path}\n\n是否立即保存为默认配置？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
        )
        if reply == QMessageBox.Yes:
            self.save_config()

    def export_config(self):
        """将当前表单配置导出为 JSON 文件"""
        default_name = "oj_config.json"
        path, _ = QFileDialog.getSaveFileName(
            self, "导出配置文件", os.path.join(BASE_DIR, default_name),
            "JSON 配置文件 (*.json);;所有文件 (*.*)"
        )
        if not path:
            return
        try:
            cfg = self.get_config()
            with open(path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
        except Exception as e:
            QMessageBox.critical(self, "导出失败", f"写入文件失败：\n{e}")
            return
        main_win = self.window()
        if hasattr(main_win, 'page_logs'):
            main_win.page_logs.append_log(f"配置已导出: {path}", "success")
