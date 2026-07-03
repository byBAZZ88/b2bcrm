import re
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QFormLayout, QGroupBox,
    QComboBox, QTextEdit, QCheckBox,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class AddCounterpartyDialog(QDialog):
    """Диалог добавления нового контрагента"""

    def __init__(self, crm, parent=None):
        super().__init__(parent)
        self.crm = crm
        self.setWindowTitle("Добавление нового контрагента")
        self.setMinimumSize(550, 650)
        self.resize(550, 700)
        self.setModal(True)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel("➕ Новый контрагент")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #1E293B;")
        layout.addWidget(title)

        ins = "padding: 8px 8px; background-color: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 4px; font-size: 13px; min-height: 18px;"

        # ─── Основные реквизиты ────────────────────────────────────────
        g1 = QGroupBox("Основные реквизиты")
        g1.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        f1 = QFormLayout(g1)
        f1.setSpacing(8)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("ООО Компания или ИП Иванов И.И.")
        self.name_input.setStyleSheet(ins)
        self.name_input.setMaxLength(200)
        f1.addRow("Название *:", self.name_input)

        self.inn_input = QLineEdit()
        self.inn_input.setPlaceholderText("10 цифр для ЮЛ / 12 цифр для ИП")
        self.inn_input.setStyleSheet(ins)
        self.inn_input.setMaxLength(12)
        self.inn_input.textChanged.connect(self._on_inn_changed)
        f1.addRow("ИНН *:", self.inn_input)

        self.kpp_input = QLineEdit()
        self.kpp_input.setPlaceholderText("9 цифр (только для ЮЛ)")
        self.kpp_input.setStyleSheet(ins)
        self.kpp_input.setMaxLength(9)
        f1.addRow("КПП:", self.kpp_input)

        self.is_ip_check = QCheckBox("Это ИП (12-значный ИНН, КПП не нужен)")
        self.is_ip_check.setFont(QFont("Arial", 9))
        self.is_ip_check.setStyleSheet("color: #64748B;")
        self.is_ip_check.toggled.connect(self._on_ip_toggled)
        f1.addRow(self.is_ip_check)

        layout.addWidget(g1)

        # ─── Контактные данные ─────────────────────────────────────────
        g2 = QGroupBox("Контактные данные")
        g2.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        f2 = QFormLayout(g2)
        f2.setSpacing(8)

        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("7XXXXXXXXXX (11 цифр)")
        self.phone_input.setStyleSheet(ins)
        self.phone_input.setMaxLength(63)
        f2.addRow("Телефон:", self.phone_input)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("email@example.com")
        self.email_input.setStyleSheet(ins)
        f2.addRow("Email:", self.email_input)

        self.manager_input = QLineEdit()
        self.manager_input.setPlaceholderText("Фамилия Имя Отчество")
        self.manager_input.setStyleSheet(ins)
        f2.addRow("ФИО представителя:", self.manager_input)

        layout.addWidget(g2)

        # ─── Дополнительно ─────────────────────────────────────────────
        g3 = QGroupBox("Дополнительно")
        g3.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        f3 = QFormLayout(g3)
        f3.setSpacing(8)

        self.lead_combo = QComboBox()
        self.lead_combo.setEditable(True)
        self.lead_combo.addItems(self.crm.get_lead_sources())
        self.lead_combo.setCurrentText("Холодный звонок")
        self.lead_combo.setStyleSheet(ins)
        f3.addRow("Канал привлечения:", self.lead_combo)

        self.viset_input = QLineEdit()
        self.viset_input.setPlaceholderText("Код из ViSet (появится после первой покупки)")
        self.viset_input.setStyleSheet(ins)
        f3.addRow("ID ViSet:", self.viset_input)

        self.desc_input = QTextEdit()
        self.desc_input.setPlaceholderText("Описание контрагента (до 200 знаков)")
        self.desc_input.setMaximumHeight(70)
        self.desc_input.setMinimumHeight(50)
        self.desc_input.setStyleSheet(ins)
        f3.addRow("Описание:", self.desc_input)

        self.comment_input = QTextEdit()
        self.comment_input.setPlaceholderText("Суть первого контакта, договорённости...")
        self.comment_input.setMaximumHeight(90)
        self.comment_input.setMinimumHeight(80)
        self.comment_input.setSizePolicy(
            self.comment_input.sizePolicy().horizontalPolicy(),
            self.comment_input.sizePolicy().verticalPolicy(). Expanding
        )
        self.comment_input.setStyleSheet(ins)
        f3.addRow("Комментарий:", self.comment_input)

        layout.addWidget(g3)

        # ─── Кнопки ────────────────────────────────────────────────────
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        save_btn = QPushButton("✅ Сохранить контрагента")
        save_btn.setStyleSheet(
            "background-color: #2563EB; color: white; padding: 12px 24px; font-weight: bold; border-radius: 6px; border: none; font-size: 13px;"
        )
        save_btn.clicked.connect(self._save)
        btn_layout.addWidget(save_btn)

        cancel_btn = QPushButton("Отмена")
        cancel_btn.setStyleSheet(
            "background-color: #E2E8F0; color: #475569; padding: 12px 24px; border-radius: 6px; border: none; font-size: 13px;"
        )
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)

    def _on_inn_changed(self, text):
        """Автоопределение ИП по длине ИНН"""
        text = text.strip()
        if len(text) == 12:
            self.is_ip_check.setChecked(True)
        elif len(text) == 10:
            self.is_ip_check.setChecked(False)

    def _on_ip_toggled(self, checked):
        """Блокировка/разблокировка КПП"""
        if checked:
            self.kpp_input.setEnabled(False)
            self.kpp_input.clear()
            self.kpp_input.setPlaceholderText("Для ИП не требуется")
            self.kpp_input.setStyleSheet(
                "padding: 8px; background-color: #F1F5F9; border: 1px solid #CBD5E1; border-radius: 4px; font-size: 12px; color: #94A3B8;"
            )
        else:
            self.kpp_input.setEnabled(True)
            self.kpp_input.setPlaceholderText("9 цифр (только для ЮЛ)")
            self.kpp_input.setStyleSheet(
                "padding: 8px; background-color: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 4px; font-size: 12px;"
            )

    def _save(self):
        """Валидация и сохранение"""
        name = self.name_input.text().strip()
        inn = self.inn_input.text().strip()
        kpp = self.kpp_input.text().strip()
        phone = self.phone_input.text().strip()
        email = self.email_input.text().strip()
        manager = self.manager_input.text().strip()
        lead_source = self.lead_combo.currentText().strip()
        viset_id = self.viset_input.text().strip()
        comment = self.comment_input.toPlainText().strip()
        description = self.desc_input.toPlainText().strip()[:200]
        is_ip = self.is_ip_check.isChecked()

        # Валидация названия
        if not name:
            QMessageBox.warning(self, "Ошибка", "Название контрагента обязательно")
            self.name_input.setFocus()
            return

        # Валидация ИНН
        if not inn:
            QMessageBox.warning(self, "Ошибка", "ИНН обязателен")
            self.inn_input.setFocus()
            return
        if not inn.isdigit():
            QMessageBox.warning(self, "Ошибка", "ИНН должен содержать только цифры")
            self.inn_input.setFocus()
            return
        if is_ip and len(inn) != 12:
            QMessageBox.warning(self, "Ошибка", "ИНН ИП должен содержать 12 цифр")
            self.inn_input.setFocus()
            return
        if not is_ip and len(inn) != 10:
            QMessageBox.warning(self, "Ошибка", "ИНН ЮЛ должен содержать 10 цифр")
            self.inn_input.setFocus()
            return

        # Валидация КПП
        if not is_ip:
            if not kpp:
                QMessageBox.warning(self, "Ошибка", "КПП обязателен для юридических лиц")
                self.kpp_input.setFocus()
                return
            if len(kpp) != 9 or not kpp.isdigit():
                QMessageBox.warning(self, "Ошибка", "КПП должен содержать 9 цифр")
                self.kpp_input.setFocus()
                return

        # Валидация телефона (один или несколько через запятую)
        phones = [p.strip() for p in phone.split(",") if p.strip()] if phone else []
        cleaned_phones = []
        for p in phones:
            p_clean = re.sub(r"\D", "", p)
            if len(p_clean) != 11 or not p_clean.startswith("7"):
                QMessageBox.warning(self, "Ошибка", f"Телефон «{p}» должен быть в формате 7XXXXXXXXXX (11 цифр)")
                self.phone_input.setFocus()
                return
            cleaned_phones.append(p_clean)
        phone_clean = ", ".join(cleaned_phones) if cleaned_phones else ""

        # Сохранение
        success, result = self.crm.add_counterparty(
            name=name,
            inn=inn,
            kpp=kpp if not is_ip else "",
            phone=phone_clean,
            manager=manager,
            lead_source=lead_source if lead_source else "Холодный звонок",
            comment=comment,
            viset_id=viset_id if viset_id else None,
            sales_amount=0.0,
            last_sale_date=None,
            description=description,
        )

        if not success:
            QMessageBox.critical(self, "Ошибка", result)
            return

        QMessageBox.information(self, "Успех", f"✅ Контрагент «{name}» успешно добавлен")
        self.accept()