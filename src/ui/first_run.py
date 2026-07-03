from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QFrame,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class FirstRunDialog(QDialog):
    """Диалог первой настройки системы"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Первая настройка CRM")
        self.setMinimumSize(450, 380)
        self.resize(480, 400)
        self.setModal(True)
        self.shop_name = None
        self.master_password = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 24, 30, 24)
        layout.setSpacing(16)

        title = QLabel("🚀 Добро пожаловать в B2B CRM")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #1E293B;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        sub = QLabel("Первый запуск системы.\nНастройте основные параметры.")
        sub.setFont(QFont("Arial", 11))
        sub.setStyleSheet("color: #64748B;")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setWordWrap(True)
        layout.addWidget(sub)

        ins = "padding: 10px; background-color: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 6px; font-size: 13px;"

        # Название магазина
        shop_label = QLabel("Название магазина (торговой точки):")
        shop_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        shop_label.setStyleSheet("color: #1E293B;")
        layout.addWidget(shop_label)

        self.shop_input = QLineEdit()
        self.shop_input.setPlaceholderText("Например: ОП Колпино")
        self.shop_input.setStyleSheet(ins)
        self.shop_input.setMaxLength(100)
        layout.addWidget(self.shop_input)

        # Мастер-пароль
        pass_label = QLabel("Мастер-пароль руководителя:")
        pass_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        pass_label.setStyleSheet("color: #1E293B;")
        layout.addWidget(pass_label)

        self.pass_input = QLineEdit()
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pass_input.setPlaceholderText("Минимум 4 символа")
        self.pass_input.setStyleSheet(ins)
        layout.addWidget(self.pass_input)

        # Подтверждение пароля
        confirm_label = QLabel("Подтвердите мастер-пароль:")
        confirm_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        confirm_label.setStyleSheet("color: #1E293B;")
        layout.addWidget(confirm_label)

        self.confirm_input = QLineEdit()
        self.confirm_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_input.setPlaceholderText("Повторите пароль")
        self.confirm_input.setStyleSheet(ins)
        self.confirm_input.returnPressed.connect(self._save)
        layout.addWidget(self.confirm_input)

        # Предупреждение
        warn = QFrame()
        warn.setStyleSheet("background-color: #FEF3C7; border: 1px solid #F59E0B; border-radius: 6px;")
        wl = QVBoxLayout(warn)
        wl.setContentsMargins(12, 10, 12, 10)
        wt = QLabel("⚠️ Внимание! Название магазина нельзя будет изменить.\nЗапишите мастер-пароль — восстановить его невозможно.")
        wt.setFont(QFont("Arial", 9))
        wt.setStyleSheet("color: #92400E;")
        wt.setWordWrap(True)
        wl.addWidget(wt)
        layout.addWidget(warn)

        layout.addStretch()

        # Кнопка
        save_btn = QPushButton("✅ Создать базу данных")
        save_btn.setStyleSheet(
            "background-color: #2563EB; color: white; padding: 14px; font-weight: bold; border-radius: 6px; border: none; font-size: 14px;"
        )
        save_btn.clicked.connect(self._save)
        layout.addWidget(save_btn)

    def _save(self):
        shop = self.shop_input.text().strip()
        pwd = self.pass_input.text()
        confirm = self.confirm_input.text()

        if not shop:
            QMessageBox.warning(self, "Ошибка", "Введите название магазина")
            self.shop_input.setFocus()
            return

        if len(pwd) < 4:
            QMessageBox.warning(self, "Ошибка", "Мастер-пароль должен быть не менее 4 символов")
            self.pass_input.setFocus()
            return

        if pwd != confirm:
            QMessageBox.warning(self, "Ошибка", "Пароли не совпадают")
            self.confirm_input.setFocus()
            return

        self.shop_name = shop
        self.master_password = pwd
        self.accept()