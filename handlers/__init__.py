from aiogram import Dispatcher
from .common import router as common_router
from .oem import router as oem_router
from .vin import router as vin_router


def setup_routers(dp: Dispatcher) -> None:
    """Регистрация всех роутеров в диспетчере aiogram."""
    dp.include_router(common_router)
    dp.include_router(oem_router)
    dp.include_router(vin_router)
