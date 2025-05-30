import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
import re

DEFAULT_LATITUDE = 56.1566 # Default coords (e.g., Aarhus center) if geocoding fails
DEFAULT_LONGITUDE = 10.2039

COLOR_SCHEME = {
    0: "blue",
    1: "green",
    2: "red",
    3: "purple",
    4: "beige",
}

def create_full_map(df):
    # Display a default map centered broadly (e.g., on Aarhus)
    m = folium.Map(location=[DEFAULT_LATITUDE, DEFAULT_LONGITUDE], 
                   zoom_start=13, 
                   control_scale=False,  # Removes the scale bar
                   attribution_control=False  # Removes the attribution text
    )

    # add a marker for the default location (Rådhusparken)
    folium.Marker(
        location=[56.152753, 10.202235],
        popup=folium.Popup("""<ul>
            <li>Rådhusparken</li>
            <li><b>Aarhus Pride Lounge</b></li>
            <li>Open: 11:00 - 18:00</li>
            </ul>""", max_width=200),
        icon=folium.Icon(color="orange", icon="info-sign"),
        tooltip="Aarhus Pride Lounge"
    ).add_to(m)

    for index, event in df.iterrows():
        address = event.get('Lokation')
        lat = event.get('Latitude')
        lon = event.get('Longitude')
        venue = event.get('Venue')
        start = event.get('Start Tidspunkt', 'N/A')
        if pd.notna(lat) and pd.notna(lon):
            # If lat/lon are already present, use them directly
            map_center = [lat, lon]
            # Use address in popup for more context
            popup_text = f"""<ul>
                    <li>{address}</li>
                    <li>{venue}</li>
                    <li>{start}</li>
                </ul>"""

            folium.Marker(
                location=map_center,
                popup=folium.Popup(popup_text, max_width=200), # Create a proper Popup object
                icon=folium.Icon(color=COLOR_SCHEME.get(index % len(COLOR_SCHEME), "blue"), icon="circle"),
                tooltip=event.get('Titel på dit arrangement', 'Click for details')
            ).add_to(m)

        else:
            continue

    st_data = st_folium(m, height=300, width=400, returned_objects=["last_object_clicked_popup"])

    if st_data["last_object_clicked_popup"] != st.session_state.get("last_clicked"):
        # If a new marker is clicked, update the session state
        st.session_state["last_clicked"] = st_data["last_object_clicked_popup"]
        st.rerun()
