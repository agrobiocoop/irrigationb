import streamlit as st
import math
import requests
from bs4 import BeautifulSoup

st.title("🌱 Υπολογισμός ETo (FAO Penman–Monteith)")

# Επιλογή πηγής δεδομένων
mode = st.radio("Επιλογή δεδομένων", ["Αυτόματα από meteo.gr", "Χειροκίνητη εισαγωγή"])

# Διαθέσιμοι σταθμοί (μπορείς να προσθέσεις όσους θες)
stations = {
    "Αλικιανός Χανίων": "https://penteli.meteo.gr/stations/alikianos/",
    "Σούδα Χανίων": "https://penteli.meteo.gr/stations/souda/",
    "Ηράκλειο": "https://penteli.meteo.gr/stations/heraklion/"
}

if mode == "Αυτόματα από meteo.gr":
    station = st.selectbox("Επιλογή σταθμού", list(stations.keys()))
    url = stations[station]

    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, "lxml")

        # Θερμοκρασία
        temp_text = soup.find("td", string="Θερμοκρασία").find_next("td").text
        t_mean = float(temp_text.split()[0])

        # Υγρασία
        rh_text = soup.find("td", string="Υγρασία").find_next("td").text
        rh_mean = float(rh_text.split()[0])

        # Άνεμος
        wind_text = soup.find("td", string="Άνεμος").find_next("td").text
        u2 = float(wind_text.split()[0])

        # Ηλιακή ακτινοβολία
        rad_text = soup.find("td", string="Ηλιακή Ακτινοβολία")
        if rad_text:
            rad_value = float(rad_text.find_next("td").text.split()[0])
            rad_unit = "W/m²"
        else:
            rad_value = 200.0
            rad_unit = "W/m²"

        t_min = t_mean - 5
        t_max = t_mean + 5
        altitude = 50  # default

        st.write(f"📡 Σταθμός: {station}")
        st.write(f"- Θερμοκρασία: {t_mean} °C")
        st.write(f"- Υγρασία: {rh_mean} %")
        st.write(f"- Άνεμος: {u2} m/s")
        st.write(f"- Ακτινοβολία: {rad_value} {rad_unit}")

    except Exception as e:
        st.error("⚠️ Αποτυχία λήψης δεδομένων από meteo.gr. Δοκίμασε χειροκίνητη εισαγωγή.")
        st.stop()

else:
    # Χειροκίνητη εισαγωγή
    t_mean = st.number_input("Μέση θερμοκρασία (°C)", value=25.0)
    t_min = st.number_input("Ελάχιστη θερμοκρασία (°C)", value=18.0)
    t_max = st.number_input("Μέγιστη θερμοκρασία (°C)", value=32.0)

    rh_mean = st.number_input("Μέση σχετική υγρασία (%)", value=60.0)
    u2 = st.number_input("Ταχύτητα ανέμου (m/s)", value=2.0)

    rad_unit = st.radio("Μονάδα ακτινοβολίας", ["W/m²", "MJ/m²/day"])
    rad_value = st.number_input("Ηλιακή ακτινοβολία", value=200.0)

    altitude = st.number_input("Υψόμετρο (m)", value=50.0)

# --- Μετατροπή ακτινοβολίας σε MJ/m²/day ---
if rad_unit == "W/m²":
    Rs = rad_value * 0.0864
else:
    Rs = rad_value

# --- Υπολογισμοί FAO Penman–Monteith ---
albedo = 0.23
Rn = (1 - albedo) * Rs
G = 0

t_k = t_mean + 273.16
P = 101.3 * ((293 - 0.0065 * altitude) / 293) ** 5.26
gamma = 0.000665 * P

es_tmax = 0.6108 * math.exp((17.27 * t_max) / (t_max + 237.3))
es_tmin = 0.6108 * math.exp((17.27 * t_min) / (t_min + 237.3))
es = (es_tmax + es_tmin) / 2
ea = (rh_mean / 100) * es

delta = (4098 * (0.6108 * math.exp((17.27 * t_mean) / (t_mean + 237.3)))) / ((t_mean + 237.3) ** 2)

eto = (0.408 * delta * (Rn - G) + gamma * (900 / t_k) * u2 * (es - ea)) / (delta + gamma * (1 + 0.34 * u2))

st.subheader("📊 Αποτέλεσμα")
st.success(f"ETo = {eto:.2f} mm/day")
