
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import pandas as pd
import re
from datetime import datetime
import os
import sys
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch
import numpy as np

import logging

# --- Geocoding Setup (with Caching) ---
def get_geocoder():
    """Initializes and returns a Nominatim geocoder with rate limiting."""
    geolocator = Nominatim(user_agent="streamlit_event_app_v3") # Updated user agent slightly
    # Add rate limiting to avoid overwhelming the geocoding service
    return RateLimiter(geolocator.geocode, min_delay_seconds=1)

def fetch_coordinates(address):
    address = address.replace(" 1.mf.", "").replace(" st", "")

    """Fetches latitude and longitude for a given address string."""
    if not isinstance(address, str) or not address.strip():
        logging.warning("Geocoding attempt with invalid address (None or empty).")
        return None
    logging.info(f"Geocoding address: {address}")
    geocode = get_geocoder()
    try:
        location = geocode(address, timeout=10) # Increased timeout
        if location:
            logging.info(f"Found coordinates: ({location.latitude}, {location.longitude})")
            return location.latitude, location.longitude
        else:
            logging.warning(f"Address not found or geocoding failed for: {address}")
            return None
    except GeocoderTimedOut:
        logging.error(f"Geocoder timed out for address: {address}")
        st.error(f"Geocoding timed out for address: {address}. Please try again later.")
        return None
    except GeocoderServiceError as e:
        logging.error(f"Geocoder service error for address {address}: {e}")
        st.error(f"Geocoding service error: {e}")
        return None
    except Exception as e:
        logging.error(f"An unexpected error occurred during geocoding for {address}: {e}")
        st.error(f"An unexpected error occurred during geocoding.")
        return None
    
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
            col = col.replace(', skriv linket her:', '')
            
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
        required_cols = ['Titel på dit arrangement', 'Arrangør', 'Lokation', 'Start Tidspunkt', 'Slut Tidspunkt']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            logging.error(f"Columns found after cleaning: {df.columns.tolist()}")
            return pd.DataFrame() # Return empty DataFrame on error

        # Convert 'Slut Tidspunkt' to datetime objects, handle potential errors
        try:
            df['Dato_dt'] = pd.to_datetime(df['Slut Tidspunkt'], format='%d/%m/%Y %H.%M.%S', errors='coerce')
        except Exception as e:
            df['Dato_dt'] = pd.NaT # Set to NaT if parsing fails globally

        return df

    except FileNotFoundError:
        return pd.DataFrame()
    except pd.errors.EmptyDataError:
        return pd.DataFrame()
    except Exception as e:
        logging.exception("Error during data loading:") # Log the full traceback
    
    return pd.DataFrame()
    
def create_event_posters(df, output_dir="event_posters"):
    """Creates poster-style graphics for all events and saves them as images."""
    os.makedirs(output_dir, exist_ok=True)
    
    # Define color palette for variety
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E2']
    
    for index, event in df.iterrows():
        try:
            title = event.get('Titel på dit arrangement', 'No Title')
            organizer = event.get('Arrangør', 'No Organizer')
            location = event.get('Lokation', 'No Location')
            start_time = event.get('Start Tidspunkt', 'No Start Time')
            end_time = event.get('Slut Tidspunkt', 'No End Time')
            
            # Create figure with poster dimensions (vertical)
            fig, ax = plt.subplots(figsize=(8, 11))
            ax.set_xlim(0, 10)
            ax.set_ylim(0, 14)
            ax.axis('off')
            
            # Select color
            color = colors[index % len(colors)]
            bg_color = color
            
            # Background
            rect = FancyBboxPatch((0.2, 0.2), 9.6, 13.6, boxstyle="round,pad=0.1", 
                                  edgecolor='black', facecolor=bg_color, linewidth=2, alpha=0.3)
            ax.add_patch(rect)
            
            # Header bar with date/time
            header_rect = FancyBboxPatch((0.3, 11.5), 9.4, 2, boxstyle="round,pad=0.05",
                                        edgecolor='black', facecolor=color, linewidth=2)
            ax.add_patch(header_rect)
            
            # Parse and format times
            try:
                start_dt = pd.to_datetime(start_time, format='%d/%m/%Y %H.%M.%S')
                end_dt = pd.to_datetime(end_time, format='%d/%m/%Y %H.%M.%S')
                date_str = start_dt.strftime('%d. %B %Y')
                time_str = f"{start_dt.strftime('%H:%M')} - {end_dt.strftime('%H:%M')}"
            except:
                date_str = start_time.split()[0] if isinstance(start_time, str) else 'Date TBD'
                time_str = 'Time TBD'
            
            # Date and time in header
            ax.text(5, 12.8, date_str, fontsize=16, weight='bold', 
                   ha='center', va='center', color='white')
            ax.text(5, 12.1, time_str, fontsize=14, weight='bold', 
                   ha='center', va='center', color='white')
            
            # Title (main text)
            title_text = ax.text(5, 10.3, title, fontsize=20, weight='bold',
                               ha='center', va='top', wrap=True, 
                               color='#1a1a1a', multialignment='center')
            
            # Wrap title if too long
            if len(title) > 40:
                title_text.set_fontsize(16)
            
            # Location section
            ax.text(0.8, 9.2, '📍 Location:', fontsize=12, weight='bold', color='#1a1a1a')
            
            # Format location - handle multiple addresses
            location_str = location.replace('\n', ', ') if isinstance(location, str) else location
            # Wrap location text
            ax.text(1.0, 8.6, location_str, fontsize=10, ha='left', va='top', 
                   wrap=True, color='#333333', style='italic', multialignment='left')
            
            # Organizer section
            ax.text(0.8, 5.5, '🎯 Organizer:', fontsize=12, weight='bold', color='#1a1a1a')
            ax.text(1.0, 4.9, str(organizer), fontsize=10, ha='left', va='top', 
                   wrap=True, color='#333333', multialignment='left')
            
            # Decorative footer line
            footer_rect = FancyBboxPatch((0.3, 0.3), 9.4, 0.8, boxstyle="round,pad=0.05",
                                        edgecolor='black', facecolor=color, linewidth=2, alpha=0.5)
            ax.add_patch(footer_rect)
            
            ax.text(5, 0.7, 'Aarhus Pride Program', fontsize=10, weight='bold',
                   ha='center', va='center', color='white')
            
            # Save the poster
            filename = f"poster_{index:03d}_{title[:20].replace('/', '_').replace(' ', '_')}.png"
            filepath = os.path.join(output_dir, filename)
            plt.savefig(filepath, dpi=150, bbox_inches='tight', facecolor='white')
            plt.close()
            
            logging.info(f"Created poster: {filename}")
            
        except Exception as e:
            logging.error(f"Error creating poster for event {index}: {e}")
            plt.close()
    
    print(f"\n✅ Created {len(df)} event posters in '{output_dir}' directory!")
    return output_dir

def create_event_grid_overview(df, output_file="events_overview.png"):
    """Creates a grid overview of all events in one image."""
    n_events = len(df)
    cols = 3
    rows = (n_events + cols - 1) // cols
    
    fig, axes = plt.subplots(rows, cols, figsize=(16, 5*rows))
    axes = axes.flatten()  # Flatten to 1D array for easier iteration
    
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E2']
    
    for index, event in df.iterrows():
        ax = axes[index]
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 10)
        ax.axis('off')
        
        color = colors[index % len(colors)]
        
        # Background
        rect = FancyBboxPatch((0.1, 0.1), 9.8, 9.8, boxstyle="round,pad=0.1",
                             edgecolor='black', facecolor=color, linewidth=2, alpha=0.2)
        ax.add_patch(rect)
        
        title = event.get('Titel på dit arrangement', 'No Title')
        location = event.get('Lokation', 'No Location')
        start_time = event.get('Start Tidspunkt', 'No Time')
        
        # Parse time
        try:
            start_dt = pd.to_datetime(start_time, format='%d/%m/%Y %H.%M.%S')
            time_str = start_dt.strftime('%d/%m %H:%M')
        except:
            time_str = str(start_time)[:20]
        
        # Title
        ax.text(5, 8.5, title, fontsize=12, weight='bold', ha='center', va='top',
               wrap=True, color='#1a1a1a', multialignment='center')
        
        # Date/Time
        ax.text(5, 6.5, f"🕐 {time_str}", fontsize=10, ha='center', va='top',
               color='#333333', weight='bold')
        
        # Location
        location_str = location.replace('\n', ', ')[:50] if isinstance(location, str) else str(location)[:50]
        ax.text(5, 5.2, f"📍 {location_str}", fontsize=9, ha='center', va='top',
               color='#555555', style='italic', wrap=True, multialignment='center')
    
    # Hide unused subplots
    for idx in range(n_events, len(axes)):
        axes[idx].axis('off')
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    
    print(f"✅ Created overview grid: {output_file}")
    return output_file

def create_upcoming_events_poster(df, output_file="upcoming_events_poster.png"):
    """Creates a poster with two columns: Warmup (May 22-29) and Pride Day (May 30)."""
    from datetime import datetime
    
    # Filter events after current date (May 22, 2026)
    current_date = datetime(2026, 5, 22)
    
    # Parse start times and filter
    upcoming_events = []
    for index, event in df.iterrows():
        try:
            start_time = event.get('Start Tidspunkt', '')
            start_dt = pd.to_datetime(start_time, format='%d/%m/%Y %H.%M.%S')
            if start_dt >= current_date:
                upcoming_events.append((index, event, start_dt))
        except:
            continue
    
    if not upcoming_events:
        print("❌ No upcoming events found after current date.")
        return None
    
    # Sort by start time
    upcoming_events.sort(key=lambda x: x[2])
    
    # Split into Warmup (May 22-29) and Pride Day (May 30)
    warmup_events = [e for e in upcoming_events if e[2].day < 30]
    pride_day_events = [e for e in upcoming_events if e[2].day == 30]
    
    max_events = max(len(warmup_events), len(pride_day_events))
    
    # Create figure with two columns - compact
    fig_height = 0.9 + max(len(warmup_events), len(pride_day_events)) * 0.5
    fig, ax = plt.subplots(figsize=(10, fig_height))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, fig_height)
    ax.axis('off')
    
    # Column headers
    ax.text(2.5, fig_height - 0.1, 'Warmup (22-29)', 
           fontsize=13, weight='bold', ha='center', va='top', color='#FF6B6B')
    ax.text(7.5, fig_height - 0.1, 'Pride Day (30)', 
           fontsize=13, weight='bold', ha='center', va='top', color='#4ECDC4')
    
    # Rainbow colors for titles
    rainbow_colors = ['#FF0000', '#FF7F00', "#A5E001", "#E2D300FF", "#4242F1", '#9400D3']
    
    # Warmup column
    y_pos_warmup = fig_height - 0.4
    for idx, (_, event, start_dt) in enumerate(warmup_events):
        title = event.get('Titel på dit arrangement', 'No Title')
        location = event.get('Lokation', 'No Location')
        start_time = start_dt.strftime('%d. %b %H:%M')
        location_str = location.replace('\n', ' | ')[:35] if isinstance(location, str) else str(location)[:35]
        
        # Event text with rainbow color
        event_text = f"{start_time}  {title}"
        color = rainbow_colors[idx % len(rainbow_colors)]
        ax.text(0.2, y_pos_warmup, event_text, fontsize=11, weight='bold', ha='left', va='top', color=color)
        
        # Location text below
        ax.text(0.4, y_pos_warmup - 0.2, f"- {location_str}", fontsize=9, ha='left', va='top', 
               color='#555555', style='italic')
        
        y_pos_warmup -= 0.5
    
    # Pride Day column
    y_pos_pride = fig_height - 0.4
    for idx, (_, event, start_dt) in enumerate(pride_day_events):
        title = event.get('Titel på dit arrangement', 'No Title')
        location = event.get('Lokation', 'No Location')
        start_time = start_dt.strftime('%d. %b %H:%M')
        location_str = location.replace('\n', ' | ')[:35] if isinstance(location, str) else str(location)[:35]
        
        # Event text with rainbow color
        event_text = f"{start_time}  {title}"
        color = rainbow_colors[idx % len(rainbow_colors)]
        ax.text(5.2, y_pos_pride, event_text, fontsize=10, weight='bold', ha='left', va='top', color=color)
        
        # Location text below
        ax.text(5.4, y_pos_pride - 0.2, f"- {location_str}", fontsize=8, ha='left', va='top', 
               color='#555555', style='italic')
        
        y_pos_pride -= 0.5
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches='tight', facecolor='none', transparent=True)
    plt.close()
    
    total_events = len(warmup_events) + len(pride_day_events)
    print(f"✅ Created upcoming events poster: {output_file} ({len(warmup_events)} warmup + {len(pride_day_events)} pride day = {total_events} total events)")
    return output_file
    
if __name__ == "__main__":
    
    df = load_data("events.csv") # Load the CSV file

    # drop emails
    df = df.drop(columns=['Mailadresse', "Kolonne 16"], errors='ignore')

    # Add these lines before your for loop
    df['Latitude'] = None
    df['Longitude'] = None
    df['Latitude_List'] = None  # Initialize as None, not as empty lists
    df['Longitude_List'] = None

    for index, event in df.iterrows():
        address = event.get('Lokation').split("\n")
        if len(address) == 1:
            coordinates = fetch_coordinates(address[0])
            if coordinates:
                lat, lon = coordinates
                df.at[index, 'Latitude'] = lat
                df.at[index, 'Longitude'] = lon
                # Store empty lists using list() to create new objects
                df.at[index, 'Latitude_List'] = None  # or just skip setting this
                df.at[index, 'Longitude_List'] = None  # or just skip setting this
            else:
                print(f"Could not find coordinates for '{address[0]}'.")
        else:
            latitudes = []
            longitudes = []
            for addr in address:
                coordinates = fetch_coordinates(addr)
                if coordinates:
                    lat, lon = coordinates
                    latitudes.append(lat)
                    longitudes.append(lon)
                else:
                    print(f"Could not find coordinates for '{addr}'.")
            
            if latitudes and longitudes:
                # Store lists as proper objects
                df.at[index, 'Latitude_List'] = latitudes.copy()  # Use copy() to ensure we have a new object
                df.at[index, 'Longitude_List'] = longitudes.copy()
            else:
                print(f"Could not find coordinates for any of the addresses: {address}")
    
    # Save the updated DataFrame with coordinates to a new CSV file
    df.to_csv("events_with_coordinates.csv", index=False)

    # Generate event overview poster
    print("\n" + "="*50)
    print("GENERATING EVENT OVERVIEW POSTER...")
    print("="*50)
    create_upcoming_events_poster(df, output_file="upcoming_events_poster.png")
    print("="*50)