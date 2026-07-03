import re
import os
import sqlite3
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QMessageBox, QFileDialog, QProgressBar, QFrame,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
import pandas as pd
from cryptography.fernet import Fernet
import json


class ViSetImportThread(QThread):
    """Фоновый поток для импорта из ViSet"""
    progress = pyqtSignal(int)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, file_path, crm, report_sunday):
        super().__init__()
        self.file_path = file_path
        self.crm = crm
        self.report_sunday = report_sunday  # Воскресенье отчётной недели
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

    def run(self):
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()

            df = pd.read_excel(self.file_path)
            df = df.iloc[1:]  # Пропустить заголовок
            total = len(df)
            updated = 0
            created = 0
            skipped = 0
            errors = []

            for idx, row in df.iterrows():
                row_num = idx + 2
                try:
                    # Берем название и вычленяем код ViSet
                    raw_name = str(row.iloc[1]).strip() if len(row) > 1 else ""
                    # Формат: "ООО 'КОМПАНИЯ' - XyZ"
                    match = re.match(r"^(.*?)\s*[-–]\s*(\S+)$", raw_name)
                    if match:
                        company_name = match.group(1).strip()
                        viset_code = match.group(2).strip()

                    else:
                        company_name = raw_name
                        viset_code = None

                    # Сумма продаж (второй столбец)
                    amount = 0.0
                    if len(row) > 2:
                        try:
                            amount = float(row.iloc[2])
                        except (ValueError, TypeError):
                            pass

                    if not company_name or amount == 0.0:
                        skipped += 1
                        continue

                    # ─── Сценарий А: Ищем по коду ViSet ─────────────────
                    found = False
                    if viset_code:
                        cursor.execute(
                            "SELECT id, sales_amount FROM counterparties WHERE viset_id = ?",
                            (viset_code,),
                        )
                        res = cursor.fetchone()
                        if res:
                            cp_id = res[0]
                            current_sales = res[1] or 0.0
                            new_sales = current_sales + amount
                            cursor.execute(
                                "UPDATE counterparties SET sales_amount = ?, last_sale_date = ? WHERE id = ?",
                                (new_sales, self._encrypt_val(self.report_sunday), cp_id),
                            )
                            conn.commit()
                            updated += 1
                            found = True
                     # ─── Сценарий Б: Ищем по названию (код не привязан) ─
                    if not found and viset_code:
                        cursor.execute(
                            "SELECT id, name, sales_amount FROM counterparties WHERE viset_id IS NULL OR viset_id = ''"
                        )
                        for row in cursor.fetchall():
                            db_name = self._decrypt_val(row[1])
                            if db_name == company_name:
                                cp_id = row[0]
                                current_sales = row[2]
                                new_sales = current_sales + amount
                                cursor.execute(
                                    "UPDATE counterparties SET viset_id = ?, sales_amount = ?, last_sale_date = ? WHERE id = ?",
                                    (viset_code, new_sales, self._encrypt_val(self.report_sunday), cp_id),
                                )
                                conn.commit()
                                updated += 1
                                found = True
                                break

                    # ─── Сценарий В: Создаём нового ─────────────────────
                    # ─── Сценарий В: Создаём нового ─────────────────────
                    if not found:
                        try:
                            import base64 as b64
                            enc_data = cursor.execute("SELECT enc_data FROM sys_config WHERE id = 1").fetchone()[0]
                            config = json.loads(b64.urlsafe_b64decode(enc_data.encode()).decode())
                            shop_name = config.get("shop_name", "")
                        except Exception:
                            shop_name = ""

                        cursor.execute(
                            """INSERT INTO counterparties (
                                shop_name, name, inn, viset_id, status,
                                lead_source, sales_amount, last_sale_date, created_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                            (
                                shop_name,
                                self._encrypt_val(company_name),
                                None,
                                viset_code if viset_code else None,
                                "Новый",
                                self._encrypt_val("Клиент колл-центра"),
                                amount if amount else 0.0,
                                self._encrypt_val(self.report_sunday),
                                self._encrypt_val(datetime.now().strftime("%Y-%m-%d")),
                            ),
                        )
                        cp_id = cursor.lastrowid
                        cursor.execute(
                            "INSERT INTO status_history (counterparty_id, status_name, changed_at) VALUES (?, ?, ?)",
                            (cp_id, "Новый", datetime.now().strftime("%Y-%m-%d")),
                        )
                        conn.commit()
                        created += 1

                except Exception as e:
                    errors.append(f"Строка {row_num}: {str(e)}")
                    skipped += 1

                self.progress.emit(int((idx + 1) / total * 100))

            conn.close()
            self.finished.emit({
                "total": total,
                "updated": updated,
                "created": created,
                "skipped": skipped,
                "errors": errors[:20],
            })

        except Exception as e:
            self.error.emit(str(e))


class ImportViSetTab(QWidget):
    """Вкладка «Загрузка данных» — еженедельный импорт из ViSet"""

    def __init__(self, crm):
        super().__init__()
        self.crm = crm
        self.file_path = None
        self.report_sunday = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # ─── Информация о периоде ───────────────────────────────────────
        info_frame = QFrame()
        info_frame.setStyleSheet("background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 10px;")
        il = QVBoxLayout(info_frame)
        il.setContentsMargins(24, 20, 24, 20)
        il.setSpacing(12)

        title = QLabel("📥 Еженедельный импорт продаж")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #1E293B;")
        il.addWidget(title)

        self.week_info = QLabel(self._get_week_info())
        self.week_info.setFont(QFont("Arial", 12))
        self.week_info.setStyleSheet("color: #475569; line-height: 160%;")
        self.week_info.setWordWrap(True)
        il.addWidget(self.week_info)

        layout.addWidget(info_frame)

        # ─── Выбор файла ────────────────────────────────────────────────
        file_row = QHBoxLayout()
        self.file_label = QLabel("Файл не выбран")
        self.file_label.setStyleSheet("color: #94A3B8; font-style: italic; padding: 8px;")
        file_row.addWidget(self.file_label, stretch=1)

        browse_btn = QPushButton("📂 Выбрать файл Excel (.xlsx, .xls)")
        browse_btn.setStyleSheet(
            "background-color: #2563EB; color: white; padding: 12px 24px; font-weight: bold; border-radius: 6px; border: none; font-size: 13px;"
        )
        browse_btn.clicked.connect(self._browse_file)
        file_row.addWidget(browse_btn)
        layout.addLayout(file_row)

        # ─── Прогресс ───────────────────────────────────────────────────
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #64748B; font-size: 12px;")
        layout.addWidget(self.status_label)

        layout.addStretch()

        # ─── Кнопка запуска ────────────────────────────────────────────
        self.start_btn = QPushButton("🚀 Запустить импорт")
        self.start_btn.setStyleSheet(
            "background-color: #10B981; color: white; padding: 14px 32px; font-weight: bold; border-radius: 8px; border: none; font-size: 14px;"
        )
        self.start_btn.clicked.connect(self._start_import)
        self.start_btn.setEnabled(False)
        layout.addWidget(self.start_btn)

    def _get_week_info(self):
        """Рассчитывает даты прошлой недели"""
        today = datetime.now()
        # Прошлый понедельник
        days_since_monday = today.weekday()
        last_monday = today - timedelta(days=days_since_monday + 7)
        last_sunday = last_monday + timedelta(days=6)
        self.report_sunday = last_sunday.strftime("%Y-%m-%d")

        return (
            f"📅 Отчётная неделя: с {last_monday.strftime('%d.%m.%Y')} по {last_sunday.strftime('%d.%m.%Y')}\n\n"
            f"Пожалуйста, выгрузите из ViSet отчёт строго за прошедшую неделю."
        )

    def _browse_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Выберите файл Excel из ViSet", "",
            "Excel файлы (*.xlsx *.xls);;Все файлы (*.*)"
        )
        if path:
            self.file_path = path
            self.file_label.setText(os.path.basename(path))
            self.file_label.setStyleSheet("color: #059669; font-weight: bold; padding: 8px;")
            self.start_btn.setEnabled(True)

    def _start_import(self):
        if not self.file_path:
            return

        reply = QMessageBox.question(
            self, "Подтверждение",
            f"Запустить импорт за неделю до {self.report_sunday}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self.start_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Импорт выполняется...")

        self.thread = ViSetImportThread(
            self.file_path,
            self.crm,
            self.report_sunday,
        )
        self.thread.finished.connect(self._on_finished)
        self.thread.error.connect(self._on_error)
        self.thread.progress.connect(self._on_progress)
        self.thread.start()

    def _on_progress(self, value):
        self.progress_bar.setValue(value)
        self.status_label.setText(f"Импорт выполняется... {value}%")

    def _on_finished(self, result):
        self.progress_bar.setValue(100)
        self.status_label.setText("Импорт завершён")

        msg = (
            f"📊 Результаты импорта ViSet:\n\n"
            f"• Всего строк в файле: {result['total']}\n"
            f"• Обновлено существующих: {result['updated']}\n"
            f"• Создано новых: {result['created']}\n"
            f"• Пропущено: {result['skipped']}"
        )

        if result['errors']:
            msg += f"\n\n⚠️ Ошибки (первые 20):\n" + "\n".join(result['errors'])

        QMessageBox.information(self, "Импорт завершён", msg)
        self.start_btn.setEnabled(True)
        self.crm.refresh_connection()
        try:
            success, msg = self.crm.create_secure_backup()
            if not success:
                QMessageBox.warning(self, "Бэкап", f"Ошибка бэкапа: {msg}")
        except Exception as e:
            QMessageBox.critical(self, "Бэкап", f"Исключение при создании бэкапа: {str(e)}")
        # Авто-бэкап после импорта
        success, msg = self.crm.create_secure_backup()
        if success:
            print(f"Бэкап создан: {msg}")

    def _on_error(self, error_msg):
        self.status_label.setText("Ошибка импорта")
        QMessageBox.critical(self, "Ошибка", f"Не удалось выполнить импорт:\n{error_msg}")
        self.start_btn.setEnabled(True)
        self.progress_bar.setVisible(False)