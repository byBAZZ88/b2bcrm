# Technical Description | Техническое описание

b2bcrm v1.3.1
2026 © byBAZZ

---

## 1. Philosophy and Purpose | Философия и назначение

### Problem | Проблема

Retail hardware and construction supply stores work with legal entities (construction companies, management companies, HOAs, manufacturers). Managers track clients in Excel, lose contact history, forget to call back. The manager does not see the real picture of work.

Розничные магазины строительных и хозяйственных товаров работают с юридическими лицами (строительные компании, УК, ТСЖ, производства). Менеджеры ведут учёт в Excel, теряют историю контактов, забывают перезвонить. Руководитель не видит реальной картины работы.

### Solution | Решение

A local CRM system that requires no internet, stores all data on the manager's computer, encrypts personal data, automates sales import from ViSet, monitors SLA deadlines, and provides a dashboard with problem clients.

Локальная CRM-система, не требующая интернета. Все данные на компьютере менеджера. Персональные данные зашифрованы. Автоматический импорт продаж из ViSet. Контроль сроков контактов (SLA). Дашборд с проблемными клиентами.

---

## 2. Project Structure | Структура проекта

```
src/
├── core.py              # Core: database, encryption, business logic
├── main_ui.py           # Main window, tab panel
├── icon.ico             # Application icon
├── crm_data.db          # Database (auto-created on first launch)
├── import_errors.log    # Import error log
├── backup_*.zip         # Auto-backups
│
└── ui/                  # UI modules
    ├── __init__.py
    ├── dashboard.py     # Dashboard tab — SLA tiles + summary
    ├── workspace.py     # Workspace tab — search, client cards, contact fixation
    ├── import_viset.py  # ViSet data import tab
    ├── settings.py      # Settings tab — dictionaries, SLA, import/export
    ├── add_counterparty.py  # New counterparty dialog
    ├── first_run.py     # First setup dialog
    ├── import_base.py   # Excel database import dialog
    └── reports.py       # Reports tab — metrics and export
```

---

## 3. Technology Stack | Технологический стек

| Component | Main (64-bit) | Lite (32-bit) |
|-----------|--------------|---------------|
| Python | 3.11+ | 3.8.6 |
| GUI | PyQt6 | PyQt5 |
| Database | SQLite3 | SQLite3 |
| Encryption | cryptography.fernet (AES-128) | cryptography.fernet (AES-128) |
| Excel | pandas + openpyxl | pandas + openpyxl |
| Build | PyInstaller | PyInstaller |
| OS | Windows 10+ 64-bit | Windows 7 SP1+ 32-bit |

---

## 4. Database | База данных

### sys_config — System Configuration

Single-row table storing encrypted JSON with settings.

Однострочная таблица с зашифрованным JSON-конфигом.

Key fields: `shop_name`, `master_password_hash`, `lock_until`, `crypto_key`, `sla_config`, `activity_types`, `lead_sources`, `statuses`.

Encrypted via base64 (not fernet) because `crypto_key` inside config is needed to initialize fernet.

Шифруется через base64 (не fernet), так как `crypto_key` внутри конфига нужен для инициализации fernet.

### counterparties — Client Database

Main table. Some fields encrypted (Fernet), some open (for SQL queries).

Основная таблица. Часть полей шифрована (Fernet), часть открыта (для SQL-запросов).

Encrypted fields (Fernet): `name`, `inn`, `kpp`, `phone`, `email`, `activity_type`, `lead_source`, `manager_name`, `last_comment`, `last_sale_date`, `created_at`, `next_contact_date`, `description`.

Open fields: `id`, `viset_id` (unique code from ViSet, non-deterministic fernet breaks search), `shop_name`, `status` (needed for WHERE queries), `sales_amount`.

### status_history — Status Change Log

Records every status change with date. Open fields for SQL grouping and filtering.

Фиксирует каждое изменение статуса с датой. Открытые поля для группировки и фильтрации.

---

## 5. Encryption | Шифрование

Encryption key generated on first launch from master password and shop name.

Ключ шифрования генерируется при первом запуске из мастер-пароля и названия магазина.

```python
raw_key = f"{master_password}:{shop_name}:byBAZZ_2026"
crypto_key = base64.urlsafe_b64encode(hashlib.sha256(raw_key.encode()).digest())
self.fernet = Fernet(crypto_key)
```

Fernet uses AES-128 in CBC mode. Each `encrypt()` call produces different ciphertext for the same input (embedded timestamp + random IV). This is why `viset_id` and `status` cannot be encrypted — searching encrypted fields is impossible.

Fernet использует AES-128 в режиме CBC. Каждый вызов `encrypt()` даёт разный шифротекст для одного входа (встроенный timestamp + случайный IV). Поэтому `viset_id` и `status` нельзя шифровать — поиск по шифрованному полю невозможен.

---

## 6. Key Algorithms | Ключевые алгоритмы

### Config Loading | Загрузка конфига

Open DB → read base64-encoded config → decode → extract `crypto_key` → initialize Fernet → decrypt other data.

Открыть БД → прочитать base64-конфиг → декодировать → извлечь `crypto_key` → инициализировать Fernet → расшифровать остальные данные.

### First Launch | Первый запуск

`main_ui.py` checks `is_first_run()` → opens `FirstRunDialog` (shop name + password) → `core.setup_system()` generates `crypto_key`, saves config → database ready.

### Client Search | Поиск клиентов

User enters text (min 3 chars) → `get_all_counterparties()` returns all clients with decrypted fields → concatenated searchable string from `name, inn, kpp, phone, email, manager, lead_source, last_comment, viset_id, description` → case-insensitive substring match → results shown in left table.

### Contact Fixation | Фиксация контакта

Manager opens card → edits details (phone, email, contact person, activity type, description) → selects new status → optionally sets next contact date (for Seasonal/Location Change/Refusal/Date Contact) → enters comment → clicks "Fix Contact" → validation (for Negotiation: phone, email, contact person, activity type required; for Date Contact: next contact date required) → all details + status + comment saved in one transaction → `status_history` record created.

### ViSet Import | Импорт из ViSet

Read Excel (5 columns: №, Name, Amount, Last Year Sales, Growth Rate) → skip header → for each row: parse name "Company Name - XyZ" → extract company name and ViSet code → Scenario A: search by ViSet code (open field) → update amount and date → Scenario B: search by company name among clients without code → bind code, update → Scenario C: create new client with status "New".

### SLA Dashboard | SLA дашборд

For each tile:
- New: all clients with "New" status (regardless of date)
- Date Contact: always shown if no date set or date has arrived
- Others: `days_in_status = today - last_status_change_date`. If `days_in_status > SLA_days` → client shown on tile

---

## 7. Statuses | Статусы

| Status | SLA (days) | Notes |
|--------|-----------|-------|
| New | 0 (all) | Requires immediate contact |
| Negotiation | 7 | Phone, email, contact person, activity type required |
| Invoice Issued | 3 | Payment control |
| Regular | 14 | Scheduled calls |
| Location Change | 0 | Contact by specified date |
| Liquidated | 0 | Excluded from work |
| Refusal | 0 | Contact by specified date |
| Seasonal | 0 | Contact by specified date |
| Date Contact | 0 | Call strictly by specified date |

---

## 8. Version Differences | Различия версий

| Component | Main (PyQt6) | Lite (PyQt5) |
|-----------|-------------|--------------|
| Dialog exec | `exec()` | `exec_()` |
| Alignment | `Qt.AlignmentFlag.AlignCenter` | `Qt.AlignCenter` |
| Cursor | `Qt.CursorShape.PointingHandCursor` | `Qt.PointingHandCursor` |
| Table behavior | `QTableWidget.SelectionBehavior.SelectRows` | `QTableWidget.SelectRows` |
| Header resize | `QHeaderView.ResizeMode.Stretch` | `QHeaderView.Stretch` |
| Message buttons | `QMessageBox.StandardButton.Yes` | `QMessageBox.Yes` |
| Dialog code | `QDialog.DialogCode.Accepted` | `QDialog.Accepted` |
| Size policy | `QSizePolicy.Expanding` | `Qt.Expanding` |

---

## 9. Build | Компиляция

### Main version (64-bit)

```powershell
cd src
pyinstaller --onefile --windowed --name "b2bcrm_v1.3.1" --add-data "ui;ui" --icon=icon.ico main_ui.py
```

### Lite version (32-bit, Win7 SP1+)

```powershell
cd src
python -m PyInstaller --onefile --windowed --name "b2bcrm_x86_v1.3.1" --add-data "ui;ui" --icon=icon.ico main_ui.py
```

---

## 10. Known Issues | Известные проблемы

1. Status overlay in card — when switching between clients in search results, old status not removed. Non-critical.
2. Auto-backup not working in EXE (pyzipper + PyInstaller issue). Postponed.
3. Win7 32-bit: `QComboBox.setEditable(True)` must be called after `addItems()`, otherwise crash.
4. Dashboard recursion in Lite — `removeTab/insertTab` requires `blockSignals(True)` to prevent infinite loop.
5. Dates with time (`2024-01-01 00:00:00`) are truncated to `YYYY-MM-DD` in all parsers.
6. Phone numbers in Excel read as float by pandas — fixed by removing `.0` suffix before validation.

---

© 2026 byBAZZ. All rights reserved.
