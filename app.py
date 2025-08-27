import streamlit as st
import pandas as pd
import math
from datetime import date

# Βασική ρύθμιση σελίδας
st.set_page_config(page_title="Υπολογιστής Άρδευσης", page_icon="🌱")

st.title("Υπολογιστής Άρδευσης Αβοκάντο 🌱💧")
st.markdown("---")

# Εισαγωγή βασικών παραμέτρων
st.header("Βασικές Παράμετροι")

eto = st.slider("Ημερήσια Εξατμισοδιαπνοή (ETo) σε mm:", 
                min_value=1.0, max_value=10.0, value=5.0, step=0.1)

st.markdown("---")

# Παράμετροι άρδευσης
st.header("Παράμετροι Αβοκάντο")

col1, col2 = st.columns(2)

with col1:
    age = st.selectbox("Ηλικία δέντρου (έτη):", 
                      options=[1, 2, 3, 5, 7, 10], index=2)
    
    soil = st.selectbox("Τύπος εδάφους:", 
                       options=["Αμμώδες", "Αμμοπηλώδες", "Πηλώδες"], 
                       index=1)

with col2:
    canopy_diameter = st.slider("Διάμετρος κόμης (m):", 
                               min_value=1.0, max_value=10.0, 
                               value=3.0, step=0.5)
    
    # Εμφάνιση εμβαδού κόμης
    area = math.pi * (canopy_diameter / 2) ** 2
    st.info(f"Εμβαδόν κόμης: {area:.1f} m²")

st.markdown("---")

# Υπολογισμοί
st.header("Αποτελέσματα Υπολογισμών")

# Συντελεστές
KC_BY_AGE = {1: 0.55, 2: 0.60, 3: 0.65, 5: 0.75, 7: 0.85, 10: 0.90}
SOIL_FACTORS = {"Αμμώδες": 1.2, "Αμμοπηλώδες": 1.0, "Πηλώδες": 0.8}

# Υπολογισμός
kc = KC_BY_AGE.get(age, 0.75)
soil_factor = SOIL_FACTORS.get(soil, 1.0)
water_liters = eto * kc * area * soil_factor

# Εμφάνιση αποτελεσμάτων
col1, col2 = st.columns(2)

with col1:
    st.metric("Συντελεστής καλλιέργειας (Kc)", f"{kc:.2f}")
    st.metric("Συντελεστής εδάφους", f"{soil_factor:.2f}")
    
with col2:
    st.metric("Ημερήσια ανάγκη νερού", f"{water_liters:.1f} λίτρα")
    st.metric("Εβδομαδιαία ανάγκη νερού", f"{water_liters * 7:.1f} λίτρα")

st.markdown("---")

# Συμβουλές άρδευσης
st.header("Συμβουλές Άρδευσης")

st.info(f"""
**Οδηγίες άρδευσης:**
- Ποτίστε το δέντρο με **{water_liters:.1f} λίτρα** νερό καθημερινά
- Καλύτερη ώρα άρδευσης: **πρωί ή απόγευμα**
- Σε ζεστές μέρες (πάνω από 30°C), αυξήστε την άρδευση κατά **20-30%**
- Χρησιμοποιήστε **στάγδην άρδευση** για καλύτερη απόδοση νερού
- Ελέγχετε την υγρασία του εδάφους πριν από κάθε άρδευση
""")

# Αποθήκευση δεδομένων
if st.button("💾 Αποθήκευση Αποτελεσμάτων"):
    today = date.today().isoformat()
    data = {
        "Ημερομηνία": today,
        "Ηλικία δέντρου": age,
        "Τύπος εδάφους": soil,
        "Διάμετρος κόμης (m)": canopy_diameter,
        "ETo (mm)": eto,
        "Κc": kc,
        "Συντελεστής εδάφους": soil_factor,
        "Νερό (λίτρα/ημέρα)": water_liters
    }
    
    df = pd.DataFrame([data])
    
    try:
        # Δοκιμάζουμε να αποθηκεύσουμε τα δεδομένα
        df.to_csv("αποτελέσματα_άρδευσης.csv", mode='a', 
                 index=False, encoding='utf-8-sig',
                 header=not pd.io.common.file_exists("αποτελέσματα_άρδευσης.csv"))
        st.success("✅ Τα δεδομένα αποθηκεύτηκαν επιτυχώς!")
    except Exception as e:
        st.error("⚠️ Η αποθήκευση απέτυχε. Μπορείτε να κάνετε screenshot των αποτελεσμάτων.")

st.markdown("---")
st.caption("Εφαρμογή ανάπτυξης: Υπολογιστής Άρδευσης Αβοκάντο | Ενημερώθηκε: 2024")