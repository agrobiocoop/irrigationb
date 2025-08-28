import streamlit as st
import requests
import math
from datetime import date, datetime
import pandas as pd
import re

st.set_page_config(page_title="ETo Calculator (meteo.gr + manual)", page_icon="💧", layout="centered")
st.title("💧 ETo (Reference Evapotranspiration) Calculator")

st.markdown(
    """
    Υπολογισμός ETo με Hargreaves–Samani (FAO-56):
    
    **ETo (mm/ημέρα) = 0.0023 × (Tmean + 17.8) × √(Tmax − Tmin) × Ra**

    όπου **Ra** = εξωγήινη ηλιακή ακτινοβολία (MJ/m²/ημ) που εξαρτάται από γεωγραφικό πλάτος και ημέρα του έτους.
    """
)

# ----------------------------
# Utilities
# ----------------------------

@st.cache_data(show_spinner=False)
def fetch_text(url: str) -> str:
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    return r.text

def parse_lat_from_noaayr(text: str) -> float | None:
    """
    NOAAYR.TXT example header line contains 'Latitude: 35.50000 N'
    """
    m = re.search(r"Latitude:\s*([0-9.]+)\s*[NnSs]", text)
    if m:
        return float(m.group(1)) * (1 if "N" in text or "n" in text else -1)
    # fallback older header style: LAT: 35deg 30min
    m2 = re.search(r"LAT:\s*(\d+)\s*deg\s*(\d+)\s*min", text, re.I)
    if m2:
        deg = float(m2.group(1)); minutes = float(m2.group(2))
        return deg + minutes/60.0
    return None

def parse_daily_temps_from_noaamo(text: str, day: int):
    """
    Extract Tmax, Tmin, and (optional) daily mean from NOAAMO.TXT daily line.
    Lines start with day number and include columns:
    DAY  AVG TEMP  HIGH  TIME  LOW  TIME  RH...
    We'll grab HIGH and LOW temps; compute Tmean as (Tmax+Tmin)/2 if not present.
    """
    # find line that starts with the day number (with spaces) e.g. ' 01' or ' 1'
    pattern = re.compile(rf"^\s*{day}\s+(.*)$", re.M)
    m = pattern.search(text)
    if not m:
        return None, None, None
    line = m.group(0)

    # split by whitespace but keep numeric tokens (incl. negative/decimal)
    tokens = re.findall(r"[-+]?\d+(?:\.\d+)?", line)
    # Heuristic:
    # tokens layout often like: [DAY, AVG, HIGH, MAX_TIME_HH, MAX_TIME_MM, LOW, LOW_TIME_HH, LOW_TIME_MM, RHavg, RHmin, RAIN, ...]
    # But sometimes AVG missing. We'll try: DAY always first
    try:
        if len(tokens) >= 3:
            # First token is day
            if int(tokens[0]) != day:
                # sometimes day omitted in tokens due to dash entries; attempt alternative
                pass
            # Try to detect if second token is AVG or HIGH:
            # If there are at least 5 tokens and times interleave, safest is to scan for plausible HIGH/LOW:
            # We'll search for two temps between -20..60 with HIGH > LOW
            nums = [float(x) for x in tokens[1:]]
            # brute force pick two temps that make sense
            t_candidates = [x for x in nums if -30 <= x <= 60]
            # choose the top two extremes as Tmax, Tmin
            if len(t_candidates) >= 2:
                tmax = max(t_candidates)
                tmin = min(t_candidates)
                tmean = (tmax + tmin) / 2.0
                return tmax, tmin, tmean
    except Exception:
        pass
    return None, None, None

def day_of_year_from_date(d: date) -> int:
    return int(d.strftime("%j"))

def ra_extraterrestrial_radiation_MJm2day(latitude_deg: float, doy: int) -> float:
    """
    FAO-56 eqns for extraterrestrial radiation Ra (MJ m-2 day-1)
    latitude in degrees (positive for N, negative for S)
    doy = day of year (1..365/366)
    """
    phi = math.radians(latitude_deg)
    dr = 1 + 0.033 * math.cos(2 * math.pi * doy / 365)  # inverse relative distance Earth-Sun
    delta = 0.409 * math.sin(2 * math.pi * doy / 365 - 1.39)  # solar declination
    omega_s = math.acos(-math.tan(phi) * math.tan(delta))  # sunset hour angle
    G_sc = 0.0820  # solar constant, MJ m-2 min-1
    Ra = (24 * 60 / math.pi) * G_sc * dr * (
        omega_s * math.sin(phi) * math.sin(delta) +
        math.cos(phi) * math.cos(delta) * math.sin(omega_s)
    )  # MJ m-2 day-1
    return Ra

def eto_hargreaves(Tmax: float, Tmin: float, Ra_MJ: float) -> float:
    Tmean = (Tmax + Tmin) / 2.0
    if Tmax <= Tmin:
        return 0.0
    return 0.0023 * (Tmean + 17.8) * math.sqrt(max(Tmax - Tmin, 0)) * Ra_MJ  # mm/day

# ----------------------------
# UI inputs
# ----------------------------
mode = st.radio("Πηγή δεδομένων:", ["Σταθμός meteo.gr", "Χειροκίνητη εισαγωγή"], index=0)

default_station = "alikianos"
station = st.text_input("Station slug (π.χ. alikianos, agia, chania, ...):", value=default_station)
d = st.date_input("Ημερομηνία υπολογισμού", value=date.today())

if mode == "Σταθμός meteo.gr":
    st.caption("Θα διαβαστούν θερμοκρασίες από τα αρχεία NOAAMO/NOAAYR του σταθμού.")
    # Try to get latitude from NOAAYR; fall back to a manual input shown as advanced
    lat = None
    with st.expander("Ρυθμίσεις γεωγραφικού πλάτους (προχωρημένοι)"):
        manual_lat = st.number_input("Γεωγραφικό πλάτος (°, N+: θετικό)", value=35.5, step=0.1, format="%.4f")

    # Fetch NOAAYR for latitude
    try:
        yr_url = f"https://penteli.meteo.gr/stations/{station}/NOAAYR.TXT"
        yr_text = fetch_text(yr_url)
        lat = parse_lat_from_noaayr(yr_text)
    except Exception as e:
        st.warning(f"Δεν κατέστη δυνατή η ανάγνωση γεωγραφικού πλάτους από NOAAYR.TXT ({e}). Χρήση χειροκίνητης τιμής.")

    if lat is None:
        lat = manual_lat

    # Fetch monthly file for given date
    try:
        mo_url = f"https://penteli.meteo.gr/stations/{station}/NOAAMO.TXT"
        mo_text = fetch_text(mo_url)
        tmax, tmin, tmean = parse_daily_temps_from_noaamo(mo_text, d.day)
        if tmax is None:
            st.error("Δεν βρέθηκαν καθημερινές θερμοκρασίες στο NOAAMO.TXT για την επιλεγμένη ημέρα.")
            st.stop()
        st.success(f"Βρέθηκαν θερμοκρασίες: Tmax={tmax:.1f}°C, Tmin={tmin:.1f}°C (Tmean≈{((tmax+tmin)/2):.1f}°C)")

        doy = day_of_year_from_date(d)
        Ra = ra_extraterrestrial_radiation_MJm2day(lat, doy)
        eto = eto_hargreaves(tmax, tmin, Ra)

        st.subheader("Αποτέλεσμα ETo")
        st.metric("ETo (mm/ημέρα)", f"{eto:.2f}")
        st.caption(f"Latitude: {lat:.4f}°, DOY: {doy}, Ra: {Ra:.2f} MJ/m²/ημ")

    except requests.HTTPError as e:
        st.error(f"HTTP σφάλμα ανάγνωσης δεδομένων σταθμού: {e}")
        st.stop()
    except Exception as e:
        st.error(f"Σφάλμα επεξεργασίας δεδομένων σταθμού: {e}")
        st.stop()

else:
    st.caption("Δώσε χειροκίνητα Tmax, Tmin και γεωγραφικό πλάτος.")
    tmax = st.number_input("Tmax (°C)", value=32.0, step=0.1)
    tmin = st.number_input("Tmin (°C)", value=20.0, step=0.1)
    lat = st.number_input("Γεωγραφικό πλάτος (°, N+: θετικό)", value=35.5, step=0.1, format="%.4f")

    doy = day_of_year_from_date(d)
    Ra = ra_extraterrestrial_radiation_MJm2day(lat, doy)
    eto = eto_hargreaves(tmax, tmin, Ra)

    st.subheader("Αποτέλεσμα ETo")
    st.metric("ETo (mm/ημέρα)", f"{eto:.2f}")
    st.caption(f"Latitude: {lat:.4f}°, DOY: {doy}, Ra: {Ra:.2f} MJ/m²/ημ")

# ----------------------------
# Save to CSV
# ----------------------------
st.markdown("---")
st.subheader("Αποθήκευση")
save = st.checkbox("Αποθήκευση αποτελέσματος σε CSV", value=False)
outfile = st.text_input("Όνομα αρχείου CSV", value="eto_log.csv")

if save and st.button("Αποθήκευση τώρα"):
    row = {
        "datetime": datetime.combine(d, datetime.min.time()).isoformat(),
        "mode": mode,
        "station": station if mode == "Σταθμός meteo.gr" else "",
        "latitude_deg": lat,
        "day_of_year": doy,
        "Tmax_C": None if mode == "Σταθμός meteo.gr" and 'tmax' not in locals() else (locals().get('tmax', None)),
        "Tmin_C": None if mode == "Σταθμός meteo.gr" and 'tmin' not in locals() else (locals().get('tmin', None)),
        "Ra_MJ_m2_day": Ra,
        "ETo_mm_day": eto
    }
    try:
        # append with header if file doesn't exist
        try:
            existing = pd.read_csv(outfile)
            header = False
        except Exception:
            header = True
        pd.DataFrame([row]).to_csv(outfile, mode="a", index=False, header=header, encoding="utf-8")
        st.success(f"✅ Αποθηκεύτηκε στο {outfile}")
    except Exception as e:
        st.error(f"Σφάλμα αποθήκευσης: {e}")
