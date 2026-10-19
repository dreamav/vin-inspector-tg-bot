import re
import html
from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from api_client import VINInspectorAPI
from states.vin_states import VinInspectorStates
from keyboards.inline import get_car_card_keyboard

router = Router(name="vin")

# Стандарт ISO 3779: 17 символов, цифры и латиница без I, O, Q
VIN_REGEX = re.compile(r"^[A-HJ-NPR-Z0-9]{17}$")


def validate_vin(raw_text: str) -> tuple[bool, str, str]:
    """
    Валидирует и нормализует VIN-код.
    Возвращает: (is_valid, normalized_vin, error_message)
    """
    # Удаляем пробелы, переносы строк и дефисы
    cleaned = re.sub(r"[\s\-]+", "", raw_text).upper()

    if len(cleaned) != 17:
        return (
            False,
            cleaned,
            f"❌ Длина VIN-кода должна составлять ровно 17 символов.\nВы ввели: <b>{len(cleaned)}</b> символов."
        )

    # Проверка на недопустимые буквы I, O, Q
    forbidden = [char for char in cleaned if char in ("I", "O", "Q")]
    if forbidden:
        unique_forbidden = ", ".join(sorted(set(forbidden)))
        return (
            False,
            cleaned,
            f"❌ В VIN-коде обнаружены недопустимые символы: <b>{unique_forbidden}</b>.\n"
            "По стандарту ISO 3779 буквы <b>I</b>, <b>O</b> и <b>Q</b> не используются во избежание путаницы с 1 и 0."
        )

    if not VIN_REGEX.match(cleaned):
        return (
            False,
            cleaned,
            "❌ VIN-код может содержать только латинские буквы и цифры (кроме I, O, Q)."
        )

    return True, cleaned, ""


@router.message(F.text, VinInspectorStates.waiting_for_vin)
@router.message(F.text)
async def handle_vin_message(
    message: Message,
    state: FSMContext,
    api_client: VINInspectorAPI
):
    """
    Обработчик входящего текста как потенциального VIN-кода.
    Срабатывает в состоянии waiting_for_vin или если текущее состояние не установлено.
    """
    text = message.text.strip()

    # Игнорируем команды (они обрабатываются в common.py)
    if text.startswith("/"):
        return

    # Валидация формата
    is_valid, vin, error_msg = validate_vin(text)
    if not is_valid:
        await message.answer(
            f"{error_msg}\n\n"
            "💡 <i>Пример корректного VIN:</i> <code>WAUZZZ8K9BA123456</code>\n"
            "Пожалуйста, проверьте и отправьте VIN снова."
        )
        return

    # Индикация отправки запроса
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    status_msg = await message.answer(f"⏳ Расшифровываю VIN <code>{vin}</code>...")

    # Запрос к бэкенду
    data = await api_client.decode_vin(vin)

    # Удаляем временное статусное сообщение
    try:
        await status_msg.delete()
    except Exception:
        pass

    if not data or not data.get("success"):
        err = data.get("error", "Автомобиль с данным VIN не найден в базе данных") if data else "Ошибка соединения"
        await message.answer(
            f"❌ <b>Ошибка расшифровки:</b>\n{html.escape(err)}\n\n"
            "Попробуйте проверить правильность VIN или отправьте другой номер.",
            parse_mode="HTML"
        )
        return

    # Извлечение данных
    make = data.get("make") or "Не указано"
    model = data.get("model") or ""
    year = str(data.get("year") or "").strip() or "Не указан"
    car_title = data.get("carTitle") or f"{year} {make} {model}".strip()
    country = data.get("plantCountry") or "Не указана"
    brand_id = data.get("brandId") or make.lower()
    catalog_site = data.get("catalogSite")
    has_catalog = bool(data.get("hasCatalog", False))

    # Дополнительные поля, если есть
    body_class = data.get("bodyClass")
    engine = data.get("engine")
    drive_type = data.get("driveType")

    # Сохраняем в контекст состояния FSM
    await state.update_data(
        vin=vin,
        make=make,
        model=model,
        year=year,
        car_title=car_title,
        country=country,
        brand_id=brand_id,
        catalog_site=catalog_site,
        has_catalog=has_catalog
    )

    # Формируем красивую карточку автомобиля
    lines = [
        "🚘 <b>Карточка автомобиля</b>",
        "",
        f"📋 <b>VIN:</b> <code>{html.escape(vin)}</code>",
        f"🏷 <b>Марка / Модель:</b> {html.escape(make)} {html.escape(model)}".strip(),
        f"🚗 <b>Полное название:</b> {html.escape(car_title)}",
        f"📅 <b>Год выпуска:</b> {html.escape(year)}",
        f"🌍 <b>Страна сборки:</b> {html.escape(country)}",
    ]

    if body_class:
        lines.append(f"🚙 <b>Кузов:</b> {html.escape(body_class)}")
    if engine:
        lines.append(f"⚙️ <b>Двигатель:</b> {html.escape(engine)}")
    if drive_type:
        lines.append(f"🛞 <b>Привод:</b> {html.escape(drive_type)}")

    if has_catalog and catalog_site:
        lines.append(f"📚 <b>Каталог бренда:</b> <a href=\"{html.escape(catalog_site)}\">Доступен online</a>")
    else:
        lines.append("📚 <b>Каталог бренда:</b> <i>Не обнаружен в локальной базе</i>")

    lines.append("")
    lines.append("<i>Выберите дальнейшее действие:</i>")

    card_text = "\n".join(lines)
    keyboard = get_car_card_keyboard(catalog_site if has_catalog else None)

    await message.answer(
        card_text,
        reply_markup=keyboard,
        disable_web_page_preview=True
    )
