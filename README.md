# b2bcrm — Local CRM for B2B Sales Department

A simple CRM system for working with legal entities. No internet required. All data stays on your computer.

Простая CRM-система для работы с юридическими лицами. Не требует интернета. Вся база на вашем компьютере.

---

## Features | Возможности

- **Client Management** — counterparty cards, contact history, full-text search
- **Sales Control** — dashboard with problem clients, SLA monitoring, import from ViSet
- **Reporting** — sales funnel, manager activity, database dynamics, Excel export
- **Encryption** — all personal data encrypted, tied to specific shop

---

## System Requirements | Системные требования

| Version | OS | Architecture |
|--------|-----|-------------|
| Main (PyQt6) | Windows 10/11 | 64-bit |
| Lite (PyQt5) | Windows 7 SP1+ | 32-bit, legacy CPU |

---

## Installation | Установка

1. Download EXE from [Releases](https://github.com/твой_юзернейм/b2bcrm/releases)
2. Place in a separate folder
3. Run
4. On first launch, enter shop name and master password

---

## Documentation | Документация

- [Technical Description](docs/TECHNICAL.md) | Техническое описание
- [User Manual (RU)](docs/Инструкция_менеджера.md) | Инструкция менеджера

---

## Development | Разработка

Python 3.11+, PyQt6, SQLite, cryptography

```bash
pip install pyqt6 pandas cryptography openpyxl pyinstaller
python main_ui.py