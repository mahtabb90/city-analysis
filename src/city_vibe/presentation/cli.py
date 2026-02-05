from __future__ import annotations

import json
import random
import logging
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Tuple

from colorama import Fore, Style, init as colorama_init

from city_vibe.analysis.metrics import summarize_series
from city_vibe.analysis.rules import CityStatus, classify_weather_status
from city_vibe.clients.geo.openmeteo_geocoding_client import OpenMeteoGeocodingClient
from city_vibe.clients.traffic.traffic_client import TrafficClient
from city_vibe.clients.weather.openmeteo_client import OpenMeteoClient
from city_vibe.config import BASE_DIR, DATABASE_PATH
from city_vibe.database import get_connection, get_or_create_city, init_db, insert_record
from city_vibe.domain.models import AnalysisResult, TrafficRecord, WeatherRecord
from city_vibe.presentation.plots import (
    plot_city_status_overview,
    plot_line_series,
    plot_metric_summary_bar,
)

logger = logging.getLogger(__name__)

REPORTS_DIR = BASE_DIR / "reports"
PLOTS_DIR = REPORTS_DIR / "plots"
SUMMARY_DIR = REPORTS_DIR / "summary"
COMMENTS_JSON_PATH = BASE_DIR / "data" / "comments.json"


# Traffic mock-api (mock_api.py kör /traffic på port 5001)
DEFAULT_TRAFFIC_BASE_URL = "http://127.0.0.1:5001/traffic"


# -----------------------------
# UI helpers (Colorama)
# -----------------------------
def ui_init() -> None:
    colorama_init(autoreset=True)


def h1(text: str) -> str:
    return f"{Style.BRIGHT}{Fore.CYAN}{text}{Style.RESET_ALL}"


def ok(text: str) -> str:
    return f"{Fore.GREEN}✅ {text}{Style.RESET_ALL}"


def warn(text: str) -> str:
    return f"{Fore.YELLOW}⚠️  {text}{Style.RESET_ALL}"


def err(text: str) -> str:
    return f"{Fore.RED}❌ {text}{Style.RESET_ALL}"


def dim(text: str) -> str:
    return f"{Style.DIM}{text}{Style.RESET_ALL}"


def vibe_banner() -> None:
    print()
    print(h1("🌆 City Vibe Analyzer"))
    print(dim("We translate meteorological data into how a city actually feels."))
    print(dim("Because numbers without context don’t tell the full story."))
    print()


def menu_print() -> None:
    print(h1("Choose your flow"))
    print(f"{Fore.MAGENTA}1){Style.RESET_ALL} Sense the city (analyze current vibe)")
    print(f"{Fore.MAGENTA}2){Style.RESET_ALL} View latest vibe analysis (from DB)")
    print(f"{Fore.MAGENTA}3){Style.RESET_ALL} List saved cities (from DB)")
    print(f"{Fore.MAGENTA}4){Style.RESET_ALL} List recent runs (from DB)")
    print(f"{Fore.MAGENTA}5){Style.RESET_ALL} Re-generate plots (from DB data)")
    print(f"{Fore.MAGENTA}6){Style.RESET_ALL} Database info")
    print(f"{Fore.MAGENTA}7){Style.RESET_ALL} Exit")


# -----------------------------
# Helpers
# -----------------------------
def _ensure_report_dirs() -> None:
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    SUMMARY_DIR.mkdir(parents=True, exist_ok=True)


def _now_slug() -> str:
    # ex: 20260204_112233
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _safe_city(city: str) -> str:
    return "".join(ch for ch in city.strip().lower().replace(" ", "_") if ch.isalnum() or ch == "_")


def _input_float(prompt: str, *, required: bool = True) -> Optional[float]:
    while True:
        raw = input(prompt).strip()
        if not raw and not required:
            return None
        try:
            return float(raw)
        except ValueError:
            print(warn("Please enter a valid number."))


def _db_row_count(table_name: str) -> int:
    with get_connection() as conn:
        row = conn.execute(f"SELECT COUNT(*) AS n FROM {table_name}").fetchone()
        return int(row["n"]) if row else 0


def _fetch_city_row(city_name: str) -> Optional[dict[str, Any]]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, name, latitude, longitude FROM cities WHERE name = ?",
            (city_name,),
        ).fetchone()
        if not row:
            return None
        return {
            "id": int(row["id"]),
            "name": row["name"],
            "latitude": row["latitude"],
            "longitude": row["longitude"],
        }


def _fetch_city_id(city_name: str) -> Optional[int]:
    row = _fetch_city_row(city_name)
    return row["id"] if row else None


def _fetch_latest_analysis(city_id: int, category: str) -> Optional[dict[str, Any]]:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT id, city_id, timestamp, category, status, metrics_json
            FROM analysis_results
            WHERE city_id = ? AND category = ?
            ORDER BY timestamp DESC
            LIMIT 1
            """,
            (city_id, category),
        ).fetchone()

    if not row:
        return None

    try:
        metrics = json.loads(row["metrics_json"]) if row["metrics_json"] else {}
    except json.JSONDecodeError:
        metrics = {"raw_metrics_json": row["metrics_json"]}

    return {
        "timestamp": row["timestamp"],
        "category": row["category"],
        "status": row["status"],
        "metrics": metrics,
    }


def _fetch_recent_points(city_id: int, *, limit: int = 30) -> tuple[list[WeatherRecord], list[TrafficRecord]]:
    """
    Hämtar senaste N datapunkter från DB och returnerar i kronologisk ordning (äldst->nyast).
    """
    with get_connection() as conn:
        w_rows = conn.execute(
            """
            SELECT id, city_id, timestamp, temperature, humidity
            FROM weather_data
            WHERE city_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (city_id, limit),
        ).fetchall()

        t_rows = conn.execute(
            """
            SELECT id, city_id, timestamp, congestion_level, speed, incidents
            FROM traffic_data
            WHERE city_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (city_id, limit),
        ).fetchall()

    w_rows = list(reversed(w_rows))
    t_rows = list(reversed(t_rows))

    weather = [
        WeatherRecord(
            id=int(r["id"]),
            city_id=int(r["city_id"]),
            timestamp=datetime.fromisoformat(str(r["timestamp"])) if isinstance(r["timestamp"], str) else r["timestamp"],
            temperature=float(r["temperature"]),
            humidity=float(r["humidity"]) if r["humidity"] is not None else 0.0,
        )
        for r in w_rows
    ]
    traffic = [
        TrafficRecord(
            id=int(r["id"]),
            city_id=int(r["city_id"]),
            timestamp=datetime.fromisoformat(str(r["timestamp"])) if isinstance(r["timestamp"], str) else r["timestamp"],
            congestion_level=float(r["congestion_level"]),
            speed=float(r["speed"]) if r["speed"] is not None else None,
            incidents=int(r["incidents"]) if r["incidents"] is not None else None,
        )
        for r in t_rows
    ]
    return weather, traffic


def _write_summary(city_name: str, run_ts_slug: str, payload: dict[str, Any]) -> Path:
    _ensure_report_dirs()
    out = SUMMARY_DIR / f"{_safe_city(city_name)}_{run_ts_slug}.json"
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return out

def _load_comments_config() -> dict[str, Any]:
    if not COMMENTS_JSON_PATH.exists():
        raise FileNotFoundError(f"Comments config not found: {COMMENTS_JSON_PATH}")
    return json.loads(COMMENTS_JSON_PATH.read_text(encoding="utf-8"))


def _pick_weather_comment(config: dict[str, Any], temperature: float) -> str:
    for rule in config.get("weather", []):
        tmin = rule.get("temperature_min")
        tmax = rule.get("temperature_max")
        if tmin is None or tmax is None:
            continue
        if float(tmin) <= temperature <= float(tmax):
            comments = rule.get("comments") or []
            return random.choice(comments) if comments else ""
    return ""


def _pick_traffic_comment(config: dict[str, Any], traffic_status: str) -> str:
    """
    Din config använder 'status' som: heavy/delayed/normal.
    Just nu har vi inte exakt samma status i analys_results (ni sparar CityStatus).
    Så vi mappar CityStatus -> config-status:
      - BAD -> heavy
      - OK -> normal
      - GOOD -> normal (du kan ändra senare)
    """
    status_map = {"BAD": "heavy", "OK": "normal", "GOOD": "normal"}
    mapped = status_map.get(traffic_status.upper(), "normal")

    # välj första matchen oavsett mode, eller prioritera "train" om du vill
    for rule in config.get("traffic", []):
        if str(rule.get("status")).lower() == mapped:
            comments = rule.get("comments") or []
            return random.choice(comments) if comments else ""
    return ""


def _resolve_coordinates(city_name: str) -> Tuple[float, float]:
    """
    Resolve city -> (lat, lon) in this order:
    1) If city exists in DB with lat/lon, reuse
    2) Geocode via Open-Meteo
    3) Fallback to manual input (only if needed)
    """
    row = _fetch_city_row(city_name)
    if row and row.get("latitude") is not None and row.get("longitude") is not None:
        lat = float(row["latitude"])
        lon = float(row["longitude"])
        print(ok(f"Using saved coordinates from DB: lat={lat}, lon={lon}"))
        return lat, lon

    print(dim("Finding city coordinates (geocoding)…"))
    geo = OpenMeteoGeocodingClient()
    try:
        lat, lon = geo.geocode(city_name, country_code="SE")
        print(ok(f"Found coordinates: lat={lat}, lon={lon}"))
        return lat, lon
    except Exception as e:
        print(warn(f"Geocoding failed: {e}"))
        print(dim("Fallback: please enter coordinates manually."))
        lat = _input_float("Latitude: ", required=True)
        lon = _input_float("Longitude: ", required=True)
        if lat is None or lon is None:
            raise ValueError("Latitude/Longitude is required.")
        return lat, lon


# -----------------------------
# Core flows
# -----------------------------
def analyze_city_run() -> None:
    """
    1) Sense the city (analyze current vibe)
    - user skriver stad
    - programmet hämtar lat/lon automatiskt (DB -> geocoding -> fallback)
    - hämtar data via clients
    - kör metrics + rules
    - sparar i SQLite (weather_data, traffic_data, analysis_results)
    - genererar plots i reports/plots/
    - skapar summary i reports/summary/ (json)
    """
    init_db()
    _ensure_report_dirs()

    print()
    print(h1("🔍 Reading the city's atmosphere…"))
    print(dim("Collecting climate signals and urban motion."))

    city_name = input(f"{Fore.CYAN}City name:{Style.RESET_ALL} ").strip()
    if not city_name:
        print(err("City name cannot be empty."))
        return

    try:
        lat, lon = _resolve_coordinates(city_name)
    except Exception as e:
        print(err(str(e)))
        return

    traffic_base_url = input(
        f"{Fore.CYAN}Traffic base url{Style.RESET_ALL} (Enter for default {DEFAULT_TRAFFIC_BASE_URL}): "
    ).strip()
    if not traffic_base_url:
        traffic_base_url = DEFAULT_TRAFFIC_BASE_URL

    run_ts_slug = _now_slug()

    # --- Fetch data via clients ---
    weather_client = OpenMeteoClient()
    traffic_client = TrafficClient(base_url=traffic_base_url)

    weather_data = weather_client.get_current_weather(lat, lon)
    if weather_data is None:
        print(err("Could not fetch weather data (Open-Meteo returned None)."))
        return

    try:
        traffic_data = traffic_client.fetch_traffic(city_name)
    except Exception as e:
        print(err(f"Could not fetch traffic data: {e}"))
        print(dim("Tip: start mock_api.py in another terminal, or verify the base URL."))
        return

    # --- Store raw records ---
    city_id = get_or_create_city(city_name, lat, lon)

    # WeatherRecord requires humidity float -> OpenMeteo current doesn't provide humidity in your client
    w_record = WeatherRecord(
        city_id=city_id,
        timestamp=weather_data["time"],
        temperature=float(weather_data["temperature"]),
        humidity=0.0,
    )
    insert_record("weather_data", w_record)

    t_record = TrafficRecord(
        city_id=city_id,
        timestamp=datetime.now(),
        congestion_level=float(traffic_data.get("congestion", traffic_data.get("congestion_level", 0.0))),
        speed=float(traffic_data["speed"]) if traffic_data.get("speed") is not None else None,
        incidents=int(traffic_data["incidents"]) if traffic_data.get("incidents") is not None else None,
    )
    insert_record("traffic_data", t_record)

    # --- Build series from DB (last N points) ---
    weather_series, traffic_series = _fetch_recent_points(city_id, limit=30)

    temps = [r.temperature for r in weather_series] or [w_record.temperature]
    congs = [r.congestion_level for r in traffic_series] or [t_record.congestion_level]

    weather_metrics = summarize_series(temps)
    traffic_metrics = summarize_series(congs)

    weather_status: CityStatus = classify_weather_status(weather_metrics)
    traffic_status: CityStatus = classify_weather_status(traffic_metrics)  # reuse same rules for now

    # --- Save analysis_results (2 rows: weather + traffic) ---
    insert_record(
        "analysis_results",
        AnalysisResult(
            city_id=city_id,
            timestamp=datetime.now(),
            category="weather",
            status=weather_status.value,
            metrics_json=json.dumps(asdict(weather_metrics), ensure_ascii=False),
        ),
    )
    insert_record(
        "analysis_results",
        AnalysisResult(
            city_id=city_id,
            timestamp=datetime.now(),
            category="traffic",
            status=traffic_status.value,
            metrics_json=json.dumps(asdict(traffic_metrics), ensure_ascii=False),
        ),
    )

    # --- Plots ---
    plot_paths: dict[str, str] = {}

    weather_line = PLOTS_DIR / f"{_safe_city(city_name)}_weather_line_{run_ts_slug}.png"
    plot_line_series(
        temps,
        weather_line,
        title=f"{city_name} - Temperature",
        x_label="Samples",
        y_label="°C",
    )
    plot_paths["weather_line"] = str(weather_line)

    traffic_line = PLOTS_DIR / f"{_safe_city(city_name)}_traffic_line_{run_ts_slug}.png"
    plot_line_series(
        congs,
        traffic_line,
        title=f"{city_name} - Congestion",
        x_label="Samples",
        y_label="Congestion",
    )
    plot_paths["traffic_line"] = str(traffic_line)

    weather_bar = PLOTS_DIR / f"{_safe_city(city_name)}_weather_metrics_{run_ts_slug}.png"
    plot_metric_summary_bar(weather_metrics, weather_bar, title=f"{city_name} - Weather Metrics")
    plot_paths["weather_metrics_bar"] = str(weather_bar)

    traffic_bar = PLOTS_DIR / f"{_safe_city(city_name)}_traffic_metrics_{run_ts_slug}.png"
    plot_metric_summary_bar(traffic_metrics, traffic_bar, title=f"{city_name} - Traffic Metrics")
    plot_paths["traffic_metrics_bar"] = str(traffic_bar)

    weather_status_plot = PLOTS_DIR / f"{_safe_city(city_name)}_weather_status_{run_ts_slug}.png"
    plot_city_status_overview(weather_status, weather_status_plot, title=f"{city_name} - Weather Status")
    plot_paths["weather_status"] = str(weather_status_plot)

    traffic_status_plot = PLOTS_DIR / f"{_safe_city(city_name)}_traffic_status_{run_ts_slug}.png"
    plot_city_status_overview(traffic_status, traffic_status_plot, title=f"{city_name} - Traffic Status")
    plot_paths["traffic_status"] = str(traffic_status_plot)

    # --- Summary file ---
    summary_payload = {
        "city": city_name,
        "run_id": run_ts_slug,
        "lat": lat,
        "lon": lon,
        "mission": (
            "We bridge the gap between objective weather data and subjective city experience. "
            "We don’t just measure numbers — we measure atmosphere."
        ),
        "latest_weather": {
            "time": str(weather_data["time"]),
            "temperature": weather_data["temperature"],
            "description": weather_data.get("description"),
        },
        "latest_traffic": traffic_data,
        "analysis": {
            "weather": {"status": weather_status.value, "metrics": asdict(weather_metrics)},
            "traffic": {"status": traffic_status.value, "metrics": asdict(traffic_metrics)},
        },
        "plots": plot_paths,
    }

    summary_path = _write_summary(city_name, run_ts_slug, summary_payload)

    # --- Nice output ---
    print()
    print(h1("✨ City vibe decoded"))
    print(f"{Style.BRIGHT}City:{Style.RESET_ALL} {city_name}  {dim(f'(lat={lat}, lon={lon})')}")
    print(f"{Style.BRIGHT}Weather vibe:{Style.RESET_ALL} {Fore.CYAN}{weather_status.value}{Style.RESET_ALL}")
    print(f"{Style.BRIGHT}Traffic vibe:{Style.RESET_ALL} {Fore.CYAN}{traffic_status.value}{Style.RESET_ALL}")
    print()
    print(dim("We don’t just measure temperature. We measure how the city feels today."))
    print(ok(f"Summary saved: {summary_path}"))
    print(ok("Plots saved:"))
    for k, v in plot_paths.items():
        print(f"  {Fore.MAGENTA}•{Style.RESET_ALL} {k}: {v}")


def view_latest_analysis_for_city() -> None:
    """
    2) View latest analysis for a city (from DB)
    """
    init_db()
    city_name = input(f"{Fore.CYAN}City name:{Style.RESET_ALL} ").strip()
    if not city_name:
        print(err("City name cannot be empty."))
        return

    city_id = _fetch_city_id(city_name)
    if city_id is None:
        print(warn("City not found in DB."))
        return

    weather = _fetch_latest_analysis(city_id, "weather")
    traffic = _fetch_latest_analysis(city_id, "traffic")

    if not weather and not traffic:
        print(warn("No analysis results found for this city."))
        return

    print()
    print(h1(f"🕒 Latest vibe analysis for {city_name}"))

    if weather:
        print(
            f"{Fore.CYAN}[WEATHER]{Style.RESET_ALL} {weather['timestamp']}  "
            f"status={Style.BRIGHT}{weather['status']}{Style.RESET_ALL}  metrics={weather['metrics']}"
        )
    else:
        print(f"{Fore.CYAN}[WEATHER]{Style.RESET_ALL} {dim('No results')}")

    if traffic:
        print(
            f"{Fore.CYAN}[TRAFFIC]{Style.RESET_ALL} {traffic['timestamp']}  "
            f"status={Style.BRIGHT}{traffic['status']}{Style.RESET_ALL}  metrics={traffic['metrics']}"
        )
    else:
        print(f"{Fore.CYAN}[TRAFFIC]{Style.RESET_ALL} {dim('No results')}")

    summaries = sorted(SUMMARY_DIR.glob(f"{_safe_city(city_name)}_*.json"), reverse=True)
    if summaries:
      latest = summaries[0]
      print(f"\nLatest summary file: {latest}")

    # Läs summary JSON och skriv "comment" till användaren
    try:
        summary = json.loads(latest.read_text(encoding="utf-8"))
        config = _load_comments_config()

        # Weather-comment baserat på temperatur
        temp = float(summary["latest_weather"]["temperature"])
        w_comment = _pick_weather_comment(config, temp)

        # Traffic-comment baserat på senaste traffic-status från DB (CityStatus)
        # (du har redan traffic = _fetch_latest_analysis(...))
        t_comment = ""
        if traffic:
            t_comment = _pick_traffic_comment(config, str(traffic["status"]))

        print("\n--- Vibe recommendation ---")
        if w_comment:
            print(f"🌤️  {w_comment}")
        if t_comment:
            print(f"🚦 {t_comment}")

    except Exception as e:
        print(f"(Could not load recommendations: {e})")



def list_saved_cities() -> None:
    """
    3) List saved cities (from DB)
    """
    init_db()
    with get_connection() as conn:
        rows = conn.execute("SELECT id, name, latitude, longitude FROM cities ORDER BY name ASC").fetchall()

    print()
    if not rows:
        print(warn("No cities saved yet."))
        return

    print(h1("🏙️  Saved cities"))
    for r in rows:
        print(f"{r['id']}: {Style.BRIGHT}{r['name']}{Style.RESET_ALL} (lat={r['latitude']}, lon={r['longitude']})")


def list_recent_runs() -> None:
    """
    4) List recent runs (from DB)
    """
    init_db()
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT c.name AS city, ar.timestamp, ar.category, ar.status
            FROM analysis_results ar
            JOIN cities c ON c.id = ar.city_id
            ORDER BY ar.timestamp DESC
            LIMIT 10
            """
        ).fetchall()

    print()
    if not rows:
        print(warn("No analysis runs found."))
        return

    print(h1("📈 Recent runs (latest 10)"))
    for r in rows:
        print(f"{r['timestamp']} | {r['city']} | {r['category']} | {Style.BRIGHT}{r['status']}{Style.RESET_ALL}")


def generate_plots_again() -> None:
    """
    5) Generate plots again (from DB data)
    """
    init_db()
    _ensure_report_dirs()

    city_name = input(f"{Fore.CYAN}City name:{Style.RESET_ALL} ").strip()
    if not city_name:
        print(err("City name cannot be empty."))
        return

    city_id = _fetch_city_id(city_name)
    if city_id is None:
        print(warn("City not found in DB."))
        return

    try:
        limit = int(input(f"{Fore.CYAN}How many datapoints?{Style.RESET_ALL} (default 30): ").strip() or "30")
    except ValueError:
        limit = 30

    weather_series, traffic_series = _fetch_recent_points(city_id, limit=limit)
    if not weather_series and not traffic_series:
        print(warn("No data points found to plot."))
        return

    temps = [r.temperature for r in weather_series]
    congs = [r.congestion_level for r in traffic_series]

    run_ts_slug = f"regen_{_now_slug()}"
    plot_paths: dict[str, str] = {}

    if temps:
        out = PLOTS_DIR / f"{_safe_city(city_name)}_weather_line_{run_ts_slug}.png"
        plot_line_series(temps, out, title=f"{city_name} - Temperature (regen)", x_label="Samples", y_label="°C")
        plot_paths["weather_line"] = str(out)

        m = summarize_series(temps)
        out2 = PLOTS_DIR / f"{_safe_city(city_name)}_weather_metrics_{run_ts_slug}.png"
        plot_metric_summary_bar(m, out2, title=f"{city_name} - Weather Metrics (regen)")
        plot_paths["weather_metrics_bar"] = str(out2)

        s = classify_weather_status(m)
        out3 = PLOTS_DIR / f"{_safe_city(city_name)}_weather_status_{run_ts_slug}.png"
        plot_city_status_overview(s, out3, title=f"{city_name} - Weather Status (regen)")
        plot_paths["weather_status"] = str(out3)

    if congs:
        out = PLOTS_DIR / f"{_safe_city(city_name)}_traffic_line_{run_ts_slug}.png"
        plot_line_series(congs, out, title=f"{city_name} - Congestion (regen)", x_label="Samples", y_label="Congestion")
        plot_paths["traffic_line"] = str(out)

        m = summarize_series(congs)
        out2 = PLOTS_DIR / f"{_safe_city(city_name)}_traffic_metrics_{run_ts_slug}.png"
        plot_metric_summary_bar(m, out2, title=f"{city_name} - Traffic Metrics (regen)")
        plot_paths["traffic_metrics_bar"] = str(out2)

        s = classify_weather_status(m)
        out3 = PLOTS_DIR / f"{_safe_city(city_name)}_traffic_status_{run_ts_slug}.png"
        plot_city_status_overview(s, out3, title=f"{city_name} - Traffic Status (regen)")
        plot_paths["traffic_status"] = str(out3)

    print()
    print(ok("Plots regenerated"))
    for k, v in plot_paths.items():
        print(f"  {Fore.MAGENTA}•{Style.RESET_ALL} {k}: {v}")


def database_info() -> None:
    """
    6) Database info
    """
    init_db()
    print()
    print(h1("🗄️  Database info"))
    print(f"DB path: {Style.BRIGHT}{DATABASE_PATH}{Style.RESET_ALL}")
    print(f"DB exists: {Style.BRIGHT}{DATABASE_PATH.exists()}{Style.RESET_ALL}")

    for table in ["cities", "weather_data", "traffic_data", "analysis_results"]:
        try:
            print(f"{table}: {_db_row_count(table)} rows")
        except Exception as e:
            print(warn(f"{table}: error reading count ({e})"))


def menu() -> None:
    """
    7) Exit
    """
    init_db()
    _ensure_report_dirs()

    vibe_banner()

    while True:
        menu_print()
        choice = input(f"{Fore.CYAN}Select option (1-7):{Style.RESET_ALL} ").strip()

        if choice == "1":
            analyze_city_run()
        elif choice == "2":
            view_latest_analysis_for_city()
        elif choice == "3":
            list_saved_cities()
        elif choice == "4":
            list_recent_runs()
        elif choice == "5":
            generate_plots_again()
        elif choice == "6":
            database_info()
        elif choice == "7":
            print(ok("Bye!"))
            break
        else:
            print(warn("Please choose 1-7."))


if __name__ == "__main__":
    ui_init()
    logging.basicConfig(level=logging.INFO)
    menu()
