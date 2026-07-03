import os
import hashlib
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QFrame, QScrollArea,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
import pandas as pd


class SettingsTab(QWidget):
    """Вкладка «Настройки» — справочники, пароль, импорт/экспорт, бэкап"""

    def __init__(self, crm):
        super().__init__()
        self.crm = crm
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Скроллируемая область для всего содержимого
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        sw = QWidget()
        svl = QVBoxLayout(sw)
        svl.setContentsMargins(30, 30, 30, 30)
        svl.setSpacing(18)

        # Авторизация
        self.auth_widget = QWidget()
        al = QVBoxLayout(self.auth_widget)
        al.setAlignment(Qt.AlignmentFlag.AlignCenter)
        li = QLabel("🔒")
        li.setFont(QFont("Arial", 48))
        li.setAlignment(Qt.AlignmentFlag.AlignCenter)
        al.addWidget(li)
        il = QLabel("Для доступа к панели управления\nвведите пароль руководителя:")
        il.setFont(QFont("Arial", 12, QFont.Weight.Medium))
        il.setAlignment(Qt.AlignmentFlag.AlignCenter)
        il.setStyleSheet("color: #475569; margin-bottom: 15px;")
        al.addWidget(il)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setFixedWidth(300)
        self.password_input.setPlaceholderText("Мастер-пароль")
        self.password_input.setStyleSheet(
            "padding: 8px; border: 1px solid #CBD5E1; border-radius: 6px; font-size: 14px;"
        )
        self.password_input.returnPressed.connect(self._handle_auth)
        al.addWidget(self.password_input, alignment=Qt.AlignmentFlag.AlignCenter)

        self.login_btn = QPushButton("Войти")
        self.login_btn.setFixedWidth(300)
        self.login_btn.setStyleSheet(
            "background-color: #2563EB; color: white; padding: 10px; font-weight: bold; border-radius: 6px; border: none; font-size: 14px;"
        )
        self.login_btn.clicked.connect(self._handle_auth)
        al.addWidget(self.login_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        svl.addWidget(self.auth_widget)

        # Панель управления (скрыта до авторизации)
        self.admin_widget = QWidget()
        adl = QVBoxLayout(self.admin_widget)
        adl.setAlignment(Qt.AlignmentFlag.AlignTop)
        adl.setSpacing(18)

        w = QLabel("⚙️ Панель управления системой")
        w.setFont(QFont("Arial", 15, QFont.Weight.Bold))
        w.setStyleSheet("color: #1E293B; margin-bottom: 10px;")
        adl.addWidget(w)

        ins = "padding: 8px; background-color: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 4px;"
        btn_style = (
            "padding: 10px; border-radius: 4px; border: none; font-weight: bold; font-size: 13px;"
        )

        # ─── Справочники ────────────────────────────────────────────────
        rf = QFrame()
        rf.setStyleSheet("background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px;")
        rl = QVBoxLayout(rf)
        rl.setSpacing(10)
        rl.addWidget(QLabel("📋 Справочники системы"))
        rl.addWidget(QLabel("Типы деятельности (через запятую):"))
        self.types_input = QLineEdit(", ".join(self.crm.get_activity_types()))
        self.types_input.setStyleSheet(ins)
        rl.addWidget(self.types_input)
        rl.addWidget(QLabel("Каналы привлечения (через запятую):"))
        self.sources_input = QLineEdit(", ".join(self.crm.get_lead_sources()))
        self.sources_input.setStyleSheet(ins)
        rl.addWidget(self.sources_input)
        rl.addWidget(QLabel("Статусы (через запятую):"))
        self.status_input = QLineEdit(", ".join(self.crm.get_statuses()))
        self.status_input.setStyleSheet(ins)
        rl.addWidget(self.status_input)
        self.save_rules_btn = QPushButton("💾 Сохранить справочники")
        self.save_rules_btn.setStyleSheet(
            "background-color: #2563EB; color: white;" + btn_style
        )
        self.save_rules_btn.clicked.connect(self._handle_save_rules)
        rl.addWidget(self.save_rules_btn)
        adl.addWidget(rf)
        # ─── SLA-настройки ─────────────────────────────────────────────
        slaf = QFrame()
        slaf.setStyleSheet("background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px;")
        slal = QVBoxLayout(slaf)
        slal.setSpacing(8)
        slal.addWidget(QLabel("⏱️ Настройка SLA (дни для алертов)"))

        sla_config = self.crm.get_sla_config()
        self.sla_inputs = {}

        sla_labels = {
            "Новый": "🔴 Новые (все)",
            "Переговоры": "🟡 Переговоры",
            "Выставлен счет": "⚡ Выставлен счет",
            "Постоянный": "🟢 Постоянные",
            "Смена локации": "🌐 Смена локации",
        }

        for status_key, label in sla_labels.items():
            row = QHBoxLayout()
            lbl = QLabel(label)
            lbl.setStyleSheet("font-weight: bold; color: #475569; font-size: 11px;")
            lbl.setFixedWidth(180)
            inp = QLineEdit()
            if status_key == "Новый":
                inp.setText("0")
                inp.setEnabled(False)
                inp.setToolTip("Новые контрагенты — все требуют контакта")
            else:
                days = sla_config["alerts"].get(status_key, {}).get("days", 7)
                inp.setText(str(days))
            inp.setStyleSheet("padding: 6px; background-color: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 4px; max-width: 60px;")
            row.addWidget(lbl)
            row.addWidget(inp)
            row.addStretch()
            slal.addLayout(row)
            self.sla_inputs[status_key] = inp

        # Реанимация
        row = QHBoxLayout()
        lbl = QLabel("⚠️ Реанимация")
        lbl.setStyleSheet("font-weight: bold; color: #475569; font-size: 11px;")
        lbl.setFixedWidth(180)
        self.sla_reanim_input = QLineEdit(str(sla_config["reanimation"]["days"]))
        self.sla_reanim_input.setStyleSheet("padding: 6px; background-color: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 4px; max-width: 60px;")
        row.addWidget(lbl)
        row.addWidget(self.sla_reanim_input)
        row.addStretch()
        slal.addLayout(row)

        self.save_sla_btn = QPushButton("💾 Сохранить SLA")
        self.save_sla_btn.setStyleSheet(
            "background-color: #2563EB; color: white; padding: 8px; border-radius: 4px; border: none; font-weight: bold; font-size: 12px;"
        )
        self.save_sla_btn.clicked.connect(self._handle_save_sla)
        slal.addWidget(self.save_sla_btn)

        adl.addWidget(slaf)
        # ─── Смена пароля ───────────────────────────────────────────────
        pf = QFrame()
        pf.setStyleSheet("background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px;")
        pl = QVBoxLayout(pf)
        pl.setSpacing(8)
        pl.addWidget(QLabel("🔑 Смена пароля руководителя"))
        self.old_pass_input = QLineEdit()
        self.old_pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.old_pass_input.setPlaceholderText("Текущий пароль")
        self.old_pass_input.setStyleSheet(ins)
        pl.addWidget(self.old_pass_input)
        self.new_pass_input = QLineEdit()
        self.new_pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.new_pass_input.setPlaceholderText("Новый пароль")
        self.new_pass_input.setStyleSheet(ins)
        pl.addWidget(self.new_pass_input)
        self.save_pass_btn = QPushButton("🔄 Сменить пароль")
        self.save_pass_btn.setStyleSheet(
            "background-color: #2563EB; color: white;" + btn_style
        )
        self.save_pass_btn.clicked.connect(self._handle_save_password)
        pl.addWidget(self.save_pass_btn)
        adl.addWidget(pf)

        # ─── Импорт / Экспорт ──────────────────────────────────────────
        iof = QFrame()
        iof.setStyleSheet("background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px;")
        iol = QVBoxLayout(iof)
        iol.setSpacing(10)
        iol.addWidget(QLabel("📥 Импорт и экспорт данных"))

        self.import_base_btn = QPushButton("📤 Загрузить базу из Excel")
        self.import_base_btn.setStyleSheet(
            "background-color: #8B5CF6; color: white;" + btn_style
        )
        self.import_base_btn.clicked.connect(self._handle_import_base)
        iol.addWidget(self.import_base_btn)

        self.export_btn = QPushButton("📥 Выгрузка базы контрагентов")
        self.export_btn.setStyleSheet(
            "background-color: #10B981; color: white;" + btn_style
        )
        self.export_btn.clicked.connect(self._handle_excel_export)
        iol.addWidget(self.export_btn)

        adl.addWidget(iof)

        # ─── Бэкап ─────────────────────────────────────────────────────
        bf = QFrame()
        bf.setStyleSheet("background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px;")
        bl = QVBoxLayout(bf)
        bl.addWidget(QLabel("💿 Безопасность данных"))
        self.backup_btn = QPushButton("📦 Создать резервную копию")
        self.backup_btn.setStyleSheet(
            "background-color: #475569; color: white;" + btn_style
        )
        self.backup_btn.clicked.connect(self._handle_create_backup)
        bl.addWidget(self.backup_btn)
        adl.addWidget(bf)

        adl.addStretch()
        svl.addWidget(self.admin_widget)
        self.admin_widget.hide()

        scroll.setWidget(sw)
        layout.addWidget(scroll)

    # ─── Обработчики ──────────────────────────────────────────────────
    def _handle_auth(self):
        password = self.password_input.text()
        success, msg = self.crm.verify_master_password(password)
        if success:
            self.admin_widget.show()
            self.auth_widget.hide()
            self.password_input.clear()
        else:
            QMessageBox.critical(self, "Ошибка доступа", msg)
            self.password_input.clear()

    def _handle_save_rules(self):
        tv = self.types_input.text().strip()
        sv = self.sources_input.text().strip()
        stv = self.status_input.text().strip()
        pt = [t.strip() for t in tv.split(",") if t.strip()]
        ps = [s.strip() for s in sv.split(",") if s.strip()]
        pst = [s.strip() for s in stv.split(",") if s.strip()]
        if not pt or not ps or not pst:
            QMessageBox.warning(self, "Внимание", "Все справочники должны содержать хотя бы одно значение")
            return
        config = self.crm._load_config()
        config["activity_types"] = pt
        config["lead_sources"] = ps
        config["statuses"] = pst
        self.crm._save_config(config)
        QMessageBox.information(self, "Успех", "✅ Справочники успешно сохранены")

    def _handle_save_sla(self):
        config = self.crm._load_config()
        sla_config = config.get("sla_config", self.crm.DEFAULT_SLA_CONFIG)

        for status_key, inp in self.sla_inputs.items():
            if status_key == "Новый":
                continue
            try:
                days = int(inp.text().strip())
                if days < 1:
                    days = 1
            except ValueError:
                QMessageBox.warning(self, "Ошибка", f"Некорректное значение для статуса «{status_key}»")
                return
            sla_config["alerts"][status_key]["days"] = days

        try:
            reanim_days = int(self.sla_reanim_input.text().strip())
            if reanim_days < 1:
                reanim_days = 1
        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Некорректное значение для реанимации")
            return
        sla_config["reanimation"]["days"] = reanim_days

        config["sla_config"] = sla_config
        self.crm._save_config(config)
        QMessageBox.information(self, "Успех", "✅ SLA-настройки сохранены")

    def _handle_save_password(self):
        old = self.old_pass_input.text()
        new = self.new_pass_input.text().strip()
        if not new:
            QMessageBox.warning(self, "Внимание", "Новый пароль не может быть пустым")
            return
        success, _ = self.crm.verify_master_password(old)
        if not success:
            QMessageBox.critical(self, "Ошибка", "Текущий пароль введён неверно")
            return
        config = self.crm._load_config()
        config["master_password_hash"] = hashlib.sha256(new.encode()).hexdigest()
        self.crm._save_config(config)
        self.old_pass_input.clear()
        self.new_pass_input.clear()
        QMessageBox.information(self, "Успех", "🔐 Пароль руководителя успешно изменён")

    def _handle_import_base(self):
        from ui.import_base import ImportBaseDialog
        dialog = ImportBaseDialog(self.crm, self)
        dialog.exec()
        self.crm.refresh_connection()

    def _handle_create_backup(self):
        success, result = self.crm.create_secure_backup()
        if success:
            QMessageBox.information(self, "Успех", f"✅ Резервная копия сохранена:\n\n{result}")
        else:
            QMessageBox.critical(self, "Ошибка", result)

    def _handle_excel_export(self):
        try:
            clients = self.crm.get_all_counterparties()
            export_data = []
            for c in clients:
                export_data.append({
                    "Название": c["name"],
                    "ИНН": c["inn"],
                    "КПП": c["kpp"],
                    "Телефон": c["phone"],
                    "Email": c["email"],
                    "ФИО представителя": c["manager"] if c["manager"] else "",
                    "Канал привлечения": c["lead_source"],
                    "Тип деятельности": c["activity_type"],
                    "Комментарий": c["last_comment"],
                    "ID ViSet": c["viset_id"] if c["viset_id"] != "НЕТ КОДА" else "",
                    "Дата создания": c["created_at"].split(" ")[0] if c["created_at"] else "",
                    "Статус": c["status"],
                    "Сумма продаж": c["sales_amount"] or 0,
                    "Дата последней продажи": c["last_sale_date"].split(" ")[0] if c["last_sale_date"] else "",
                    "Дата след. контакта": c.get("next_contact_date", ""),
                    "Магазин": c.get("shop_name", self.crm.get_shop_name()),
                    "Описание": c.get("description", ""),
                })
            df = pd.DataFrame(export_data)
            column_order = [
                "Название", "ИНН", "КПП", "Телефон", "Email",
                "ФИО представителя", "Канал привлечения", "Тип деятельности",
                "Комментарий", "ID ViSet", "Дата создания", "Статус",
                "Сумма продаж", "Дата последней продажи", "Дата след. контакта", "Магазин", "Описание"
            ]
            df = df[column_order]
            desktop_path = os.path.join(
                os.path.expanduser("~"), "Desktop",
                f"CRM_Export_{self.crm.get_shop_name()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            )
            df.to_excel(desktop_path, index=False)
            QMessageBox.information(self, "Успех", f"✅ Файл сохранён на Рабочий стол:\n\n{desktop_path}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось выполнить выгрузку: {str(e)}")

    def is_locked(self):
        """Проверяет блокировку настроек"""
        return self.crm.is_settings_locked()