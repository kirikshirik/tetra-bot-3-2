# config.py
import os
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла (опционально, для локальной разработки)
load_dotenv()

# --- Основные настройки ---
# Рекомендуется хранить токен в переменных окружения для безопасности
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8080782592:AAEfvF60b5LccOMLDNHnVbN2lSNhvRjyly0")
BOT_VERSION = "8.2_With_Emoji"

# --- Настройки Google Sheets ---
GOOGLE_SHEET_ID = "1Mip6C-o4Fvi777_lYYrZg-I_JkB4vVDmT1_w694mBcw"
GOOGLE_SERVICE_ACCOUNT_JSON_PATH = "service_account.json"
DOWNTIME_WORKSHEET_NAME = "Простои"
RESPONSIBLE_GROUPS_WORKSHEET_NAME = "Группы"
USER_ROLES_WORKSHEET_NAME = "Пользователи_Роли"

# --- Настройки отчетов и уведомлений ---
# ID чатов/групп для отправки отчетов (в виде списка строк)
REPORTS_CHAT_IDS = ["483262851", "323628998"]
SCHEDULER_TIMEZONE = "Europe/Moscow"
TOP_N_REASONS_FOR_SUMMARY = 3

# --- Кэш ---
CACHE_REFRESH_INTERVAL_SECONDS = 300  # 5 минут
CACHE_MAX_AGE_SECONDS = 900           # 15 минут

# --- Роли пользователей ---
ADMIN_ROLE = "Администратор"
EMPLOYEE_ROLE = "Сотрудник"

# --- Бизнес-данные (словари для клавиатур и логики) ---
PRODUCTION_SITES = {
    "omet": "ОМЕТ", "gambini2": "Гамбини-2", "gambini3": "Гамбини-3",
    "mts2": "МТС-2", "mts4": "МТС-4",
}

# --- НОВЫЙ СЛОВАРЬ ДЛЯ ЭМОДЗИ ---
PRODUCTION_SITE_EMOJIS = {
    "omet": "🔵",
    "gambini2": "🟡",
    "gambini3": "🟢",
    "mts2": "🔴",
    "mts4": "⚫️",
}

LINES_SECTIONS = {
    "omet": {"omet1": "ОМЕТ1", "omet2": "ОМЕТ2", "omet3": "ОМЕТ3", "omet4": "ОМЕТ4", "omet5": "ОМЕТ5", "sdf": "СДФ"},
    "gambini2": {"raskat": "раскат", "tisnenie": "Тиснение", "namotchik": "Намотчик", "bunker": "Бункер", "rezka": "Резка", "gilza": "Гильза", "uno": "Уно", "fbs": "фбс", "printer": "Принтер"},
    "gambini3": {"raskat": "раскат", "tisnenie": "Тиснение", "namotchik": "Намотчик", "ambalazh": "Амбалаж", "bunker": "Бункер", "rezka": "Резка", "gilza": "Гильza", "uno": "Уно", "fbs": "фбс", "infinity": "Инфинити", "printer": "Принтер"},
    "mts2": {"raskat": "Раскат", "tisnenie": "Тиснение", "folder": "фолдер", "ambalazh": "Амбалаж", "rezka": "Резка", "tekna": "Текна", "keyspaker": "Кейспакер", "printer": "Принтер"},
    "mts4": {"raskat": "Раскат", "tisnenie": "Тиснение", "folder": "фолдер", "ambalazh": "Амбалаж", "rezka": "Резка", "keyspaker": "Кейспакер", "printer": "Принтер"}
}
DOWNTIME_REASONS = {
    "perevod": "Перевод", "mehanika": "Механика", "kip": "КИП", "obryv": "Обрыв",
    "net_osnovy": "Нет основы", "net_operatora": "Нет оператора", "obed": "Обед",
    "zamena": "Замена", "net_plana": "Нет плана", "phd": "ПХД", "net_vozduha": "Нет воздуха"
}

# --- Заголовки таблиц (должны соответствовать таблице) ---
SHEET_HEADERS = [
    "Порядковый номер заявки",
    "Timestamp_записи", "ID_пользователя_Telegram", "Username_Telegram",
    "Имя_пользователя_Telegram", "Площадка", "Линия_Секция",
    "Направление_простоя", "Причина_простоя_описание", "Время_простоя_минут",
    "Начало_смены_простоя", "Конец_смены_простоя",
    "Ответственная_группа",
    "Кто_принял_заявку_ID", "Кто_принял_заявку_Имя", "Время_принятия_заявки",
    "Кто_завершил_работу_в_группе_ID", "Кто_завершил_работу_в_группе_Имя", "Время_завершения_работы_группой",
    "Дополнительный_комментарий_инициатора",
    "ID_Фото"
]
GROUP_NAME_COLUMN = "Название группы"
GROUP_ID_COLUMN = "ID группы"
USER_ID_COLUMN = "ID_пользователя_Telegram"
USER_ROLE_COLUMN = "Роль"
