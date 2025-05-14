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

def detect_device_type():
    """
    Detects device type in Streamlit by analyzing User-Agent
    
    Returns:
        str: 'mobile', 'tablet', or 'desktop'
    """
    # Get the user agent from Streamlit's session state
    try:
        # Access the underlying connection
        user_agent = st.get_connection_client().user_agent
        if user_agent:
            user_agent = user_agent.lower()
            
            # Check for tablets first (as some tablets also match mobile patterns)
            if re.search(r'ipad|tablet|kindle', user_agent):
                return 'tablet'
            # Check for mobile devices
            elif re.search(r'android|iphone|ipod|windows phone|blackberry|mobile', user_agent):
                return 'mobile'
            else:
                return 'desktop'
        else:
            return 'desktop'  # Default if user_agent can't be determined
    except:
        # Fallback method using session state width
        # Streamlit provides the browser width which we can use as a rough estimate
        if 'browser_width' not in st.session_state:
            # Using JavaScript to get the browser width
            st.markdown(
                """
                <script>
                const width = window.innerWidth;
                sessionStorage.setItem('browser_width', width);
                window.parent.document.querySelector('iframe[src*="streamlit_app"]').addEventListener('load', function() {
                    window.parent.document.querySelector('iframe[src*="streamlit_app"]').contentWindow.postMessage({
                        type: 'streamlit:setComponentValue',
                        value: width
                    }, '*');
                });
                </script>
                """,
                unsafe_allow_html=True
            )
            return 'desktop'  # Default on first load
        
        width = st.session_state.browser_width
        if width < 768:
            return 'mobile'
        elif width < 1024:
            return 'tablet'
        else:
            return 'desktop'

def create_full_map(df):
    # Display a default map centered broadly (e.g., on Aarhus)
    m = folium.Map(location=[DEFAULT_LATITUDE, DEFAULT_LONGITUDE], 
                   zoom_start=14, 
                   control_scale=False,  # Removes the scale bar
                   attribution_control=False  # Removes the attribution text
    )

    # add a marker for the default location (Rådhusparken)
    folium.Marker(
        location=[56.152753, 10.202235],
        popup=folium.Popup("""<b>Aarhus Pride Lounge (Rådhusparken)</b><ul>
            <li>Rådhusparken</li>
            <li>Rådhuspladsen 1, 8000 Aarhus C</li>
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
        start = event.get('Dato', 'N/A')
        if pd.notna(lat) and pd.notna(lon):
            # If lat/lon are already present, use them directly
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
    
    # detect device type
    device_type = detect_device_type()
    if device_type == 'mobile':
        height = 300
        width = 400
    elif device_type == 'tablet':
        height = 400
        width = 600
    else:
        height = 500
        width = 800

    st_data = st_folium(m, height=height, width=width, returned_objects=["last_object_clicked_popup"])

    if st_data["last_object_clicked_popup"] != st.session_state.get("last_clicked"):
        # If a new marker is clicked, update the session state
        st.session_state["last_clicked"] = st_data["last_object_clicked_popup"]
        st.rerun()
