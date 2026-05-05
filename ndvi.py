import random
import logging

import requests

logger = logging.getLogger(__name__)

AGRO_API_BASE = "http://agromonitoring.com/agromonitoring/v1.0"


def _get_mock_ndvi(lat: float, lon: float) -> float:
    """Fallback: случайное значение NDVI от 0.1 до 0.9."""
    return round(random.uniform(0.1, 0.9), 2)


def get_satellite_ndvi(lat: float, lon: float, api_key: str) -> float:
    """
    Запрашивает исторический NDVI через OpenWeatherMap Agro API.
    При отсутствии доступа (401/404) возвращает симулированное значение.
    """
    try:
        # Шаг 1: получить список полигонов для ключа
        polygons_url = f"{AGRO_API_BASE}/polygons"
        resp = requests.get(polygons_url, params={"appid": api_key}, timeout=10)

        if resp.status_code in (401, 403, 404):
            print("Agro API недоступно, используется симуляция NDVI")
            logger.warning("Agro API вернул %s, fallback на симуляцию.", resp.status_code)
            return _get_mock_ndvi(lat, lon)

        resp.raise_for_status()
        polygons = resp.json()

        if not polygons:
            print("Agro API недоступно, используется симуляция NDVI")
            logger.warning("Нет зарегистрированных полигонов, fallback на симуляцию.")
            return _get_mock_ndvi(lat, lon)

        polygon_id = polygons[0]["id"]

        # Шаг 2: получить последнее значение NDVI для первого полигона
        ndvi_url = f"{AGRO_API_BASE}/ndvi/history"
        ndvi_resp = requests.get(
            ndvi_url,
            params={"polyid": polygon_id, "appid": api_key},
            timeout=10,
        )

        if ndvi_resp.status_code in (401, 403, 404):
            print("Agro API недоступно, используется симуляция NDVI")
            logger.warning("NDVI endpoint вернул %s, fallback на симуляцию.", ndvi_resp.status_code)
            return _get_mock_ndvi(lat, lon)

        ndvi_resp.raise_for_status()
        history = ndvi_resp.json()

        if history:
            return round(history[-1].get("data", {}).get("mean", _get_mock_ndvi(lat, lon)), 2)

        print("Agro API недоступно, используется симуляция NDVI")
        logger.warning("История NDVI пуста, fallback на симуляцию.")
        return _get_mock_ndvi(lat, lon)

    except requests.RequestException as exc:
        print("Agro API недоступно, используется симуляция NDVI")
        logger.warning("Ошибка запроса к Agro API: %s, fallback на симуляцию.", exc)
        return _get_mock_ndvi(lat, lon)


def get_mock_ndvi(lat: float, lon: float) -> float:
    """Публичный псевдоним для обратной совместимости."""
    return _get_mock_ndvi(lat, lon)


def analyze_ndvi(ndvi: float) -> str:
    if ndvi < 0.3:
        return (
            f"NDVI: <b>{ndvi}</b>\n"
            "🔴 Критическое состояние. Высокий риск потери урожая, требуется выезд агронома."
        )
    elif ndvi <= 0.6:
        return (
            f"NDVI: <b>{ndvi}</b>\n"
            "🟠 Растения в стрессе. Рекомендуется точечное внесение удобрений "
            "(запланировать вылет DJI Agras T40)."
        )
    else:
        return (
            f"NDVI: <b>{ndvi}</b>\n"
            "🟢 Вегетация в норме. Вмешательство не требуется."
        )
