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

# Απλοποιημένη συνάρτηση για ανάκτηση δεδομένων
@st.cache_data(ttl=3600)
def get_meteo_data(url="https://penteli.meteo.gr/stations/alikianos/"):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Αναζήτηση δεδομένων στον πίνακα
        data = {}
        table = soup.find('table', {'class': 'meteo-table'})
        
        if table:
            rows = table.find_all('tr')
            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 2:
                    param_name = cols[0].get_text().strip().lower()
                    param_value = cols[1].get_text().strip()
                    
                    # Εξαγωγή αριθμητικών τιμών
                    if 'μέση' in param_name and 'θερμοκρασία' in param_name:
                        data['temp_avg'] = float(re.sub('[^0-9.]', '', param_value))
                    elif 'ελάχιστη' in param_name and 'θερμοκρασία' in param_name:
                        data['temp_min'] = float(re.sub('[^0-9.]', '', param_value))
                    elif 'μέγιστη' in param_name and 'θερμοκρασία' in param_name:
                        data['temp_max'] = float(re.sub('[^0-9.]', '', param_value))
                    elif 'υγρασία' in param_name and 'μέση' in param_name:
                        data['rh_avg'] = float(re.sub('[^0-9.]', '', param_value))
                    elif 'ακτινοβολία' in param_name:
                        data['radiation'] = float(re.sub('[^0-9.]', '', param_value))
                    elif 'άνεμος' in param_name and 'μέση' in param_name:
                        data['wind_speed'] = float(re.sub('[^0-9.]', '', param_value))
        
        return data
        
    except Exception as e:
        st.error(f"Σφάλμα ανάκτησης δεδομένων: {str(e)}")
        return None

# Συνάρτηση υπολογισμού ETo
def calculate_eto(temp_avg, temp_min, temp_max, rh_avg, radiation, wind_speed):
    try:
        # Απλοποιημένος υπολογισμός ETo
        wind_ms = wind_speed * (1000 / 3600)
        radiation_mj = radiation * 0.0036
        
        # Βασικός τύπος για ETo (απλοποιημένος)
        eto = (0.408 * 0.25 * radiation_mj + 0.07 * (temp_avg + 5) * (1 - rh_avg/100)) * 0.85
        return max(0.5, min(10.0, round(eto, 2)))
        
    except:
        return 5.0  # Προεπιλεγμένη τιμή

# Κύρια εφαρμογή
def main():
    st.title("Υπολογιστής ETo από Μετεωρολογικά Δεδομένα 🌦️")
    
    # Ανάκτηση δεδομένων
    if st.button("🔍 Ανάκτηση δεδομένων από τον Αλικιανό"):
        with st.spinner("Ανάκτηση δεδομένων..."):
            meteo_data = get_meteo_data()
            
            if meteo_data:
                st.success("Τα δεδομένα ανακτήθηκε επιτυχώς!")
                
                # Εμφάνιση δεδομένων
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Μέση Θερμοκρασία", f"{meteo_data.get('temp_avg', 0):.1f} °C")
                    st.metric("Ελάχιστη Θερμοκρασία", f"{meteo_data.get('temp_min', 0):.1f} °C")
                    st.metric("Μέγιστη Θερμοκρασία", f"{meteo_data.get('temp_max', 0):.1f} °C")
                
                with col2:
                    st.metric("Υγρασία", f"{meteo_data.get('rh_avg', 0):.1f} %")
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
                
                st.info(f"**Ημερήσια Εξατμισοδιαπνοή (ETo): {eto:.2f} mm**")
                
            else:
                st.warning("Δεν ήταν δυνατή η ανάκτηση δεδομένων. Χρησιμοποιήστε χειροκίτη εισαγωγή.")
    
    # Χειροκίτη εισαγωγή δεδομένων
    st.subheader("Χειροκίτη εισαγωγή δεδομένων")
    
    col1, col2 = st.columns(2)
    with col1:
        temp_avg = st.number_input("Μέση Θερμοκρασία (°C)", value=20.0)
        temp_min = st.number_input("Ελάχιστη Θερμοκρασία (°C)", value=15.0)
        temp_max = st.number_input("Μέγιστη Θερμοκρασία (°C)", value=25.0)
    
    with col2:
        rh_avg = st.number_input("Μέση Υγρασία (%)", value=60.0)
        radiation = st.number_input("Ακτινοβολία (Wh/m²)", value=5000.0)
        wind_speed = st.number_input("Ταχύτητα Ανέμου (km/h)", value=10.0)
    
    if st.button("Υπολογισμός ETo"):
        eto = calculate_eto(temp_avg, temp_min, temp_max, rh_avg, radiation, wind_speed)
        st.success(f"**Ημερήσια Εξατμισοδιαπνοή (ETo): {eto:.2f} mm**")

if __name__ == "__main__":
    main()