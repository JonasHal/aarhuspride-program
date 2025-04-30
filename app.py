import pandas as pd
import streamlit as st

import streamlit_folium as st_folium
from folium import Map, Marker, Popup

# Load the data
df = pd.read_csv("Kopi af Pride arrangementer 2025 (svar) - Formularsvar 1.csv")

# Clean the data



#run the app
st.set_page_config(page_title="Aarhus Pride - Program", page_icon=":rainbow_flag:", layout="wide")

st.title("Aarhus Pride - Program")

#run the app
st.dataframe(df, use_container_width=True)