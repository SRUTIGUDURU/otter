import streamlit as st
import os
import time
import json
import datetime
from pathlib import Path
import sqlite3
from urllib.parse import urlparse, parse_qs

# Import services
from services.spotify_service import (
    get_spotify_auth_url, get_spotify_token, get_spotify_client_from_token,
    analyze_user_genres, find_opposite_tracks, create_anti_playlist
)
from services.youtube_service import (
    get_authenticated_service,
    analyze_recent_genres, search_authentic_music, create_anti_playlist_main_flow
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
SPOTIFY_CLIENT_ID = os.environ.get("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET")
SPOTIFY_SCOPE = "playlist-modify-public user-library-read user-top-read"

YOUTUBE_CLIENT_ID = os.environ.get("YOUTUBE_CLIENT_ID")
YOUTUBE_CLIENT_SECRET = os.environ.get("YOUTUBE_CLIENT_SECRET")
YOUTUBE_SCOPES = ['https://www.googleapis.com/auth/youtube.force-ssl', 'https://www.googleapis.com/auth/youtubepartner']

# Set redirect URIs based on environment
# For local development
BASE_URL = os.environ.get("BASE_URL", "https://otter-anti.streamlit.app")
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
        auth_info = get_youtube_auth_url(YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, YOUTUBE_REDIRECT_URI, YOUTUBE_SCOPES)
        st.session_state.youtube_flow_state = auth_info['state']  # Store state for CSRF
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
        # Get query parameters from URL
        query_params = st.experimental_get_query_params()
        code = query_params.get("code", [""])[0]
        
        if code:
            # Exchange code for token
            token_info = get_spotify_token(SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REDIRECT_URI, SPOTIFY_SCOPE, code)
            st.session_state.spotify_token = token_info
            st.session_state.authenticated_spotify = True
            st.session_state.callback_processed = True
            st.session_state.working = False
            st.success("Successfully authenticated with Spotify!")
            
            # Clear URL parameters after processing
            time.sleep(1)  # Brief pause to let the success message display
            st.experimental_set_query_params()
            st.experimental_rerun()
    except Exception as e:
        st.error(f"Error processing Spotify callback: {str(e)}")
        st.session_state.working = False

def process_youtube_callback():
    """Process the YouTube OAuth callback"""
    try:
        # Get query parameters from URL
        query_params = st.experimental_get_query_params()
        code = query_params.get("code", [""])[0]
        state = query_params.get("state", [""])[0]
        
        if code and state:
            # Verify state matches to prevent CSRF
            if state != st.session_state.get('youtube_flow_state'):
                st.error("State mismatch. Authentication flow may have been tampered with.")
                return
                
            # Construct full callback URL
            callback_url = f"{BASE_URL}/callback/youtube?{urlparse(st.experimental_get_query_params()).query}"
            
            # Exchange code for credentials
            credentials = get_youtube_credentials_from_callback(
                YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, YOUTUBE_REDIRECT_URI, YOUTUBE_SCOPES, callback_url
            )
            
            # Store credentials in session state
            st.session_state.youtube_credentials = {
                'token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': credentials.scopes,
                'expiry': credentials.expiry.timestamp() if credentials.expiry else None
            }
            
            st.session_state.authenticated_youtube = True
            st.session_state.callback_processed = True
            st.session_state.working = False
            st.success("Successfully authenticated with YouTube!")
            
            # Clear URL parameters after processing
            time.sleep(1)  # Brief pause to let the success message display
            st.experimental_set_query_params()
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
            # Get spotify client
            spotify_client = get_spotify_client_from_token(
                st.session_state.spotify_token,
                SPOTIFY_CLIENT_ID,
                SPOTIFY_CLIENT_SECRET,
                SPOTIFY_REDIRECT_URI,
                SPOTIFY_SCOPE
            )
            
            # Get user ID for history storage
            spotify_user = spotify_client.me()
            spotify_user_id = spotify_user['id']
            
            # Load history
            history = load_history(spotify_user_id, 'spotify')
            
            # Create progress container
            progress_container = st.empty()
            progress_container.info("Analyzing your music preferences...")
            
            # Progress 1: Analyze music taste
            top_genres = analyze_user_genres(spotify_client)
            if top_genres:
                progress_container.info(f"Found your top genres: {', '.join([g for g, _ in top_genres[:3]])}")
            else:
                progress_container.warning("Could not determine your music preferences. Creating a diverse playlist instead.")
            
            # Progress 2: Find opposite tracks
            progress_container.info("Searching for music opposite to your taste...")
            track_ids = find_opposite_tracks(spotify_client, top_genres, history)
            
            if not track_ids:
                progress_container.error("Could not find enough contrasting tracks. Please try again later.")
                st.session_state.working = False
                st.session_state.done = True
                return
            
            # Progress 3: Create playlist
            progress_container.info(f"Found {len(track_ids)} unique contrasting tracks. Creating playlist...")
            result_message = create_anti_playlist(spotify_client)
            
            # Save to history
            save_history(spotify_user_id, 'spotify', track_ids)
            
            # Final message
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
            # Get YouTube Music client
            ytmusic = get_youtube_client_from_creds_data(st.session_state.youtube_credentials)
            
            # Get user info (this is simplified; in production get a stable user ID)
            youtube_user_info = ytmusic.get_user_info()
            youtube_user_id = youtube_user_info.get('header', {}).get('title', 'unknown_user')
            
            # Load history
            history = load_history(youtube_user_id, 'youtube')
            
            # Create progress container
            progress_container = st.empty()
            progress_container.info("Analyzing your YouTube Music listening history...")
            
            # Progress 1: Analyze music taste (optional for YouTube)
            genre_ranking = analyze_recent_genres(ytmusic)
            if genre_ranking:
                progress_container.info(f"Found your top YouTube genres: {', '.join([g for g, _ in genre_ranking[:3]])}")
            
            # Progress 2: Search for authentic music
            progress_container.info("Searching for authentic world music...")
            all_candidates = search_authentic_music(ytmusic, history)
            
            if not all_candidates:
                progress_container.error("Could not find enough authentic music. Please try again later.")
                st.session_state.working = False
                st.session_state.done = True
                return
            
            # Progress 3: Create playlist
            progress_container.info(f"Found {len(all_candidates)} authentic tracks. Creating playlist...")
            result_message, track_ids = youtube_create_playlist(ytmusic, all_candidates)
            
            # Save to history
            save_history(youtube_user_id, 'youtube', [track['id'] for track in all_candidates[:25]])
            
            # Final message
            progress_container.success(result_message)
            st.balloons()
        
        st.session_state.working = False
        st.session_state.done = True
    except Exception as e:
        st.error(f"Error creating YouTube anti-playlist: {str(e)}")
        st.session_state.working = False

# Main app UI
def main():
    # Custom CSS
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

    # App header
    st.markdown(f'<h1 class="otter-title">{APP_TITLE}</h1>', unsafe_allow_html=True)
    st.markdown(f'<p class="otter-tagline">{TAGLINE}</p>', unsafe_allow_html=True)
    
    # Process callbacks if present in URL
    query_params = st.experimental_get_query_params()
    callback_path = st.experimental_get_query_params().get("path", [""])[0]
    
    if "code" in query_params and "callback/spotify" in callback_path and not st.session_state.callback_processed:
        process_spotify_callback()
    elif "code" in query_params and "callback/youtube" in callback_path and not st.session_state.callback_processed:
        process_youtube_callback()
    
    # Show main content if not in authentication flow
    if not st.session_state.working and not st.session_state.done:
        # Main selection buttons
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Anti-Playlist for Spotify"):
                set_service('spotify')
        
        with col2:
            if st.button("Anti-Playlist for YouTube"):
                set_service('youtube')
                
        # Information about anti-playlists
        with st.expander("What is an Anti-Playlist?"):
            st.markdown("""
            An **Anti-Playlist** contains music that is the opposite of what you normally listen to. It's designed to:
            
            * Introduce you to completely different genres
            * Expose you to music from diverse cultures and languages
            * Break you out of your musical comfort zone
            * Create a refreshing contrast to your usual listening habits
            
            Each anti-playlist contains around 25 songs that are carefully selected to be different from your usual taste while still being listenable.
            """)
    
    # If authenticated with Spotify, show create playlist button
    elif st.session_state.authenticated_spotify and not st.session_state.working and not st.session_state.done:
        st.success("You're connected to Spotify!")
        if st.button("Create My Spotify Anti-Playlist"):
            create_spotify_anti_playlist()
    
    # If authenticated with YouTube, show create playlist button
    elif st.session_state.authenticated_youtube and not st.session_state.working and not st.session_state.done:
        st.success("You're connected to YouTube Music!")
        if st.button("Create My YouTube Anti-Playlist"):
            create_youtube_anti_playlist()
    
    # After playlist is created, show restart button
    if st.session_state.done:
        if st.button("Create Another Anti-Playlist"):
            st.session_state.done = False
            st.session_state.working = False
            st.session_state.selected_service = None
            st.experimental_rerun()

if __name__ == "__main__":
    main()
