import json
import os
from datetime import datetime, timedelta
import folium
import numpy as np
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from streamlit_folium import st_folium

from weather import get_weather, get_weather_status, check_flight_safety
from ndvi import get_mock_ndvi, analyze_ndvi
from telemetry import get_active_machinery

load_dotenv()

FIELDS_FILE = os.path.join(os.path.dirname(__file__), "fields.json")

st.set_page_config(
    page_title="Агрокластер — Панель управления",
    page_icon="🌾",
    layout="wide",
)

# ── Авторизация ───────────────────────────────────────────────────────────────
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("Вход в систему")
    username = st.text_input("Логин")
    password = st.text_input("Пароль", type="password")
    if st.button("Войти"):
        admin_user = os.getenv("ADMIN_USERNAME", "")
        admin_pass = os.getenv("ADMIN_PASSWORD", "")
        if username == admin_user and password == admin_pass:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Неверные данные")
    st.stop()

# ── Дашборд (только для авторизованных) ──────────────────────────────────────
st.title("🌾 Панель управления Агрокластером")
st.caption("Данные о погоде и состоянии вегетации по полям Бухарской области")
st.divider()


@st.cache_data(ttl=300)
def load_fields() -> list:
    with open(FIELDS_FILE, encoding="utf-8") as f:
        return json.load(f)


@st.cache_data(ttl=300)
def fetch_field_data(lat: float, lon: float) -> dict:
    data = get_weather(lat, lon)
    weather_summary, tech_status = get_weather_status(data)
    temp = data["main"]["temp"]
    wind = data["wind"]["speed"]
    description = data["weather"][0]["description"].capitalize()
    ndvi = get_mock_ndvi(lat, lon)
    ndvi_text = analyze_ndvi(ndvi)
    ndvi_text_clean = (
        ndvi_text
        .replace("<b>", "**").replace("</b>", "**")
        .replace("NDVI: ", "")
    )
    safe, danger_reason = check_flight_safety(data)
    return {
        "temp": temp,
        "wind": wind,
        "description": description,
        "tech_status": tech_status,
        "ndvi": ndvi,
        "ndvi_text": ndvi_text_clean,
        "flight_safe": safe,
        "flight_danger_reason": danger_reason,
    }


def tech_status_color(status: str) -> str:
    if status.startswith("🔴"):
        return "#ff4b4b"
    if status.startswith("🟠"):
        return "#ffa500"
    return "#21c354"


def ndvi_color(ndvi: float) -> str:
    if ndvi < 0.3:
        return "#ff4b4b"
    if ndvi <= 0.6:
        return "#ffa500"
    return "#21c354"


def ndvi_polygon_color(ndvi: float) -> str:
    """Цвет полигона на карте по значению NDVI."""
    if ndvi > 0.6:
        return "green"
    if ndvi >= 0.4:
        return "yellow"
    return "red"


try:
    fields = load_fields()
except Exception as e:
    st.error(f"Не удалось загрузить fields.json: {e}")
    st.stop()

btn_col, time_col = st.columns([1, 4])
with btn_col:
    if st.button("🔄 Обновить данные"):
        st.cache_data.clear()
        st.rerun()
with time_col:
    st.caption(f"Последнее обновление: **{datetime.now().strftime('%d.%m.%Y %H:%M:%S')}**")

# ── Интерактивная карта ───────────────────────────────────────────────────────
st.subheader("🗺 Карта полей и техники")

center_lat = fields[0]["coordinates"][0]
center_lon = fields[0]["coordinates"][1]
m = folium.Map(location=[center_lat, center_lon], zoom_start=13, tiles="OpenStreetMap")

# Полигоны полей с цветом по NDVI
for field in fields:
    lat = field["coordinates"][0]
    lon = field["coordinates"][1]
    ndvi_val = get_mock_ndvi(lat, lon)
    color = ndvi_polygon_color(ndvi_val)
    polygon = field.get("polygon", [])
    if polygon:
        folium.Polygon(
            locations=polygon,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.4,
            weight=2,
            tooltip=folium.Tooltip(
                f"<b>{field['name']}</b><br>"
                f"Владелец: {field.get('organization', '—')}<br>"
                f"Культура: {field.get('crop', '—')}<br>"
                f"NDVI: {ndvi_val}"
            ),
        ).add_to(m)

# Динамические маркеры техники из telemetry
for machine in get_active_machinery(fields):
    folium.Marker(
        location=[machine["lat"], machine["lon"]],
        tooltip=(
            f"<b>{machine['icon']} {machine['name']}</b><br>"
            f"Статус: {machine['status']}<br>"
            f"Скорость: {machine['speed']} км/ч"
        ),
        icon=folium.DivIcon(
            html=f'<div style="font-size:24px">{machine["icon"]}</div>',
            icon_size=(30, 30),
            icon_anchor=(15, 15),
        ),
    ).add_to(m)

st_folium(m, use_container_width=True, height=450, returned_objects=[])

st.divider()

# ── Карточки полей ────────────────────────────────────────────────────────────
cols = st.columns(len(fields))

for col, field in zip(cols, fields):
    name = field["name"]
    lat = field["coordinates"][0]
    lon = field["coordinates"][1]
    organization = field.get("organization", "—")

    with col:
        with st.container(border=True):
            st.subheader(f"📌 {name}")
            st.caption(f"🗺 {lat:.4f}°N, {lon:.4f}°E")
            st.caption(f"🏢 Владелец: **{organization}**")
            st.divider()

            try:
                d = fetch_field_data(lat, lon)
            except Exception as e:
                st.error(f"Ошибка получения данных: {e}")
                continue

            # Погода
            st.markdown("**☁️ Погода**")
            m1, m2 = st.columns(2)
            m1.metric("Температура", f"{d['temp']:.1f} °C")
            m2.metric("Ветер", f"{d['wind']:.1f} м/с")
            st.caption(d["description"])

            st.divider()

            # Статус техники
            st.markdown("**🚜 Статус техники**")
            color = tech_status_color(d["tech_status"])
            st.markdown(
                f"<div style='background:{color}22; border-left: 4px solid {color};"
                f"padding:8px 12px; border-radius:6px; font-size:0.9em'>"
                f"{d['tech_status']}</div>",
                unsafe_allow_html=True,
            )

            st.divider()

            # NDVI
            st.markdown("**🌱 Индекс NDVI**")
            nc = ndvi_color(d["ndvi"])
            st.progress(
                int(d["ndvi"] * 100),
                text=f"NDVI = {d['ndvi']}",
            )
            st.markdown(
                f"<div style='background:{nc}22; border-left: 4px solid {nc};"
                f"padding:8px 12px; border-radius:6px; font-size:0.9em'>"
                f"{d['ndvi_text']}</div>",
                unsafe_allow_html=True,
            )

            st.divider()

            # Панель диспетчеризации
            st.markdown("#### 🎛️ Панель управления")
            flight_safe = d["flight_safe"]
            flight_reason = d["flight_danger_reason"]

            col1, col2 = st.columns(2)
            if col1.button(
                "🚁 Направить DJI Agras",
                key=f"drone_{name}",
                use_container_width=True,
                disabled=not flight_safe,
            ):
                st.toast(f"Команда отправлена: DJI Agras T40 вылетает на {name}!", icon="🚁")

            if not flight_safe:
                st.markdown(
                    f"<div style='color:#ff4b4b; font-size:0.85em; margin-top:4px'>"
                    f"⚠️ Вылет запрещен: {flight_reason}!</div>",
                    unsafe_allow_html=True,
                )

            if col2.button("🚜 Маршрут для трактора", key=f"tractor_{name}", use_container_width=True):
                st.toast(f"Координаты загружены в автопилот FJDynamics. Трактор выдвигается на {name}.", icon="🚜")

st.divider()

# ── Историческая аналитика ────────────────────────────────────────────────────
with st.expander("📈 Динамика вегетации (NDVI) за 30 дней"):
    dates = [datetime.today().date() - timedelta(days=i) for i in range(29, -1, -1)]
    rng = np.random.default_rng(seed=42)
    ndvi_history = pd.DataFrame(
        rng.uniform(0.4, 0.9, size=(30, 3)),
        index=dates,
        columns=["Поле Северное", "Поле Южное", "Поле Экспериментальное"],
    )
    st.line_chart(ndvi_history)
