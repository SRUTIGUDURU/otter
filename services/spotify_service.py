import os
import json
import datetime
from collections import defaultdict
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from tqdm import tqdm
import time
import random

# --- Spotify Configuration ---
# IMPORTANT: Replace with your actual Spotify Client ID and Secret
# For security, consider using environment variables instead of hardcoding:
SPOTIFY_CLIENT_ID = os.environ.get('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.environ.get('SPOTIFY_CLIENT_SECRET')
SPOTIFY_REDIRECT_URI = 'https://otter-anti.streamlit.app' # Must match your Spotify Developer Dashboard redirect URI
SPOTIFY_SCOPE = 'playlist-modify-public user-library-read user-top-read'

# --- Genre Opposition Mapping ---
# As provided in your prompt.
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

# --- World Music Categories / Authentic Genres for Spotify ---
# This list is flattened from the AUTHENTIC_MUSIC_SEARCHES in your prompt.
WORLD_MUSIC_CATEGORIES = [
    'j-pop', 'japanese music', 'anime songs', 'japanese rock', 'city pop', 'enka', 'shakuhachi', 'koto pop',
    'k-pop', 'korean ballad', 'korean rock', 'korean ost', 'trot', 'pansori', 'k-hiphop',
    'c-pop', 'mandarin songs', 'chinese ballad', 'cantopop', 'chinese rock', 'guqin', 'erhu fusion',
    'bollywood', 'punjabi music', 'tamil songs', 'hindi songs', 'indian classical', 'dhrupad', 'sitar',
    'thai pop', 'thai rock', 'luk thung', 'thai ost', 'piphat', 'mor lam',
    'vpop', 'vietnamese ballad', 'vietnamese rock', 'dan tranh', 'ca trù',
    'qawwali', 'pakistani pop', 'coke studio', 'sufi rock',
    'afghan traditional', 'rubab music', 'afghan pop',
    'dombra music', 'kazakh folk', 'modern kazakh pop',
    'arabic music', 'arabic pop', 'lebanese music', 'egyptian music', 'oud taqsim',
    'persian music', 'iranian pop', 'persian classical', 'santur',
    'turkish pop', 'turkish rock', 'arabesque', 'turkish folk', 'ney',
    'israeli music', 'hebrew songs', 'mizrahi music', 'klezmer',
    'afrobeats', 'nigerian music', 'nollywood songs', 'highlife', 'juju',
    'azonto', 'highlife', 'ghana gospel',
    'south african music', 'amapiano', 'kwaito', 'afrikaans music', 'mbube',
    'ethiopian music', 'ethiopian jazz', 'traditional ethiopian', 'krar',
    'kenyan music', 'benga', 'kenyan pop', 'nyatiti',
    'rai', 'chaabi', 'gnawa',
    'french music', 'chanson', 'french pop', 'french rock', 'musique concrète',
    'german music', 'deutschpop', 'neue deutsche welle', 'schlager', 'krautrock',
    'italian music', 'italian pop', 'neapolitan songs', 'opera',
    'spanish music', 'spanish pop', 'flamenco', 'spanish rock', 'sephardic',
    'russian music', 'russian pop', 'russian rock', 'chanson', 'balalaika',
    'portuguese music', 'fado', 'portuguese pop', 'cante alentejano',
    'swedish music', 'norwegian music', 'danish music', 'finnish music', 'kulning',
    'balkan brass', 'gypsy music', 'sevdah', 'turbo folk',
    'laïko', 'rembetiko', 'greek folk', 'bouzouki',
    'mexican music', 'mariachi', 'ranchera', 'mexican rock', 'son jarocho',
    'brazilian music', 'bossa nova', 'samba', 'mpb', 'forró',
    'tango', 'argentinian music', 'rock nacional', 'chacarera',
    'vallenato', 'cumbia', 'colombian music', 'champeta', 'bambuco',
    'huayno', 'criolla', 'afro-peruvian',
    'reggaeton', 'latin trap', 'dembow', 'perreo', 'plena',
    'throat singing', 'tuvan folk', 'igil music',
    'long song', 'morin khuur', 'overtone singing',
    'powwow', 'navajo chant', 'iroquois social dance',
    'didgeridoo', 'clapsticks', 'dreamtime music',
    'katajjaq', 'throat singing inuit', 'drum dance',
    'joik', 'northern sami music',
    'didgeridoo music', 'aboriginal music',
    'ukulele instrumental', 'steel guitar hawaii', 'hula music',
    'maori music', 'taonga pūoro', 'waiata',
    'xenharmonic', 'just intonation', '72-EDO',
    'harsh noise wall', 'power electronics', 'merzbow',
    'aleatoric music', 'spectralism', 'fluxus',
    'dark ambient', 'space music', 'drone ambient',
    'acousmatic', 'sound collage', 'musique concrète',
    'georgian polyphony', 'traditional georgian music', 'panduri songs',
    'duduk music', 'armenian folk', 'ashugh songs',
    'mugham', 'azerbaijani pop', 'tar music',
    'shashmaqam', 'dutar music', 'uzbek traditional',
    'komuz music', 'epic poetry songs', 'kyrgyz folk',
    'tajik pop', 'rubab music', 'traditional tajik music',
    'saung music', 'burmese classical', 'pat waing',
    'mor lam lao', 'laotian traditional music',
    'pinpeat', 'cambodian rock', 'khmer traditional music',
    'meke music', 'fijian choral',
    'garamut drum', 'sing-sing music',
    'samoan slap dance', 'polynesian harmonies',
    'trikitixa', 'basque folk music',
    'joik', 'laplandic chants',
    'gypsy jazz', 'romani violin',
    'tatar folk music', 'kubyz', 'tatar throat singing',
    'canadian indie', 'first nations chants', 'québécois folk',
    'inuit drum dance', 'yupik chants',
    'haitian compas', 'rara music', 'vodou drumming',
    'bachata', 'merengue', 'dominican dembow',
    'son cubano', 'rumba', 'cuban trova',
    'bomba y plena', 'reggaeton', 'jíbaro music',
    'charango music', 'andino folk', 'bolivian morenada',
    'nueva canción', 'cueca', 'mapuche music',
    'arpa paraguaya', 'polca paraguaya',
    'joropo', 'cuatro music', 'gaita zuliana',
    'candombe', 'murga', 'tango uruguayo',
    'kora music', 'ngoni', 'griot storytelling',
    'sabar drums', 'mbalax',
    'coupé-décalé', 'zoblazo',
    'soukous', 'ndombolo', 'rumba congolese',
    'mbira dzavadzimu', 'chimurenga music',
    'valiha music', 'salegy',
    'gnawa', 'chaabi marocain', 'andalusi music',
    'rai', 'kabyle music', 'malouf',
    'muwashshah', 'syrian oud music',
    'maqam al-iraqi', 'joza music',
    'tenores di bitti', 'cantu a tenore',
    'polyphonic corsican chant', 'paghjella',
    'singing bowls', 'tibetan horn', 'chanting monks',
    'khomus music', 'yakutian throat singing',
    'ethno jazz', 'worldbeat', 'balkan fusion',
    'folktronica', 'synth-folk', 'digital cumbia',
    'afro house', 'deep tribal beats', 'ancestral rhythms'
]

def get_spotify_client():
    """Authenticates with Spotify using OAuth 2.0."""
    print("🔐 Authenticating with Spotify...")
    try:
        sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=SPOTIFY_CLIENT_ID,
            client_secret=SPOTIFY_CLIENT_SECRET,
            redirect_uri=SPOTIFY_REDIRECT_URI,
            scope=SPOTIFY_SCOPE
        ))
        print("✅ Spotify authentication successful!")
        return sp
    except Exception as e:
        print(f"❌ Spotify authentication failed: {e}")
        print("Please check your Client ID, Client Secret, and Redirect URI in the Spotify Developer Dashboard.")
        return None

def analyze_user_genres(sp):
    """Analyzes user's top genres from their listening history on Spotify."""
    print("🎧 Analyzing your music preferences...")
    
    if not sp:
        print("   ❌ Spotify client not initialized. Skipping genre analysis.")
        return []

    top_artists = []
    # Fetch top artists for different time ranges
    for term in ['short_term', 'medium_term', 'long_term']:
        try:
            print(f"   🔍 Fetching top artists for {term}...")
            results = sp.current_user_top_artists(time_range=term, limit=50) # Increased limit for better genre coverage
            top_artists.extend(results['items'])
        except spotipy.SpotifyException as e:
            print(f"   ⚠ Couldn't get {term} top artists: {e}")
        except Exception as e:
            print(f"   ❌ An unexpected error occurred fetching {term} top artists: {e}")
    
    if not top_artists:
        print("   ⚠ No top artist data found for genre analysis.")
        return []

    # Count genre occurrences from all fetched artists
    genre_counter = defaultdict(int)
    for artist in top_artists:
        for genre in artist.get('genres', []):
            genre_counter[genre] += 1
    
    # Map raw Spotify genres to our predefined genres for opposition mapping
    mapped_genres = defaultdict(int)
    for genre_raw, count in genre_counter.items():
        found_match = False
        for our_genre in GENRE_OPPOSITES:
            if our_genre in genre_raw.lower(): # Check if our broad genre is in Spotify's specific genre tag
                mapped_genres[our_genre] += count
                found_match = True
                break
        # If no direct match to our broad categories, add as-is to see other popular genres
        if not found_match:
            mapped_genres[genre_raw] += count

    sorted_genres = sorted(mapped_genres.items(), key=lambda x: -x[1])
    
    if sorted_genres:
        print("📊 Your top analyzed music genres:")
        for genre, count in sorted_genres[:5]: # Display top 5
            print(f"  • {genre.capitalize()}: {count} occurrences")
    else:
        print("   ⚠ No identifiable top genres found.")
    
    return sorted_genres

def find_opposite_tracks(sp, top_genres, existing_tracks=None):
    """
    Finds tracks that are opposite to user's preferred genres,
    prioritizing world music categories and general anti-genres.
    """
    if existing_tracks is None:
        existing_tracks = set()
    
    print("🔍 Searching for contrasting music tracks...")
    candidates = []
    
    if not sp:
        print("   ❌ Spotify client not initialized. Skipping track search.")
        return candidates

    # Get specific opposite genres from user's top genres (top 3 for strong signal)
    opposite_genre_keywords = set()
    for genre, _ in top_genres[:3]:
        # Add directly mapped opposites
        for opposite in GENRE_OPPOSITES.get(genre, []):
            opposite_genre_keywords.add(opposite)
        # Add a few random world music categories to broaden the search
        # These are used as keywords for search, not necessarily Spotify's exact genres
    
    # Add a selection of diverse world music categories to ensure broader contrast
    num_world_genres_to_add = min(10, len(WORLD_MUSIC_CATEGORIES))
    opposite_genre_keywords.update(random.sample(WORLD_MUSIC_CATEGORIES, num_world_genres_to_add))
    
    if not opposite_genre_keywords:
        print("   ⚠ No specific contrasting genres or world music categories to search for.")
        return candidates

    print(f"  🎵 Exploring approximately {len(opposite_genre_keywords)} contrasting genres/keywords.")
    
    # Iterate through selected genres/keywords to find tracks
    # Use tqdm to show progress for this potentially long loop
    for genre_keyword in tqdm(list(opposite_genre_keywords), desc="   Searching genres/keywords"):
        try:
            # Note: Spotify's 'genre' search is often limited to its own defined genre seeds.
            # Using broader keyword searches might yield more results for niche/world music.
            results = sp.search(q=genre_keyword, type='track', limit=20) # Get 20 tracks per keyword
            for track in results['tracks']['items']:
                if track['id'] not in existing_tracks:
                    candidates.append({
                        'id': track['id'],
                        'name': track['name'],
                        'artist': track['artists'][0]['name'] if track['artists'] else 'Unknown Artist',
                        'genre_keyword': genre_keyword # Store the keyword used to find it
                    })
                if len(candidates) >= 50: # Limit total candidates to a reasonable number
                    break
        except spotipy.SpotifyException as e:
            # print(f"   ⚠ Couldn't search for '{genre_keyword}': {e}") # Too verbose in loop
            pass # Suppress common "Invalid genre" errors for niche searches
        except Exception as e:
            print(f"   ❌ Error searching for '{genre_keyword}': {e}")
        if len(candidates) >= 50:
            break
        time.sleep(0.1) # Small delay to respect API rate limits

    random.shuffle(candidates) # Shuffle final candidates for variety
    return candidates[:25] # Return top 25 candidates for the playlist

def create_anti_playlist_main_flow(sp):
    """Main function to create the anti-playlist on Spotify."""
    print("🚀 Starting Anti-Playlist Creation for Spotify")
    
    if not sp:
        print("❌ Cannot proceed: Spotify client not authenticated.")
        return

    # Step 1: Analyze user's music taste
    top_genres = analyze_user_genres(sp)
    
    # Step 2: Find contrasting tracks
    # For a real implementation, you might want to fetch existing anti-playlist songs from Spotify
    # if you track them there (similar to YTMusic service). For now, we skip that.
    candidates = find_opposite_tracks(sp, top_genres, existing_tracks=set())
    
    if not candidates:
        print("❌ Couldn't find any suitable contrasting tracks. Playlist not created.")
        return
    
    print(f"✅ Found {len(candidates)} contrasting tracks for your playlist.")
    
    # Step 3: Create playlist
    now = datetime.datetime.now()
    playlist_name = f"Anti-Playlist {now.strftime('%B %Y')}"
    playlist_desc = (
        f"A unique collection of music designed to contrast your usual listening tastes. "
        f"Generated on {now.strftime('%Y-%m-%d')}."
    )
    
    try:
        print("   🏗️ Creating new Spotify playlist...")
        user_info = sp.me()
        if not user_info or 'id' not in user_info:
            print("   ❌ Could not retrieve user ID from Spotify.")
            return
        user_id = user_info['id']

        playlist = sp.user_playlist_create(
            user=user_id,
            name=playlist_name,
            public=True, # Can be set to False for private playlist
            description=playlist_desc
        )
        print(f"   ✓ Playlist created successfully: '{playlist['name']}' (ID: {playlist['id']})")
        
        # Add tracks to playlist in batches (Spotify max 100 tracks per call)
        track_ids = [track['id'] for track in candidates]
        batch_size = 100 # Spotify's limit
        for i in tqdm(range(0, len(track_ids), batch_size), desc="   Adding tracks"):
            batch = track_ids[i:i+batch_size]
            sp.playlist_add_items(playlist['id'], batch)
            time.sleep(0.5) # Small delay for rate limits
        
        print(f"\n🎉 SUCCESS! Created playlist: '{playlist_name}'")
        print(f"  • Contains {len(track_ids)} contrasting tracks.")
        
        # Collect and display genres/keywords included for user info
        genres_included = set(track['genre_keyword'] for track in candidates)
        if genres_included:
            print(f"  • Genres/Keywords explored: {', '.join(sorted(genres_included))}")
        
        print(f"  • View your new playlist here: {playlist['external_urls']['spotify']}")
        
    except spotipy.SpotifyException as e:
        print(f"❌ Spotify API error creating playlist: {e}")
        print("Please check your Spotify API permissions and try again.")
    except Exception as e:
        print(f"❌ An unexpected error occurred during playlist creation: {e}")

def main():
    print("🚀 Starting Anti-Playlist Creator for Spotify")
    print("=" * 50)
    
    spotify_client = get_spotify_client()
    if spotify_client:
        create_anti_playlist_main_flow(spotify_client)
        print("\n✅ Anti-playlist creation process completed!")
    else:
        print("\n❌ Failed to get authenticated Spotify client. Exiting.")

if __name__ == "__main__":
    main()
