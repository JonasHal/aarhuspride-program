import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd

from functions import fetch_coordinates

DEFAULT_LATITUDE = 56.1566 # Default coords (e.g., Aarhus center) if geocoding fails
DEFAULT_LONGITUDE = 10.2039

COLOR_SCHEME = {
    0: "blue",
    1: "green",
    2: "red",
    3: "purple",
    4: "yellow"
}

def create_full_map(df):
    # Display a default map centered broadly (e.g., on Aarhus)
    m = folium.Map(location=[DEFAULT_LATITUDE, DEFAULT_LONGITUDE], zoom_start=14, control_scale=True)

    # add a marker for the default location (Rådhusparken)
    folium.Marker(
        location=[56.152753, 10.202235],
        popup=folium.Popup("<b>Aarhus Pride Lounge (Rådhusparken)</b>", max_width=200),
        icon=folium.Icon(color="orange", icon="info-sign"),
        tooltip="Aarhus Pride Lounge"
    ).add_to(m)

    for index, event in df.iterrows():
        address = event.get('Lokation')
        venue = event.get('Venue')
        start = event.get('Dato', 'N/A')
        coordinates = None # Initialize coordinates
        if pd.notna(address) and isinstance(address, str):
            coordinates = fetch_coordinates(address) # Fetch coordinates
            if coordinates:
                lat, lon = coordinates
                map_center = [lat, lon]
                # Use address in popup for more context
                popup_text = f"""<b>{event.get('Titel på dit arrangement', 'Event')}</b><ul>
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
                # Case where geocoding failed for a provided address
                st.warning(f"Could not find coordinates for '{address}'. Map cannot be displayed accurately.")
                folium.Marker(
                        location=[DEFAULT_LATITUDE, DEFAULT_LONGITUDE],
                        popup="Default location shown (Aarhus). Event address could not be geocoded.",
                        icon=folium.Icon(color=COLOR_SCHEME.get(index % len(COLOR_SCHEME), "blue"), icon="circle"),
                        tooltip="Approximate Area"
                ).add_to(m)
                st.write("Showing map centered on Aarhus.")
    
    st_data = st_folium(m, height=700, width=500, returned_objects=["last_object_clicked_popup"])

    if st_data["last_object_clicked_popup"] != st.session_state.get("last_clicked"):
        # If a new marker is clicked, update the session state
        st.session_state["last_clicked"] = st_data["last_object_clicked_popup"]
        st.rerun()