import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from streamlit_scroll_to_top import scroll_to_here
import os
from PIL import Image
import io
import re
import logging
from datetime import datetime
import urllib.parse # Needed for Google Maps link
from preprocess import fetch_coordinates # Import geocoding function from functions.py

# --- Configuration and Setup ---
st.set_page_config(layout="wide", page_title="Event Program")
logging.basicConfig(level=logging.INFO) # Configure logging

DATA_FILE = "events_with_coordinates.csv"
IMAGE_DIR = "PR"
DEFAULT_LATITUDE = 56.1566 # Default coords (e.g., Aarhus center) if geocoding fails
DEFAULT_LONGITUDE = 10.2039

@st.cache_resource # Cache the function to avoid reloading data unnecessarily
def load_data(file_path):
    """Loads event data from a CSV file and performs robust cleaning on column names."""
    try:
        df = pd.read_csv(file_path, parse_dates=['Dato_dt']) # Parse 'Dato_dt' as datetime during loading

        # Optional: Filter out past events (uncomment if needed)
        today = pd.to_datetime(datetime.today().date())
        df = df.dropna(subset=['Dato_dt']) # Drop rows where date conversion failed
        df = df[df['Dato_dt'] >= today] # Keep events from today onwards
        
        df = df.sample(frac=1).reset_index(drop=True)

        return df

    except FileNotFoundError:
        st.error(f"Error: Data file not found at '{file_path}'. Please create it.")
        return pd.DataFrame()
    except pd.errors.EmptyDataError:
        st.error(f"Error: Data file '{file_path}' is empty.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"An unexpected error occurred loading the data: {e}")
        logging.exception("Error during data loading:") # Log the full traceback
        return pd.DataFrame()

# --- Image Handling ---
def find_image(organizer_name, image_dir=IMAGE_DIR):
    """Finds an image file in the specified directory matching the organizer name (case-insensitive)."""
    if not organizer_name or not isinstance(organizer_name, str):
        return None # Cannot find image without valid organizer name
    if not os.path.isdir(image_dir):
        # Don't clutter the UI with warnings if dir not found, log it instead
        logging.warning(f"Image directory '{image_dir}' not found.")
        return None
    try:
        for filename in os.listdir(image_dir):
            name_part, ext = os.path.splitext(filename)
            # Check if it's a common image extension
            if ext.lower() in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp']:
                 # Simple comparison: organizer name matches filename base (case-insensitive)
                if name_part.lower() == organizer_name.lower():
                    return os.path.join(image_dir, filename)
    except Exception as e:
        logging.error(f"Error accessing image directory '{image_dir}': {e}")
    return None # Return None if no matching image is found or on error

def display_event_image(event):
    # Display Image
    image_path = find_image(event.get('Billede eller PR', ''))
    if image_path:
        try:
            image = Image.open(image_path)
            st.image(image, use_container_width=True)
        except Exception as e:
            st.warning(f"Could not load image: {e}")
            st.caption("Image Error")
    else:
        st.caption(f"No PR image found for '{event.get('Billede eller PR', '')}'")


def display_event_overview(df):
    """Display events in a responsive grid with proper image and card layout."""
    import base64
    import streamlit as st
    from math import ceil
    
    # Initialize session state for selected event if not exists
    if 'selected_event_index' not in st.session_state:
        st.session_state.selected_event_index = None
    
    # Function to handle button click
    def set_event_index(idx):
        st.session_state.selected_event_index = idx
        st.session_state.scroll_to_top = True
    
    # Calculate responsive layout
    col_width = 200  # Same as minmax in CSS
    page_width = 1100  # Approximate max width of Streamlit content area
    max_cols = 4  # Maximum number of columns to show
    num_cols = min(max_cols, max(1, page_width // col_width))
    
    # Enhanced CSS for better styling
    st.markdown("""
    <style>
    /* Overall container adjustments */
    .block-container {
        padding-bottom: 1rem;
        max-width: 100%;
    }
    
    /* Card styling */
    .event-card {
        background: rgba(17, 17, 17, 0.7);
        border-radius: 12px;
        overflow: hidden;
        display: flex;
        flex-direction: column;
        height: 100%;
        box-shadow: 0 3px 10px rgba(0,0,0,0.2);
        transition: transform 0.2s;
    }
    
    .event-card:hover {
        transform: translateY(-5px);
    }
    
    /* Image container */
    .event-img-container {
        width: 100%;
        height: 180px;
        position: relative;
        overflow: hidden;
        background: #111;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    
    .event-img {
        width: 100%;
        height: 100%;
        object-fit: cover;
    }
    
    /* Button styling */
    .stExpander .stButton button {
        width: 100%;
    }
    
    /* Remove extra padding within columns */
    .stColumnContainer {
        gap: 1.5rem !important;
    }
    
    .stColumn > div {
        padding: 0 !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Create rows of columns for the grid
    num_events = len(df)
    num_rows = ceil(num_events / num_cols)
    event_rows = []
    
    # Create rows of events
    for i in range(num_rows):
        start_idx = i * num_cols
        end_idx = min(start_idx + num_cols, num_events)
        event_rows.append(list(df.iloc[start_idx:end_idx].iterrows()))
    
    # Display rows and columns
    for row_idx, event_row in enumerate(event_rows):
        cols = st.columns(num_cols)
        
        for col_idx, (original_idx, event) in enumerate(event_row):
            with cols[col_idx]:
                # Create card container
                with st.container():
                    # Start card div
                    st.markdown('<div class="event-card">', unsafe_allow_html=True)
                    
                    st.caption(f"{event.get("Start Tidspunkt", "N/A")}")
                    # Image container
                    image_path = find_image(event.get('Billede eller PR', ''))
                    if image_path:
                        try:
                            # Read image and convert to base64
                            with open(image_path, "rb") as img_file:
                                img_bytes = img_file.read()
                                img_b64 = base64.b64encode(img_bytes).decode()
                            st.markdown(
                                f'<div class="event-img-container"><img src="data:image/png;base64,{img_b64}" class="event-img"/></div>',
                                unsafe_allow_html=True
                            )
                        except Exception:
                            st.markdown(
                                '<div class="event-img-container" style="color:#777;">No Image</div>',
                                unsafe_allow_html=True
                            )
                    else:
                        st.markdown(
                            '<div class="event-img-container" style="color:#777;">No Image</div>',
                            unsafe_allow_html=True
                        )
                    
                    # Display title
                    title = event.get('Titel på dit arrangement', f'Event {row_idx * num_cols + col_idx + 1}')
                    st.subheader(title, anchor=False)
                    
                    # Create a truly unique key using the original index
                    btn_key = f"btn_idx_{original_idx}"
                    
                    # Add button
                    st.button(
                        "View Details", 
                        key=btn_key, 
                        on_click=set_event_index, 
                        args=(original_idx,)
                    )
                    
                    # End card div
                    st.markdown('</div>', unsafe_allow_html=True)
    
    # If a button was clicked, the session state will be updated
    if st.session_state.selected_event_index is not None:
        # You might want to uncomment this to automatically refresh
        # st.rerun()
        pass


# --- UI Functions ---
def display_event_card(event, index):
    """Displays a summary card for an event in the overview."""
    st.subheader(event.get('Titel på dit arrangement', 'No Title'), anchor=False)

    # Use three columns: Image, Basic Info, Happenings
    col1, _, col2, col3 = st.columns([1, 0.2, 1, 1])

    with col1:
        display_event_image(event)
        # Use the event's index in the dataframe as a unique key for the button
        if st.button("View Details", key=f"details_{index}", type="primary"):
            st.session_state.selected_event_index = index
            st.rerun() # Rerun the script to switch to detail view

    with col2:
        # Display Basic Info and Details Button
        st.write(f"**📅 Date and Time:** {event.get('Start Tidspunkt', 'N/A')}")
        st.write(f"**📅 End:** {event.get('Slut Tidspunkt', 'N/A')}")
        lokation = event.get('Lokation', 'N/A')
        if pd.notna(lokation) and isinstance(lokation, str) and lokation.strip():
            st.write(f"**📍 Location:** {lokation}")
            st.link_button("View on Google Maps", f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(event.get('Lokation', ''))}")
        else:
            st.write("No location provided.")

        st.write(f"**🏛️ Venue:** {event.get('Venue', 'N/A')}")
        st.write(f"**🏳️‍🌈 Organiser:** {event.get('Arrangør', 'N/A')}")
        st.write(f"**👥 Target Audience:** {event.get('Målgruppe', 'N/A')}")
        
        billetlink = event.get('Hvis der er Billetsalg', 'N/A')
        if pd.notna(billetlink) and isinstance(billetlink, str) and billetlink.strip():
            st.write(f"**Entry:** {event.get('Er der fri entré til dit event, eller skal deltagerne betale et beløb i døren?', 'N/A')}")
            st.link_button("🎟️ Get Tickets", billetlink)
        else:
            st.write(f"**Entry:** {event.get('Er der fri entré til dit event, eller skal deltagerne betale et beløb i døren?', 'N/A')}")
        
        st.caption(f"Sponsored by {event.get('Sponsorer', 'N/A')}")

    with col3:
         # Display Happenings/Schedule
         st.write("**Schedule / Happenings:**")
         happenings = event.get('Tidpunkter og Titel på Happenings')

         if pd.notna(happenings) and isinstance(happenings, str) and happenings.strip():
             # Split by newline and display as a list
             lines = happenings.strip().split('\n')
             for line in lines:
                 st.markdown(f"- {line.strip()}")
             if not lines: # Handle case where it might be whitespace
                 st.caption("N/A")
         else:
             st.caption("No specific schedule provided.")



def display_event_details(event):
    """Displays the full details page for a selected event."""

    # Handle scroll action
    if st.session_state.scroll_to_top:
        scroll_to_here(0, key='top')  # 0ms for instant scroll
        st.container(height=30)
        st.session_state.scroll_to_top = False

    # --- Back Button ---
    if st.button("⬅️ Back to Overview", type="primary"):
        st.session_state.selected_event_index = None
        st.rerun() # Rerun to go back to overview

    # --- Event Title and Basic Info ---
    st.title(event.get('Titel på dit arrangement', 'No Title'))
    st.caption(f"Organised by: {event.get('Arrangør', 'N/A')}")
    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Event Information", anchor=False)
        st.write(f"**📅 Start Time:** {event.get('Start Tidspunkt', 'N/A')}")
        st.write(f"**📅 End Time:** {event.get('Slut Tidspunkt', 'N/A')}")

        #Lokation
        lokation = event.get('Lokation', 'N/A')
        if pd.notna(lokation) and isinstance(lokation, str) and lokation.strip():
            st.write(f"**📍 Location:** {lokation}")
            st.link_button("View on Google Maps", f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(event.get('Lokation', ''))}")
        else:
            st.write("No location provided.")
        st.write(f"**🏛️ Venue:** {event.get('Venue', 'N/A')}")

        #Billetsalg
        billetlink = event.get('Hvis der er Billetsalg', 'N/A')
        if pd.notna(billetlink) and isinstance(billetlink, str) and billetlink.strip():
            st.write(f"**Entry:** {event.get('Er der fri entré til dit event, eller skal deltagerne betale et beløb i døren?', 'N/A')}")
            st.link_button("🎟️ Get Tickets", billetlink)
        else:
            st.write(f"**Entry:** {event.get('Er der fri entré til dit event, eller skal deltagerne betale et beløb i døren?', 'N/A')}")
        
        st.write(f"**👥 Target Audience:** {event.get('Målgruppe', 'N/A')}")
        st.write(f"**✨ Vibe:** {event.get('Stemning', 'N/A')}")
        st.write(f"**♿ Accessibility:** {event.get('Tilgængelighed', 'N/A')}")
        st.write(f"**🍺 Alcohol:** {event.get('Alkohol?', 'N/A')}")

        # --- Code of Conduct Link Button ---
        coc_link = event.get('Evt. link til code of conduct')
        if pd.notna(coc_link) and isinstance(coc_link, str) and coc_link.strip():
             # Basic check if it looks like a valid URL
             if coc_link.startswith('http://') or coc_link.startswith('https://'):
                 st.link_button("📜 View Code of Conduct", coc_link)
             else:
                 # Display the text if it's not a standard link
                 st.write(f"**📜 Code of Conduct:** {coc_link}")

        else: # Optional: uncomment to explicitly state no CoC link
            st.write("**📜 Code of Conduct:** Not provided")


        st.subheader("Description", anchor=False)
        description = event.get('Kort beskrivelse af arrangementet', 'No description provided.')
        st.markdown(description if pd.notna(description) else 'No description provided.')


        st.subheader("Happenings / Schedule", anchor=False)
        happenings = event.get('Tidpunkter og Titel på Happenings')
        if pd.notna(happenings) and isinstance(happenings, str) and happenings.strip():
            # Split by newline and display as a list
            lines = happenings.strip().split('\n')
            for line in lines:
                st.markdown(f"- {line.strip()}")
            if not lines: # Handle case where it might be just whitespace
                 st.write("No specific schedule provided.")
        else:
            st.write("No specific schedule provided.")


    with col2:
        # --- PR Image ---
        st.subheader("PR Image", anchor=False)
        image_path = find_image(event.get('Billede eller PR', ''))
        if image_path:
            try:
                image = Image.open(image_path)
                st.image(image, use_container_width=True)
            except Exception as e:
                st.error(f"Could not load image: {e}")
        else:
            st.caption("No PR image found.")

        # --- Map ---
        st.subheader("Location Map", anchor=False)
        address = event.get('Lokation')
        lat = event.get('Latitude')
        lon = event.get('Longitude')
        lat_list = event.get('Latitude_List')
        lon_list = event.get('Longitude_List')
        venue = event.get('Venue')
        start = event.get('Start Tidspunkt', 'N/A')
        if pd.notna(lat) and pd.notna(lon):
            # If lat/lon are already present, use them directly
            map_center = [lat, lon]
            # Use address in popup for more context
            popup_text = f"""<b>{event.get('Titel på dit arrangement', 'Event')}</b><ul>
                    <li>{address}</li>
                    <li>{venue}</li>
                    <li>{start}</li>
                </ul>"""
                # Use address in popup for more context
            m = folium.Map(location=map_center, zoom_start=15)
            folium.Marker(
                location=map_center,
                popup=folium.Popup(popup_text, max_width=200), # Create a proper Popup object
                icon=folium.Icon(color="blue", icon="info-sign"),
                tooltip=event.get('Titel på dit arrangement', 'Click for details')
            ).add_to(m)
        elif pd.notna(lat_list) and pd.notna(lon_list):
            # If lat/lon lists are present, use them all
            import json
            m = folium.Map(location=[DEFAULT_LATITUDE, DEFAULT_LONGITUDE], zoom_start=14)
            for lat, lon, add, ven in zip(json.loads(lat_list), json.loads(lon_list), address.split("\n"), venue.split(", ")):
                map_center = [lat, lon]
                # Use address in popup for more context
                popup_text = f"""<ul>
                        <li>{add}</li>
                        <li>{ven}</li>
                    </ul>"""
                folium.Marker(
                    location=map_center,
                    popup=folium.Popup(popup_text, max_width=200), # Create a proper Popup object
                    icon=folium.Icon(color="blue", icon="info-sign"),
                    tooltip=ven
                ).add_to(m)
            
        else:
            # Case where geocoding failed for a provided address
            st.warning(f"Could not find coordinates for '{address}'. Map cannot be displayed accurately.")
            # Display a default map centered broadly (e.g., on Aarhus)
            m = folium.Map(location=[DEFAULT_LATITUDE, DEFAULT_LONGITUDE], zoom_start=12)
            folium.Marker(
                    location=[DEFAULT_LATITUDE, DEFAULT_LONGITUDE],
                    popup="Default location shown (Aarhus). Event address could not be geocoded.",
                    icon=folium.Icon(color="green", icon="info-sign"),
                    tooltip="Approximate Area"
            ).add_to(m)
            st.write("Showing map centered on Aarhus.")
        
        st_folium(m, height=350, width=350)

        # --- Google Maps Link Button ---
        if pd.notna(address) and isinstance(address, str):
            # Offer link based on address even if geocoding failed
            Maps_url = f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(address)}"
            st.link_button(f"Search '{address}' on Google Maps", Maps_url)
        # No button if no address and no coordinates


# --- Main App Logic ---
def main():
    """Main function to run the Streamlit application."""

    # Logo
    st.logo("pride_logo_tns.png", size="large")

    # --- Load Data ---
    df = load_data(DATA_FILE)

    if df.empty:
        # Check if the file exists but is empty or failed loading vs file not found
        if os.path.exists(DATA_FILE):
             st.warning("Event data file exists but is empty or could not be loaded correctly. Please check the `data.csv` file format and content.")
        # load_data function handles the FileNotFoundError case
        return # Stop execution if data loading failed or file is empty

    # --- Initialize Session State ---
    if 'selected_event_index' not in st.session_state:
        st.session_state.selected_event_index = None

    if "show_full_map" not in st.session_state:
        st.session_state.show_full_map = False

    if "last_clicked" not in st.session_state:
        st.session_state.last_clicked = None

    if 'scroll_to_top' not in st.session_state:
        st.session_state.scroll_to_top = False

    # --- Sidebar ---
    st.sidebar.title("🗓️ Event Program")

    # Description of the app with details
    st.sidebar.markdown("This app displays the event program for Aarhus Pride.")
    st.sidebar.markdown("You can view the event details, including a Google Maps Link and schedule.")
    st.sidebar.markdown("Use the buttons to navigate between the event overview and details.")
    st.sidebar.markdown("You can also view all events on the overview map.")

    if st.sidebar.button("Homepage"):
        st.session_state.selected_event_index = None
        st.session_state.show_full_map = False
        st.rerun()

    if st.sidebar.button("Overview Map"):
        st.session_state.show_full_map = True
        st.session_state.selected_event_index = None
        st.rerun()

    st.sidebar.markdown("---")
    if st.session_state.selected_event_index is None:
        st.sidebar.info("Click **'View Details'** on an event card to see more information, including a map and schedule.")
    else:
        st.sidebar.info("Showing event details. Use the buttons below or the 'Back' button on the main page.")
        # Add an explicit back button in the sidebar as well
        if st.sidebar.button("⬅️ Back to Event Overview"):
             st.session_state.selected_event_index = None
             st.rerun()

    # --- Full Map Page ---
    if st.session_state.get('show_full_map', True):
        if st.button("<- Go Back to Event Overview", type="primary"):
            st.session_state.show_full_map = False
            st.session_state.selected_event_index = None
            st.rerun()

        st.title("🏳️‍🌈 Full Event Map 🏳️‍🌈")
        st.markdown("All Events are displayed on the map below.")
        
        if st.session_state.last_clicked:
            #google maps the address of the selected event
            address = st.session_state.last_clicked.split("\n")[0]
            Maps_url = f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(address)}"
            st.link_button(f"Search '{address}' on Google Maps", Maps_url)
        else:
            main_address = "Rådhuspladsen 1, 8000 Aarhus C"
            Maps_url = f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(main_address)}"
            st.link_button(f"Search 'Rådhusparken' on Google Maps", Maps_url)
            
        from map import create_full_map

        # Create and display the full map with all events
        create_full_map(df)
        st.stop()

    # --- Page Rendering ---
    if st.session_state.selected_event_index is None:
        # --- Event Overview Page ---
        st.title("🌈 Aarhus Pride Events 🌈", anchor=False)
        st.sidebar.markdown("---")
        # Optional: Add filters or other controls here later
        if not st.session_state.get('show_full_map', False):
            if st.button("Click Me for Overview Map", type="primary"):
                st.session_state.show_full_map = True
                st.session_state.selected_event_index = None
                st.rerun()
        else:
            st.button("Event Overview", on_click=lambda: st.session_state.update({"show_full_map": False, "selected_event_index": None}))
            
        st.markdown("Or Browse the upcoming events below.")

        st.checkbox("With Details", value=False, key="show_details")
        st.checkbox("Order by Timestamp", value=True, key="order_by_time")

        # Shuffle the rows by time 
        if st.session_state["order_by_time"]:
            df = df.sort_values(by='Start Tidspunkt')

        if df.empty:
            # This case should be less likely now with earlier checks, but good to keep
            st.info("No upcoming events found in the data.")
        else:
            # seperate the events into two dfs one for warmup (before 31st of may) and one for ones after
            warmup_df = df[df['Dato_dt'] < pd.to_datetime("2025-05-31")]
            main_events_df = df[df['Dato_dt'] >= pd.to_datetime("2025-05-31")]

            if warmup_df.empty:
                hey = None # No warmup events to display, but we can still show the main events
            else:
                with st.expander("Warmup", expanded=False):
                    if not st.session_state.show_details:
                        display_event_overview(warmup_df)
                    else:
                        st.caption("These events are part of the warmup to Aarhus Pride.")
                        st.markdown("---")
                        # Display events as cards
                        for index, event in warmup_df.iterrows():
                            # Pass the event data (as a Series) and its index
                            display_event_card(event, index)
                            st.markdown("---")

            with st.expander("Events and Happenings", expanded=True):
                if not st.session_state.show_details:
                    display_event_overview(main_events_df)
                else:
                    # Display events as cards
                    for index, event in main_events_df.iterrows():
                        # Pass the event data (as a Series) and its index
                        display_event_card(event, index)
                        st.markdown("---") # Separator between cards

    else:
        # --- Event Detail Page ---
        # Validate the index before accessing DataFrame row
        if isinstance(st.session_state.selected_event_index, int) and 0 <= st.session_state.selected_event_index < len(df):
            selected_event = df.iloc[st.session_state.selected_event_index]
            display_event_details(selected_event)

        else:
            st.error("Invalid event selected or the data might have changed. Returning to the overview.")
            logging.warning(f"Invalid selected_event_index encountered: {st.session_state.selected_event_index}")
            st.session_state.selected_event_index = None
            # Give user a moment to see the error before rerunning
            st.button("Return to Overview", on_click=lambda: st.rerun(), type="primary")


# --- Run the App ---
if __name__ == "__main__":
    main()