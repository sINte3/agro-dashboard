import json
import os
from datetime import datetime
import folium
import streamlit as st
from dotenv import load_dotenv
from streamlit_folium import st_folium

from weather import get_weather, get_weather_status
from ndvi import get_mock_ndvi, analyze_ndvi
from telemetry import get_active_machinery

load_dotenv()

FIELDS_FILE = os.path.join(os.path.dirname(__file__), "fields.json")

st.set_page_config(
    page_title="Агрокластер — Панель управления",
    page_icon="🌾",
    layout="wide",
)

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
    # Убираем HTML-теги для Streamlit (он работает с markdown)
    ndvi_text_clean = (
        ndvi_text
        .replace("<b>", "**").replace("</b>", "**")
        .replace("NDVI: ", "")
    )
    return {
        "temp": temp,
        "wind": wind,
        "description": description,
        "tech_status": tech_status,
        "ndvi": ndvi,
        "ndvi_text": ndvi_text_clean,
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

center_lat = fields[0]["lat"]
center_lon = fields[0]["lon"]
m = folium.Map(location=[center_lat, center_lon], zoom_start=9, tiles="OpenStreetMap")

# Маркеры полей
for field in fields:
    ndvi_val = get_mock_ndvi(field["lat"], field["lon"])
    folium.Marker(
        location=[field["lat"], field["lon"]],
        tooltip=f"<b>{field['name']}</b><br>NDVI: {ndvi_val}",
        popup=folium.Popup(f"<b>{field['name']}</b><br>NDVI: {ndvi_val}", max_width=200),
        icon=folium.Icon(color="green", icon="leaf", prefix="fa"),
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
    lat = field["lat"]
    lon = field["lon"]

    with col:
        with st.container(border=True):
            st.subheader(f"📌 {name}")
            st.caption(f"🗺 {lat:.4f}°N, {lon:.4f}°E")
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
