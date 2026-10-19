import logging
from typing import Any, Dict, Optional
import aiohttp

logger = logging.getLogger(__name__)


class VINInspectorAPI:
    """Асинхронный HTTP-клиент для взаимодействия с бэкендом VIN Inspector."""

    def __init__(self, base_url: str, timeout: float = 15.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self._session: Optional[aiohttp.ClientSession] = None

    async def get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self.timeout)
        return self._session

    async def close(self) -> None:
        """Закрывает активную aiohttp сессию."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def decode_vin(self, vin: str) -> Dict[str, Any]:
        """
        Запрашивает декодирование VIN-кода:
        GET /api/decode-vin.php?vin={vin}
        """
        url = f"{self.base_url}/api/decode-vin.php"
        params = {"vin": vin.strip().upper()}

        try:
            session = await self.get_session()
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    logger.error(
                        f"decode-vin failed with status {response.status}: {await response.text()}"
                    )
                    return {
                        "success": False,
                        "error": f"Сервер вернул ошибку HTTP {response.status}",
                    }
                data = await response.json(content_type=None)
                return data
        except aiohttp.ClientConnectorError as e:
            logger.error(f"Connection error to backend: {e}")
            return {
                "success": False,
                "error": "Не удалось подключиться к локальному бэкенду VIN Inspector. Убедитесь, что PHP-сервер запущен на http://localhost:8000.",
            }
        except TimeoutError:
            logger.error("Timeout while requesting decode-vin")
            return {
                "success": False,
                "error": "Таймаут ожидания ответа от сервера VIN Inspector.",
            }
        except Exception as e:
            logger.exception(f"Unexpected error in decode_vin: {e}")
            return {
                "success": False,
                "error": f"Внутренняя ошибка при запросе: {str(e)}",
            }

    async def check_oem(self, oem: str, brand: str, vin: str) -> Dict[str, Any]:
        """
        Проверяет совместимость запчасти по артикулу:
        GET /api/check-oem.php?oem={oem}&brand={brand}&vin={vin}
        """
        url = f"{self.base_url}/api/check-oem.php"
        params = {
            "oem": oem.strip(),
            "brand": brand.strip(),
            "vin": vin.strip().upper(),
        }

        try:
            session = await self.get_session()
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    logger.error(
                        f"check-oem failed with status {response.status}: {await response.text()}"
                    )
                    return {
                        "success": False,
                        "error": f"Сервер вернул ошибку HTTP {response.status}",
                    }
                data = await response.json(content_type=None)
                return data
        except aiohttp.ClientConnectorError as e:
            logger.error(f"Connection error to backend: {e}")
            return {
                "success": False,
                "error": "Не удалось подключиться к бэкенду. Проверьте запуск локального сервера.",
            }
        except TimeoutError:
            logger.error("Timeout while requesting check-oem")
            return {
                "success": False,
                "error": "Таймаут ожидания ответа от каталога запчастей.",
            }
        except Exception as e:
            logger.exception(f"Unexpected error in check_oem: {e}")
            return {
                "success": False,
                "error": f"Внутренняя ошибка при проверке артикула: {str(e)}",
            }
