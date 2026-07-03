from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import QDateEdit
from datetime import datetime, timedelta
from ui.add_counterparty import AddCounterpartyDialog
import re
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QFrame, QLineEdit,
    QPushButton, QMessageBox, QScrollArea, QComboBox,
    QSplitter, QTextEdit, QFormLayout, QGroupBox,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor


class WorkspaceTab(QWidget):
    """Вкладка «Рабочий стол» — поиск, карточка, фиксация контактов"""

    def __init__(self, crm):
        super().__init__()
        self.crm = crm
        self.selected_client = None
        self.edit_mode = False
        self.search_results = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Панель поиска
        sf = QFrame()
        sf.setStyleSheet("background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px;")
        sl = QHBoxLayout(sf)
        sl.setContentsMargins(12, 10, 12, 10)
        sl.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск по любым полям базы данных...")
        self.search_input.setStyleSheet(
            "padding: 10px; background-color: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 6px; font-size: 13px;"
        )
        self.search_input.returnPressed.connect(self._perform_search)

        self.status_filter = QComboBox()
        self.status_filter.addItem("Все статусы", None)
        for s in self.crm.get_statuses():
            self.status_filter.addItem(s, s)
        self.status_filter.setStyleSheet(
            "padding: 8px; background-color: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 6px; font-size: 13px; min-width: 140px;"
        )

        sb = QPushButton("🔍 Искать")
        sb.setStyleSheet(
            "background-color: #2563EB; color: white; padding: 10px 24px; font-weight: bold; border-radius: 6px; border: none; font-size: 13px;"
        )
        sb.clicked.connect(self._perform_search)

        ab = QPushButton("+ Новый контрагент")
        ab.setStyleSheet(
            "background-color: #10B981; color: white; padding: 10px 20px; font-weight: bold; border-radius: 6px; border: none; font-size: 13px;"
        )
        ab.clicked.connect(self._add_counterparty_dialog)

        sl.addWidget(self.search_input, stretch=3)
        sl.addWidget(self.status_filter)
        sl.addWidget(sb)
        sl.addWidget(ab)
        layout.addWidget(sf)

        # Сплиттер
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Левая панель
        lp = QFrame()
        lp.setStyleSheet("background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px;")
        ll = QVBoxLayout(lp)
        ll.setContentsMargins(8, 8, 8, 8)
        lt = QLabel("Результаты поиска")
        lt.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        lt.setStyleSheet("color: #475569; padding: 4px;")
        ll.addWidget(lt)

        self.results_table = QTableWidget()
        self.results_table.setColumnCount(3)
        self.results_table.setHorizontalHeaderLabels(["Название", "ИНН", "Статус"])
        hdr = self.results_table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.results_table.setStyleSheet("""
            QTableWidget { background-color: #FFFFFF; border: 1px solid #E2E8F0; gridline-color: #CBD5E1; }
            QHeaderView::section { background-color: #F1F5F9; color: #475569; font-weight: bold; padding: 6px; border: 1px solid #CBD5E1; }
            QTableWidget::item:selected { background-color: #DBEAFE; color: #1E293B; }
        """)
        self.results_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.results_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.results_table.clicked.connect(self._on_result_selected)
        ll.addWidget(self.results_table)
        splitter.addWidget(lp)

        # Правая панель
        self.right_panel = QFrame()
        self.right_panel.setStyleSheet("background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px;")
        self.right_layout = QVBoxLayout(self.right_panel)
        self.right_layout.setContentsMargins(12, 12, 12, 12)
        self.right_layout.setSpacing(8)
        self._show_placeholder()
        splitter.addWidget(self.right_panel)
        splitter.setSizes([450, 650])

        layout.addWidget(splitter, stretch=1)

    # ─── Поиск ─────────────────────────────────────────────────────────
    def _show_placeholder(self):
        while self.right_layout.count():
            item = self.right_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        p = QLabel("👈 Выберите контрагента из списка слева\nчтобы увидеть подробную информацию")
        p.setFont(QFont("Arial", 12))
        p.setStyleSheet("color: #94A3B8;")
        p.setAlignment(Qt.AlignmentFlag.AlignCenter)
        p.setWordWrap(True)
        self.right_layout.addWidget(p)
        self.right_layout.addStretch()

    def _perform_search(self):
        query = self.search_input.text().strip().lower()
        status_filter = self.status_filter.currentData()

        if len(query) < 3:
            QMessageBox.warning(self, "Поиск", "Введите минимум 3 символа для поиска")
            return

        all_clients = self.crm.get_all_counterparties()
        results = []
        for c in all_clients:
            if status_filter and c["status"] != status_filter:
                continue
            searchable = " ".join([
                str(c.get(k, "")) for k in [
                    "name", "inn", "kpp", "phone", "email",
                    "manager", "lead_source",
                    "last_comment", "viset_id", "description"
                ]
            ]).lower()
            if query not in searchable:
                continue
            results.append(c)

        self.search_results = results
        self._populate_results_table(results)
        self.selected_client = None
        self._show_placeholder()

    def _populate_results_table(self, results):
        self.results_table.setRowCount(len(results))
        for row_idx, client in enumerate(results):
            self.results_table.setItem(row_idx, 0, QTableWidgetItem(client["name"]))
            self.results_table.setItem(row_idx, 1, QTableWidgetItem(client["inn"]))
            si = QTableWidgetItem(client["status"])
            colors = {
                "Новый": QColor("#EF4444"), "Переговоры": QColor("#D97706"),
                "Выставлен счет": QColor("#2563EB"), "Постоянный": QColor("#059669"),
                "Смена локации": QColor("#6B7280"),
            }
            si.setForeground(colors.get(client["status"], QColor("#000000")))
            self.results_table.setItem(row_idx, 2, si)

    def _on_result_selected(self):
        row = self.results_table.currentRow()
        if row < 0 or row >= len(self.search_results):
            return
        self.selected_client = self.search_results[row]
        self.edit_mode = False
        self._build_client_card_view()

    # ─── Карточка: просмотр ────────────────────────────────────────────
    def _build_client_card_view(self):
        c = self.selected_client
        if not c:
            return
        while self.right_layout.count():
            item = self.right_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                # Удаляем вложенные layout'ы
                sub = item.layout()
                while sub.count():
                    sub_item = sub.takeAt(0)
                    if sub_item.widget():
                        sub_item.widget().deleteLater()
                sub.deleteLater()

        ct = QLabel(f"📋 {c['name']}")
        ct.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        ct.setStyleSheet("color: #1E293B; padding: 4px 0;")
        self.right_layout.addWidget(ct)

        slayout = QHBoxLayout()
        st = QLabel(f"Статус: {c['status']}")
        st.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        colors = {
            "Новый": "#EF4444", "Переговоры": "#D97706",
            "Выставлен счет": "#2563EB", "Постоянный": "#059669",
            "Смена локации": "#6B7280",
            "Ликвидация": "#94A3B8", "Отказ от сотрудничества": "#94A3B8",
        }
        st.setStyleSheet(f"color: {colors.get(c['status'], '#000000')};")
        slayout.addWidget(st)
        slayout.addStretch()
        self.right_layout.addLayout(slayout)
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background-color: #E2E8F0;")
        sep.setFixedHeight(1)
        self.right_layout.addWidget(sep)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        sw = QWidget()
        fl = QFormLayout(sw)
        fl.setSpacing(8)
        fl.setContentsMargins(4, 8, 4, 8)

        ls = "font-weight: bold; color: #475569; font-size: 11px;"
        vs = "color: #1E293B; font-size: 12px; padding: 2px 0;"

        def af(label, value):
            lbl = QLabel(label)
            lbl.setStyleSheet(ls)
            val = QLabel(str(value) if value else "—")
            val.setStyleSheet(vs)
            val.setWordWrap(True)
            val.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            fl.addRow(lbl, val)

        af("ИНН", c["inn"])
        af("КПП", c["kpp"])
        af("Код ViSet", c["viset_id"])
        af("Магазин", c.get("shop_name", ""))
        af("ФИО представителя", c["manager"] if c["manager"] else "Не указан")
        af("Телефон", c["phone"])
        af("Email", c["email"])
        af("Тип деятельности", c["activity_type"])
        af("Канал привлечения", c["lead_source"])
        af("Сумма продаж", f"{(c['sales_amount'] or 0):,.2f} руб.")
        af("Последняя продажа", c["last_sale_date"])
        af("Дата создания", c["created_at"])
        af("След. контакт", c.get("next_contact_date", ""))
        af("Описание", c.get("description", ""))
        af("Последний комментарий", c["last_comment"])

        scroll.setWidget(sw)
        self.right_layout.addWidget(scroll, stretch=1)

        ob = QPushButton("🔧 Открыть карточку для работы")
        ob.setStyleSheet(
            "background-color: #2563EB; color: white; padding: 12px; font-weight: bold; border-radius: 6px; border: none; font-size: 13px;"
        )
        ob.clicked.connect(self._enter_edit_mode)
        self.right_layout.addWidget(ob)

    # ─── Карточка: редактирование ──────────────────────────────────────
    def _enter_edit_mode(self):
        self.edit_mode = True
        self._build_client_card_edit()

    def _build_client_card_edit(self):
        c = self.selected_client
        if not c:
            return
        while self.right_layout.count():
            item = self.right_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        ct = QLabel(f"✏️ Редактирование: {c['name']}")
        ct.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        ct.setStyleSheet("color: #1E293B; padding: 4px 0;")
        self.right_layout.addWidget(ct)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background-color: #E2E8F0;")
        sep.setFixedHeight(1)
        self.right_layout.addWidget(sep)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        sw = QWidget()
        el = QVBoxLayout(sw)
        el.setSpacing(10)

        ins = "padding: 6px 8px; background-color: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 4px; font-size: 12px;"

        eg = QGroupBox("📝 Редактирование реквизитов")
        eg.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        form = QFormLayout(eg)
        form.setSpacing(8)
        # ИНН и КПП — только для статуса «Новый»
        if c["status"] == "Новый":
            self.edit_inn = QLineEdit(c["inn"])
            self.edit_inn.setPlaceholderText("10 цифр для ЮЛ / 12 цифр для ИП")
            self.edit_inn.setMaxLength(12)
            self.edit_inn.setStyleSheet(ins)
            form.addRow("ИНН:", self.edit_inn)

            self.edit_kpp = QLineEdit(c["kpp"])
            self.edit_kpp.setPlaceholderText("9 цифр для ЮЛ")
            self.edit_kpp.setMaxLength(9)
            self.edit_kpp.setStyleSheet(ins)
            form.addRow("КПП:", self.edit_kpp)
        self.edit_phone = QLineEdit(c["phone"])
        self.edit_phone.setPlaceholderText("7XXXXXXXXXX")
        self.edit_phone.setStyleSheet(ins)
        self.edit_phone.setMaxLength(63)
        form.addRow("Телефон:", self.edit_phone)

        self.edit_email = QLineEdit(c["email"])
        self.edit_email.setPlaceholderText("email@example.com")
        self.edit_email.setStyleSheet(ins)
        form.addRow("Email:", self.edit_email)

        self.edit_manager = QLineEdit(c["manager"])
        self.edit_manager.setPlaceholderText("ФИО представителя")
        self.edit_manager.setStyleSheet(ins)
        form.addRow("ФИО представителя:", self.edit_manager)

        self.edit_activity = QComboBox()
        self.edit_activity.setEditable(True)
        self.edit_activity.addItems(self.crm.get_activity_types())
        if c["activity_type"]:
            self.edit_activity.setCurrentText(c["activity_type"])
        self.edit_activity.setStyleSheet(ins)
        form.addRow("Тип деятельности:", self.edit_activity)

        self.edit_description = QTextEdit()
        self.edit_description.setPlaceholderText("Описание контрагента (до 200 знаков)")
        self.edit_description.setMaximumHeight(70)
        self.edit_description.setMinimumHeight(50)
        self.edit_description.setStyleSheet(ins)
        if c.get("description"):
            self.edit_description.setPlainText(c["description"])
        form.addRow("Описание:", self.edit_description)

        el.addWidget(eg)

        cg = QGroupBox("📞 Фиксация нового контакта")
        cg.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        cf = QFormLayout(cg)
        cf.setSpacing(8)

        self.contact_status = QComboBox()
        self.contact_status.addItems(self.crm.get_statuses())
        self.contact_status.setCurrentText(c["status"])
        self.contact_status.setStyleSheet(ins)
        cf.addRow("Новый статус:", self.contact_status)
        # Дата следующего контакта (календарь)
        from PyQt6.QtWidgets import QDateEdit
        from PyQt6.QtCore import QDate
        self.next_contact_date = QDateEdit()
        self.next_contact_date.setCalendarPopup(True)
        self.next_contact_date.calendarWidget().setStyleSheet("""
            QCalendarWidget QToolButton {
                color: #1E293B;
                font-weight: bold;
                font-size: 13px;
                background-color: #FFFFFF;
            }
            QCalendarWidget QToolButton:hover {
                color: #2563EB;
            }
            QCalendarWidget QSpinBox {
                color: #1E293B;
            }
        """)
        self.next_contact_date.setDisplayFormat("yyyy-MM-dd")
        self.next_contact_date.setMinimumDate(QDate.currentDate())
        self.next_contact_date.setMinimumWidth(140)
        if c.get("next_contact_date"):
            try:
                dt = datetime.strptime(c["next_contact_date"].split(" ")[0], "%Y-%m-%d")
                self.next_contact_date.setDate(QDate(dt.year, dt.month, dt.day))
            except Exception:
                pass
        cf.addRow("След. контакт:", self.next_contact_date)

        self.contact_comment = QTextEdit()
        self.contact_comment.setPlaceholderText("Опишите результат контакта...")
        self.contact_comment.setMaximumHeight(100)
        self.contact_comment.setStyleSheet(ins)
        cf.addRow("Комментарий:", self.contact_comment)

        fb = QPushButton("✅ Зафиксировать контакт")
        fb.setStyleSheet(
            "background-color: #10B981; color: white; padding: 10px; font-weight: bold; border-radius: 6px; border: none; font-size: 13px;"
        )
        fb.clicked.connect(self._fix_contact)
        cf.addRow(fb)
        el.addWidget(cg)

        bb = QPushButton("↩️ Вернуться к просмотру")
        bb.setStyleSheet(
            "background-color: #E2E8F0; color: #475569; padding: 8px; border-radius: 4px; border: none; font-weight: bold;"
        )
        bb.clicked.connect(self._exit_edit_mode)
        el.addWidget(bb)
        el.addStretch()

        scroll.setWidget(sw)
        self.right_layout.addWidget(scroll, stretch=1)

    def _exit_edit_mode(self):
        self.edit_mode = False
        self._build_client_card_view()

    # ─── Фиксация контакта ─────────────────────────────────────────────
    def _fix_contact(self):
        if not self.selected_client:
            return
        c = self.selected_client
        new_status = self.contact_status.currentText()
        # Запрет перевода существующего клиента в статус «Новый»
        if new_status == "Новый" and c["status"] != "Новый":
            QMessageBox.critical(self, "Ошибка", "⚠️ Нельзя перевести существующего клиента обратно в статус «Новый»")
            return
        comment = self.contact_comment.toPlainText().strip()

        if not comment:
            QMessageBox.warning(self, "Внимание", "Необходимо ввести комментарий о контакте")
            return

        phone_raw = self.edit_phone.text().strip()
        phones = [p.strip() for p in phone_raw.split(",") if p.strip()] if phone_raw else []
        cleaned_phones = []
        phone_error = None
        for p in phones:
            p_clean = re.sub(r"\D", "", p)
            if len(p_clean) != 11 or not p_clean.startswith("7"):
                phone_error = f"• Телефон «{p}» (формат: 7XXXXXXXXXX, 11 цифр)"
                break
            cleaned_phones.append(p_clean)
        phone_clean = ", ".join(cleaned_phones) if cleaned_phones else ""
        
        email = self.edit_email.text().strip()
        manager = self.edit_manager.text().strip()
        activity_type = self.edit_activity.currentText().strip()
        # Сохранение ИНН/КПП если статус был Новый
        if c["status"] == "Новый" and hasattr(self, 'edit_inn'):
            new_inn = self.edit_inn.text().strip()
            new_kpp = self.edit_kpp.text().strip()
            
            # Валидация ИНН
            if new_inn:
                if not new_inn.isdigit() or len(new_inn) not in (10, 12):
                    QMessageBox.warning(self, "Ошибка", "ИНН должен содержать 10 или 12 цифр")
                    return
                # Проверка дубликата
                existing = self.crm.get_all_counterparties()
                for cl in existing:
                    if cl["inn"] == new_inn and cl["id"] != c["id"]:
                        QMessageBox.warning(self, "Ошибка", "Контрагент с таким ИНН уже существует")
                        return
            
            # Валидация КПП
            if new_kpp and new_inn and len(new_inn) == 10:
                if not new_kpp.isdigit() or len(new_kpp) != 9:
                    QMessageBox.warning(self, "Ошибка", "КПП должен содержать 9 цифр")
                    return
            
            # Сохраняем
            self.crm.cursor.execute(
                "UPDATE counterparties SET inn = ?, kpp = ? WHERE id = ?",
                (
                    self.crm._encrypt_val(new_inn) if new_inn else None,
                    self.crm._encrypt_val(new_kpp) if new_kpp else None,
                    c["id"],
                ),
            )
            self.crm.conn.commit()
            c["inn"] = new_inn
            c["kpp"] = new_kpp
        description = self.edit_description.toPlainText().strip()
        next_contact = self.next_contact_date.date().toString("yyyy-MM-dd")
        # Проверка даты для статусов с обязательным контактом
        if new_status in ["Сезонный", "Смена локации", "Отказ от сотрудничества", "Контакт по дате"]:
            if not next_contact:
                QMessageBox.critical(self, "Ошибка", 
                    f"⚠️ Для статуса «{new_status}» необходимо указать дату следующего контакта")
                return
            try:
                next_dt = datetime.strptime(next_contact, "%Y-%m-%d")
                today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                if next_dt <= today:
                    QMessageBox.critical(self, "Ошибка", 
                        "⚠️ Дата следующего контакта не может быть сегодняшней или прошлой")
                    return
                if next_dt > today + timedelta(days=100):
                    reply = QMessageBox.question(self, "Подтверждение",
                        f"Дата контакта больше 100 дней ({next_contact}). Это нормально?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                    if reply != QMessageBox.StandardButton.Yes:
                        return
            except ValueError:
                QMessageBox.critical(self, "Ошибка", "⚠️ Некорректный формат даты")
                return

        if new_status == "Переговоры":
            errors = []
            if not phone_clean:
                errors.append("• Телефон (обязателен)")
            elif phone_error:
                errors.append(phone_error)
            if not email:
                errors.append("• Электронная почта (обязательна)")
            else:
                if not re.match(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$', email):
                    errors.append("• Электронная почта (некорректный формат, только латиница)")
            if not manager:
                errors.append("• ФИО представителя (обязательно)")
            if not activity_type:
                errors.append("• Тип деятельности (обязателен)")
            if errors:
                QMessageBox.critical(
                    self, "Ошибка перевода статуса",
                    "⚠️ Для перехода на этап «Переговоры» необходимо заполнить:\n\n" + "\n".join(errors)
                )
                return
        # Валидация для «Контакт по дате»
        if new_status == "Контакт по дате":
            if not next_contact:
                QMessageBox.critical(
                    self, "Ошибка",
                    "⚠️ Для статуса «Контакт по дате» необходимо указать дату следующего контакта (ГГГГ-ММ-ДД)"
                )
                return
            try:
                datetime.strptime(next_contact, "%Y-%m-%d")
            except ValueError:
                QMessageBox.critical(
                    self, "Ошибка",
                    "⚠️ Некорректный формат даты. Используйте ГГГГ-ММ-ДД (например, 2026-12-31)"
                )
                return

        self.crm.cursor.execute(
            "UPDATE counterparties SET phone = ?, email = ?, manager_name = ?, activity_type = ?, description = ? WHERE id = ?",
            (
                self.crm._encrypt_val(phone_clean) if phone_clean else None,
                self.crm._encrypt_val(email) if email else None,
                self.crm._encrypt_val(manager) if manager else None,
                self.crm._encrypt_val(activity_type) if activity_type else None,
                self.crm._encrypt_val(description) if description else None,
                c["id"],
            ),
        )
        self.crm.conn.commit()

        self.crm.update_counterparty_status(c["id"], new_status, email, activity_type, comment, next_contact_date=next_contact if next_contact else None)

        c["phone"] = phone_clean
        c["email"] = email
        c["manager"] = manager
        c["activity_type"] = activity_type
        c["status"] = new_status
        c["next_contact_date"] = next_contact
        c["last_comment"] = comment
        c["description"] = description
        c["next_contact_date"] = next_contact

        self.contact_comment.clear()
        QMessageBox.information(
            self, "Успех",
            f"✅ Данные сохранены\nСтатус изменён на «{new_status}»\nКонтакт зафиксирован"
        )
        # Обновляем список, только если был активный поиск
        if self.search_input.text().strip():
            self._perform_search()
        self._build_client_card_view()

    def _add_counterparty_dialog(self):
        from ui.add_counterparty import AddCounterpartyDialog
        dialog = AddCounterpartyDialog(self.crm, self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            if self.search_input.text().strip():
                self._perform_search()


    # ─── Публичные методы для MainWindow ───────────────────────────────
    def show_filtered(self, client_ids):
        """Показывает отфильтрованный список клиентов по ID"""
        self.search_input.clear()
        self.status_filter.setCurrentIndex(0)
        all_clients = self.crm.get_all_counterparties()
        self.search_results = [c for c in all_clients if c["id"] in client_ids]
        self._populate_results_table(self.search_results)
        self.selected_client = None
        self._show_placeholder()