import os
import json
import datetime
import pickle
import random
import time
from collections import defaultdict

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from ytmusicapi import YTMusic
from tqdm import tqdm

# --- Configuration Paths ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN_FILE = os.path.join(BASE_DIR, 'token.pickle')
CLIENT_SECRETS_FILE = os.path.join(BASE_DIR, 'client_secret.json') # Ensure this file exists in the same directory
SCOPES = ['https://www.googleapis.com/auth/youtube'] # Scope for YouTube Data API, used for ytmusicapi authentication
HISTORY_FILE = os.path.join(BASE_DIR, 'anti_playlist_history.json')

# --- Genre Opposition Mapping ---
# This is a large, curated list as provided in your prompt.
GENRE_OPPOSITES = {
    'pop': [
        'classical symphony', 'gregorian chant', 'gamelan', 'throat singing', 'ambient',
        'death metal', 'noise music', 'tuvan overtone', 'balinese kecak', 'tibetan ritual',
        'inuit katajjaq', 'baroque fugue', 'renaissance madrigal', 'medieval chant'
    ],
    'rock': [
        'bossa nova', 'qawwali', 'fado', 'kora music', 'tabla solo', 'enka', 'free jazz',
        'african mbira', 'persian santur', 'andean pan flute', 'drone ambient', 'lowercase music',
        'silence composition'
    ],
    'hip hop': [
        'bluegrass', 'opera aria', 'celtic harp', 'flamenco', 'sitar', 'opera', 'celtic folk',
        'gregorian chant', 'georgian polyphony', 'arabic maqam', 'hindustani dhrupad',
        'unaccompanied kora', 'solo shakuhachi', 'handpan meditation'
    ],
    'electronic': [
        'acoustic folk', 'chamber music', 'handpan', 'didgeridoo', 'erhu', 'sitar raga', 'flamenco',
        'field recordings', 'natural soundscapes', 'forest ambiance', 'bone flute', 'lithophone',
        'prehistoric music'
    ],
    'indie': [
        'traditional japanese', 'african drums', 'mongolian music', 'oud music', 'steel drum',
        'bollywood', 'mariachi', 'afrobeat', 'j-pop', 'cumbia', 'berber ahwash', 'sami joik',
        'australian didgeridoo', 'circuit bending', 'broken music', 'power electronics'
    ],
    'jazz': [
        'techno', 'drum and bass', 'minimal synth', 'noise rock', 'eurodance',
        'algorithmic music', 'trap', 'EDM festival mix', 'computer-generated music'
    ],
    'classical': [
        'punk rock', 'gabber', 'breakcore', 'glitch hop', 'lo-fi phonk',
        'auto-tuned rap', 'chiptune', 'footwork', 'trap metal'
    ],
    'metal': [
        'binaural beats', 'lo-fi chillhop', 'nature sounds', 'harp concerto', 'soft jazz trio',
        'meditative ambient', 'bossa nova', 'seashore field recordings'
    ],
    'reggae': [
        'industrial noise', 'black metal', 'military march', 'hard techno', 'cold wave',
        'atonal serialism', 'cybergrind', 'marching band'
    ],
    'folk': [
        'synthwave', 'future bass', 'dubstep', 'trance', 'eurobeat',
        'hyperpop', 'trap soul', 'auto-tuned mumble rap'
    ],
    'blues': [
        'psytrance', 'ambient glitch', 'vaporwave', 'hardstyle EDM', 'deep house',
        'sound collage', 'electro swing remix'
    ],
    'country': [
        'k-pop', 'electro house', 'glitchcore', 'drill rap', 'nightcore',
        'vaportrap', 'future funk', 'russian rave'
    ],
    'techno': [
        'string quartet', 'acoustic flamenco', 'gospel choir', 'carnatic vocal',
        'baroque ensemble', 'folkloric lullaby', 'woodland flute trio'
    ],
    'lo-fi': [
        'marching band', 'symphonic metal', 'big band swing', 'post-hardcore', 'grindcore',
        'math rock', 'melodic death metal'
    ]
}

# --- Curated Authentic Music Searches ---
# This is the full, extensive list from your prompt.
AUTHENTIC_MUSIC_SEARCHES = [
    # Asian
    ('japanese', ['j-pop', 'japanese music', 'anime songs', 'japanese rock', 'city pop', 'enka', 'shakuhachi', 'koto pop']),
    ('korean', ['k-pop', 'korean ballad', 'korean rock', 'korean ost', 'trot', 'pansori', 'k-hiphop']),
    ('chinese', ['c-pop', 'mandarin songs', 'chinese ballad', 'cantopop', 'chinese rock', 'guqin', 'erhu fusion']),
    ('indian', ['bollywood', 'punjabi music', 'tamil songs', 'hindi songs', 'indian classical', 'dhrupad', 'sitar']),
    ('thai', ['thai pop', 'thai rock', 'luk thung', 'thai ost', 'piphat', 'mor lam']),
    ('vietnamese', ['vpop', 'vietnamese ballad', 'vietnamese rock', 'dan tranh', 'ca trù']),

    # Central & South Asian
    ('pakistani', ['qawwali', 'pakistani pop', 'coke studio', 'sufi rock']),
    ('afghan', ['afghan traditional', 'rubab music', 'afghan pop']),
    ('kazakh', ['dombra music', 'kazakh folk', 'modern kazakh pop']),

    # Middle Eastern & Central Asian
    ('arabic', ['arabic music', 'arabic pop', 'lebanese music', 'egyptian music', 'oud taqsim']),
    ('persian', ['persian music', 'iranian pop', 'persian classical', 'santur']),
    ('turkish', ['turkish pop', 'turkish rock', 'arabesque', 'turkish folk', 'ney']),
    ('hebrew', ['israeli music', 'hebrew songs', 'mizrahi music', 'klezmer']),

    # African
    ('nigerian', ['afrobeats', 'nigerian music', 'nollywood songs', 'highlife', 'juju']),
    ('ghanaian', ['azonto', 'highlife', 'ghana gospel']),
    ('south african', ['south african music', 'amapiano', 'kwaito', 'afrikaans music', 'mbube']),
    ('ethiopian', ['ethiopian music', 'ethiopian jazz', 'traditional ethiopian', 'krar']),
    ('kenyan', ['kenyan music', 'benga', 'kenyan pop', 'nyatiti']),
    ('north african', ['rai', 'chaabi', 'gnawa']),

    # European
    ('french', ['french music', 'chanson', 'french pop', 'french rock', 'musique concrète']),
    ('german', ['german music', 'deutschpop', 'neue deutsche welle', 'schlager', 'krautrock']),
    ('italian', ['italian music', 'italian pop', 'neapolitan songs', 'opera']),
    ('spanish', ['spanish music', 'spanish pop', 'flamenco', 'spanish rock', 'sephardic']),
    ('russian', ['russian music', 'russian pop', 'russian rock', 'chanson', 'balalaika']),
    ('portuguese', ['portuguese music', 'fado', 'portuguese pop', 'cante alentejano']),
    ('nordic', ['swedish music', 'norwegian music', 'danish music', 'finnish music', 'kulning']),
    ('balkan', ['balkan brass', 'gypsy music', 'sevdah', 'turbo folk']),
    ('greek', ['laïko', 'rembetiko', 'greek folk', 'bouzouki']),

    # Latin American
    ('mexican', ['mexican music', 'mariachi', 'ranchera', 'mexican rock', 'son jarocho']),
    ('brazilian', ['brazilian music', 'bossa nova', 'samba', 'mpb', 'forró']),
    ('argentinian', ['tango', 'argentinian music', 'rock nacional', 'chacarera']),
    ('colombian', ['vallenato', 'cumbia', 'colombian music', 'champeta', 'bambuco']),
    ('peruvian', ['huayno', 'criolla', 'afro-peruvian']),
    ('reggaeton', ['reggaeton', 'latin trap', 'dembow', 'perreo', 'plena']),

    # Indigenous & Traditional
    ('tuvan', ['throat singing', 'tuvan folk', 'igil music']),
    ('mongolian', ['long song', 'morin khuur', 'overtone singing']),
    ('native american', ['powwow', 'navajo chant', 'iroquois social dance']),
    ('aboriginal', ['didgeridoo', 'clapsticks', 'dreamtime music']),
    ('inuït', ['katajjaq', 'throat singing inuit', 'drum dance']),
    ('sami', ['joik', 'northern sami music']),

    # Oceanian & Polynesian
    ('australian', ['didgeridoo music', 'aboriginal music']),
    ('polynesian', ['ukulele instrumental', 'steel guitar hawaii', 'hula music']),
    ('new zealand', ['maori music', 'taonga pūoro', 'waiata']) ,

    # Experimental & Obscure
    ('microtonal', ['xenharmonic', 'just intonation', '72-EDO']),
    ('noise', ['harsh noise wall', 'power electronics', 'merzbow']),
    ('avant-garde', ['aleatoric music', 'spectralism', 'fluxus']),
    ('ambient', ['dark ambient', 'space music', 'drone ambient']),
    ('electroacoustic', ['acousmatic', 'sound collage', 'musique concrète']),
    ('georgian', ['georgian polyphony', 'traditional georgian music', 'panduri songs']),
    ('armenian', ['duduk music', 'armenian folk', 'ashugh songs']),
    ('azerbaijani', ['mugham', 'azerbaijani pop', 'tar music']),
    ('uzbek', ['shashmaqam', 'dutar music', 'uzbek traditional']),
    ('kyrgyz', ['komuz music', 'epic poetry songs', 'kyrgyz folk']),
    ('tajik', ['tajik pop', 'rubab music', 'traditional tajik music']),

    # Southeast Asia Expanded
    ('burmese', ['saung music', 'burmese classical', 'pat waing']),
    ('lao', ['mor lam lao', 'laotian traditional music']),
    ('cambodian', ['pinpeat', 'cambodian rock', 'khmer traditional music']),

    # Pacific Islands & Melanesia
    ('fijian', ['meke music', 'fijian choral']),
    ('papua new guinea', ['garamut drum', 'sing-sing music']),
    ('samoan', ['samoan slap dance', 'polynesian harmonies']),

    # Native and Ethnic Minorities
    ('basque', ['trikitixa', 'basque folk music']),
    ('sami', ['joik', 'laplandic chants']),
    ('romani', ['gypsy jazz', 'romani violin']),
    ('tatars', ['tatar folk music', 'kubyz', 'tatar throat singing']),

    # North American Diversity
    ('canadian', ['canadian indie', 'first nations chants', 'québécois folk']),
    ('alaskan', ['inuit drum dance', 'yupik chants']),
    ('haitian', ['haitian compas', 'rara music', 'vodou drumming']),
    ('dominican', ['bachata', 'merengue', 'dominican dembow']),
    ('cuban', ['son cubano', 'rumba', 'cuban trova']),
    ('puerto rican', ['bomba y plena', 'reggaeton', 'jíbaro music']),

    # South America Continued
    ('bolivian', ['charango music', 'andino folk', 'bolivian morenada']),
    ('chilean', ['nueva canción', 'cueca', 'mapuche music']),
    ('paraguayan', ['arpa paraguaya', 'polca paraguaya']),
    ('venezuelan', ['joropo', 'cuatro music', 'gaita zuliana']),
    ('uruguayan', ['candombe', 'murga', 'tango uruguayo']),

    # African Expansion
    ('malian', ['kora music', 'ngoni', 'griot storytelling']),
    ('senegalese', ['sabar drums', 'mbalax']),
    ('ivorian', ['coupé-décalé', 'zoblazo']),
    ('congolese', ['soukous', 'ndombolo', 'rumba congolese']),
    ('zimbabwean', ['mbira dzavadzimu', 'chimurenga music']),
    ('madagascan', ['valiha music', 'salegy']),

    # Middle East & North Africa Add-ons
    ('moroccan', ['gnawa', 'chaabi marocain', 'andalusi music']),
    ('algerian', ['rai', 'kabyle music', 'malouf']),
    ('syrian', ['muwashshah', 'syrian oud music']),
    ('iraqi', ['maqam al-iraqi', 'joza music']),

    # Rare & Archaic
    ('sardinian', ['tenores di bitti', 'cantu a tenore']),
    ('corsican', ['polyphonic corsican chant', 'paghjella']),
    ('tibetan', ['singing bowls', 'tibetan horn', 'chanting monks']),
    ('yakut', ['khomus music', 'yakutian throat singing']),

    # Fusion/Modern Folk Hybrid
    ('global fusion', ['ethno jazz', 'worldbeat', 'balkan fusion']),
    ('electro folk', ['folktronica', 'synth-folk', 'digital cumbia']),
    ('tribal house', ['afro house', 'deep tribal beats', 'ancestral rhythms'])
]

# Keywords to filter OUT (dance videos, covers, etc.)
EXCLUDE_KEYWORDS = [
    'dance', 'dancing', 'choreography', 'tutorial', 'lesson', 'cover version',
    'reaction', 'remix', 'mashup', 'workout', 'fitness', 'wedding', 'party',
    'tiktok', 'instagram', 'reels', 'shorts', 'challenge', 'trending', 'study', 'long', 'hour', 'cleansing', 'relaxation', 'studying',
    'dj', 'mix', 'compilation', 'playlist', 'karaoke', 'instrumental version', 'mindfulness', 'meditation',
    'how to', 'learn', 'step by step', 'easy', 'beginner', 'class', 'ambience', 'relaxing','cafe',
    'performance', 'stage', 'live concert', 'festival', 'competition', 'remix', 'ai cover', 'fan edit', 'karaoke', 'sped up', 'slowed', 'fake', 'deepfake', 'bootleg', 'nightcore', 'parody', 'tiktok'
]

# Keywords to PREFER (actual music)
PREFER_KEYWORDS = [
    'official', 'original', 'authentic', 'traditional', 'classical',
    'instrumental', 'solo', 'ensemble', 'orchestra', 'chamber',
    'album', 'studio', 'recorded', 'composition', 'piece', 'artiste'
    'official', 'original', 'authentic', 'traditional', 'ancestral', 'heritage',
    'classical', 'composition', 'opus', 'raga', 'maqam', 'suite', 'sonata', 'fugue', 'cantata',
    'instrumental', 'solo', 'duet', 'ensemble', 'quartet', 'orchestra', 'symphony',
    'chamber', 'recital', 'live performance', 'concert',
    'album', 'studio', 'recorded', 'mastered', 'released', 'production', 'label', 'EP', 'LP',
    'artiste', 'musician', 'virtuoso', 'composer', 'vocalist', 'performer', 'band',
    'score', 'soundtrack', 'archives', 'session', 'ethnomusicology', 'field recording',
    'museum recording', 'cultural preservation', 'academic', 'intangible heritage'
]

def get_authenticated_service():
    """Authenticates with YouTube Music via OAuth 2.0 flow."""
    print("🔐 Step 1/6: Authenticating with YouTube Music...")
    credentials = None
    
    if os.path.exists(TOKEN_FILE):
        print("   ✓ Found existing token file.")
        with open(TOKEN_FILE, 'rb') as token:
            credentials = pickle.load(token)
    else:
        print("   ⚠ No existing token found.")
    
    if not credentials or not credentials.valid:
    if credentials and credentials.expired and credentials.refresh_token:
        print("   🔄 Refreshing expired credentials...")
        try:
            credentials.refresh(Request())
        except Exception as e:
            print(f"   ❌ Failed to refresh token: {e}. Re-authenticating.")
            credentials = None

    if not credentials:
        print("   🌐 Starting OAuth flow - browser will open for authentication...")
        try:
            flow = Flow.from_client_secrets_file(
                CLIENT_SECRETS_FILE,
                scopes=SCOPES,
                redirect_uri='https://otter-anti.streamlit.app/oauth2callback'
            )
            auth_url, _ = flow.authorization_url(prompt='consent')
            st.write(f"Please go to this URL: [Authorize]({auth_url})")
            code = st.text_input("Enter the authorization code:")
            if code:
                flow.fetch_token(code=code)
                credentials = flow.credentials
                with open('token.pickle', 'wb') as token:
                    pickle.dump(credentials, token)
        except Exception as e:
            print(f"   ❌ Failed to complete OAuth flow: {e}. Check client_secret.json.")
        
        print("   💾 Saving credentials for future use...")
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(credentials, token)
    else:
        print("   ✓ Using valid existing credentials.")
    
    print("   🎵 Initializing YouTube Music API...")
    try:
        # ytmusicapi can be initialized with the token from google_auth_oauthlib
        ytmusic = YTMusic(authorization=credentials.token)
        print("   ✅ Authentication successful!")
        return ytmusic
    except Exception as e:
        print(f"   ❌ Failed to initialize YTMusic API with OAuth token: {e}")
        print("   🔄 Trying cookie-based authentication (requires headers_auth.json from ytmusicapi setup)...")
        try:
            ytmusic = YTMusic() # This will look for headers_auth.json or use a guest session
            print("   ✅ Fallback cookie-based authentication successful!")
            return ytmusic
        except Exception as e_fallback:
            print(f"   ❌ Fallback authentication also failed: {e_fallback}")
            print("   Please ensure you have configured ytmusicapi or your client_secret.json is valid.")
            return None

def load_history():
    """Loads previously saved anti-playlist songs from a JSON file."""
    print("📚 Step 2/6: Loading previous anti-playlist history...")
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                history = set(json.load(f))
            print(f"   ✓ Loaded {len(history)} songs from history file.")
            return history
        except json.JSONDecodeError:
            print("   ⚠ Corrupted history file - starting fresh.")
            return set()
        except Exception as e:
            print(f"   ❌ Error loading history file: {e} - starting fresh.")
            return set()
    else:
        print("   ℹ No history file found - starting fresh.")
        return set()

def save_history(song_ids):
    """Saves a set of song IDs to the history JSON file."""
    try:
        print(f"   💾 Saving {len(song_ids)} songs to history...")
        with open(HISTORY_FILE, "w") as f:
            json.dump(list(song_ids), f, indent=4)
        print("   ✓ History saved successfully.")
    except Exception as e:
        print(f"   ❌ Error saving history: {e}.")

def get_existing_anti_playlist_songs(ytmusic):
    """Scans user's existing playlists for 'anti playlist' and collects song IDs."""
    print("📋 Step 3/6: Scanning existing anti-playlists...")
    existing_anti_songs = set()
    anti_playlist_count = 0
    
    if not ytmusic:
        print("   ❌ YTMusic client not initialized. Skipping playlist scan.")
        return existing_anti_songs

    max_retries = 3
    for attempt in range(max_retries):
        try:
            print("   🔍 Fetching playlist library...")
            playlists = ytmusic.get_library_playlists()
            break
        except Exception as e:
            print(f"   ⚠ Attempt {attempt + 1} failed to fetch playlists: {e}")
            if attempt < max_retries - 1:
                print(f"   🔄 Retrying in {(attempt + 1) * 2} seconds...")
                time.sleep((attempt + 1) * 2)
            else:
                print(f"   ❌ All attempts failed. Could not fetch playlists.")
                return existing_anti_songs
    else: # If loop completes without break
        print("   ❌ Failed to fetch playlists after multiple attempts.")
        return existing_anti_songs
        
    if playlists:
        for pl in tqdm(playlists, desc="   Scanning playlists", leave=False):
            if 'title' in pl and 'anti playlist' in pl['title'].lower():
                anti_playlist_count += 1
                try:
                    playlist_details = ytmusic.get_playlist(pl['playlistId'])
                    if 'tracks' in playlist_details and playlist_details['tracks']:
                        for track in playlist_details['tracks']:
                            video_id = track.get('videoId')
                            if video_id:
                                existing_anti_songs.add(video_id)
                except Exception as e:
                    print(f"   ⚠ Error processing playlist '{pl.get('title', 'Unknown')}' ({pl.get('playlistId', 'Unknown')}): {e}")
                    continue
                    
    print(f"   🎯 Found {anti_playlist_count} anti-playlists with {len(existing_anti_songs)} unique songs.")
    return existing_anti_songs

def analyze_recent_genres(ytmusic):
    """Analyzes recent listening history to identify user's preferred genres."""
    print("🎧 Step 4/6: Analyzing your listening history...")
    
    if not ytmusic:
        print("   ❌ YTMusic client not initialized. Skipping history analysis.")
        return []

    try:
        print("   📥 Fetching listening history...")
        history = ytmusic.get_history()
        recent_tracks = history[:200] if len(history) > 200 else history
        print(f"   ✓ Retrieved {len(recent_tracks)} recent tracks.")
    except Exception as e:
        print(f"   ❌ Error getting history: {e}.")
        return []
    
    if not recent_tracks:
        print("   ⚠ No listening history found.")
        return []
    
    genre_counter = defaultdict(int)
    print("   🔍 Analyzing genres in your music...")
    
    for track in tqdm(recent_tracks, desc="   Processing tracks", leave=False):
        track_title = track.get('title', '').lower()
        # Handle album which can be a dict or a string
        track_album = track.get('album', {})
        if isinstance(track_album, dict) and 'name' in track_album:
            track_album = track_album['name'].lower()
        elif isinstance(track_album, str):
            track_album = track_album.lower()
        else:
            track_album = ''
        
        artists = track.get('artists', [])
        track_artist = artists[0].get('name', '').lower() if artists and isinstance(artists, list) and artists[0] else ''
        
        text_sources = [track_title, track_album, track_artist]
        
        for text in text_sources:
            if text:
                for genre, opposites in GENRE_OPPOSITES.items():
                    if genre in text:
                        genre_counter[genre] += 3 # Stronger weight for direct genre match
                    # Check if the first word of any opposite genre is in the text
                    # This is a very rough heuristic for 'opposite' detection
                    elif any(opposite.split()[0] in text for opposite in opposites):
                        genre_counter[genre] += 1
    
    result = sorted(genre_counter.items(), key=lambda x: -x[1])
    active_genres_count = len([g for g, c in result if c > 0])
    print(f"   ✅ Genre analysis complete - found {active_genres_count} active genres.")
    return result

def is_authentic_music(title, description=""):
    """
    Checks if a video appears to be authentic music rather than
    dance videos, covers, or other non-music content based on keywords.
    """
    title_lower = title.lower()
    desc_lower = description.lower() # description might not always be available from search results
    
    # Calculate exclude score
    exclude_score = sum(1 for keyword in EXCLUDE_KEYWORDS if keyword in title_lower or keyword in desc_lower)
    
    # Calculate prefer score
    prefer_score = sum(1 for keyword in PREFER_KEYWORDS if keyword in title_lower or keyword in desc_lower)
    
    # Additional general music indicators
    music_indicators = ['official', 'original', 'instrumental', 'classical', 'traditional', 'music video', 'audio', 'track', 'song']
    has_music_indicator = any(indicator in title_lower for indicator in music_indicators)
    
    # Strong rejection criteria: if multiple exclude keywords or strong exclude without strong prefer
    if exclude_score >= 2 or (exclude_score >= 1 and prefer_score == 0 and not has_music_indicator):
        return False
    
    # Strong acceptance criteria: if prefer score is good or clear music indicator
    if prefer_score >= 1 or has_music_indicator:
        return True
    
    # Neutral case: if no strong indicators either way, default to true
    return True # Consider it authentic if no strong negative signs

def search_authentic_music(ytmusic, existing_anti_songs, history):
    """
    Searches for authentic traditional music from various cultures,
    filtering out non-music content.
    """
    candidates = []
    
    if not ytmusic:
        print("   ❌ YTMusic client not initialized. Skipping music search.")
        return candidates

    print("🌍 Searching for authentic traditional music...")
    
    # Shuffle the music searches for variety
    music_searches_shuffled = AUTHENTIC_MUSIC_SEARCHES.copy()
    random.shuffle(music_searches_shuffled)
    
    # Limit to a reasonable number of cultures for a single run
    search_limit_cultures = min(15, len(music_searches_shuffled)) 
    
    for culture, search_terms in tqdm(music_searches_shuffled[:search_limit_cultures], desc="Searching cultures"):
        # print(f"   🎵 Searching {culture} music...") # Too verbose for tqdm
        culture_candidates = []
        
        # Limit search terms per culture
        search_term_limit = min(2, len(search_terms))

        for search_term in search_terms[:search_term_limit]:
            search_queries = [
                f"{search_term} traditional",
                f"{search_term} instrumental",
                f"{search_term} authentic",
                search_term # Plain term as well
            ]
            
            for query in search_queries:
                if len(culture_candidates) >= 2: # Max 2 good candidates per culture
                    break
                
                try:
                    # Request slightly more results to filter down
                    results = ytmusic.search(query, filter='songs', limit=20) 
                    
                    for track in results:
                        if len(culture_candidates) >= 2:
                            break
                            
                        video_id = track.get('videoId')
                        title = track.get('title', '')
                        
                        if not video_id or not title:
                            continue
                        
                        # Skip if already in existing anti-playlists or history
                        if video_id in existing_anti_songs or video_id in history:
                            # print(f"      - Skipping duplicate: {title}") # Too verbose
                            continue
                        
                        # Apply authenticity check
                        if is_authentic_music(title):
                            # Check for duration (prefer longer tracks)
                            # ytmusicapi search results can have 'duration' (string) and 'duration_seconds' (int)
                            duration_seconds = track.get('duration_seconds')
                            # Ensure it's a number and longer than 60 seconds (1 minute)
                            if duration_seconds and duration_seconds > 60:
                                culture_candidates.append({
                                    'id': video_id,
                                    'culture': culture,
                                    'search_term': search_term,
                                    'title': title,
                                    'query': query,
                                    'duration_seconds': duration_seconds
                                })
                                # print(f"      ✓ Found: {title} ({culture})") # Too verbose
                                break # Found a good one for this query, move to next query or culture
                            elif not duration_seconds: # If duration info is missing, still consider it
                                culture_candidates.append({
                                    'id': video_id,
                                    'culture': culture,
                                    'search_term': search_term,
                                    'title': title,
                                    'query': query,
                                    'duration_seconds': 0 # Indicate unknown duration
                                })
                                # print(f"      ✓ Found: {title} (No duration info) ({culture})") # Too verbose
                                break
                            # else: Too short, skip implicitly
                except Exception as e:
                    # print(f"   ⚠ Error searching for '{query}': {e}") # Too verbose
                    continue
                    
                time.sleep(0.1) # Small delay to avoid hammering API
        
        candidates.extend(culture_candidates)
        # print(f"      → Added {len(culture_candidates)} authentic tracks from {culture}.") # Too verbose
        time.sleep(0.3) # Delay between cultures
    
    print(f"   ✅ Found {len(candidates)} total authentic music candidates.")
    return candidates

def create_anti_playlist_main_flow(ytmusic):
    """Orchestrates the creation of the anti-playlist."""
    if not ytmusic:
        print("❌ Cannot proceed: YouTube Music client not authenticated or initialized.")
        return

    existing_anti_songs = get_existing_anti_playlist_songs(ytmusic)
    history = load_history()
    
    # Analyze musical preferences  
    genre_ranking = analyze_recent_genres(ytmusic)
    
    if genre_ranking:
        print(f"   📊 Top detected genres:")
        for genre, count in genre_ranking[:3]: # Show top 3
            print(f"      • {genre.capitalize()}: {count} occurrences")
    else:
        print("   ⚠ No genres detected from listening history.")
    
    print("🔍 Step 5/6: Searching for authentic cultural music candidates...")
    
    # Search for authentic music instead of genre-based opposites
    all_candidates = search_authentic_music(ytmusic, existing_anti_songs, history)
    
    if not all_candidates:
        print("   ❌ No suitable authentic music tracks found. Cannot create playlist.")
        return
    
    # Select diverse tracks prioritizing cultural diversity
    print("   🌐 Selecting culturally diverse tracks for final playlist...")
    final_tracks_info = [] # Store full candidate info, not just IDs
    cultures_used = set()
    
    random.shuffle(all_candidates) # Shuffle for variety in selection
    
    # First pass: try to get one track per unique culture, up to 25
    for candidate in all_candidates:
        if len(final_tracks_info) >= 25: # Target playlist size
            break
        if candidate['culture'] not in cultures_used:
            final_tracks_info.append(candidate)
            cultures_used.add(candidate['culture'])
            # print(f"      ✓ Selected: {candidate['title']} ({candidate['culture']})") # Too verbose
    
    # Second pass: fill any remaining slots up to 25 with diverse tracks
    for candidate in all_candidates:
        if len(final_tracks_info) >= 25:
            break
        # Avoid adding tracks already selected (by ID)
        if candidate['id'] not in [t['id'] for t in final_tracks_info]:
            final_tracks_info.append(candidate)
            # print(f"      ✓ Added: {candidate['title']} ({candidate['culture']})") # Too verbose
    
    final_track_ids = [t['id'] for t in final_tracks_info]

    print(f"   📋 Final selection: {len(final_track_ids)} tracks from {len(cultures_used)} distinct cultures.")
    
    if final_track_ids:
        print("🎵 Step 6/6: Creating anti-playlist on YouTube Music...")
        
        now = datetime.datetime.now()
        playlist_title = f"Anti Playlist {now.strftime('%B %Y')}"
        playlist_description = (
            f"An auto-generated collection of authentic and culturally diverse music "
            f"from {', '.join(sorted(cultures_used))} designed to contrast "
            f"your usual listening habits. Created on {now.strftime('%Y-%m-%d')}."
        )
        
        print(f"   📝 Playlist title: '{playlist_title}'")
        
        try:
            print("   🏗️ Creating playlist...")
            # create_playlist returns the playlist ID
            playlist_id = ytmusic.create_playlist(playlist_title, playlist_description, privacy_status='PRIVATE')
            print(f"   ✓ Playlist created successfully with ID: {playlist_id}")
            
            print("   ➕ Adding tracks to playlist...")
            # Add playlist items in batches (ytmusicapi add_playlist_items takes max 100 items per call)
            batch_size = 50 # Using 50 to be safe, max is 100
            for i in tqdm(range(0, len(final_track_ids), batch_size), desc="   Adding tracks"):
                batch = final_track_ids[i:i+batch_size]
                ytmusic.add_playlist_items(playlist_id, batch)
                time.sleep(0.5) # Small delay between batches to avoid rate limits
            
            # Update history with all newly added song IDs
            history.update(final_track_ids)
            save_history(history)
            
            print(f"\n🎉 SUCCESS! Created '{playlist_title}' with:")
            print(f"   • {len(final_track_ids)} authentic music tracks")
            print(f"   • {len(cultures_used)} different cultures")
            print(f"   • Cultures included: {', '.join(sorted(cultures_used))}")
            print(f"   • View your new playlist here: https://music.youtube.com/playlist?list={playlist_id}")
            
        except Exception as e:
            print(f"   ❌ Error creating or adding tracks to playlist: {e}")
            print("   Please check your internet connection and YouTube Music API permissions.")
    else:
        print("   ⚠ Final track selection resulted in no tracks. Cannot create playlist.")

def main():
    print("🚀 Starting Authentic Anti-Playlist Creator for YouTube Music")
    print("=" * 50)
    
    ytmusic_client = get_authenticated_service()
    if ytmusic_client:
        create_anti_playlist_main_flow(ytmusic_client)
        print("\n✅ Authentic anti-playlist creation process completed!")
    else:
        print("\n❌ Failed to get authenticated YouTube Music service. Exiting.")

if __name__ == "__main__":
    main()
