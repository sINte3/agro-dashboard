import random

MACHINERY = [
    {"name": "Трактор New Holland T7060", "icon": "🚜", "field_index": 0, "type": "tractor"},
    {"name": "Трактор Puma Case 210",     "icon": "🚜", "field_index": 1, "type": "tractor"},
    {"name": "Дрон DJI Agras T40",        "icon": "🚁", "field_index": 2, "type": "drone"},
]


def get_active_machinery(fields: list) -> list:
    """Возвращает список активной техники с динамическими координатами внутри полигона поля."""
    result = []
    for machine in MACHINERY:
        field = fields[machine["field_index"]]
        polygon = field.get("polygon", [])

        if polygon:
            lats = [p[0] for p in polygon]
            lons = [p[1] for p in polygon]
            lat = random.uniform(min(lats), max(lats))
            lon = random.uniform(min(lons), max(lons))
        else:
            coords = field["coordinates"]
            lat = coords[0] + random.uniform(-0.005, 0.005)
            lon = coords[1] + random.uniform(-0.005, 0.005)

        if machine["type"] == "drone":
            speed = round(random.uniform(15, 30), 1)
        else:
            speed = round(random.uniform(5, 12), 1)

        result.append({
            "name": machine["name"],
            "icon": machine["icon"],
            "field_name": field["name"],
            "lat": lat,
            "lon": lon,
            "speed": speed,
            "status": "В работе",
        })
    return result
