import streamlit as st
import os
import time
import json
import datetime
from pathlib import Path
import sqlite3
from urllib.parse import urlparse, parse_qs
SPOTIFY_REDIRECT_URI = st.secrets["SPOTIFY_REDIRECT_URI"]
YOUTUBE_CLIENT_ID=st.secrets["YOUTUBE_CLIENT_ID"]
YOUTUBE_CLIENT_SECRET=st.secrets["YOUTUBE_CLIENT_SECRET"]
YOUTUBE_REDIRECT_URI=st.secrets["YOUTUBE_REDIRECT_URI"]
SPOTIFY_CLIENT_ID =st.secrets["SPOTIFY_CLIENT_ID"]
SPOTIFY_CLIENT_SECRET =st.secrets["SPOTIFY_CLIENT_SECRET"]


# Import services - keeping all original function names exactly as they were
from services.spotify_service import (
    get_spotify_auth_url, get_spotify_token, get_spotify_client_from_token,
    analyze_user_genres, find_opposite_tracks, create_anti_playlist
)
from services.youtube_service import (
    get_authenticated_service, analyze_recent_genres, search_authentic_music, 
    create_anti_playlist_main_flow  # Preserved original name
)

# Database helper
from database import init_db, save_history, load_history

# App Config and Helper Functions
APP_TITLE = "OTTER."
TAGLINE = "Your Anti-Playlist Generator"
DEBUG = os.environ.get("DEBUG", "false").lower() == "true"

# Initialize the database
init_db()

# Initialize session state variables if they don't exist
if 'authenticated_spotify' not in st.session_state:
    st.session_state.authenticated_spotify = False
if 'authenticated_youtube' not in st.session_state:
    st.session_state.authenticated_youtube = False
if 'spotify_token' not in st.session_state:
    st.session_state.spotify_token = None
if 'youtube_credentials' not in st.session_state:
    st.session_state.youtube_credentials = None
if 'callback_processed' not in st.session_state:
    st.session_state.callback_processed = False
if 'selected_service' not in st.session_state:
    st.session_state.selected_service = None
if 'working' not in st.session_state:
    st.session_state.working = False
if 'done' not in st.session_state:
    st.session_state.done = False

# Environment variables (loaded by Streamlit automatically from .env file)
SPOTIFY_CLIENT_ID = get_secret("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = get_secret("SPOTIFY_CLIENT_SECRET")
SPOTIFY_SCOPE = "playlist-modify-public user-library-read user-top-read"

YOUTUBE_CLIENT_ID = get_secret("YOUTUBE_CLIENT_ID")
YOUTUBE_CLIENT_SECRET = get_secret("YOUTUBE_CLIENT_SECRET")
YOUTUBE_SCOPES = ['https://www.googleapis.com/auth/youtube.force-ssl', 
                 'https://www.googleapis.com/auth/youtubepartner']

# Set redirect URIs based on environment
BASE_URL = get_secret("BASE_URL", "https://otter-anti.streamlit.app")
SPOTIFY_REDIRECT_URI = f"{BASE_URL}/callback/spotify"
YOUTUBE_REDIRECT_URI = f"{BASE_URL}/callback/youtube"

# Helper functions
def set_service(service_name):
    st.session_state.selected_service = service_name
    if service_name == 'spotify':
        authenticate_spotify()
    elif service_name == 'youtube':
        authenticate_youtube()

def authenticate_spotify():
    """Start Spotify authentication flow"""
    auth_url = get_spotify_auth_url(SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REDIRECT_URI, SPOTIFY_SCOPE)
    st.session_state.working = True
    st.markdown(f"""
    ### Connecting to Spotify...
    
    Click the link below to authorize OTTER with your Spotify account:
    
    [Authorize with Spotify]({auth_url})
    
    After authorization, you'll be redirected back to this app.
    """)

def authenticate_youtube():
    """Start YouTube authentication flow"""
    try:
        auth_info = get_authenticated_service()
        st.session_state.youtube_flow_state = auth_info['state']
        st.session_state.working = True
        st.markdown(f"""
        ### Connecting to YouTube Music...
        
        Click the link below to authorize OTTER with your Google account:
        
        [Authorize with YouTube]({auth_info['url']})
        
        After authorization, you'll be redirected back to this app.
        """)
    except Exception as e:
        st.error(f"Error initiating YouTube authentication: {e}")

def process_spotify_callback():
    """Process the Spotify OAuth callback"""
    try:
        query_params = st.query_params
        code = query_params.get("code", [""])[0]
        
        if code:
            token_info = get_spotify_token(SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REDIRECT_URI, SPOTIFY_SCOPE, code)
            st.session_state.spotify_token = token_info
            st.session_state.authenticated_spotify = True
            st.session_state.callback_processed = True
            st.session_state.working = False
            st.success("Successfully authenticated with Spotify!")
            
            time.sleep(1)
            st.query_params
            st.experimental_rerun()
    except Exception as e:
        st.error(f"Error processing Spotify callback: {str(e)}")
        st.session_state.working = False

def process_youtube_callback():
    """Process the YouTube OAuth callback"""
    try:
        query_params = st.query_params
        code = query_params.get("code", [""])[0]
        state = query_params.get("state", [""])[0]
        
        if code and state:
            if state != st.session_state.get('youtube_flow_state'):
                st.error("State mismatch. Authentication flow may have been tampered with.")
                return
                
            # Note: This assumes create_anti_playlist_main_flow handles the callback
            # as the original youtube_service import didn't include get_youtube_credentials_from_callback
            credentials = create_anti_playlist_main_flow.process_callback(
                code,
                YOUTUBE_CLIENT_ID,
                YOUTUBE_CLIENT_SECRET,
                YOUTUBE_REDIRECT_URI
            )
            
            st.session_state.youtube_credentials = credentials
            st.session_state.authenticated_youtube = True
            st.session_state.callback_processed = True
            st.session_state.working = False
            st.success("Successfully authenticated with YouTube!")
            
            time.sleep(1)
            st.query_params
            st.experimental_rerun()
    except Exception as e:
        st.error(f"Error processing YouTube callback: {str(e)}")
        st.session_state.working = False

def create_spotify_anti_playlist():
    """Create an anti-playlist on Spotify"""
    if not st.session_state.authenticated_spotify or not st.session_state.spotify_token:
        st.error("Please authenticate with Spotify first.")
        return
    
    try:
        st.session_state.working = True
        
        with st.spinner("Creating your Spotify anti-playlist..."):
            spotify_client = get_spotify_client_from_token(
                st.session_state.spotify_token,
                SPOTIFY_CLIENT_ID,
                SPOTIFY_CLIENT_SECRET,
                SPOTIFY_REDIRECT_URI,
                SPOTIFY_SCOPE
            )
            
            spotify_user = spotify_client.me()
            spotify_user_id = spotify_user['id']
            history = load_history(spotify_user_id, 'spotify')
            
            progress_container = st.empty()
            progress_container.info("Analyzing your music preferences...")
            
            top_genres = analyze_user_genres(spotify_client)
            if top_genres:
                progress_container.info(f"Found your top genres: {', '.join([g for g, _ in top_genres[:3]])}")
            
            progress_container.info("Searching for music opposite to your taste...")
            track_ids = find_opposite_tracks(spotify_client, top_genres, history)
            
            if not track_ids:
                progress_container.error("Could not find enough contrasting tracks.")
                st.session_state.working = False
                st.session_state.done = True
                return
            
            progress_container.info(f"Found {len(track_ids)} unique contrasting tracks. Creating playlist...")
            result_message = create_anti_playlist(spotify_client)
            
            save_history(spotify_user_id, 'spotify', track_ids)
            progress_container.success(result_message)
            st.balloons()
        
        st.session_state.working = False
        st.session_state.done = True
    except Exception as e:
        st.error(f"Error creating Spotify anti-playlist: {str(e)}")
        st.session_state.working = False

def create_youtube_anti_playlist():
    """Create an anti-playlist on YouTube Music"""
    if not st.session_state.authenticated_youtube or not st.session_state.youtube_credentials:
        st.error("Please authenticate with YouTube first.")
        return
    
    try:
        st.session_state.working = True
        
        with st.spinner("Creating your YouTube Music anti-playlist..."):
            # Using the original create_anti_playlist_main_flow function
            result = create_anti_playlist_main_flow(
                st.session_state.youtube_credentials,
                YOUTUBE_CLIENT_ID,
                YOUTUBE_CLIENT_SECRET
            )
            
            if result:
                st.success("Successfully created YouTube Music anti-playlist!")
                st.balloons()
            else:
                st.error("Failed to create YouTube Music anti-playlist")
        
        st.session_state.working = False
        st.session_state.done = True
    except Exception as e:
        st.error(f"Error creating YouTube anti-playlist: {str(e)}")
        st.session_state.working = False

# Main app UI
def main():
    st.markdown("""
    <style>
    .otter-title {
        font-size: 4.5em;
        font-weight: bold;
        color: #1DB954;
        margin-bottom: 0;
        letter-spacing: 2px;
        text-align: center;
    }
    .otter-tagline {
        font-size: 1.5em;
        color: #bbb;
        margin-bottom: 30px;
        text-align: center;
    }
    .stButton > button {
        background-color: #333;
        color: white;
        border: 2px solid #555;
        padding: 15px 25px;
        border-radius: 8px;
        font-size: 1.1em;
        width: 100%;
        transition: all 0.3s;
    }
    .stButton > button:hover {
        background-color: #444;
        border-color: #1DB954;
        transform: translateY(-2px);
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown(f'<h1 class="otter-title">{APP_TITLE}</h1>', unsafe_allow_html=True)
    st.markdown(f'<p class="otter-tagline">{TAGLINE}</p>', unsafe_allow_html=True)
    
    query_params = st.query_params  # This is correct
    callback_path = st.query_params.get("path", [""])[0]
    
    if "code" in query_params and "callback/spotify" in callback_path and not st.session_state.callback_processed:
        process_spotify_callback()
    elif "code" in query_params and "callback/youtube" in callback_path and not st.session_state.callback_processed:
        process_youtube_callback()
    
    if not st.session_state.working and not st.session_state.done:
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Anti-Playlist for Spotify"):
                set_service('spotify')
        
        with col2:
            if st.button("Anti-Playlist for YouTube"):
                set_service('youtube')
                
        with st.expander("What is an Anti-Playlist?"):
            st.markdown("""
            An **Anti-Playlist** contains music that is the opposite of what you normally listen to. It's designed to:
            
            * Introduce you to completely different genres
            * Expose you to music from diverse cultures and languages
            * Break you out of your musical comfort zone
            * Create a refreshing contrast to your usual listening habits
            
            Each anti-playlist contains around 25 songs that are carefully selected to be different from your usual taste while still being listenable.
            """)
    
    elif st.session_state.authenticated_spotify and not st.session_state.working and not st.session_state.done:
        st.success("You're connected to Spotify!")
        if st.button("Create My Spotify Anti-Playlist"):
            create_spotify_anti_playlist()
    
    elif st.session_state.authenticated_youtube and not st.session_state.working and not st.session_state.done:
        st.success("You're connected to YouTube Music!")
        if st.button("Create My YouTube Anti-Playlist"):
            create_youtube_anti_playlist()
    
    if st.session_state.done:
        if st.button("Create Another Anti-Playlist"):
            st.session_state.done = False
            st.session_state.working = False
            st.session_state.selected_service = None
            st.experimental_rerun()

if __name__ == "__main__":
    main()
