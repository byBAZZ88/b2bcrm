import pyzipper  # для сборки EXE
from ui.reports import ReportsTab
from PyQt6.QtGui import QIcon
from ui.first_run import FirstRunDialog
from ui.import_viset import ImportViSetTab
import sys
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTabWidget,
    QVBoxLayout, QHBoxLayout, QLabel, QMessageBox,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from core import CRMCore
from ui.dashboard import DashboardTab
from ui.settings import SettingsTab
from ui.workspace import WorkspaceTab


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("B2B CRM — Администратор магазина")
        self.setWindowIcon(QIcon("icon.ico"))
        self.resize(1280, 820)

        self.crm = CRMCore()

        if self.crm.is_first_run():
            dialog = FirstRunDialog(self)
            if dialog.exec() == dialog.DialogCode.Accepted:
                self.crm.setup_system(dialog.shop_name, dialog.master_password)
            else:
                QMessageBox.critical(self, "Ошибка", "Настройка не завершена. Программа будет закрыта.")
                sys.exit(1)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(15, 15, 15, 10)

        self._build_header(main_layout)
        self._build_tabs(main_layout)
        self._build_footer(main_layout)

        locked, lock_msg = self.settings_tab.is_locked()
        if locked:
            self.tabs.setTabEnabled(3, False)
            QTimer.singleShot(500, lambda: QMessageBox.warning(
                self, "Настройки заблокированы", lock_msg
            ))

    # ═════════════════════════════════════════════════════════════════════
    #  КАРКАС
    # ═════════════════════════════════════════════════════════════════════
    def _build_header(self, parent):
        h = QHBoxLayout()
        t = QLabel("Управление базой контрагентов")
        t.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        t.setStyleSheet("color: #1E293B;")
        self.shop_label = QLabel(f"Магазин: {self.crm.get_shop_name()}")
        self.shop_label.setFont(QFont("Arial", 11, QFont.Weight.Medium))
        self.shop_label.setStyleSheet(
            "background-color: #2563EB; color: white; padding: 6px 12px; border-radius: 6px;"
        )
        h.addWidget(t)
        h.addStretch()
        h.addWidget(self.shop_label)
        parent.addLayout(h)

    def _build_tabs(self, parent):
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::panel { border: 1px solid #CBD5E1; border-radius: 8px; background-color: #FFFFFF; }
            QTabBar::tab { background: #E2E8F0; color: #475569; padding: 10px 20px;
                font-weight: bold; border-top-left-radius: 6px; border-top-right-radius: 6px; margin-right: 2px; }
            QTabBar::tab:selected { background: #FFFFFF; color: #2563EB;
                border: 1px solid #CBD5E1; border-bottom-color: #FFFFFF; }
        """)

        self.dashboard_tab = DashboardTab(self.crm, switch_to_workspace=self._switch_to_workspace_filter)
        self.workspace_tab = WorkspaceTab(self.crm)
        self.import_tab = ImportViSetTab(self.crm)
        self.tab_reports = ReportsTab(self.crm, switch_to_workspace=self._switch_to_workspace_filter)
        self.settings_tab = SettingsTab(self.crm)

        self.tabs.addTab(self.dashboard_tab, "📊 Дашборд")
        self.tabs.addTab(self.workspace_tab, "🖥️ Рабочий стол")
        self.tabs.addTab(self.import_tab, "📥 Загрузка данных")
        self.tabs.addTab(self.tab_reports, "📈 Отчёты")
        self.tabs.addTab(self.settings_tab, "⚙️ Настройки")
        parent.addWidget(self.tabs)
        self.tabs.currentChanged.connect(self._on_tab_changed)

    def _build_footer(self, parent):
        f = QHBoxLayout()
        c = QLabel("b2bcrm beta 1.3.1 | 2026 © byBAZZ")
        c.setFont(QFont("Arial", 9))
        c.setStyleSheet("color: #94A3B8; margin-top: 5px;")
        f.addStretch()
        f.addWidget(c)
        parent.addLayout(f)

    def _switch_to_workspace_filter(self, problem_ids):
        """Переход на Рабочий стол с отфильтрованным списком"""
        self.tabs.setCurrentIndex(1)
        self.workspace_tab.show_filtered(problem_ids)
    def _on_tab_changed(self, index):
        """Обновление вкладок при переключении"""
        if index == 0:
            self.dashboard_tab.refresh()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())