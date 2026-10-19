from typing import Optional
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_car_card_keyboard(catalog_url: Optional[str] = None) -> InlineKeyboardMarkup:
    """Клавиатура под карточкой расшифрованного автомобиля."""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="🔍 Проверить запчасть по OEM",
            callback_data="action:check_oem"
        )
    )

    row_buttons = []
    if catalog_url and catalog_url.startswith("http"):
        row_buttons.append(
            InlineKeyboardButton(
                text="🌐 Каталог авто",
                url=catalog_url
            )
        )
    row_buttons.append(
        InlineKeyboardButton(
            text="🚗 Другой VIN",
            callback_data="action:new_vin"
        )
    )
    builder.row(*row_buttons)

    return builder.as_markup()


def get_oem_result_keyboard(
    part_url: Optional[str] = None,
    has_more_fitment: bool = False,
    fitment_count: int = 0
) -> InlineKeyboardMarkup:
    """Клавиатура под результатом проверки совместимости запчасти."""
    builder = InlineKeyboardBuilder()

    if has_more_fitment and fitment_count > 0:
        builder.row(
            InlineKeyboardButton(
                text=f"📋 Все совместимые авто ({fitment_count})",
                callback_data="action:all_fitment"
            )
        )

    if part_url and part_url.startswith("http"):
        builder.row(
            InlineKeyboardButton(
                text="🔗 Открыть в каталоге",
                url=part_url
            )
        )

    builder.row(
        InlineKeyboardButton(
            text="🔄 Проверить другой номер",
            callback_data="action:check_oem"
        ),
        InlineKeyboardButton(
            text="🚗 Новый VIN",
            callback_data="action:new_vin"
        )
    )

    return builder.as_markup()


def get_full_fitment_keyboard(part_url: Optional[str] = None) -> InlineKeyboardMarkup:
    """Клавиатура под полным списком совместимых автомобилей."""
    builder = InlineKeyboardBuilder()

    if part_url and part_url.startswith("http"):
        builder.row(
            InlineKeyboardButton(
                text="🔗 Открыть деталь в каталоге",
                url=part_url
            )
        )

    builder.row(
        InlineKeyboardButton(
            text="🔄 Проверить другой номер",
            callback_data="action:check_oem"
        ),
        InlineKeyboardButton(
            text="🚗 Новый VIN",
            callback_data="action:new_vin"
        )
    )

    return builder.as_markup()


def get_cancel_oem_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура в режиме ожидания ввода артикула OEM."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="🔙 Назад к автомобилю",
            callback_data="action:back_to_car"
        ),
        InlineKeyboardButton(
            text="🚗 Новый VIN",
            callback_data="action:new_vin"
        )
    )
    return builder.as_markup()

