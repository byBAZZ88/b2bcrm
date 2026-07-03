from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QGridLayout, QMessageBox,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class DashboardTab(QWidget):
    """Вкладка «Дашборд» — 7 плиток + сводная информация"""

    def __init__(self, crm, switch_to_workspace=None):
        super().__init__()
        self.crm = crm
        self.switch_to_workspace = switch_to_workspace
        self._build_ui()

    def _build_ui(self):
        if self.layout():
            QWidget().setLayout(self.layout())

        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 20, 20, 20)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        sw = QWidget()
        sl = QVBoxLayout(sw)
        sl.setSpacing(16)

        stats = self.crm.get_dashboard_stats()

        # Сетка SLA-плиток (2×3)
        grid = QGridLayout()
        grid.setSpacing(12)

        sla_tiles = [t for t in stats["tiles"] if t["key"] != "total"]
        for idx, tile_data in enumerate(sla_tiles):
            tile = self._create_tile(
                tile_data["count"], tile_data["title"], tile_data["hint"],
                tile_data["color"], tile_data["text_color"],
            )
            tile.setCursor(Qt.CursorShape.PointingHandCursor)
            tile.mousePressEvent = lambda event, k=tile_data["key"]: self._on_tile_click(k)
            grid.addWidget(tile, idx // 3, idx % 3)

        sl.addLayout(grid)

        # Плитка «Всего»
        total_data = next((t for t in stats["tiles"] if t["key"] == "total"), None)
        if total_data:
            tf = QFrame()
            tf.setStyleSheet(
                f"background-color: {total_data['color']}; border-radius: 12px; border: 1px solid #E2E8F0;"
            )
            tf.setToolTip(total_data["hint"])
            tf.setFixedHeight(80)
            tl = QHBoxLayout(tf)
            tl.setContentsMargins(24, 12, 24, 12)
            tt = QLabel(total_data["title"])
            tt.setFont(QFont("Arial", 13, QFont.Weight.Bold))
            tt.setStyleSheet(f"color: {total_data['text_color']};")
            tc = QLabel(str(total_data["count"]))
            tc.setFont(QFont("Arial", 28, QFont.Weight.Bold))
            tc.setStyleSheet(f"color: {total_data['text_color']};")
            tc.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            tl.addWidget(tt)
            tl.addStretch()
            tl.addWidget(tc)
            sl.addWidget(tf)

        # Сводная информация
        info = QFrame()
        info.setStyleSheet("background-color: #F8FAFC; border-radius: 10px; border: 1px solid #E2E8F0;")
        il = QVBoxLayout(info)
        il.setContentsMargins(20, 16, 20, 16)
        active = sum(1 for t in sla_tiles if t['count'] > 0)
        txt = (f"📈 СВОДНЫЕ ОПЕРАЦИОННЫЕ ПОКАЗАТЕЛИ:\n\n"
               f"• Общий объем зафиксированных продаж: {stats['total_sales']:,.2f} руб.\n"
               f"• Всего контрагентов в базе: {stats['total']}\n"
               f"• Статусов, требующих внимания: {active} из {len(sla_tiles)}")
        it = QLabel(txt)
        it.setFont(QFont("Arial", 11, QFont.Weight.Medium))
        it.setStyleSheet("color: #475569; line-height: 160%;")
        it.setWordWrap(True)
        il.addWidget(it)
        sl.addWidget(info)
        sl.addStretch()

        scroll.setWidget(sw)
        outer.addWidget(scroll)

    def _create_tile(self, count, title, hint, bg_color, text_color):
        """Создаёт одну плитку дашборда с подсказкой"""
        # Если 0 — блёкло-серая
        if count == 0:
            bg_color = "#F1F5F9"
            text_color = "#94A3B8"
        
        frame = QFrame()
        frame.setStyleSheet(
            f"background-color: {bg_color}; border-radius: 12px; border: 1px solid #E2E8F0;"
        )
        frame.setToolTip(hint)
        frame.setMinimumHeight(135)
        frame.setMaximumHeight(150)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 12, 16, 10)
        layout.setSpacing(4)

        t = QLabel(title)
        t.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        t.setStyleSheet(f"color: {text_color};")
        t.setWordWrap(True)
        t.setFixedHeight(32)

        v = QLabel(str(count))
        v.setFont(QFont("Arial", 30, QFont.Weight.Bold))
        v.setStyleSheet(f"color: {text_color};")
        v.setAlignment(Qt.AlignmentFlag.AlignCenter)

        h = QLabel(hint)
        h.setFont(QFont("Arial", 7))
        h.setStyleSheet(f"color: {text_color}; opacity: 0.65;")
        h.setWordWrap(True)
        h.setFixedHeight(26)

        layout.addWidget(t)
        layout.addWidget(v)
        layout.addWidget(h)
        return frame

    def _on_tile_click(self, filter_key):
        """Клик по плитке → переход на Рабочий стол с фильтром"""
        problem_ids = self.crm.get_clients_by_sla_filter(filter_key)
        if not problem_ids:
            QMessageBox.information(self, "Нет данных", "По данному фильтру нет клиентов для отработки.")
            return
        if self.switch_to_workspace:
            self.switch_to_workspace(problem_ids)

    def refresh(self):
        """Перестраивает дашборд"""
        if self.layout():
            QWidget().setLayout(self.layout())
        self._build_ui()