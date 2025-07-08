# utils/reports.py
import logging
from datetime import datetime, timedelta, time
from collections import Counter, defaultdict
from pytz import timezone

from aiogram.utils.markdown import escape_md
from aiogram import Bot

from config import (SCHEDULER_TIMEZONE, TOP_N_REASONS_FOR_SUMMARY,
                    PRODUCTION_SITES, LINES_SECTIONS, ADMIN_ROLE, PRODUCTION_SITE_EMOJIS)
from utils.storage import DataStorage

# Создаем обратный словарь для поиска ключа по названию площадки (в нижнем регистре для надежности)
SITE_NAME_TO_KEY = {v.lower(): k for k, v in PRODUCTION_SITES.items()}

def get_shift_time_range(shift_type: str) -> (datetime, datetime):
    tz = timezone(SCHEDULER_TIMEZONE)
    now_local = datetime.now(tz)
    time_08_00 = time(8, 0)
    time_20_00 = time(20, 0)

    if time_08_00 <= now_local.time() < time_20_00:
        current_start = now_local.replace(hour=8, minute=0, second=0, microsecond=0)
        current_end = now_local.replace(hour=20, minute=0, second=0, microsecond=0)
    else:
        if now_local.time() >= time_20_00:
            current_start = now_local.replace(hour=20, minute=0, second=0, microsecond=0)
            current_end = (now_local + timedelta(days=1)).replace(hour=8, minute=0, second=0, microsecond=0)
        else:
            current_start = (now_local - timedelta(days=1)).replace(hour=20, minute=0, second=0, microsecond=0)
            current_end = now_local.replace(hour=8, minute=0, second=0, microsecond=0)

    if shift_type == 'current':
        return current_start, current_end
    elif shift_type == 'previous':
        if current_start.time() == time_08_00:
            prev_end = current_start
            prev_start = (current_start - timedelta(days=1)).replace(hour=20, minute=0, second=0, microsecond=0)
        else:
            prev_end = current_start
            prev_start = current_start.replace(hour=8, minute=0, second=0, microsecond=0)
        return prev_start, prev_end

    return None, None


def calculate_shift_times(record_datetime: datetime) -> (str, str):
    tz = timezone(SCHEDULER_TIMEZONE)
    record_datetime_aware = record_datetime.astimezone(tz) if record_datetime.tzinfo else tz.localize(record_datetime)
    record_date = record_datetime_aware.date()
    record_time = record_datetime_aware.time()
    time_08_00 = time(8, 0)
    time_20_00 = time(20, 0)

    if time_08_00 <= record_time < time_20_00:
        start_dt = tz.localize(datetime.combine(record_date, time_08_00))
        end_dt = tz.localize(datetime.combine(record_date, time_20_00))
    elif record_time >= time_20_00:
        start_dt = tz.localize(datetime.combine(record_date, time_20_00))
        end_dt = tz.localize(datetime.combine(record_date + timedelta(days=1), time_08_00))
    else:
        start_dt = tz.localize(datetime.combine(record_date - timedelta(days=1), time_20_00))
        end_dt = tz.localize(datetime.combine(record_date, time_08_00))

    return start_dt.strftime("%Y-%m-%d %H:%M:%S"), end_dt.strftime("%Y-%m-%d %H:%M:%S")

def _parse_datetime_from_sheet(dt_string: str) -> datetime | None:
    """Пытается распарсить строку с датой из таблицы, пробуя несколько форматов."""
    formats_to_try = [
        "%Y-%m-%d %H:%M:%S",
        "%d.%m.%Y %H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
    ]
    for fmt in formats_to_try:
        try:
            return datetime.strptime(dt_string, fmt)
        except ValueError:
            continue
    logging.warning(f"Не удалось распознать формат даты-времени: '{dt_string}'")
    return None

async def get_downtime_report_for_period(start_dt: datetime, end_dt: datetime, storage: DataStorage):
    cache_status = ""
    if storage.downtime_cache.get("error"):
        cache_status += f"\n\n⚠️ **Кэш-ошибка: {storage.downtime_cache['error']}.**"
    if storage.is_cache_stale():
        cache_status += f"\n\n⚠️ **Данные могут быть неактуальны (кэш устарел).**"

    headers = storage.downtime_cache.get("headers")
    data_rows = storage.downtime_cache.get("data_rows")

    if not headers or data_rows is None:
        return {}, 0, 0, f"Нет данных о простоях для анализа.{cache_status}"

    try:
        required_cols = [
            "Timestamp_записи", "Площадка", "Линия_Секция", "Направление_простоя",
            "Время_простоя_минут", "Причина_простоя_описание", "Ответственная_группа",
            "Дополнительный_комментарий_инициатора", "Кто_принял_заявку_Имя", "Кто_завершил_работу_в_группе_Имя"
        ]
        idx_map = {col: headers.index(col) for col in required_cols}
    except ValueError as e:
        logging.error(f"Отсутствует необходимый столбец в таблице: {e}")
        error_message = f"Ошибка конфигурации отчета: столбец '{str(e).split()[0]}' не найден в таблице."
        return {}, 0, 0, error_message

    downtimes_by_site = defaultdict(lambda: {'total_minutes': 0, 'entries': []})
    total_minutes_overall = 0
    record_count = 0
    tz = timezone(SCHEDULER_TIMEZONE)

    for row in data_rows:
        try:
            if len(row) <= max(idx_map.values()): continue
            
            record_timestamp_str = row[idx_map["Timestamp_записи"]]
            if not record_timestamp_str: continue
            
            record_dt = _parse_datetime_from_sheet(record_timestamp_str)
            if not record_dt: continue

            record_dt_aware = tz.localize(record_dt)

            if start_dt <= record_dt_aware < end_dt:
                record_count += 1
                site_name = row[idx_map['Площадка']] # Получаем "чистое" имя без экранирования
                line_section = escape_md(row[idx_map['Линия_Секция']])
                reason = escape_md(row[idx_map['Направление_простоя']])
                duration = int(row[idx_map["Время_простоя_минут"]] or 0)
                description = escape_md(row[idx_map["Причина_простоя_описание"]])
                resp_group = escape_md(row[idx_map['Ответственная_группа']])
                accepted_by = escape_md(row[idx_map['Кто_принял_заявку_Имя']])
                completed_by = escape_md(row[idx_map['Кто_завершил_работу_в_группе_Имя']])
                initiator_comment = escape_md(row[idx_map["Дополнительный_комментарий_инициатора"]])

                total_minutes_overall += duration
                downtimes_by_site[site_name]['total_minutes'] += duration

                entry_details = [
                    f"   └ ⚙️ **{line_section}: {reason} ({duration} мин.)**",
                    f"         └ 🗒️ Описание: _{description}_",
                    f"         └ 👥 Отв. группа: {resp_group}"
                ]
                if accepted_by:
                    entry_details.append(f"         └ 👨‍💻 Принял: {accepted_by}")
                if completed_by:
                    entry_details.append(f"         └ 👨‍💻 Работу в группе завершил: {completed_by}")

                if initiator_comment and "Без доп. комментария" not in initiator_comment:
                    entry_details.append(f"         └ 🗣️ Комментарий инициатора: _{initiator_comment}_")
                
                downtimes_by_site[site_name]['entries'].append("\n".join(entry_details))

        except (ValueError, IndexError) as e:
            logging.warning(f"Пропущена некорректная строка при создании отчета: {row}. Ошибка: {e}")
            continue

    if record_count == 0:
        no_records_message = f"✅ **Отчет за смену**\nНет корректных записей за смену с {start_dt.strftime('%d.%m.%Y %H:%M')} по {end_dt.strftime('%d.%m.%Y %H:%M')}.{cache_status}"
        return {}, 0, 0, no_records_message

    reports_by_site_dict = {}
    for site_name_from_sheet, data in sorted(downtimes_by_site.items()):
        
        # ИЗМЕНЕНИЕ: Приводим имя площадки из таблицы к нижнему регистру и убираем пробелы для надежного поиска
        site_key = SITE_NAME_TO_KEY.get(site_name_from_sheet.strip().lower())
        emoji = PRODUCTION_SITE_EMOJIS.get(site_key, '⚪️') # Белый круг - эмодзи по умолчанию
        
        site_total_minutes = data['total_minutes']
        # Экранируем Markdown в названии площадки перед отправкой
        escaped_site_name = escape_md(site_name_from_sheet)
        report_parts = [f"{emoji} **{escaped_site_name} Общее время простоя: {site_total_minutes} минут.**"]
        report_parts.extend(data['entries'])
        reports_by_site_dict[site_name_from_sheet] = "\n".join(report_parts)

    return reports_by_site_dict, total_minutes_overall, record_count, cache_status


async def generate_admin_shift_summary(start_dt: datetime, end_dt: datetime, storage: DataStorage):
    headers = storage.downtime_cache.get("headers")
    data_rows = storage.downtime_cache.get("data_rows")

    if not headers or data_rows is None: return "Нет данных для сводки."

    try:
        idx_map = {col: headers.index(col) for col in ["Timestamp_записи", "Время_простоя_минут", "Направление_простоя"]}
    except ValueError as e: return f"Ошибка конфигурации сводки: столбец '{str(e).split()[0]}' не найден."
    
    total_minutes = 0
    reason_counts = Counter()
    tz = timezone(SCHEDULER_TIMEZONE)

    for row in data_rows:
        try:
            if len(row) <= max(idx_map.values()): continue
            record_timestamp_str = row[idx_map["Timestamp_записи"]]
            if not record_timestamp_str: continue
            
            record_dt = _parse_datetime_from_sheet(record_timestamp_str)
            if not record_dt: continue

            record_dt_aware = tz.localize(record_dt)

            if start_dt <= record_dt_aware < end_dt:
                duration = int(row[idx_map["Время_простоя_минут"]] or 0)
                reason = row[idx_map["Направление_простоя"]] or "Не указана"
                total_minutes += duration
                reason_counts[reason] += duration
        except (ValueError, IndexError) as e:
            logging.warning(f"Пропущена некорректная строка при создании сводки: {row}. Ошибка: {e}")
            continue

    if total_minutes == 0:
        return f"За смену ({start_dt.strftime('%H:%M')}-{end_dt.strftime('%H:%M')}) простоев не зафиксировано."

    hours, minutes = divmod(total_minutes, 60)
    top_reasons_list = reason_counts.most_common(TOP_N_REASONS_FOR_SUMMARY)
    top_reasons = [f"- {escape_md(r)} ({m} мин.)" for r, m in top_reasons_list]
    summary = (f"**Сводка за смену ({start_dt.strftime('%H:%M %d.%m')})**\n\n"
               f"Общий простой: **{hours} ч {minutes} мин.**\n\n"
               f"**Топ-{len(top_reasons)} причины:**\n" + "\n".join(top_reasons))
    return summary


async def generate_line_status_report(storage: DataStorage):
    report_lines = ["**Статус линий на текущий момент:**"]
    for site_key, site_name in PRODUCTION_SITES.items():
        if site_key not in LINES_SECTIONS: continue
        
        emoji = PRODUCTION_SITE_EMOJIS.get(site_key, '⚪️')
        report_lines.append(f"\n{emoji} **{escape_md(site_name)}**")
        
        for line_key, line_name in LINES_SECTIONS[site_key].items():
            line_tuple = (site_name, line_name)
            if line_tuple in storage.active_downtimes:
                reason = storage.active_downtimes[line_tuple]
                report_lines.append(f"   🔴 {escape_md(line_name)}: **ПРОСТОЙ** ({escape_md(reason)})")
            else:
                report_lines.append(f"   🟢 {escape_md(line_name)}: Работает")
    return "\n".join(report_lines)


async def scheduled_line_status_report(bot: Bot, storage: DataStorage):
    logging.info("SCHEDULER: Запуск задачи на отправку отчета о статусе линий.")
    admin_ids = [uid for uid, role in storage.user_roles.items() if role == ADMIN_ROLE]
    if not admin_ids:
        logging.warning("SCHEDULER: Нет администраторов для отправки отчета о статусе линий.")
        return
    report_text = await generate_line_status_report(storage)
    for admin_id in admin_ids:
        try:
            await bot.send_message(int(admin_id), report_text, parse_mode="Markdown")
        except Exception as e:
            logging.error(f"SCHEDULER: Не удалось отправить отчет о статусе линий админу {admin_id}: {e}")
    logging.info(f"SCHEDULER: Отчет о статусе линий отправлен {len(admin_ids)} администраторам.")