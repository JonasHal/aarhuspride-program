import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import os
from PIL import Image
import io
import re
import logging
from datetime import datetime
import urllib.parse # Needed for Google Maps link
from functions import fetch_coordinates # Import geocoding function from functions.py

# --- Configuration and Setup ---
st.set_page_config(layout="wide", page_title="Event Program")
logging.basicConfig(level=logging.INFO) # Configure logging

DATA_FILE = "data.csv"
IMAGE_DIR = "PR"
DEFAULT_LATITUDE = 56.1566 # Default coords (e.g., Aarhus center) if geocoding fails
DEFAULT_LONGITUDE = 10.2039

@st.cache_data # Cache the loaded data
def load_data(file_path):
    """Loads event data from a CSV file and performs robust cleaning on column names."""
    try:
        df = pd.read_csv(file_path)

        # --- Robust Column Name Cleaning ---
        cleaned_columns = []
        for col in df.columns:
            original_col = col # Keep original for logging if needed
            # 1. Remove bracketed content (handles multi-line content within brackets)
            col = re.sub(r'\s*\[.*?\]\s*', '', col, flags=re.DOTALL)
            # 2. Remove specific known suffixes
            col = col.replace('- Maks en sætning', '')
            # 3. Replace newline characters with spaces
            col = col.replace('\n', ' ')
            # 4. Replace multiple whitespace chars with a single space
            col = re.sub(r'\s+', ' ', col)
            # 5. Strip leading/trailing whitespace
            col = col.strip()
            cleaned_columns.append(col)

        df.columns = cleaned_columns
        # --- End Column Cleaning ---

        # Verify essential columns *after* cleaning
        required_cols = ['Titel på dit arrangement', 'Arrangør', 'Lokation', 'Dato']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            st.error(f"After cleaning column names, the CSV file is missing required columns: {missing_cols}. Please check the source file headers.")
            # Log the columns found after cleaning for easier debugging
            logging.error(f"Columns found after cleaning: {df.columns.tolist()}")
            return pd.DataFrame() # Return empty DataFrame on error

        # Convert 'Dato' to datetime objects, handle potential errors
        try:
            df['Dato_dt'] = pd.to_datetime(df['Dato'], dayfirst=True, errors='coerce')
        except Exception as e:
            st.warning(f"Could not parse all dates in 'Dato' column: {e}. Rows with invalid dates might be excluded or handled improperly.")
            df['Dato_dt'] = pd.NaT # Set to NaT if parsing fails globally

        # Optional: Filter out past events (uncomment if needed)
        # today = pd.to_datetime(datetime.today().date())
        # df = df.dropna(subset=['Dato_dt']) # Drop rows where date conversion failed
        # df = df[df['Dato_dt'] >= today]

        # Sort by date (handle NaT dates - place them last or first as needed)
        df = df.sort_values(by='Dato_dt', ascending=True, na_position='last').reset_index(drop=True)

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

# --- UI Functions ---
def display_event_card(event, index):
    """Displays a summary card for an event in the overview."""
    st.subheader(event.get('Titel på dit arrangement', 'No Title'))

    # Use three columns: Image, Basic Info, Happenings
    col1, _, col2, col3 = st.columns([1, 0.2, 1, 1])

    with col1:
        # Display Image
        image_path = find_image(event.get('Arrangør', ''))
        if image_path:
            try:
                image = Image.open(image_path)
                st.image(image, use_container_width=True)
            except Exception as e:
                st.warning(f"Could not load image: {e}")
                st.caption("Image Error")
        else:
            st.caption(f"No PR image found for '{event.get('Arrangør', '')}'")

    with col2:
        # Display Basic Info and Details Button
        st.write(f"**📅 Date:** {event.get('Dato', 'N/A')}")
        st.write(f"**📍 Location:** {event.get('Lokation', 'N/A')}")
        st.write(f"**🏳️‍🌈 Organiser:** {event.get('Arrangør', 'N/A')}")
        st.write(f"**Entry:** {event.get('Er der fri entré til dit event, eller skal deltagerne betale et beløb i døren?', 'N/A')}")

        # Use the event's index in the dataframe as a unique key for the button
        if st.button("View Details", key=f"details_{index}", type="primary"):
            st.session_state.selected_event_index = index
            st.rerun() # Rerun the script to switch to detail view

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
        st.subheader("Event Information")
        st.write(f"**📅 Date:** {event.get('Dato', 'N/A')}")
        st.write(f"**📍 Location:** {event.get('Lokation', 'N/A')}")
        st.write(f"**💰 Entry:** {event.get('Er der fri entré til dit event, eller skal deltagerne betale et beløb i døren?', 'N/A')}")
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
                 st.write(f"**📜 Code of Conduct:** Provided (non-standard link: {coc_link})")
        # else: # Optional: uncomment to explicitly state no CoC link
        #     st.write("**📜 Code of Conduct:** Not provided.")
        # --- End Code of Conduct ---


        st.subheader("Description")
        description = event.get('Kort beskrivelse af arrangementet', 'No description provided.')
        st.markdown(description if pd.notna(description) else 'No description provided.')


        st.subheader("Happenings / Schedule")
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
        st.subheader("PR Image")
        image_path = find_image(event.get('Arrangør', ''))
        if image_path:
            try:
                image = Image.open(image_path)
                st.image(image, use_container_width=True)
            except Exception as e:
                st.error(f"Could not load image: {e}")
        else:
            st.caption("No PR image found.")

        # --- Map ---
        st.subheader("Location Map")
        address = event.get('Lokation')
        coordinates = None # Initialize coordinates
        if pd.notna(address) and isinstance(address, str):
            coordinates = fetch_coordinates(address) # Fetch coordinates
            if coordinates:
                lat, lon = coordinates
                map_center = [lat, lon]
                # Use address in popup for more context
                popup_text = f"<b>{event.get('Titel på dit arrangement', 'Event')}</b><br>{address}"
                m = folium.Map(location=map_center, zoom_start=15)
                folium.Marker(
                    location=map_center,
                    popup=folium.Popup(popup_text, max_width=200), # Create a proper Popup object
                    tooltip=event.get('Titel på dit arrangement', 'Click for details')
                ).add_to(m)
                # Display map using st_folium
                st_folium(m, height=350, width=700)
            else:
                # Case where geocoding failed for a provided address
                st.warning(f"Could not find coordinates for '{address}'. Map cannot be displayed accurately.")
                # Display a default map centered broadly (e.g., on Aarhus)
                m = folium.Map(location=[DEFAULT_LATITUDE, DEFAULT_LONGITUDE], zoom_start=12, tiles="CartoDB positron")
                folium.Marker(
                     location=[DEFAULT_LATITUDE, DEFAULT_LONGITUDE],
                     popup="Default location shown (Aarhus). Event address could not be geocoded.",
                     tooltip="Approximate Area"
                ).add_to(m)
                st.write("Showing map centered on Aarhus.")
                st_folium(m, height=350, width=350)
        else:
            # Case where no address was provided at all
            st.info("No location address provided for this event. Cannot display map.")

        # --- Google Maps Link Button ---
        if pd.notna(address) and isinstance(address, str):
            # Offer link based on address even if geocoding failed
            Maps_url = f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(address)}"
            st.link_button(f"Search '{address}' on Google Maps", Maps_url)
        # No button if no address and no coordinates


# --- Main App Logic ---
def main():
    """Main function to run the Streamlit application."""

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

    # --- Sidebar ---
    st.sidebar.title("🗓️ Event Program")
    st.sidebar.markdown("---")
    if st.session_state.selected_event_index is None:
        st.sidebar.info("Click **'View Details'** on an event card to see more information, including a map and schedule.")
    else:
        st.sidebar.info("Showing event details. Use the buttons below or the 'Back' button on the main page.")
        # Add an explicit back button in the sidebar as well
        if st.sidebar.button("⬅️ Back to Event Overview"):
             st.session_state.selected_event_index = None
             st.rerun()

    st.sidebar.markdown("---")
    # Optional: Add filters or other controls here later
    if not st.session_state.get('show_full_map', False):
        if st.sidebar.button("Show Full Map"):
            st.session_state.show_full_map = True
            st.session_state.selected_event_index = None
            st.rerun()
    else:
        st.sidebar.button("Event Overview", on_click=lambda: st.session_state.update({"show_full_map": False, "selected_event_index": None}))
            

    # --- Full Map Page ---
    if st.session_state.get('show_full_map', True):
        if st.button("<- Go Back to Event Overview", type="primary"):
            st.session_state.show_full_map = False
            st.session_state.selected_event_index = None
            st.rerun()

        st.title("Full Event Map")
        st.markdown("All events are displayed on the map below.")
        st.markdown("---")
        
        from map import create_full_map

        # Create and display the full map with all events
        create_full_map(df)
        st.stop()

    # --- Page Rendering ---
    if st.session_state.selected_event_index is None:
        # --- Event Overview Page ---
        st.title("Aarhus Pride 2025 - Program Overview")
        st.markdown("Browse the upcoming events below.")
        st.markdown("---")

        if df.empty:
            # This case should be less likely now with earlier checks, but good to keep
            st.info("No upcoming events found in the data.")
        else:
            # Display events as cards
            for index, event in df.iterrows():
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