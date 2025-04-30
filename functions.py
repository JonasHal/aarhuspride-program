
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

import logging
import streamlit as st

# --- Geocoding Setup (with Caching) ---
# Cache the geocoder instance and the geocode function results
@st.cache_resource
def get_geocoder():
    """Initializes and returns a Nominatim geocoder with rate limiting."""
    geolocator = Nominatim(user_agent="streamlit_event_app_v2") # Updated user agent slightly
    # Add rate limiting to avoid overwhelming the geocoding service
    return RateLimiter(geolocator.geocode, min_delay_seconds=1)

@st.cache_data(ttl=60*60*24) # Cache results for 24 hours
def fetch_coordinates(address):
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