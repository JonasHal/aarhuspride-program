
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import pandas as pd
import re
from datetime import datetime
import os
import sys

import logging

# --- Geocoding Setup (with Caching) ---
def get_geocoder():
    """Initializes and returns a Nominatim geocoder with rate limiting."""
    geolocator = Nominatim(user_agent="streamlit_event_app_v2") # Updated user agent slightly
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