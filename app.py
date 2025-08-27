import streamlit as st
import pandas as pd
import math
from datetime import date
import requests
from bs4 import BeautifulSoup
import re

# Ρύθμιση σελίδας
st.set_page_config(
    page_title="Υπολογιστής ETo από Μετεωρολογικά Δεδομένα",
    page_icon="🌦️",
    layout="centered"
)

# Κρύβουμε το default menu για καλύτερη εμφάνιση
hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

st.title("Υπολογιστής ETo από Μετεωρολογικά Δεδομένα 🌦️")
st.markdown("---")

# Συνάρτηση για ανάκτηση δεδομένων από τον σταθμό του ΕΜΥ
@st.cache_data(ttl=3600)  # Cache για 1 ώρα
def get_meteo_data(url="https://penteli.meteo.gr/stations/alikianos/"):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Αναζήτηση δεδομένων στον πίνακα
        data_table = soup.find('table', {'class': 'meteo-table'})
        if not data_table:
            return None
            
        rows = data_table.find_all('tr')
        data = {}
        
        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 2:
                param_name = cols[0].get_text().strip().lower()
                param_value = cols[1].get_text().strip()
                
                # Εξαγωγή θερμοκρασίας
                if 'θερμοκρασία' in param_name and 'μέση' in param_name:
                    data['temp_avg'] = float(param_value.replace('°C', '').strip())
                elif 'θερμοκρασία' in param_name and 'ελάχιστη' in param_name:
                    data['temp_min'] = float(param_value.replace('°C', '').strip())
                elif 'θερμοκρασία' in param_name and 'μέγιστη' in param_name:
                    data['temp_max'] = float(param_value.replace('°C', '').strip())
                
                # Εξαγωγή υγρασίας
                elif 'υγρασία' in param_name and 'μέση' in param_name:
                    data['rh_avg'] = float(param_value.replace('%', '').strip())
                
                # Εξαγωγή ακτινοβολίας
                elif 'ακτινοβολία' in param_name and 'ολική' in param_name:
                    data['radiation'] = float(param_value.replace('Wh/m²', '').strip())
                
                # Εξαγωγή ανέμου
                elif 'άνεμος' in param_name and 'μέση' in param_name:
                    wind_text = param_value.replace('km/h', '').strip()
                    data['wind_speed'] = float(wind_text) if wind_text else 0
        
        return data
        
    except Exception as e:
        st.error(f"Σφάλμα ανάκτησης δεδομένων: {str(e)}")
        return None

# Συνάρτηση υπολογισμού ETo με FAO Penman-Monteith
def calculate_eto(temp_avg, temp_min, temp_max, rh_avg, radiation, wind_speed):
    try:
        # Μετατροπές μονάδων
        wind_ms = wind_speed * (1000 / 3600)  # km/h to m/s
        radiation_mj = radiation * 0.0036  # Wh/m² to MJ/m²/day
        
        # 1. Κλίση της καμπύλης πίεσης ατμών (Δ)
        es = 0.6108 * math.exp((17.27 * temp_avg) / (temp_avg + 237.3))
        delta = (4098 * es) / ((temp_avg + 237.3) ** 2)
        
        # 2. Ατμοσφαιρική πίεση (P) και ψυχομετρική σταθερά (γ)
        P = 101.3  # kPa
        gamma = 0.000665 * P
        
        # 3. Πίεση ατμών κορεσμού (e_s) και πραγματική πίεση ατμών (e_a)
        e_s = 0.6108 * math.exp((17.27 * temp_avg) / (temp_avg + 237.3))
        e_a = (rh_avg / 100) * e_s
        
        # 4. Καθαρή ακτινοβολία (R_n)
        R_ns = (1 - 0.23) * radiation_mj  # Αλβέδο 0.23
        R_nl = 4.903e-9 * (((temp_max + 273) ** 4 + (temp_min + 273) ** 4) / 2) * (0.34 - 0.14 * math.sqrt(e_a)) * 1.35
        R_n = R_ns - R_nl
        
        # 5. Ροή θερμότητας εδάφους (G) - αμελητέα για ημερήσιους υπολογισμούς
        G = 0
        
        # 6. Τελικός υπολογισμός ETo
        numerator = (0.408 * delta * (R_n - G)) + (gamma * (900 / (temp_avg + 273)) * wind_ms * (e_s - e_a))
        denominator = delta + (gamma * (1 + 0.34 * wind_ms))
        eto = numerator / denominator
        
        return max(0, round(eto, 2))
        
    except Exception as e:
        st.error(f"Σφάλμα υπολογισμού ETo: {str(e)}")
        return None

# Κύρια εφαρμογή
def main():
    st.sidebar.header("Ρυθμίσεις Πηγής Δεδομένων")
    
    option = st.sidebar.radio(
        "Επιλέξτε πηγή δεδομένων:",
        ["Αλικιανός (προεπιλογή)", "Άλλος σταθμός", "Χειροκίνητη εισαγωγή"]
    )
    
    meteo_data = None
    custom_url = ""
    
    if option == "Αλικιανός (προεπιλογή)":
        st.info("Ανάκτηση δεδομένων από τον σταθμό του Αλικιανού...")
        meteo_data = get_meteo_data()
        
    elif option == "Άλλος σταθμός":
        custom_url = st.sidebar.text_input(
            "URL σταθμού ΕΜΥ:",
            value="https://penteli.meteo.gr/stations/alikianos/"
        )
        if st.sidebar.button("Ανάκτηση δεδομένων"):
            meteo_data = get_meteo_data(custom_url)
    
    # Εμφάνιση δεδομένων
    if meteo_data:
        st.subheader("Μετεωρολογικά Δεδομένα")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Μέση Θερμοκρασία", f"{meteo_data.get('temp_avg', 0):.1f} °C")
            st.metric("Ελάχιστη Θερμοκρασία", f"{meteo_data.get('temp_min', 0):.1f} °C")
        with col2:
            st.metric("Μέγιστη Θερμοκρασία", f"{meteo_data.get('temp_max', 0):.1f} °C")
            st.metric("Υγρασία", f"{meteo_data.get('rh_avg', 0):.1f} %")
        with col3:
            st.metric("Ακτινοβολία", f"{meteo_data.get('radiation', 0):.0f} Wh/m²")
            st.metric("Άνεμος", f"{meteo_data.get('wind_speed', 0):.1f} km/h")
        
        # Υπολογισμός ETo
        eto = calculate_eto(
            meteo_data.get('temp_avg', 0),
            meteo_data.get('temp_min', 0),
            meteo_data.get('temp_max', 0),
            meteo_data.get('rh_avg', 0),
            meteo_data.get('radiation', 0),
            meteo_data.get('wind_speed', 0)
        )
        
        if eto is not None:
            st.success(f"Η ημερήσια εξατμισοδιαπνοή (ETo) είναι: **{eto:.2f} mm**")
            
            # Εμφάνιση πρόσθετων πληροφοριών
            st.subheader("Πρόσθετες Πληροφορίες")
            st.info(f"""
            **Ερμηνεία της τιμής ETo:**
            - {eto:.2f} mm αντιστοιχεί σε **{eto * 10:.0f} λίτρα ανά m²** daily
            - Αυτή είναι η ποσότητα νερού που χάνεται daily από εξάτμιση και διαπνοή
            - Για ακριβέστερους γεωργικούς υπολογισμούς, πολλαπλασιάστε με τον συντελεστή καλλιέργειας (Kc)
            """)
    
    else:
        st.warning("Δεν ήταν δυνατή η ανάκτηση δεδομένων. Χρησιμοποιήστε χειροκίνητη εισαγωγή.")
        
        st.subheader("Χειροκίνητη Εισαγωγή Δεδομένων")
        col1, col2 = st.columns(2)
        
        with col1:
            temp_avg = st.number_input("Μέση Θερμοκρασία (°C)", min_value=-10.0, max_value=50.0, value=20.0)
            temp_min = st.number_input("Ελάχιστη Θερμοκρασία (°C)", min_value=-10.0, max_value=50.0, value=15.0)
            temp_max = st.number_input("Μέγιστη Θερμοκρασία (°C)", min_value=-10.0, max_value=50.0, value=25.0)
        
        with col2:
            rh_avg = st.number_input("Μέση Σχετική Υγρασία (%)", min_value=0.0, max_value=100.0, value=60.0)
            radiation = st.number_input("Συνολική Ηλιακή Ακτινοβολία (Wh/m²)", min_value=0.0, max_value=10000.0, value=5000.0)
            wind_speed = st.number_input("Μέση Ταχύτητα Ανέμου (km/h)", min_value=0.0, max_value=100.0, value=10.0)
        
        if st.button("Υπολογισμός ETo"):
            eto = calculate_eto(temp_avg, temp_min, temp_max, rh_avg, radiation, wind_speed)
            if eto is not None:
                st.success(f"Η ημερήσια εξατμισοδιαπνοή (ETo) είναι: **{eto:.2f} mm**")
    
    st.markdown("---")
    st.caption("Εφαρμογή ανάπτυξης: Υπολογιστής ETo από Μετεωρολογικά Δεδομένα | Πηγή: ΕΜΥ")

if __name__ == "__main__":
    main()