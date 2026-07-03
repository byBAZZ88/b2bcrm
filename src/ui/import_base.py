import re
import os
import sqlite3
from datetime import datetime
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QMessageBox, QFileDialog, QProgressBar, QFrame,
    QCheckBox,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
import pandas as pd
from cryptography.fernet import Fernet
import json


class ImportThread(QThread):
    """Фоновый поток для импорта (со своим соединением SQLite)"""
    progress = pyqtSignal(int)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, file_path, crm, skip_duplicates):
        super().__init__()
        self.file_path = file_path
        self.crm = crm
        self.skip_duplicates = skip_duplicates
        self.db_name = crm.db_name
        self.crypto_key = crm.crypto_key
        self.fernet = Fernet(self.crypto_key)

    def _encrypt_val(self, val):
        if val is None or val == "":
            return ""
        return self.fernet.encrypt(str(val).encode()).decode()

    def _decrypt_val(self, val):
        if val is None or val == "":
            return ""
        try:
            return self.fernet.decrypt(val.encode()).decode()
        except Exception:
            return ""

    def _is_inn_duplicate(self, cursor, inn):
        if not inn:
            return False
        cursor.execute("SELECT inn FROM counterparties")
        for row in cursor.fetchall():
            if row[0] and self._decrypt_val(row[0]) == inn:
                return True
        return False

    def _log_error(self, log_path, row_num, name, inn, error_msg):
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"Строка {row_num}: {error_msg}\n")
            f.write(f"  Название: {name if name else '—'}\n")
            f.write(f"  ИНН: {inn if inn else '—'}\n")
            f.write("\n")

    def run(self):
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()

            log_path = os.path.join(os.path.dirname(self.db_name), "import_errors.log")
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(f"Лог импорта от {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Файл: {self.file_path}\n")
                f.write("=" * 60 + "\n\n")

            df = pd.read_excel(self.file_path)
            total = len(df)
            success = 0
            skipped = 0
            error_count = 0

            col_map = {
                "name": "Название", "inn": "ИНН", "kpp": "КПП",
                "phone": "Телефон", "email": "Email",
                "manager": "ФИО представителя", "lead_source": "Канал привлечения",
                "activity_type": "Тип деятельности", "comment": "Комментарий",
                "viset_id": "ID ViSet", "created_at": "Дата создания", "status": "Статус",
                "sales_amount": "Сумма продаж", "last_sale_date": "Дата последней продажи",
                "next_contact_date": "Дата след. контакта", "shop_name_col": "Магазин",
                "description": "Описание",
            }

            today = datetime.now().strftime("%Y-%m-%d")

            for idx, row in df.iterrows():
                row_num = idx + 2
                try:
                    name = str(row.get(col_map["name"], "")).strip()
                    inn = str(row.get(col_map["inn"], "")).strip()
                    kpp = str(row.get(col_map["kpp"], "")).strip()
                    phone = str(row.get(col_map["phone"], "")).strip()
                    email = str(row.get(col_map["email"], "")).strip()
                    manager = str(row.get(col_map["manager"], "")).strip()
                    lead_source = str(row.get(col_map["lead_source"], "")).strip()
                    activity_type = str(row.get(col_map["activity_type"], "")).strip()
                    comment = str(row.get(col_map["comment"], "")).strip()
                    viset_id = str(row.get(col_map["viset_id"], "")).strip()
                    created_at = str(row.get(col_map["created_at"], "")).strip()
                    status = str(row.get(col_map["status"], "")).strip()
                    sales_amount_str = str(row.get(col_map["sales_amount"], "0")).strip()
                    last_sale_date = str(row.get(col_map["last_sale_date"], "")).strip()
                    next_contact_date = str(row.get(col_map["next_contact_date"], "")).strip()
                    shop_name_col = str(row.get(col_map["shop_name_col"], "")).strip()
                    description = str(row.get(col_map["description"], "")).strip()

                    inn = inn.replace(".0", "").replace(" ", "").replace("\xa0", "")
                    kpp = kpp.replace(".0", "").replace(" ", "").replace("\xa0", "")
                    # Телефон: исправляем float из Excel
                    if phone and phone not in ["nan", "NaN", ""]:
                        if phone.endswith(".0"):
                            phone = phone[:-2]
                    phone = re.sub(r"\D", "", phone)
                    if viset_id in ["nan", "NaN", "", "None"]:
                        viset_id = None
                    if created_at in ["nan", "NaN", "", "None"]:
                        created_at = today
                    if status in ["nan", "NaN", "", "None"]:
                        status = "Новый"
                    if sales_amount_str in ["nan", "NaN", ""]:
                        sales_amount_str = "0"
                    try:
                        sales_amount = float(sales_amount_str)
                    except ValueError:
                        sales_amount = 0.0
                    if last_sale_date in ["nan", "NaN", ""]:
                        last_sale_date = None
                    if next_contact_date in ["nan", "NaN", ""]:
                        next_contact_date = None
                    if description in ["nan", "NaN", ""]:
                        description = ""

                    # Магазин: из файла или из конфига БД
                    if shop_name_col and shop_name_col not in ["nan", "NaN", ""]:
                        final_shop_name = shop_name_col
                    else:
                        try:
                            import base64 as b64
                            enc_data = cursor.execute("SELECT enc_data FROM sys_config WHERE id = 1").fetchone()[0]
                            config = json.loads(b64.urlsafe_b64decode(enc_data.encode()).decode())
                            final_shop_name = config.get("shop_name", "")
                        except Exception:
                            final_shop_name = ""

                    if not name or name in ["nan", "NaN", ""]:
                        self._log_error(log_path, row_num, name, inn, "Пустое название")
                        skipped += 1
                        error_count += 1
                        continue

                    if not inn or inn in ["nan", "NaN", ""]:
                        self._log_error(log_path, row_num, name, inn, "Пустой ИНН")
                        skipped += 1
                        error_count += 1
                        continue

                    if not (len(inn) == 10 or len(inn) == 12) or not inn.isdigit():
                        self._log_error(log_path, row_num, name, inn, f"Некорректный ИНН: {inn}")
                        skipped += 1
                        error_count += 1
                        continue

                    if self._is_inn_duplicate(cursor, inn):
                        if self.skip_duplicates:
                            skipped += 1
                            continue
                        else:
                            self._log_error(log_path, row_num, name, inn, "Дубликат ИНН")
                            skipped += 1
                            error_count += 1
                            continue

                    # КПП — опционально
                    if kpp and kpp not in ["nan", "NaN", ""]:
                        if len(kpp) != 9 or not kpp.isdigit():
                            kpp = ""

                    # Телефон — опционально
                    if phone and phone not in ["nan", "NaN"]:
                        if len(phone) != 11 or not phone.startswith("7"):
                            phone = ""

                    valid_statuses = ["Новый", "Переговоры", "Выставлен счет", "Постоянный", "Смена локации", "Ликвидация", "Отказ от сотрудничества", "Сезонный", "Контакт по дате"]
                    if status not in valid_statuses:
                        status = "Новый"

                    cursor.execute(
                        """INSERT INTO counterparties (
                            shop_name, name, inn, kpp, phone, manager_name,
                            lead_source, last_comment, status, viset_id,
                            sales_amount, last_sale_date, created_at, next_contact_date, description
                          ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            final_shop_name,
                            self._encrypt_val(name),
                            self._encrypt_val(inn),
                            self._encrypt_val(kpp) if kpp not in ["nan", "NaN", ""] else None,
                            self._encrypt_val(phone) if phone and phone not in ["nan", "NaN"] else None,
                            self._encrypt_val(manager) if manager and manager not in ["nan", "NaN", ""] else None,
                            self._encrypt_val(lead_source) if lead_source and lead_source not in ["nan", "NaN", ""] else None,
                            self._encrypt_val(comment) if comment and comment not in ["nan", "NaN", ""] else None,
                            status,
                            viset_id if viset_id else None,
                            sales_amount,
                            self._encrypt_val(last_sale_date) if last_sale_date else None,
                            self._encrypt_val(created_at),
                            self._encrypt_val(next_contact_date) if next_contact_date else None,
                            self._encrypt_val(description) if description else None,
                        ),
                    )

                    cp_id = cursor.lastrowid
                    cursor.execute(
                        "INSERT INTO status_history (counterparty_id, status_name, changed_at) VALUES (?, ?, ?)",
                        (cp_id, status, created_at),
                    )

                    conn.commit()
                    success += 1

                except Exception as e:
                    name_val = str(row.get(col_map["name"], "?"))
                    inn_val = str(row.get(col_map["inn"], "?"))
                    self._log_error(log_path, row_num, name_val, inn_val, str(e))
                    skipped += 1
                    error_count += 1

                self.progress.emit(int((idx + 1) / total * 100))

            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"\n{'=' * 60}\n")
                f.write(f"Итого: всего {total}, успешно {success}, пропущено {skipped}, ошибок {error_count}\n")

            conn.close()
            self.finished.emit({
                "total": total,
                "success": success,
                "skipped": skipped,
                "errors": error_count,
                "log_path": log_path,
            })

        except Exception as e:
            self.error.emit(str(e))

class ImportBaseDialog(QDialog):
    """Диалог импорта готовой базы контрагентов из Excel"""

    def __init__(self, crm, parent=None):
        super().__init__(parent)
        self.crm = crm
        self.file_path = None
        self.setWindowTitle("Импорт базы контрагентов из Excel")
        self.setMinimumSize(520, 300)
        self.resize(540, 320)
        self.setModal(True)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("📤 Загрузка базы из Excel")
        title.setFont(QFont("Arial", 15, QFont.Weight.Bold))
        title.setStyleSheet("color: #1E293B;")
        layout.addWidget(title)

        info = QFrame()
        info.setStyleSheet("background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px;")
        il = QVBoxLayout(info)
        il.setContentsMargins(14, 12, 14, 12)
        hint = QLabel(
            "Колонки в файле (строго в этом порядке):\n\n"
            "Название | ИНН | КПП | Телефон | Email | ФИО представителя |\n"
            "Канал привлечения | Тип деятельности | Комментарий | ID ViSet |\n"
            "Дата создания | Статус\n\n"
            "• Первая строка — заголовки (пропускается)\n"
            "• Статус: Новый / Переговоры / Выставлен счет / Постоянный / Смена локации\n"
            "• Дата создания: ГГГГ-ММ-ДД (пусто = сегодня)\n"
            "• Статус пустой = «Новый»"
        )
        hint.setFont(QFont("Arial", 9))
        hint.setStyleSheet("color: #475569; line-height: 150%;")
        hint.setWordWrap(True)
        il.addWidget(hint)
        layout.addWidget(info)

        file_row = QHBoxLayout()
        self.file_label = QLabel("Файл не выбран")
        self.file_label.setStyleSheet("color: #94A3B8; font-style: italic; padding: 6px;")
        file_row.addWidget(self.file_label, stretch=1)

        browse_btn = QPushButton("📂 Выбрать файл")
        browse_btn.setStyleSheet(
            "background-color: #2563EB; color: white; padding: 10px 20px; font-weight: bold; border-radius: 6px; border: none; font-size: 13px;"
        )
        browse_btn.clicked.connect(self._browse_file)
        file_row.addWidget(browse_btn)
        layout.addLayout(file_row)

        self.skip_dup_check = QCheckBox("Пропускать дубликаты ИНН (без вывода ошибок)")
        self.skip_dup_check.setChecked(True)
        layout.addWidget(self.skip_dup_check)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #64748B; font-size: 11px;")
        layout.addWidget(self.status_label)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.import_btn = QPushButton("🚀 Загрузить")
        self.import_btn.setStyleSheet(
            "background-color: #10B981; color: white; padding: 12px 24px; font-weight: bold; border-radius: 6px; border: none; font-size: 13px;"
        )
        self.import_btn.clicked.connect(self._start_import)
        self.import_btn.setEnabled(False)
        btn_layout.addWidget(self.import_btn)

        cancel_btn = QPushButton("Закрыть")
        cancel_btn.setStyleSheet(
            "background-color: #E2E8F0; color: #475569; padding: 12px 24px; border-radius: 6px; border: none; font-size: 13px;"
        )
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)

    def _browse_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Выберите файл Excel", "",
            "Excel файлы (*.xlsx *.xls);;Все файлы (*.*)"
        )
        if path:
            self.file_path = path
            self.file_label.setText(os.path.basename(path))
            self.file_label.setStyleSheet("color: #059669; font-weight: bold; padding: 6px;")
            self.import_btn.setEnabled(True)

    def _start_import(self):
        if not self.file_path:
            return

        self.import_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Импорт выполняется...")

        self.thread = ImportThread(
            self.file_path,
            self.crm,
            self.skip_dup_check.isChecked(),
        )
        self.thread.progress.connect(self._on_progress)
        self.thread.finished.connect(self._on_finished)
        self.thread.error.connect(self._on_error)
        self.thread.start()

    def _on_progress(self, value):
        self.progress_bar.setValue(value)
        self.status_label.setText(f"Импорт выполняется... {value}%")

    def _on_finished(self, result):
        self.progress_bar.setValue(100)
        self.status_label.setText("Импорт завершён")

        total = result['total']
        success = result['success']
        skipped = result['skipped']
        errors = result['errors']
        log_path = result.get('log_path', '')

        if errors > 0:
            msg = (
                f"📊 Импорт завершён с ошибками\n\n"
                f"• Всего строк: {total}\n"
                f"• Успешно: {success}\n"
                f"• Пропущено: {skipped}\n"
                f"• Ошибок: {errors}\n\n"
                f"Подробности в файле:\n{log_path}"
            )
            QMessageBox.warning(self, "Импорт завершён", msg)
        else:
            msg = (
                f"✅ Импорт успешно завершён\n\n"
                f"• Всего строк: {total}\n"
                f"• Успешно: {success}\n"
                f"• Пропущено: {skipped}"
            )
            QMessageBox.information(self, "Импорт завершён", msg)

        self.import_btn.setEnabled(True)
        self.accept()

    def _on_error(self, error_msg):
        self.status_label.setText("Ошибка импорта")
        QMessageBox.critical(self, "Ошибка", f"Не удалось выполнить импорт:\n{error_msg}")
        self.import_btn.setEnabled(True)
        self.progress_bar.setVisible(False)