import requests
import os
from dotenv import load_dotenv

load_dotenv()

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
WIND_SPEED_LIMIT = float(os.getenv("WIND_SPEED_LIMIT", 10))  # м/с
DRONE_WIND_LIMIT = 6.0  # м/с — лимит для дронов

WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"

PRECIPITATION_CODES = set(range(200, 622))  # грозы, морось, дождь, снег


def get_weather(lat: float, lon: float) -> dict:
    params = {
        "lat": lat,
        "lon": lon,
        "appid": OPENWEATHER_API_KEY,
        "units": "metric",
        "lang": "ru",
    }
    response = requests.get(WEATHER_URL, params=params, timeout=10)
    response.raise_for_status()
    return response.json()


def has_precipitation(data: dict) -> bool:
    weather_id = data["weather"][0]["id"]
    return weather_id in PRECIPITATION_CODES


def get_weather_status(data: dict) -> tuple[str, str]:
    """Возвращает (краткая_сводка, статус_техники) в HTML."""
    temp = data["main"]["temp"]
    wind_speed = data["wind"]["speed"]
    description = data["weather"][0]["description"].capitalize()

    precipitation = has_precipitation(data)
    wind_too_strong = wind_speed > WIND_SPEED_LIMIT

    summary = (
        f"🌡 <b>{temp:.1f}°C</b>, 💨 <b>{wind_speed:.1f} м/с</b>, {description}"
    )

    if wind_too_strong:
        tech_status = "🔴 Дроны запрещены (сильный ветер)!"
    elif precipitation:
        tech_status = "🟠 Тракторы на автопилоте не рекомендованы (размыв грунта)."
    else:
        tech_status = "🟢 Условия идеальны для дронов и тракторов."

    return summary, tech_status


def check_flight_safety(weather_data: dict) -> tuple[bool, str]:
    """
    Проверяет безопасность вылета дрона.
    Возвращает (безопасно: bool, причина запрета: str).
    """
    wind_speed = weather_data["wind"]["speed"]
    weather_id = weather_data["weather"][0]["id"]

    if wind_speed > DRONE_WIND_LIMIT:
        return False, f"сильный ветер ({wind_speed:.1f} м/с)"
    if weather_id in PRECIPITATION_CODES:
        return False, "осадки (дождь/снег)"
    return True, ""


def analyze_weather(data: dict) -> str:
    """Полный текстовый отчёт о погоде (для команды /weather)."""
    temp = data["main"]["temp"]
    wind_speed = data["wind"]["speed"]
    description = data["weather"][0]["description"].capitalize()
    city_name = data["name"]

    precipitation = has_precipitation(data)
    wind_too_strong = wind_speed > WIND_SPEED_LIMIT

    lines = [
        f"📍 <b>{city_name}</b>",
        f"🌡 Температура: <b>{temp:.1f}°C</b>",
        f"💨 Ветер: <b>{wind_speed:.1f} м/с</b>",
        f"☁️ {description}",
        "",
    ]

    if wind_too_strong:
        lines.append("🔴 <b>ПРЕДУПРЕЖДЕНИЕ:</b> Вывод дронов запрещён (сильный ветер)!")

    if precipitation:
        lines.append(
            "🟠 <b>ПРЕДУПРЕЖДЕНИЕ:</b> Вывод тракторов на автопилоте не рекомендуется "
            "(возможен размыв грунта)."
        )

    if not wind_too_strong and not precipitation:
        lines.append("🟢 <b>ПОГОДА В НОРМЕ:</b> Условия идеальны для запуска дронов и тракторов.")

    return "\n".join(lines)
