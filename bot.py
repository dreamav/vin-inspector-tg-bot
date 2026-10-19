import asyncio
import logging
import sys

# Обеспечиваем корректный вывод UTF-8 / Emoji в консоли Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from api_client import VINInspectorAPI
from config import config
from handlers import setup_routers

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("vin_bot")


async def set_main_menu(bot: Bot) -> None:
    """Установка команд в главное меню Telegram."""
    commands = [
        BotCommand(command="start", description="🚗 Начать работу / Ввести VIN"),
        BotCommand(command="help", description="ℹ️ Инструкция и справка"),
        BotCommand(command="cancel", description="❌ Отменить текущее действие"),
    ]
    try:
        await bot.set_my_commands(commands)
    except Exception as e:
        logger.warning(f"Не удалось установить команды меню бота: {e}")


async def main() -> None:
    if not config.bot_token or config.bot_token == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        logger.error(
            "\n" + "=" * 60 + "\n"
            "❌ ОШИБКА: BOT_TOKEN не задан!\n"
            "Пожалуйста, укажите токен Telegram-бота в файле .env:\n"
            "BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz\n"
            + "=" * 60
        )
        sys.exit(1)

    logger.info(f"Запуск VIN Inspector бота... Целевой бэкенд: {config.backend_url}")

    # Инициализация бота и хранилища состояний FSM
    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Инициализация асинхронного клиента для бэкенда
    api_client = VINInspectorAPI(
        base_url=config.backend_url,
        timeout=config.request_timeout
    )
    # Передаём api_client во workflow_data диспетчера для внедрения зависимостей в хэндлеры
    dp["api_client"] = api_client

    # Подключение обработчиков
    setup_routers(dp)

    # Установка команд меню
    await set_main_menu(bot)

    # Пропуск накопившихся обновлений перед стартом
    await bot.delete_webhook(drop_pending_updates=True)

    bot_info = await bot.get_me()
    logger.info(f"Успешное подключение к Telegram API! Бот: @{bot_info.username} ({bot_info.full_name})")
    logger.info("VIN Inspector Bot запущен и ожидает сообщений (Long Polling)...")

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        logger.info("Завершение работы бота...")
        await api_client.close()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен.")
