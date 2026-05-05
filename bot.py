import json
import logging
import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

from weather import get_weather, analyze_weather, get_weather_status
from ndvi import get_mock_ndvi, analyze_ndvi

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
FIELDS_FILE = os.path.join(os.path.dirname(__file__), "fields.json")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def load_fields() -> list:
    with open(FIELDS_FILE, encoding="utf-8") as f:
        return json.load(f)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🌾 <b>Агро-погодный бот</b>\n\n"
        "Команды:\n"
        "/weather [город] — погода для указанного города\n"
        "/report — сводка по всем полям (погода + NDVI)",
        parse_mode="HTML",
    )


async def weather_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text(
            "Укажите город: /weather Бухара", parse_mode="HTML"
        )
        return

    city = " ".join(context.args)
    await update.message.reply_text("⏳ Получаю данные о погоде...")

    try:
        # Геокодируем город через OWM
        import requests as req
        geo_url = "https://api.openweathermap.org/geo/1.0/direct"
        geo_resp = req.get(
            geo_url,
            params={"q": city, "limit": 1, "appid": os.getenv("OPENWEATHER_API_KEY")},
            timeout=10,
        )
        geo_resp.raise_for_status()
        geo = geo_resp.json()
        if not geo:
            raise ValueError("Город не найден")

        data = get_weather(geo[0]["lat"], geo[0]["lon"])
        report = analyze_weather(data)
        await update.message.reply_text(report, parse_mode="HTML")
    except Exception as e:
        logger.error("Ошибка получения погоды: %s", e)
        await update.message.reply_text(
            f"❌ Не удалось получить данные для города <b>{city}</b>.\n"
            "Проверьте название и попробуйте снова.",
            parse_mode="HTML",
        )


async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("⏳ Собираю данные по всем полям...")

    try:
        fields = load_fields()
    except Exception as e:
        logger.error("Ошибка загрузки fields.json: %s", e)
        await update.message.reply_text("❌ Не удалось загрузить список полей.")
        return

    lines = ["🌾 <b>АГРО-СВОДКА ПО ПОЛЯМ</b>\n"]

    for field in fields:
        name = field["name"]
        lat = field["lat"]
        lon = field["lon"]

        try:
            weather_data = get_weather(lat, lon)
            weather_summary, tech_status = get_weather_status(weather_data)
        except Exception as e:
            logger.error("Погода для поля %s: %s", name, e)
            weather_summary = "❌ Данные недоступны"
            tech_status = "—"

        ndvi = get_mock_ndvi(lat, lon)
        ndvi_report = analyze_ndvi(ndvi)

        lines.append(f"📌 <b>{name}</b>")
        lines.append(f"   {weather_summary}")
        lines.append(f"   {tech_status}")
        lines.append(f"   {ndvi_report}")
        lines.append("")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


def main() -> None:
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("weather", weather_command))
    app.add_handler(CommandHandler("report", report_command))

    logger.info("Бот запущен. Ожидание команд...")
    app.run_polling()


if __name__ == "__main__":
    main()
