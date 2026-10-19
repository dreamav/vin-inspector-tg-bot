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
        # Передаём управление обработчику VIN
        from handlers.vin import handle_vin_message
        await handle_vin_message(message, state, api_client)
        return

    data = await state.get_data()
    vin = data.get("vin")
    brand = data.get("brand_id") or data.get("make", "")
    car_title = data.get("car_title") or "Автомобиль"

    if not vin:
        await message.answer(
            "⚠️ Данные об автомобиле не найдены. Пожалуйста, отправьте 17-значный VIN-код заново."
        )
        await state.set_state(VinInspectorStates.waiting_for_vin)
        return

    if len(clean_code) < 3:
        await message.answer(
            "❌ Слишком короткий артикул. Артикул запчасти обычно содержит от 4 до 15 символов.\n"
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

    card_text = "\n".join(lines)
    keyboard = get_oem_result_keyboard(part_url=part_url)

    await message.answer(
        card_text,
        reply_markup=keyboard,
        disable_web_page_preview=True
    )
