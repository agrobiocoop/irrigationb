import streamlit as st
import pandas as pd
import math
from datetime import date
import requests
import re

# Ρύθμιση σελίδας
st.set_page_config(
    page_title="Υπολογιστής ETo από Μετεωρολογικά Δεδομένα",
    page_icon="🌦️",
    layout="centered"
)

# Απλοποιημένη συνάρτηση για ανάκτηση δεδομένων (χωρίς BeautifulSoup)
@st.cache_data(ttl=3600)
def get_meteo_data(url="https://penteli.meteo.gr/stations/alikianos/"):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        content = response.text
        
        # Αναζήτηση δεδομένων με regex (χωρίς BeautifulSoup)
        data = {}
        
        # Μέση θερμοκρασία
        temp_avg_match = re.search(r'θερμοκρασία[^>]*μέση[^>]*>([^<]+)<', content, re.IGNORECASE)
        if temp_avg_match:
            data['temp_avg'] = float(re.sub('[^0-9.]', '', temp_avg_match.group(1)))
        
        # Ελάχιστη θερμοκρασία
        temp_min_match = re.search(r'θερμοκρασία[^>]*ελάχιστη[^>]*>([^<]+)<', content, re.IGNORECASE)
        if temp_min_match:
            data['temp_min'] = float(re.sub('[^0-9.]', '', temp_min_match.group(1)))
        
        # Μέγιστη θερμοκρασία
        temp_max_match = re.search(r'θερμοκρασία[^>]*μέγιστη[^>]*>([^<]+)<', content, re.IGNORECASE)
        if temp_max_match:
            data['temp_max'] = float(re.sub('[^0-9.]', '', temp_max_match.group(1)))
        
        # Υγρασία
        rh_match = re.search(r'υγρασία[^>]*μέση[^>]*>([^<]+)<', content, re.IGNORECASE)
        if rh_match:
            data['rh_avg'] = float(re.sub('[^0-9.]', '', rh_match.group(1)))
        
        # Ακτινοβολία
        radiation_match = re.search(r'ακτινοβολία[^>]*ολική[^>]*>([^<]+)<', content, re.IGNORECASE)
        if radiation_match:
            data['radiation'] = float(re.sub('[^0-9.]', '', radiation_match.group(1)))
        
        # Άνεμος
        wind_match = re.search(r'άνεμος[^>]*μέση[^>]*>([^<]+)<', content, re.IGNORECASE)
        if wind_match:
            data['wind_speed'] = float(re.sub('[^0-9.]', '', wind_match.group(1)))
        
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
        
        # Πρόσθετες πληροφορίες
        st.markdown("---")
        st.subheader("Πληροφορίες για το ETo")
        st.info("""
        **Η Εξατμισοδιαπνοή (ETo)** είναι ένα μέτρο της ποσότητας νερού που χάνεται στην ατμόσφαιρα 
        μέσω της εξάτμισης από το έδαφος και της διαπνοής των φυτών. 
        
        - **Χαμηλό ETo (< 3mm)**: Χαμηλές ανάγκες σε άρδευση
        - **Μέτριο ETo (3-6mm)**: Μέτριες ανάγκες σε άρδευση  
        - **Υψηλό ETo (> 6mm)**: Υψηλές ανάγκες σε άρδευση
        """)

if __name__ == "__main__":
    main()