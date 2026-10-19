from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext

from states.vin_states import VinInspectorStates
from keyboards.inline import get_car_card_keyboard

router = Router(name="common")


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Приветственное сообщение и инструкция."""
    await state.clear()
    await state.set_state(VinInspectorStates.waiting_for_vin)

    text = (
        "👋 <b>Добро пожаловать в VIN Inspector Bot!</b>\n\n"
        "Я помогу вам быстро проверить автомобиль и оригинальные запчасти к нему:\n"
        "• 🚘 <b>Декодирование VIN:</b> марка, модель, год, страна производства\n"
        "• 📚 <b>Каталог:</b> быстрый переход в каталог оригинальных запчастей\n"
        "• 🔍 <b>OEM-проверка:</b> точная совместимость запчасти по номеру детали\n\n"
        "👉 <b>Отправьте мне 17-значный VIN-код автомобиля для проверки.</b>"
    )
    await message.answer(text)


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Справка по использованию бота."""
    text = (
        "ℹ️ <b>Как пользоваться ботом:</b>\n\n"
        "1. <b>Проверка авто:</b> отправьте 17-значный VIN-код (например, <code>WAUZZZ8K9BA123456</code>).\n"
        "2. <b>Проверка запчасти:</b> после расшифровки VIN нажмите кнопку <i>«🔍 Проверить запчасть по OEM»</i> "
        "и введите артикул детали (например, <code>06E115562A</code>).\n\n"
        "📌 <b>Команды:</b>\n"
        "/start — Перезапуск бота и ввод нового VIN\n"
        "/help — Справка и помощь\n"
        "/cancel — Сбросить текущее действие"
    )
    await message.answer(text)


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    """Сброс текущего состояния FSM."""
    await state.clear()
    await state.set_state(VinInspectorStates.waiting_for_vin)
    await message.answer(
        "❌ Действие отменено.\n\n"
        "🚗 Отправьте 17-значный VIN-код автомобиля для проверки."
    )


@router.callback_query(F.data == "action:new_vin")
async def cb_new_vin(callback: CallbackQuery, state: FSMContext):
    """Кнопка 'Новый VIN'."""
    await state.clear()
    await state.set_state(VinInspectorStates.waiting_for_vin)
    await callback.message.answer(
        "🚗 <b>Отправьте 17-значный VIN-код автомобиля:</b>"
    )
    await callback.answer()


@router.callback_query(F.data == "action:back_to_car")
async def cb_back_to_car(callback: CallbackQuery, state: FSMContext):
    """Возврат к карточке ранее расшифрованного автомобиля."""
    data = await state.get_data()
    vin = data.get("vin")

    if not vin:
        await state.clear()
        await state.set_state(VinInspectorStates.waiting_for_vin)
        await callback.message.answer("🚗 Данные не найдены. Отправьте VIN-код заново.")
        await callback.answer()
        return

    # Восстанавливаем состояние ожидания команд/нового ввода
    car_title = data.get("car_title", "Автомобиль")
    make = data.get("make", "—")
    model = data.get("model", "")
    year = data.get("year", "—")
    country = data.get("country", "—")
    catalog_site = data.get("catalog_site")
    has_catalog = data.get("has_catalog", False)

    text = (
        f"🚘 <b>Карточка автомобиля</b>\n\n"
        f"📋 <b>VIN:</b> <code>{vin}</code>\n"
        f"🏷 <b>Марка / Модель:</b> {make} {model}".strip() + "\n"
        f"🚗 <b>Полное название:</b> {car_title}\n"
        f"📅 <b>Год выпуска:</b> {year}\n"
        f"🌍 <b>Страна сборки:</b> {country}\n"
    )

    if has_catalog and catalog_site:
        text += f"📚 <b>Каталог бренда:</b> <a href=\"{catalog_site}\">Доступен online</a>\n"

    text += "\n<i>Выберите действие ниже:</i>"

    keyboard = get_car_card_keyboard(catalog_site if has_catalog else None)
    await callback.message.answer(text, reply_markup=keyboard, disable_web_page_preview=True)
    await callback.answer()
