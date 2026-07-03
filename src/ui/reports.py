from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QComboBox, QPushButton, QDateEdit, QSpinBox, QScrollArea,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont
from datetime import datetime, timedelta


class ReportsTab(QWidget):
    """Вкладка «Отчёты» — оперативные показатели и выгрузка"""

    def __init__(self, crm, switch_to_workspace=None):
        super().__init__()
        self.crm = crm
        self.switch_to_workspace = switch_to_workspace
        self.current_start = None
        self.current_end = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # ═══ Верхняя панель: фильтр периода ═══
        filter_frame = QFrame()
        filter_frame.setStyleSheet(
            "background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px;"
        )
        fl = QHBoxLayout(filter_frame)
        fl.setContentsMargins(16, 10, 16, 10)
        fl.setSpacing(10)

        period_label = QLabel("Период:")
        period_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        period_label.setStyleSheet("color: #1E293B;")
        fl.addWidget(period_label)

        # Выпадающий список периода
        self.period_combo = QComboBox()
        self.period_combo.addItems(["День", "Неделя", "Месяц", "Квартал", "Год", "Произвольный"])
        self.period_combo.setStyleSheet(
            "padding: 8px; background-color: #FFFFFF; border: 1px solid #CBD5E1; "
            "border-radius: 6px; font-size: 13px; min-width: 130px;"
        )
        self.period_combo.currentTextChanged.connect(self._on_period_changed)
        fl.addWidget(self.period_combo)

        # Виджеты для выбора дат (меняются в зависимости от периода)
        self.period_stack = QWidget()
        self.period_stack_layout = QHBoxLayout(self.period_stack)
        self.period_stack_layout.setContentsMargins(0, 0, 0, 0)
        self.period_stack_layout.setSpacing(10)
        fl.addWidget(self.period_stack, stretch=1)

        fl.addStretch()

        # Кнопка «Обновить»
        refresh_btn = QPushButton("🔄 Обновить")
        refresh_btn.setStyleSheet(
            "background-color: #2563EB; color: white; padding: 10px 20px; "
            "font-weight: bold; border-radius: 6px; border: none; font-size: 13px;"
        )
        refresh_btn.clicked.connect(self._refresh)
        fl.addWidget(refresh_btn)

        layout.addWidget(filter_frame)

        # Инициализируем период по умолчанию — неделя
        self.period_combo.setCurrentText("Неделя")
        self._on_period_changed("Неделя")
        self.current_start, self.current_end = self._get_period_dates()

        # ═══ Основная область ═══
        main_area = QHBoxLayout()
        main_area.setSpacing(12)

        # Левая панель — выгрузка
        left_panel = QFrame()
        left_panel.setStyleSheet(
            "background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px;"
        )
        left_panel.setFixedWidth(200)
        ll = QVBoxLayout(left_panel)
        ll.setContentsMargins(14, 14, 14, 14)
        ll.setSpacing(12)

        export_title = QLabel("Выгрузка отчётов")
        export_title.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        export_title.setStyleSheet("color: #1E293B;")
        ll.addWidget(export_title)

        excel_btn = QPushButton("📥 Excel")
        excel_btn.setStyleSheet(
            "background-color: #10B981; color: white; padding: 10px; "
            "font-weight: bold; border-radius: 6px; border: none; font-size: 13px;"
        )
        excel_btn.clicked.connect(self._export_excel)
        ll.addWidget(excel_btn)

        pdf_btn = QPushButton("📄 PDF")
        pdf_btn.setStyleSheet(
            "background-color: #E2E8F0; color: #94A3B8; padding: 10px; "
            "font-weight: bold; border-radius: 6px; border: none; font-size: 13px;"
        )
        pdf_btn.setEnabled(False)
        pdf_btn.setToolTip("Будет доступно в версии 1.4")
        ll.addWidget(pdf_btn)

        self.update_time = QLabel("")
        self.update_time.setFont(QFont("Arial", 9))
        self.update_time.setStyleSheet("color: #94A3B8;")
        self.update_time.setWordWrap(True)
        ll.addWidget(self.update_time)

        ll.addStretch()
        main_area.addWidget(left_panel)

        # Правая панель — показатели
        right_panel = QScrollArea()
        right_panel.setWidgetResizable(True)
        right_panel.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.stats_widget = QWidget()
        self.stats_layout = QVBoxLayout(self.stats_widget)
        self.stats_layout.setContentsMargins(0, 0, 0, 0)
        self.stats_layout.setSpacing(12)
        right_panel.setWidget(self.stats_widget)
        main_area.addWidget(right_panel, stretch=1)

        layout.addLayout(main_area, stretch=1)

    def _on_period_changed(self, period):
        """Перестраивает виджеты выбора периода"""
        # Очищаем старые виджеты
        while self.period_stack_layout.count():
            item = self.period_stack_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        ins = "padding: 8px; background-color: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 6px; font-size: 13px;"

        if period == "День":
            self.date_from = QDateEdit()
            self.date_from.setCalendarPopup(True)
            self.date_from.setDate(QDate.currentDate())
            self.date_from.setStyleSheet(ins)
            self.period_stack_layout.addWidget(QLabel("Дата:"))
            self.period_stack_layout.addWidget(self.date_from)

        elif period == "Неделя":
            self.week_spin = QSpinBox()
            self.week_spin.setRange(1, 53)
            self.week_spin.setValue(QDate.currentDate().weekNumber()[0])
            self.week_spin.setStyleSheet(ins)
            self.year_spin_week = QSpinBox()
            self.year_spin_week.setRange(2020, 2100)
            self.year_spin_week.setValue(QDate.currentDate().year())
            self.year_spin_week.setStyleSheet(ins)
            self.period_stack_layout.addWidget(QLabel("Неделя №"))
            self.period_stack_layout.addWidget(self.week_spin)
            self.period_stack_layout.addWidget(QLabel("Год"))
            self.period_stack_layout.addWidget(self.year_spin_week)

        elif period == "Месяц":
            self.month_combo = QComboBox()
            self.month_combo.addItems(["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
                                        "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"])
            self.month_combo.setCurrentIndex(QDate.currentDate().month() - 1)
            self.month_combo.setStyleSheet(ins)
            self.year_spin_month = QSpinBox()
            self.year_spin_month.setRange(2020, 2100)
            self.year_spin_month.setValue(QDate.currentDate().year())
            self.year_spin_month.setStyleSheet(ins)
            self.period_stack_layout.addWidget(self.month_combo)
            self.period_stack_layout.addWidget(self.year_spin_month)

        elif period == "Квартал":
            self.quarter_combo = QComboBox()
            self.quarter_combo.addItems(["1 квартал", "2 квартал", "3 квартал", "4 квартал"])
            current_quarter = (QDate.currentDate().month() - 1) // 3
            self.quarter_combo.setCurrentIndex(current_quarter)
            self.quarter_combo.setStyleSheet(ins)
            self.year_spin_quarter = QSpinBox()
            self.year_spin_quarter.setRange(2020, 2100)
            self.year_spin_quarter.setValue(QDate.currentDate().year())
            self.year_spin_quarter.setStyleSheet(ins)
            self.period_stack_layout.addWidget(self.quarter_combo)
            self.period_stack_layout.addWidget(self.year_spin_quarter)

        elif period == "Год":
            self.year_spin = QSpinBox()
            self.year_spin.setRange(2020, 2100)
            self.year_spin.setValue(QDate.currentDate().year())
            self.year_spin.setStyleSheet(ins)
            self.period_stack_layout.addWidget(QLabel("Год"))
            self.period_stack_layout.addWidget(self.year_spin)

        elif period == "Произвольный":
            self.date_from = QDateEdit()
            self.date_from.setCalendarPopup(True)
            self.date_from.setDate(QDate.currentDate().addMonths(-1))
            self.date_from.setStyleSheet(ins)
            self.date_to = QDateEdit()
            self.date_to.setCalendarPopup(True)
            self.date_to.setDate(QDate.currentDate())
            self.date_to.setStyleSheet(ins)
            self.period_stack_layout.addWidget(QLabel("С:"))
            self.period_stack_layout.addWidget(self.date_from)
            self.period_stack_layout.addWidget(QLabel("По:"))
            self.period_stack_layout.addWidget(self.date_to)

    def _get_period_dates(self):
        """Возвращает (start_date, end_date) в зависимости от выбранного периода"""
        period = self.period_combo.currentText()

        if period == "День":
            d = self.date_from.date()
            start = d.toPyDate()
            end = start

        elif period == "Неделя":
            week = self.week_spin.value()
            year = self.year_spin_week.value()
            # Первый день недели (понедельник) по ISO
            jan4 = datetime(year, 1, 4)
            start = jan4 - timedelta(days=jan4.weekday()) + timedelta(weeks=week - 1)
            end = start + timedelta(days=6)

        elif period == "Месяц":
            month = self.month_combo.currentIndex() + 1
            year = self.year_spin_month.value()
            start = datetime(year, month, 1)
            if month == 12:
                end = datetime(year + 1, 1, 1) - timedelta(days=1)
            else:
                end = datetime(year, month + 1, 1) - timedelta(days=1)

        elif period == "Квартал":
            quarter = self.quarter_combo.currentIndex() + 1
            year = self.year_spin_quarter.value()
            start_month = (quarter - 1) * 3 + 1
            start = datetime(year, start_month, 1)
            end_month = start_month + 2
            if end_month == 12:
                end = datetime(year + 1, 1, 1) - timedelta(days=1)
            else:
                end = datetime(year, end_month + 1, 1) - timedelta(days=1)

        elif period == "Год":
            year = self.year_spin.value()
            start = datetime(year, 1, 1)
            end = datetime(year, 12, 31)

        elif period == "Произвольный":
            start = self.date_from.date().toPyDate()
            end = self.date_to.date().toPyDate()

        return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")

    def _refresh(self):
        """Обновляет все показатели"""
        self.current_start, self.current_end = self._get_period_dates()

        # Очищаем старые показатели
        while self.stats_layout.count():
            item = self.stats_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Получаем данные
        stats = self._get_stats()

        # ═══ Строка 1 ═══
        row1 = QHBoxLayout()
        row1.setSpacing(12)
        row1.addWidget(self._create_stat_tile("Контактов за период", str(stats["total_contacts"]), "#DBEAFE", "#2563EB"))
        row1.addWidget(self._create_stat_tile("Новых клиентов", str(stats["new_clients"]), "#FEE2E2", "#EF4444", "new_clients"))
        row1.addWidget(self._create_stat_tile("Переведено в Переговоры", str(stats["to_negotiation"]), "#FEF3C7", "#D97706", "to_negotiation"))
        self.stats_layout.addLayout(row1)

        # ═══ Строка 2 ═══
        row2 = QHBoxLayout()
        row2.setSpacing(12)
        row2.addWidget(self._create_stat_tile("Выставлено счетов", str(stats["to_invoiced"]), "#DBEAFE", "#2563EB", "to_invoiced"))
        row2.addWidget(self._create_stat_tile("Стали Постоянными", str(stats["to_permanent"]), "#D1FAE5", "#059669", "to_permanent"))
        row2.addWidget(self._create_stat_tile("Отказов и ушедших", str(stats["lost"]), "#F1F5F9", "#6B7280", "lost"))
        self.stats_layout.addLayout(row2)

        # ═══ Строка 3 (мелким) ═══
        row3 = QHBoxLayout()
        row3.setSpacing(12)
        row3.addWidget(self._create_stat_tile("Просрочено контактов (SLA)", str(stats["overdue"]), "#FEE2E2", "#DC2626", "overdue"))
        
        far_count = len(self._get_far_contact_ids())
        row3.addWidget(self._create_stat_tile("Контакт по дате > 100 дн.", str(far_count), "#FEF3C7", "#92400E", "far_contacts"))
        row3.addStretch()
        self.stats_layout.addLayout(row3)

        # ═══ Последние контакты ═══
        last_title = QLabel("Последние зафиксированные контакты")
        last_title.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        last_title.setStyleSheet("color: #1E293B; margin-top: 8px;")
        self.stats_layout.addWidget(last_title)

        table = QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["Время", "Клиент", "Статус", "Комментарий"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        table.setMaximumHeight(150)
        table.setStyleSheet("""
            QTableWidget { background-color: #FFFFFF; border: 1px solid #E2E8F0; gridline-color: #CBD5E1; }
            QHeaderView::section { background-color: #F1F5F9; color: #475569; font-weight: bold; padding: 6px; border: 1px solid #CBD5E1; }
        """)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        recent = self._get_recent_contacts(5)
        table.setRowCount(len(recent))
        for i, r in enumerate(recent):
            table.setItem(i, 0, QTableWidgetItem(r["date"]))
            table.setItem(i, 1, QTableWidgetItem(r["name"]))
            table.setItem(i, 2, QTableWidgetItem(f"{r['old_status']} → {r['new_status']}"))
            table.setItem(i, 3, QTableWidgetItem(r["comment"][:50]))

        self.stats_layout.addWidget(table)

        self.update_time.setText(f"Данные на:\n{datetime.now().strftime('%d.%m.%Y %H:%M')}")
        self.stats_layout.addStretch()

    def _create_stat_tile(self, title, value, bg, fg, filter_key=None):
        """Создаёт плитку с показателем (кликабельную, если filter_key задан)"""
        frame = QFrame()
        frame.setStyleSheet(
            f"background-color: {bg}; border-radius: 10px; border: 1px solid #E2E8F0;"
        )
        frame.setMinimumHeight(70)
        if filter_key:
            frame.setCursor(Qt.CursorShape.PointingHandCursor)
            frame.setToolTip("Нажмите для просмотра списка")
            frame.mousePressEvent = lambda event, k=filter_key: self._on_tile_click(k)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(4)

        t = QLabel(title)
        t.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        t.setStyleSheet(f"color: {fg};")
        t.setWordWrap(True)

        v = QLabel(str(value))
        v.setFont(QFont("Arial", 22, QFont.Weight.Bold))
        v.setStyleSheet(f"color: {fg};")

        layout.addWidget(t)
        layout.addWidget(v)
        return frame

    def _on_tile_click(self, filter_key):
        """Клик по плитке — переход на Рабочий стол с отфильтрованным списком"""
        if not self.switch_to_workspace:
            return
        
        if filter_key == "overdue":
            # Просроченные контакты
            ids = self._get_overdue_ids()
        elif filter_key == "far_contacts":
            # Контакт по дате > 100 дней
            ids = self._get_far_contact_ids()
        elif filter_key == "new_clients":
            ids = self._get_status_ids("Новый")
        elif filter_key == "to_negotiation":
            ids = self._get_status_ids("Переговоры")
        elif filter_key == "to_invoiced":
            ids = self._get_status_ids("Выставлен счет")
        elif filter_key == "to_permanent":
            ids = self._get_status_ids("Постоянный")
        elif filter_key == "lost":
            ids = self._get_lost_ids()
        else:
            return
        
        if ids:
            self.switch_to_workspace(ids)
        else:
            QMessageBox.information(self, "Нет данных", "Нет клиентов по данному фильтру")

    def _get_overdue_ids(self):
        """Клиенты с превышенным SLA"""
        sla_config = self.crm.get_sla_config()
        clients = self.crm.get_all_counterparties()
        current_date = datetime.now()
        self.crm.cursor.execute(
            "SELECT counterparty_id, MAX(changed_at) FROM status_history GROUP BY counterparty_id"
        )
        last_changes = {row[0]: row[1] for row in self.crm.cursor.fetchall()}
        ids = []
        for c in clients:
            status = c["status"]
            if status in sla_config["alerts"] and status != "Новый":
                limit = sla_config["alerts"][status]["days"]
                if limit == 0:
                    continue
                last = last_changes.get(c["id"])
                if last:
                    try:
                        days = (current_date - datetime.strptime(last.split(" ")[0], "%Y-%m-%d")).days
                        if days > limit:
                            ids.append(c["id"])
                    except Exception:
                        pass
        return ids

    def _get_far_contact_ids(self):
        """Клиенты с датой след. контакта > 100 дней"""
        current_date = datetime.now()
        far_date = (current_date + timedelta(days=100)).strftime("%Y-%m-%d")
        ids = []
        for c in self.crm.get_all_counterparties():
            nd = c.get("next_contact_date", "")
            if nd:
                try:
                    nd_clean = nd.split(" ")[0]
                    if nd_clean > far_date:
                        ids.append(c["id"])
                except Exception:
                    pass
        return ids

    def _get_status_ids(self, status_name):
        """Клиенты с указанным статусом"""
        return [c["id"] for c in self.crm.get_all_counterparties() if c["status"] == status_name]

    def _get_lost_ids(self):
        """Клиенты в статусах Отказ/Смена локации/Ликвидация"""
        lost_statuses = ["Отказ от сотрудничества", "Смена локации", "Ликвидация"]
        return [c["id"] for c in self.crm.get_all_counterparties() if c["status"] in lost_statuses]

    def _get_stats(self):
        """Собирает статистику за период"""
        start = self.current_start
        end = self.current_end

        # Общее количество изменений статуса (контактов)
        self.crm.cursor.execute(
            "SELECT COUNT(*) FROM status_history WHERE changed_at BETWEEN ? AND ?",
            (start, end),
        )
        total_contacts = self.crm.cursor.fetchone()[0]

        # Новых клиентов за период
        self.crm.cursor.execute(
            "SELECT COUNT(*) FROM counterparties WHERE created_at BETWEEN ? AND ?",
            (self.crm._encrypt_val(start), self.crm._encrypt_val(end)),
        )
        new_clients = self.crm.cursor.fetchone()[0] if total_contacts else 0
        # Проще через статус
        self.crm.cursor.execute(
            "SELECT COUNT(*) FROM status_history WHERE status_name = 'Новый' AND changed_at BETWEEN ? AND ?",
            (start, end),
        )
        new_clients = self.crm.cursor.fetchone()[0]

        # Переходов в Переговоры
        self.crm.cursor.execute(
            "SELECT COUNT(*) FROM status_history WHERE status_name = 'Переговоры' AND changed_at BETWEEN ? AND ?",
            (start, end),
        )
        to_negotiation = self.crm.cursor.fetchone()[0]

        # Переходов в Выставлен счет
        self.crm.cursor.execute(
            "SELECT COUNT(*) FROM status_history WHERE status_name = 'Выставлен счет' AND changed_at BETWEEN ? AND ?",
            (start, end),
        )
        to_invoiced = self.crm.cursor.fetchone()[0]

        # Переходов в Постоянный
        self.crm.cursor.execute(
            "SELECT COUNT(*) FROM status_history WHERE status_name = 'Постоянный' AND changed_at BETWEEN ? AND ?",
            (start, end),
        )
        to_permanent = self.crm.cursor.fetchone()[0]

        # Отказов и ушедших
        self.crm.cursor.execute(
            "SELECT COUNT(*) FROM status_history WHERE status_name IN ('Отказ от сотрудничества', 'Смена локации', 'Ликвидация') AND changed_at BETWEEN ? AND ?",
            (start, end),
        )
        lost = self.crm.cursor.fetchone()[0]

        # Среднее время в Новых (от создания до первого перехода в Переговоры)
        self.crm.cursor.execute(
            """SELECT AVG(julianday(sh.changed_at) - julianday(cp.created_at))
               FROM status_history sh
               JOIN counterparties cp ON sh.counterparty_id = cp.id
               WHERE sh.status_name = 'Переговоры'
               AND sh.changed_at BETWEEN ? AND ?""",
            (start, end),
        )
        avg_new = self.crm.cursor.fetchone()[0]
        avg_new_days = round(avg_new) if avg_new else 0

        # Просроченные контакты
        overdue = 0
        sla_config = self.crm.get_sla_config()
        clients = self.crm.get_all_counterparties()
        current_date = datetime.now()
        self.crm.cursor.execute(
            "SELECT counterparty_id, MAX(changed_at) FROM status_history GROUP BY counterparty_id"
        )
        last_changes = {row[0]: row[1] for row in self.crm.cursor.fetchall()}

        for c in clients:
            status = c["status"]
            if status in sla_config["alerts"]:
                limit = sla_config["alerts"][status]["days"]
                if status == "Новый" or limit == 0:
                    continue
                last = last_changes.get(c["id"])
                if last:
                    try:
                        last_clean = last.split(" ")[0]
                        days = (current_date - datetime.strptime(last_clean, "%Y-%m-%d")).days
                        if days > limit:
                            overdue += 1
                    except Exception:
                        pass

        return {
            "total_contacts": total_contacts,
            "new_clients": new_clients,
            "to_negotiation": to_negotiation,
            "to_invoiced": to_invoiced,
            "to_permanent": to_permanent,
            "lost": lost,
            "avg_new_days": avg_new_days,
            "overdue": overdue,
        }

    def _get_recent_contacts(self, limit=5):
        """Последние зафиксированные контакты"""
        self.crm.cursor.execute(
            """SELECT sh.changed_at, cp.name, sh.status_name, 
                      (SELECT sh2.status_name FROM status_history sh2 
                       WHERE sh2.counterparty_id = sh.counterparty_id 
                       AND sh2.changed_at < sh.changed_at 
                       ORDER BY sh2.changed_at DESC LIMIT 1) as old_status,
                      cp.last_comment
               FROM status_history sh
               JOIN counterparties cp ON sh.counterparty_id = cp.id
               ORDER BY sh.changed_at DESC, sh.id DESC LIMIT ?""",
            (limit,),
        )
        result = []
        for row in self.crm.cursor.fetchall():
            result.append({
                "date": row[0],
                "name": self.crm._decrypt_val(row[1]) if row[1] else "?",
                "old_status": row[3] if row[3] else "Новый",
                "new_status": row[2],
                "comment": self.crm._decrypt_val(row[4]) if row[4] else "",
            })
        return result

    def _export_excel(self):
        """Выгружает полный отчёт в Excel"""
        if not self.current_start or not self.current_end:
            QMessageBox.warning(self, "Ошибка", "Нажмите «Обновить» перед экспортом")
            return

        import pandas as pd
        import os
        from datetime import datetime

        start = self.current_start
        end = self.current_end

        # Собираем все данные
        stats = self._get_stats()

        # Создаём writer
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        filename = f"Отчёт_{start}_{end}.xlsx"
        filepath = os.path.join(desktop, filename)

        with pd.ExcelWriter(filepath, engine="openpyxl") as writer:

            # Лист 1: Сводка
            summary = pd.DataFrame([
                ["Контактов за период", stats["total_contacts"]],
                ["Новых клиентов", stats["new_clients"]],
                ["Переведено в Переговоры", stats["to_negotiation"]],
                ["Выставлено счетов", stats["to_invoiced"]],
                ["Стали Постоянными", stats["to_permanent"]],
                ["Отказов и ушедших", stats["lost"]],
                ["Среднее время в Новых (дней)", stats["avg_new_days"]],
                ["Просрочено контактов", stats["overdue"]],
            ], columns=["Показатель", "Значение"])
            summary.to_excel(writer, sheet_name="Сводка", index=False)

            # Лист 2: Воронка (когортный анализ)
            # Берём клиентов, у которых первая запись в истории в периоде
            self.crm.cursor.execute(
                """SELECT DISTINCT counterparty_id FROM status_history 
                   WHERE changed_at BETWEEN ? AND ?
                   AND status_name = 'Новый'""",
                (start, end),
            )
            cohort_ids = [row[0] for row in self.crm.cursor.fetchall()]
            total_in_cohort = len(cohort_ids)

            if total_in_cohort > 0:
                reached = {"Переговоры": 0, "Выставлен счет": 0, "Постоянный": 0}
                for cid in cohort_ids:
                    self.crm.cursor.execute(
                        "SELECT status_name FROM status_history WHERE counterparty_id = ? ORDER BY changed_at",
                        (cid,),
                    )
                    statuses = [row[0] for row in self.crm.cursor.fetchall()]
                    if "Переговоры" in statuses:
                        reached["Переговоры"] += 1
                    if "Выставлен счет" in statuses:
                        reached["Выставлен счет"] += 1
                    if "Постоянный" in statuses:
                        reached["Постоянный"] += 1

                funnel = pd.DataFrame([
                    ["Новый", total_in_cohort, "100%"],
                    ["Переговоры", reached["Переговоры"], f"{reached['Переговоры']/total_in_cohort*100:.0f}%"],
                    ["Выставлен счет", reached["Выставлен счет"], f"{reached['Выставлен счет']/total_in_cohort*100:.0f}%"],
                    ["Постоянный", reached["Постоянный"], f"{reached['Постоянный']/total_in_cohort*100:.0f}%"],
                ], columns=["Этап", "Количество", "Конверсия от когорты"])
            else:
                funnel = pd.DataFrame(columns=["Этап", "Количество", "Конверсия от когорты"])

            funnel.to_excel(writer, sheet_name="Воронка", index=False)

            # Лист 3: Клиенты по статусам
            status_data = []
            for status in self.crm.get_statuses():
                count = sum(1 for c in self.crm.get_all_counterparties() if c["status"] == status)
                status_data.append({"Статус": status, "Количество": count})
            pd.DataFrame(status_data).to_excel(writer, sheet_name="По статусам", index=False)

            # Лист 4: Каналы привлечения
            self.crm.cursor.execute(
                """SELECT sh.counterparty_id, cp.lead_source, sh.status_name
                   FROM status_history sh
                   JOIN counterparties cp ON sh.counterparty_id = cp.id
                   WHERE sh.changed_at BETWEEN ? AND ? AND sh.status_name = 'Новый'""",
                (start, end),
            )
            channels = {}
            for row in self.crm.cursor.fetchall():
                source = self.crm._decrypt_val(row[1]) if row[1] else "Не указан"
                channels[source] = channels.get(source, 0) + 1

            if channels:
                ch_data = sorted(channels.items(), key=lambda x: x[1], reverse=True)
                pd.DataFrame(ch_data, columns=["Канал", "Новых клиентов"]).to_excel(
                    writer, sheet_name="Каналы привлечения", index=False
                )

            # Лист 5: Качество данных
            clients = self.crm.get_all_counterparties()
            no_phone = sum(1 for c in clients if not c["phone"])
            no_email = sum(1 for c in clients if not c["email"])
            no_activity = sum(1 for c in clients if not c["activity_type"])
            no_contacts = 0
            for c in clients:
                self.crm.cursor.execute(
                    "SELECT COUNT(*) FROM status_history WHERE counterparty_id = ? AND status_name != 'Новый'",
                    (c["id"],),
                )
                if self.crm.cursor.fetchone()[0] == 0:
                    no_contacts += 1

            quality = pd.DataFrame([
                ["Без телефона", no_phone],
                ["Без Email", no_email],
                ["Без типа деятельности", no_activity],
                ["Без контактов (только Новый)", no_contacts],
            ], columns=["Проблема", "Количество"])
            quality.to_excel(writer, sheet_name="Качество данных", index=False)

            # Лист 6: Динамика базы по месяцам
            # Собираем за последние 12 месяцев от конца периода
            dynamics = []
            end_dt = datetime.strptime(end, "%Y-%m-%d")
            for i in range(12):
                month_start = (end_dt.replace(day=1) - timedelta(days=1)).replace(day=1)
                month_start = month_start.replace(month=((month_start.month - i - 1) % 12) + 1, 
                                                   year=month_start.year - ((month_start.month - i - 1) // 12))
                month_end = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
                m_start = month_start.strftime("%Y-%m-%d")
                m_end = month_end.strftime("%Y-%m-%d")

                # Новые
                self.crm.cursor.execute(
                    "SELECT COUNT(*) FROM status_history WHERE status_name = 'Новый' AND changed_at BETWEEN ? AND ?",
                    (m_start, m_end),
                )
                new_cnt = self.crm.cursor.fetchone()[0]

                # Ушедшие
                self.crm.cursor.execute(
                    "SELECT COUNT(*) FROM status_history WHERE status_name IN ('Отказ от сотрудничества', 'Смена локации', 'Ликвидация') AND changed_at BETWEEN ? AND ?",
                    (m_start, m_end),
                )
                lost_cnt = self.crm.cursor.fetchone()[0]

                dynamics.append({
                    "Месяц": month_start.strftime("%Y-%m"),
                    "Новые": new_cnt,
                    "Ушедшие": lost_cnt,
                    "Прирост": new_cnt - lost_cnt,
                })

            pd.DataFrame(dynamics).to_excel(writer, sheet_name="Динамика базы", index=False)

        QMessageBox.information(self, "Готово", f"Отчёт сохранён на Рабочий стол:\n{filename}")