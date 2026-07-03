import os
import sqlite3
import hashlib
import json
import re
from datetime import datetime, timedelta
import base64
from cryptography.fernet import Fernet
import zipfile


class CRMCore:
    # ─── СТАТУСЫ ВОРОНКИ ПО ТЗ ─────────────────────────────────────────
    STATUS_NEW = "Новый"
    STATUS_NEGOTIATION = "Переговоры"
    STATUS_INVOICED = "Выставлен счет"
    STATUS_PERMANENT = "Постоянный"
    STATUS_SEASONAL = "Сезонный"
    STATUS_FLOATING = "Контакт по дате"
    STATUS_LOCATION_CHANGE = "Смена локации"
    STATUS_LIQUIDATION = "Ликвидация"
    STATUS_REFUSAL = "Отказ от сотрудничества"

    DEFAULT_STATUSES = [
        STATUS_NEW,
        STATUS_NEGOTIATION,
        STATUS_INVOICED,
        STATUS_PERMANENT,
        STATUS_SEASONAL,
        STATUS_FLOATING,
        STATUS_LOCATION_CHANGE,
        STATUS_LIQUIDATION,
        STATUS_REFUSAL,
    ]

    # ─── СПРАВОЧНИКИ ПО УМОЛЧАНИЮ ─────────────────────────────────────
    DEFAULT_ACTIVITY_TYPES = [
        "Производство",
        "Ремонтные бригады",
        "Строительство зданий",
        "Металлоконструкции",
        "Логистика",
        "Дорожное строительство",
        "Водоснабжение и водоотведение",
        "Электромонтажные работы",
        "Озеленение и ландшафты",
        "Производство мебели и декора",
        "Фирма-перекуп",
        "телекоммуникации",
        "Госучреждение",
        "Другое",
    ]

    DEFAULT_LEAD_SOURCES = [
        "Клиент колл-центра",
        "Холодный поиск",
        "Визит в магазин",
        "Рекомендация",
        "Яндекс.Карты / 2ГИС",
        "Повторный клиент",
    ]

    # ─── SLA-КОНФИГУРАЦИЯ ────────────────────────────────────────────
    DEFAULT_SLA_CONFIG = {
        "alerts": {
            "Новый": {
                "days": 0,
                "title": "🔴 Критические алерты: Новые",
                "hint": "Все новые контрагенты требуют немедленного контакта! Срочно свяжись и переведи на этап переговоров.",
                "color": "#FEE2E2",
                "text_color": "#EF4444",
            },
            "Переговоры": {
                "days": 7,
                "title": "🟡 Внимание: Переговоры",
                "hint": "Нет контактов более 7 дней. Клиент остывает. Позвони, предложи акцию и продвинь к сделке.",
                "color": "#FEF3C7",
                "text_color": "#D97706",
            },
            "Выставлен счет": {
                "days": 3,
                "title": "⚡ Контроль: Выставлен счет",
                "hint": "Счет не оплачен более 3 дней. Напомни клиенту о брони товара и уточни дату оплаты.",
                "color": "#DBEAFE",
                "text_color": "#2563EB",
            },
            "Постоянный": {
                "days": 14,
                "title": "🟢 Плановый обзвон: Постоянные",
                "hint": "Нет звонков и покупок 14 дней. Прояви заботу: напомни о себе, спроси, какая нужна помощь.",
                "color": "#D1FAE5",
                "text_color": "#059669",
            },
            "Сезонный": {
                "days": 0,
                "title": "❄️ Сезонный",
                "hint": "Плановый контакт раз в 90 дней. Поздравить с праздниками, узнать планы на следующий сезон.",
                "color": "#E0E7FF",
                "text_color": "#4338CA",
            },
            "Контакт по дате": {
                "days": 0,
                "title": "📅 Контакт по дате",
                "hint": "Звонок строго по указанной дате. Без отработки висит в дашборде.",
                "color": "#FEE2E2",
                "text_color": "#DC2626",
            },
            "Смена локации": {
                "days": 0,
                "title": "🌐 Смена локации",
                "hint": "Плановый прозвон раз в месяц. Проверь, не вернулся ли контрагент работать в наш регион.",
                "color": "#F3F4F6",
                "text_color": "#6B7280",
            },
            "Ликвидация": {
                "days": 0,
                "title": "💀 Ликвидация",
                "hint": "Контрагенты с этим статусом исключены из активной работы.",
                "color": "#F1F5F9",
                "text_color": "#94A3B8",
            },
            "Отказ от сотрудничества": {
                "days": 0,
                "title": "🚫 Отказ от сотрудничества",
                "hint": "Контрагенты, отказавшиеся от работы. Контакт по указанной дате. Проверить, не изменилась ли ситуация.",
                "color": "#F3F4F6",
                "text_color": "#6B7280",
            },
        },
        "reanimation": {
            "days": 90,
            "title": "⚠️ Реанимация: Нет продаж > 90 дней",
            "hint": "Критический отток: клиент не покупал 3 месяца! Выясни причину и попытайся вернуть.",
            "color": "#FEE2E2",
            "text_color": "#DC2626",
        },
    }

    # ─── ИНИЦИАЛИЗАЦИЯ ──────────────────────────────────────────────────
    def __init__(self, db_name="crm_data.db"):
        self.db_name = db_name
        self.failed_attempts = 0
        self.conn = sqlite3.connect(self.db_name)
        self.cursor = self.conn.cursor()
        self._init_database()
        
        # Пытаемся загрузить ключ из конфига
        if not self.is_first_run():
            self._load_crypto_key()
        # Если первый запуск — ключ будет создан в setup_system

    def _load_crypto_key(self):
        """Загружает ключ шифрования из конфига"""
        try:
            self.cursor.execute("SELECT enc_data FROM sys_config WHERE id = 1")
            res = self.cursor.fetchone()
            if res:
                config = json.loads(self._simple_decrypt(res[0]))
                self.crypto_key = config.get("crypto_key", "").encode()
                self.fernet = Fernet(self.crypto_key)
                return True
        except Exception:
            pass
        return False

    def _simple_decrypt(self, val):
        """Простое обратимое шифрование для хранения ключа (base64)"""
        if val is None or val == "":
            return ""
        try:
            return base64.urlsafe_b64decode(val.encode()).decode()
        except Exception:
            return ""
    
    def _simple_encrypt(self, val):
        """Простое обратимое шифрование для хранения ключа (base64)"""
        if val is None or val == "":
            return ""
        return base64.urlsafe_b64encode(val.encode()).decode()

    # ─── ШИФРОВАНИЕ ────────────────────────────────────────────────────
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
            return "[ОШИБКА ДЕКРИПТА]"

    # ─── ИНИЦИАЛИЗАЦИЯ БД ───────────────────────────────────────────────
    def _init_database(self):
        self.cursor.execute(
            """CREATE TABLE IF NOT EXISTS sys_config (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                enc_data TEXT NOT NULL)"""
        )
        self.cursor.execute(
            """CREATE TABLE IF NOT EXISTS counterparties (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                viset_id TEXT,
                shop_name TEXT NOT NULL DEFAULT '',
                name TEXT NOT NULL,
                inn TEXT,
                kpp TEXT,
                phone TEXT,
                email TEXT,
                activity_type TEXT,
                lead_source TEXT DEFAULT 'Клиент колл-центра',
                manager_name TEXT,
                status TEXT NOT NULL DEFAULT 'Новый',
                sales_amount REAL DEFAULT 0.0,
                last_sale_date TEXT,
                last_comment TEXT,
                created_at TEXT,
                next_contact_date TEXT,
                description TEXT)"""
        )
        self.cursor.execute(
            """CREATE UNIQUE INDEX IF NOT EXISTS idx_inn_unique 
            ON counterparties(inn) WHERE inn IS NOT NULL AND inn != ''"""
        )
        self.cursor.execute(
            """CREATE TABLE IF NOT EXISTS status_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                counterparty_id INTEGER NOT NULL,
                status_name TEXT NOT NULL,
                changed_at TEXT NOT NULL,
                FOREIGN KEY (counterparty_id) REFERENCES counterparties(id))"""
        )
        self.conn.commit()

    # ─── ПЕРВЫЙ ЗАПУСК ──────────────────────────────────────────────────
    def is_first_run(self):
        return self.cursor.execute("SELECT COUNT(*) FROM sys_config").fetchone()[0] == 0

    def setup_system(self, shop_name, master_password):
        # Генерируем ключ из пароля + магазина
        raw_key = f"{master_password}:{shop_name}:byBAZZ_2026"
        self.crypto_key = base64.urlsafe_b64encode(hashlib.sha256(raw_key.encode()).digest())
        self.fernet = Fernet(self.crypto_key)
        
        password_hash = hashlib.sha256(master_password.encode()).hexdigest()
        config_dict = {
            "shop_name": shop_name,
            "master_password_hash": password_hash,
            "lock_until": None,
            "sla_config": self.DEFAULT_SLA_CONFIG,
            "activity_types": self.DEFAULT_ACTIVITY_TYPES,
            "lead_sources": self.DEFAULT_LEAD_SOURCES,
            "statuses": self.DEFAULT_STATUSES,
            "crypto_key": self.crypto_key.decode(),
        }
        self.cursor.execute(
            "INSERT OR REPLACE INTO sys_config (id, enc_data) VALUES (1, ?)",
            (self._simple_encrypt(json.dumps(config_dict)),),
        )
        self.conn.commit()

    # ─── РАБОТА С КОНФИГОМ ─────────────────────────────────────────────
    def _load_config(self):
        self.cursor.execute("SELECT enc_data FROM sys_config WHERE id = 1")
        res = self.cursor.fetchone()
        return json.loads(self._simple_decrypt(res[0])) if res else {}

    def _save_config(self, config_dict):
        self.cursor.execute(
            "UPDATE sys_config SET enc_data = ? WHERE id = 1",
            (self._simple_encrypt(json.dumps(config_dict)),),
        )
        self.conn.commit()

    def get_shop_name(self):
        return self._load_config().get("shop_name", "Неизвестный ОП")

    def get_sla_config(self):
        return self._load_config().get("sla_config", self.DEFAULT_SLA_CONFIG)

    def get_activity_types(self):
        return self._load_config().get("activity_types", self.DEFAULT_ACTIVITY_TYPES)

    def get_lead_sources(self):
        return self._load_config().get("lead_sources", self.DEFAULT_LEAD_SOURCES)

    def get_statuses(self):
        return self._load_config().get("statuses", self.DEFAULT_STATUSES)

    # ─── БЛОКИРОВКА НАСТРОЕК ──────────────────────────────────────────
    def is_settings_locked(self):
        config = self._load_config()
        lock_until_str = config.get("lock_until")
        if not lock_until_str:
            return False, ""
        try:
            lock_until = datetime.strptime(lock_until_str, "%Y-%m-%d %H:%M:%S")
            if datetime.now() < lock_until:
                minutes_left = int((lock_until - datetime.now()).total_seconds() / 60) + 1
                return True, f"Доступ заблокирован! Осталось {minutes_left} мин."
            else:
                config["lock_until"] = None
                self._save_config(config)
                return False, ""
        except (ValueError, TypeError):
            return False, ""

    # ─── АВТОРИЗАЦИЯ ────────────────────────────────────────────────────
    def verify_master_password(self, password):
        config = self._load_config()
        lock_until_str = config.get("lock_until")

        if lock_until_str:
            try:
                lock_until = datetime.strptime(lock_until_str, "%Y-%m-%d %H:%M:%S")
                if datetime.now() < lock_until:
                    minutes_left = int((lock_until - datetime.now()).total_seconds() / 60) + 1
                    return False, f"Доступ заблокирован! Попробуйте через {minutes_left} мин."
                else:
                    config["lock_until"] = None
                    self._save_config(config)
            except (ValueError, TypeError):
                pass

        input_hash = hashlib.sha256(password.encode()).hexdigest()
        if input_hash == config.get("master_password_hash"):
            self.failed_attempts = 0
            return True, "Успешно"
        else:
            self.failed_attempts += 1
            if self.failed_attempts >= 3:
                lock_time = (datetime.now() + timedelta(minutes=60)).strftime("%Y-%m-%d %H:%M:%S")
                config["lock_until"] = lock_time
                self._save_config(config)
                self.failed_attempts = 0
                return False, "Превышено количество попыток. Блокировка 60 минут."
            return False, f"Неверный пароль. Осталось попыток: {3 - self.failed_attempts}"

    # ─── ПРОВЕРКА ДУБЛИКАТА ИНН ────────────────────────────────────────
    def _is_inn_duplicate(self, inn, exclude_id=None):
        if not inn or not inn.strip():
            return False
        inn_clean = inn.strip()
        self.cursor.execute("SELECT id, inn FROM counterparties")
        for row in self.cursor.fetchall():
            if exclude_id and row[0] == exclude_id:
                continue
            if row[1] and self._decrypt_val(row[1]) == inn_clean:
                return True
        return False

    # ─── ДОБАВЛЕНИЕ КОНТРАГЕНТА ────────────────────────────────────────
    def add_counterparty(
        self, name, inn, kpp="", phone="", manager="",
        lead_source="", comment="", viset_id=None,
        sales_amount=0.0, last_sale_date=None, custom_date=None,
        description="",
    ):
        inn = str(inn).strip() if inn else ""
        if inn and (not (len(inn) == 10 or len(inn) == 12) or not inn.isdigit()):
            return False, "Ошибка: некорректный ИНН (должен быть 10 или 12 цифр)"
        if inn and self._is_inn_duplicate(inn):
            return False, "Ошибка: контрагент с таким ИНН уже существует"

        kpp = str(kpp).strip() if kpp else ""
        if inn and len(inn) == 10 and (not kpp or len(kpp) != 9 or not kpp.isdigit()):
            return False, "Ошибка: КПП обязателен для ЮЛ (9 цифр)"

        phone = str(phone).strip() if phone else ""
        if phone:
            phones = [p.strip() for p in phone.split(",") if p.strip()]
            cleaned_phones = []
            for p in phones:
                p_clean = re.sub(r"\D", "", p)
                if len(p_clean) != 11 or not p_clean.startswith("7"):
                    return False, f"Ошибка: некорректный телефон «{p}» (формат: 7XXXXXXXXXX)"
                cleaned_phones.append(p_clean)
            phone = ", ".join(cleaned_phones)

        shop_name = self.get_shop_name()
        current_date = custom_date if custom_date else datetime.now().strftime("%Y-%m-%d")

        self.cursor.execute(
            """INSERT INTO counterparties (
                shop_name, name, inn, kpp, phone, manager_name,
                lead_source, last_comment, status, viset_id,
                sales_amount, last_sale_date, created_at, next_contact_date, description
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                shop_name,
                self._encrypt_val(name),
                self._encrypt_val(inn) if inn else None,
                self._encrypt_val(kpp) if kpp else None,
                self._encrypt_val(phone) if phone else None,
                self._encrypt_val(manager) if manager else None,
                self._encrypt_val(lead_source) if lead_source else None,
                self._encrypt_val(comment) if comment else None,
                self.STATUS_NEW,
                viset_id if viset_id else None,
                sales_amount,
                self._encrypt_val(last_sale_date) if last_sale_date else None,
                self._encrypt_val(current_date),
                None,  # next_contact_date
                self._encrypt_val(description) if description else None,
            ),
        )

        cp_id = self.cursor.lastrowid
        self.cursor.execute(
            "INSERT INTO status_history (counterparty_id, status_name, changed_at) VALUES (?, ?, ?)",
            (cp_id, self.STATUS_NEW, current_date),
        )
        self.conn.commit()
        return True, cp_id

    # ─── ОБНОВЛЕНИЕ СТАТУСА ─────────────────────────────────────────────
    def update_counterparty_status(
        self, cp_id, new_status, email="", activity_type="", comment="",
        custom_date=None, next_contact_date=None,
    ):
        current_date = custom_date if custom_date else datetime.now().strftime("%Y-%m-%d")

        self.cursor.execute(
            """UPDATE counterparties 
               SET status = ?, email = ?, activity_type = ?, last_comment = ?, next_contact_date = ? 
               WHERE id = ?""",
            (
                new_status,
                self._encrypt_val(email) if email else None,
                self._encrypt_val(activity_type) if activity_type else None,
                self._encrypt_val(comment) if comment else None,
                self._encrypt_val(next_contact_date) if next_contact_date else None,
                cp_id,
            ),
        )
        self.cursor.execute(
            "INSERT INTO status_history (counterparty_id, status_name, changed_at) VALUES (?, ?, ?)",
            (cp_id, new_status, current_date),
        )
        self.conn.commit()
        return True, "Статус изменен"
    def set_next_contact_date(self, cp_id, next_date):
        """Устанавливает дату следующего контакта"""
        self.cursor.execute(
            "UPDATE counterparties SET next_contact_date = ? WHERE id = ?",
            (self._encrypt_val(next_date) if next_date else None, cp_id),
        )
        self.conn.commit()

    # ─── ПОЛУЧЕНИЕ ВСЕХ КОНТРАГЕНТОВ ──────────────────────────────────
    def get_all_counterparties(self):
        self.cursor.execute(
            """SELECT id, viset_id, name, inn, kpp, manager_name, status, 
                   sales_amount, phone, email, activity_type, lead_source, 
                   last_comment, last_sale_date, shop_name, created_at, next_contact_date,
                   description
            FROM counterparties"""
        )
        result = []
        for row in self.cursor.fetchall():
            result.append({
                "id": row[0],
                "viset_id": row[1] if row[1] else "НЕТ КОДА",
                "name": self._decrypt_val(row[2]),
                "inn": self._decrypt_val(row[3]) if row[3] else "",
                "kpp": self._decrypt_val(row[4]) if row[4] else "",
                "manager": self._decrypt_val(row[5]) if row[5] else "",
                "status": row[6],
                "sales_amount": row[7],
                "phone": self._decrypt_val(row[8]) if row[8] else "",
                "email": self._decrypt_val(row[9]) if row[9] else "",
                "activity_type": self._decrypt_val(row[10]) if row[10] else "",
                "lead_source": self._decrypt_val(row[11]) if row[11] else "",
                "last_comment": self._decrypt_val(row[12]) if row[12] else "",
                "last_sale_date": self._decrypt_val(row[13]) if row[13] else "",
                "shop_name": row[14],
                "created_at": self._decrypt_val(row[15]) if row[15] else "",
                "next_contact_date": self._decrypt_val(row[16]) if row[16] else "",
                "description": self._decrypt_val(row[17]) if row[17] else "",
            })
        return result

    # ─── СТАТИСТИКА ДАШБОРДА ──────────────────────────────────────────
    # ─── СТАТИСТИКА ДАШБОРДА ──────────────────────────────────────────
    def get_dashboard_stats(self):
        clients = self.get_all_counterparties()
        sla_config = self.get_sla_config()
        current_date = datetime.now()
        total_count = len(clients)

        stats = {
            "alerts": {"Новый": 0, "Переговоры": 0, "Выставлен счет": 0,
                        "Постоянный": 0, "Сезонный": 0, "Контакт по дате": 0, "Смена локации": 0,
                        "Ликвидация": 0, "Отказ от сотрудничества": 0},
            "reanimation": 0,
            "total": total_count,
            "total_sales": sum(c["sales_amount"] or 0.0 for c in clients),
            "tiles": [],
        }

        self.cursor.execute(
            "SELECT counterparty_id, MAX(changed_at) FROM status_history GROUP BY counterparty_id"
        )
        last_status_change = {row[0]: row[1] for row in self.cursor.fetchall()}

        for client in clients:
            status = client["status"]
            client_id = client["id"]

            # Новые — все, независимо от даты
            if status == "Новый":
                stats["alerts"]["Новый"] += 1
            elif status in sla_config["alerts"] and status != "Новый":
                limit_days = sla_config["alerts"][status]["days"]
                last_change = last_status_change.get(client_id)
                days_in_status = 0
                
                # Проверка пользовательской даты контакта
                next_date = client.get("next_contact_date")
                
                if status == "Контакт по дате":
                    # Всегда показываем, если нет даты или дата наступила
                    if next_date:
                        try:
                            next_clean = next_date.split(" ")[0]
                            next_dt = datetime.strptime(next_clean, "%Y-%m-%d")
                            if current_date >= next_dt:
                                days_in_status = 1
                        except (ValueError, TypeError):
                            days_in_status = 1
                    else:
                        days_in_status = 1
                
                elif status in ["Сезонный", "Смена локации", "Отказ от сотрудничества"]:
                    if next_date:
                        try:
                            next_clean = next_date.split(" ")[0]
                            next_dt = datetime.strptime(next_clean, "%Y-%m-%d")
                            if current_date >= next_dt:
                                days_in_status = limit_days + 1
                        except (ValueError, TypeError):
                            pass
                
                # Стандартный SLA если не сработала пользовательская дата
                if days_in_status == 0:
                    if last_change:
                        try:
                            last_change_clean = last_change.split(" ")[0]
                            last_change_date = datetime.strptime(last_change_clean, "%Y-%m-%d")
                            days_in_status = (current_date - last_change_date).days
                        except (ValueError, TypeError):
                            pass
                    elif client.get("created_at"):
                        try:
                            created_clean = client["created_at"].split(" ")[0]
                            days_in_status = (current_date - datetime.strptime(created_clean, "%Y-%m-%d")).days
                        except (ValueError, TypeError):
                            pass
                
                if days_in_status > limit_days:
                    stats["alerts"][status] += 1

            # Реанимация
            if (client["sales_amount"] or 0) > 0 and client["last_sale_date"]:
                try:
                    sale_date = datetime.strptime(client["last_sale_date"], "%d.%m.%Y")
                    if (current_date - sale_date).days > sla_config["reanimation"]["days"]:
                        stats["reanimation"] += 1
                except (ValueError, TypeError):
                    pass

        for status_key, alert_cfg in sla_config["alerts"].items():
            stats["tiles"].append({
                "key": f"alert_{status_key}",
                "count": stats["alerts"][status_key],
                "title": alert_cfg["title"],
                "hint": alert_cfg["hint"],
                "color": alert_cfg["color"],
                "text_color": alert_cfg["text_color"],
            })

        reanim_cfg = sla_config["reanimation"]
        stats["tiles"].append({
            "key": "reanimation",
            "count": stats["reanimation"],
            "title": reanim_cfg["title"],
            "hint": reanim_cfg["hint"],
            "color": reanim_cfg["color"],
            "text_color": reanim_cfg["text_color"],
        })

        stats["tiles"].append({
            "key": "total",
            "count": total_count,
            "title": "📋 Всего контрагентов",
            "hint": "Общее количество карточек в базе данных магазина",
            "color": "#DBEAFE",
            "text_color": "#2563EB",
        })

        return stats

    # ─── ПОЛУЧЕНИЕ КЛИЕНТОВ ПО SLA-ФИЛЬТРУ ────────────────────────────
    def get_clients_by_sla_filter(self, filter_key):
        clients = self.get_all_counterparties()
        sla_config = self.get_sla_config()
        current_date = datetime.now()

        self.cursor.execute(
            "SELECT counterparty_id, MAX(changed_at) FROM status_history GROUP BY counterparty_id"
        )
        last_changes = {row[0]: row[1] for row in self.cursor.fetchall()}

        result_ids = []

        for c in clients:
            if filter_key == "alert_Новый":
                if c["status"] == "Новый":
                    result_ids.append(c["id"])

            elif filter_key == "reanimation":
                if (c["sales_amount"] or 0) > 0 and c["last_sale_date"]:
                    try:
                        sale_date = datetime.strptime(c["last_sale_date"], "%d.%m.%Y")
                        if (current_date - sale_date).days > sla_config["reanimation"]["days"]:
                            result_ids.append(c["id"])
                    except (ValueError, TypeError):
                        pass

            elif filter_key.startswith("alert_"):
                status_name = filter_key.replace("alert_", "")
                if c["status"] == status_name:
                    limit_days = sla_config["alerts"][status_name]["days"]
                    last_change = last_changes.get(c["id"])
                    days_in_status = 0
                    
                    next_date = c.get("next_contact_date")
                    
                    if status_name == "Контакт по дате":
                        if next_date:
                            try:
                                next_clean = next_date.split(" ")[0]
                                next_dt = datetime.strptime(next_clean, "%Y-%m-%d")
                                if current_date >= next_dt:
                                    days_in_status = 1
                            except (ValueError, TypeError):
                                days_in_status = 1
                        else:
                            days_in_status = 1
                    
                    elif status_name in ["Сезонный", "Смена локации", "Отказ от сотрудничества"]:
                        if next_date:
                            try:
                                next_clean = next_date.split(" ")[0]
                                next_dt = datetime.strptime(next_clean, "%Y-%m-%d")
                                if current_date >= next_dt:
                                    days_in_status = limit_days + 1
                            except (ValueError, TypeError):
                                pass
                    
                    if days_in_status == 0:
                        if last_change:
                            try:
                                days_in_status = (current_date - datetime.strptime(last_change.split(" ")[0], "%Y-%m-%d")).days
                            except (ValueError, TypeError):
                                pass
                        elif c.get("created_at"):
                            try:
                                days_in_status = (current_date - datetime.strptime(c["created_at"].split(" ")[0], "%Y-%m-%d")).days
                            except (ValueError, TypeError):
                                pass
                    
                    if days_in_status > limit_days:
                        result_ids.append(c["id"])

        return result_ids

    def refresh_connection(self):
        """Обновляет соединение с БД (после массового импорта)"""
        self.conn.commit()
    # ─── РЕЗЕРВНОЕ КОПИРОВАНИЕ ─────────────────────────────────────────
    def create_secure_backup(self):
        """Создаёт Excel-бэкап базы в ZIP с паролем (название магазина)"""
        try:
            import pandas as pd
            from datetime import datetime
            import pyzipper
            import os
            
            shop_name_clean = re.sub(r"[^\w\-_]", "_", self.get_shop_name())
            date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            clients = self.get_all_counterparties()
            export_data = []
            for c in clients:
                export_data.append({
                    "Название": c["name"],
                    "ИНН": c["inn"],
                    "КПП": c["kpp"],
                    "Телефон": c["phone"],
                    "Email": c["email"],
                    "ФИО представителя": c["manager"] if c["manager"] else "",
                    "Канал привлечения": c["lead_source"],
                    "Тип деятельности": c["activity_type"],
                    "Комментарий": c["last_comment"],
                    "ID ViSet": c["viset_id"] if c["viset_id"] != "НЕТ КОДА" else "",
                    "Дата создания": c["created_at"].split(" ")[0] if c["created_at"] else "",
                    "Статус": c["status"],
                    "Сумма продаж": c["sales_amount"] or 0,
                    "Дата последней продажи": c["last_sale_date"].split(" ")[0] if c["last_sale_date"] else "",
                    "Дата след. контакта": c.get("next_contact_date", ""),
                    "Магазин": c.get("shop_name", self.get_shop_name()),
                })
            
            df = pd.DataFrame(export_data)
            temp_excel = f"backup_temp_{date_str}.xlsx"
            df.to_excel(temp_excel, index=False)
            
            zip_password = self.get_shop_name()
            
            backup_filename = f"backup_{shop_name_clean}_{date_str}_SYSTEM.zip"
            backup_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), backup_filename)
            
            with pyzipper.AESZipFile(backup_path, 'w', compression=pyzipper.ZIP_DEFLATED, encryption=pyzipper.WZ_AES) as zipf:
                zipf.setpassword(zip_password.encode())
                zipf.write(temp_excel, arcname=f"backup_{date_str}.xlsx")
            
            if os.path.exists(temp_excel):
                os.remove(temp_excel)
            
            return True, backup_filename
        except Exception as e:
            return False, f"Ошибка создания бэкапа: {str(e)}"