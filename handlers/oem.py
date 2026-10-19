import html
import re
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from api_client import VINInspectorAPI
from states.vin_states import VinInspectorStates
from keyboards.inline import (
    get_oem_result_keyboard,
    get_cancel_oem_keyboard,
)

router = Router(name="oem")

# Регулярка для проверки, не ввёл ли пользователь снова VIN (17 символов)
VIN_REGEX = re.compile(r"^[A-HJ-NPR-Z0-9]{17}$")


def is_vehicle_match(item: dict, car_title: str, make: str, model: str) -> bool:
    """Определяет, совпадает ли автомобиль из таблицы совместимости с текущим авто."""
    target = f"{car_title} {make} {model}".lower().strip()
    ymm = (item.get("yearMakeModel") or "").lower()
    if not ymm or not target:
        return False
    words = re.findall(r"[a-z0-9]{3,}", target)
    if not words:
        return False
    matches = [w for w in words if w in ymm]
    return len(matches) >= min(2, len(words))


def format_fitment_summary(
    vehicles: list[dict],
    car_title: str = "",
    make: str = "",
    model: str = "",
    max_items: int = 5
) -> str:
    """Форматирует компактный блок списка совместимых автомобилей для карточки OEM."""
    if not vehicles:
        return (
            "📋 <b>Список совместимых авто:</b>\n"
            "<i>Детальная таблица доступна на странице детали в онлайн-каталоге.</i>"
        )

    total = len(vehicles)
    shown = vehicles[:max_items]

    lines = [f"📋 <b>Список совместимых автомобилей (найдено: {total}):</b>"]

    for item in shown:
        ymm = html.escape((item.get("yearMakeModel") or "Модель не указана").strip())
        trim = html.escape((item.get("trimEngine") or "").strip())
        options = html.escape((item.get("options") or "").strip())

        is_match = is_vehicle_match(item, car_title, make, model)
        badge = " ⭐️ <b>[Текущее авто]</b>" if is_match else ""

        entry_text = f"• <b>{ymm}</b>{badge}"
        details = []
        if trim and trim != "—":
            details.append(f"Двигатель: {trim}")
        if options and options != "—":
            details.append(f"Опции: {options}")

        if details:
            entry_text += f"\n  └ <i>{'; '.join(details)}</i>"

        lines.append(entry_text)

    if total > max_items:
        lines.append(f"<i>...и ещё {total - max_items} модификаций (нажмите кнопку ниже)</i>")

    return "\n".join(lines)


@router.callback_query(F.data == "action:check_oem")
async def start_oem_check(callback: CallbackQuery, state: FSMContext):
    """Переход в режим ввода артикула (OEM) для текущего автомобиля."""
    data = await state.get_data()
    vin = data.get("vin")

    if not vin:
        await callback.message.answer(
            "⚠️ Сначала необходимо расшифровать VIN-код автомобиля.\n"
            "🚗 Пожалуйста, отправьте 17-значный VIN-код:"
        )
        await state.set_state(VinInspectorStates.waiting_for_vin)
        await callback.answer()
        return

    car_title = data.get("car_title") or f"{data.get('make', '')} {data.get('model', '')}".strip()
    brand = data.get("make") or data.get("brand_id", "")

    await state.set_state(VinInspectorStates.waiting_for_oem)

    text = (
        "🔍 <b>Проверка совместимости запчасти (OEM)</b>\n\n"
        f"🚘 <b>Автомобиль:</b> {html.escape(car_title)}\n"
        f"📋 <b>VIN:</b> <code>{html.escape(vin)}</code>\n"
        f"🏷 <b>Каталог бренда:</b> {html.escape(brand)}\n\n"
        "👉 <b>Введите OEM-артикул запчасти</b> (например: <code>06E115562A</code>):"
    )

    await callback.message.answer(
        text,
        reply_markup=get_cancel_oem_keyboard()
    )
    await callback.answer()


@router.message(F.text, VinInspectorStates.waiting_for_oem)
async def process_oem_input(
    message: Message,
    state: FSMContext,
    api_client: VINInspectorAPI
):
    """Обработка ввода OEM-артикула запчасти."""
    raw_text = message.text.strip()

    # Игнорируем команды
    if raw_text.startswith("/"):
        return

    # Очищаем артикул от случайных разделителей и пробелов
    clean_code = re.sub(r"[\s\-_]+", "", raw_text).upper()

    # Если пользователь внезапно ввёл 17-значный VIN вместо артикула
    if len(clean_code) == 17 and VIN_REGEX.match(clean_code):
        await state.set_state(VinInspectorStates.waiting_for_vin)
        from handlers.vin import handle_vin_message
        await handle_vin_message(message, state, api_client)
        return

    data = await state.get_data()
    vin = data.get("vin")
    brand = data.get("brand_id") or data.get("make", "")
    make = data.get("make", "")
    model = data.get("model", "")
    car_title = data.get("car_title") or "Автомобиль"

    if not vin:
        await message.answer(
            "⚠️ Данные об автомобиле не найдены. Пожалуйста, отправьте 17-значный VIN-код заново."
        )
        await state.set_state(VinInspectorStates.waiting_for_vin)
        return

    if len(clean_code) < 3:
        await message.answer(
            "❌ Слишком короткий артикул. Номер детали обычно содержит от 4 до 15 символов.\n"
            "💡 Пример: <code>06E115562A</code>\n\n"
            "Попробуйте ввести номер ещё раз:",
            reply_markup=get_cancel_oem_keyboard()
        )
        return

    # Индикация запроса
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    status_msg = await message.answer(
        f"⏳ Проверяю совместимость артикула <code>{html.escape(raw_text)}</code> с <code>{html.escape(vin)}</code>..."
    )

    result = await api_client.check_oem(oem=raw_text, brand=brand, vin=vin)

    try:
        await status_msg.delete()
    except Exception:
        pass

    if not result or not result.get("success"):
        err = result.get("error", "Деталь с данным артикулом не найдена в каталоге") if result else "Ошибка соединения с бэкендом"
        await message.answer(
            f"❌ <b>Результат проверки:</b>\n{html.escape(err)}\n\n"
            f"Убедитесь в правильности номера запчасти для каталога <b>{html.escape(brand)}</b>.",
            reply_markup=get_cancel_oem_keyboard()
        )
        return

    # Извлечение параметров проверки
    oem_out = result.get("oem") or raw_text
    part_title = result.get("partTitle") or "Оригинальная деталь"
    status = (result.get("status") or "").lower()
    confirm_text = result.get("confirmText") or ""
    part_url = result.get("partUrl") or result.get("cleanPartUrl")
    fitment_vehicles = result.get("fitmentVehicles") or []

    # Сохраняем результат в FSM для просмотра полного списка совместимых авто
    await state.update_data(
        last_fitment=fitment_vehicles,
        last_oem=oem_out,
        last_part_title=part_title,
        last_part_url=part_url,
    )

    # Формируем статус совместимости
    if status == "fit":
        status_badge = "✅ <b>Совместимость:</b> Деталь подходит для этого авто"
    elif status == "not-fit":
        status_badge = "❌ <b>Совместимость:</b> Деталь НЕ подходит для этого авто"
    elif status:
        status_badge = f"⚠️ <b>Статус совместимости:</b> {html.escape(status)}"
    else:
        status_badge = "ℹ️ <b>Статус:</b> Информация получена"

    lines = [
        "📦 <b>Результат проверки совместимости OEM</b>",
        "",
        f"🚘 <b>Автомобиль:</b> {html.escape(car_title)}",
        f"📋 <b>VIN:</b> <code>{html.escape(vin)}</code>",
        f"🔢 <b>Артикул детали:</b> <code>{html.escape(oem_out)}</code>",
        f"🏷 <b>Наименование:</b> {html.escape(part_title)}",
        "",
        status_badge,
    ]

    if confirm_text:
        lines.append(f"💬 <i>Подтверждение каталога:</i> {html.escape(confirm_text)}")

    # Добавляем блок совместимых автомобилей
    lines.append("")
    lines.append(format_fitment_summary(
        fitment_vehicles,
        car_title=car_title,
        make=make,
        model=model,
        max_items=5
    ))

    card_text = "\n".join(lines)
    keyboard = get_oem_result_keyboard(
        part_url=part_url,
        has_more_fitment=len(fitment_vehicles) > 5,
        fitment_count=len(fitment_vehicles)
    )

    await message.answer(
        card_text,
        reply_markup=keyboard,
        disable_web_page_preview=True
    )


@router.callback_query(F.data == "action:all_fitment")
async def show_all_fitment_vehicles(callback: CallbackQuery, state: FSMContext):
    """Показывает полный список совместимых автомобилей."""
    data = await state.get_data()
    vehicles = data.get("last_fitment") or []
    oem = data.get("last_oem", "")
    part_title = data.get("last_part_title", "Запчасть")
    part_url = data.get("last_part_url")
    car_title = data.get("car_title", "")
    make = data.get("make", "")
    model = data.get("model", "")

    if not vehicles:
        await callback.answer("Список совместимых автомобилей пуст.", show_alert=True)
        return

    header = (
        f"📋 <b>Полный список совместимых автомобилей ({len(vehicles)} шт.)</b>\n"
        f"📦 <b>Деталь:</b> {html.escape(part_title)} (<code>{html.escape(oem)}</code>)\n\n"
    )

    items_text = []
    for idx, item in enumerate(vehicles, 1):
        ymm = html.escape((item.get("yearMakeModel") or "Модель не указана").strip())
        trim = html.escape((item.get("trimEngine") or "").strip())
        options = html.escape((item.get("options") or "").strip())

        is_match = is_vehicle_match(item, car_title, make, model)
        badge = " ⭐️ <b>[Текущее авто]</b>" if is_match else ""

        row = [f"<b>{idx}. {ymm}</b>{badge}"]
        if trim and trim != "—":
            row.append(f"   ├ <i>Двигатель:</i> {trim}")
        if options and options != "—":
            row.append(f"   └ <i>Опции:</i> {options}")

        items_text.append("\n".join(row))

    # Склеиваем сообщения, учитывая лимит Telegram 4096 символов
    full_body = "\n\n".join(items_text)
    keyboard = get_full_fitment_keyboard(part_url=part_url)

    if len(header) + len(full_body) <= 4000:
        await callback.message.answer(
            header + full_body,
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
    else:
        # Если список очень длинный, отправляем частями
        chunks = []
        current_chunk = header
        for entry in items_text:
            if len(current_chunk) + len(entry) + 2 > 3800:
                chunks.append(current_chunk)
                current_chunk = entry + "\n\n"
            else:
                current_chunk += entry + "\n\n"
        if current_chunk:
            chunks.append(current_chunk)

        for i, chunk in enumerate(chunks):
            is_last = (i == len(chunks) - 1)
            await callback.message.answer(
                chunk,
                reply_markup=keyboard if is_last else None,
                disable_web_page_preview=True
            )

    await callback.answer()
