# =============================================================================
# LEGATUM MUSIC SYSTEM - CORE ENGINE (VERSION 12.2 LOGIC FIX)
# =============================================================================
# Autor: Legatum Dev Team (Lead: Adrian Barron Trujillo)
# Licencia: Proprietary Enterprise License
# Estado: Mission Critical / Production Ready
#
# CHANGELOG V12.2 (SMART SEARCH SPLIT):
# + [CRITICAL] Se mejoro la logica find_artist para manejar entradas compuestas.
# + [LOGIC] Agregada deteccion de patron "Cancion - Artista".
# + [LOGIC] Si se detecta un guion, el sistema separa la busqueda y prioriza
#           encontrar al artista del lado derecho de la cadena.
# =============================================================================

import os
import sys
import time
import json
import logging
import random
import html
import re
import socket
import base64
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
from logging.handlers import RotatingFileHandler
import requests
import wikipedia

# Framework Web
from flask import Flask, render_template, request, url_for, jsonify

# =============================================================================
# [SECCION 1] CONFIGURACION MAESTRA (SYSTEM CONFIGURATION)
# =============================================================================

class Config:
    """
    Centro de Comando de Configuracion.
    Define el comportamiento fisico, logico y las credenciales del sistema.
    """
    
    APP_NAME = "Legatum Music Search"
    VERSION = "12.2-Platinum"
    
    # --- CREDENCIALES DE APIS ---
    # Se utilizan variables de entorno por seguridad, con fallback a las claves proporcionadas.
    SPOTIFY_CLIENT_ID = os.environ.get('SPOTIFY_CLIENT_ID', 'c0df85c5327842fe8966ffdd1ba5a260')
    SPOTIFY_CLIENT_SECRET = os.environ.get('SPOTIFY_CLIENT_SECRET', '8182c8b561604f7990c0952d3d0cf88d')
    
    # --- URLs OFICIALES DE SPOTIFY ---
    URL_AUTH_SPOTIFY = 'https://accounts.spotify.com/api/token'
    URL_BASE_SPOTIFY = 'https://api.spotify.com/v1/search'
    URL_ARTIST_BASE = 'https://api.spotify.com/v1/artists/'
    
    # 2. LAST.FM
    LASTFM_API_KEY = os.environ.get('LASTFM_API_KEY', '5dd2074bba107468fa58c78c4fdc0413')
    LASTFM_BASE_URL = 'http://ws.audioscrobbler.com/2.0/'
    
    # 3. YOUTUBE
    YOUTUBE_KEY = os.environ.get('YOUTUBE_KEY', 'AIzaSyBUEWLmnvc4uufcxEszVP6TsEklgwdOqi4')
    YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3/search"
    
    # --- RECURSOS VISUALES ---
    PLACEHOLDER_IMG = "https://cdn-icons-png.flaticon.com/512/148/148841.png"
    
    # --- PARAMETROS DE RED ---
    CACHE_TTL = 3600         
    DISK_CACHE_DIR = "legatum_secure_vault" 
    LOG_DIR = "legatum_audit_logs" 
    MAX_RETRIES = 2          
    TIMEOUT_REQUEST = 5     
    TIMEOUT_QUICK = 3        
    
    # --- POOL DE ARTISTAS ---
    POOL_ARTISTAS = [
        "Kendrick Lamar", "The Weeknd", "Arctic Monkeys", "Dua Lipa", "Bad Bunny",
        "Coldplay", "Eminem", "Feid", "Guns N' Roses", "Harry Styles", 
        "Imagine Dragons", "J Balvin", "Karol G", "Luis Miguel", "Shakira", 
        "Taylor Swift", "Bruno Mars", "Ariana Grande", "Billie Eilish", "Drake", 
        "Ed Sheeran", "Post Malone", "Rihanna", "Justin Bieber", "Katy Perry", 
        "Queen", "Metallica", "AC/DC", "Daddy Yankee", "Rosalia", 
        "Maluma", "BTS", "Blackpink", "Anuel AA", "Ozuna", 
        "Juanes", "Cafe Tacvba", "Soda Stereo", "Panteon Rococo", "Mana", 
        "Reik", "Zoe", "Caifanes", "Molotov", "Enjambre", 
        "Siddhartha", "Camilo", "Rauw Alejandro", "Wisin y Yandel", "Don Omar", 
        "Tego Calderon", "50 Cent", "Snoop Dogg", "Dr. Dre", "Jay-Z", 
        "Kanye West", "Travis Scott", "Linkin Park", "Red Hot Chili Peppers", 
        "Nirvana", "Foo Fighters", "Green Day", "Blink-182", "The Beatles", 
        "Pink Floyd", "Led Zeppelin", "Rolling Stones", "U2", "Bon Jovi", 
        "Aerosmith", "Scorpions", "Iron Maiden", "Judas Priest", "Black Sabbath", 
        "Ozzy Osbourne", "Miley Cyrus", "SZA", "Olivia Rodrigo", "Doja Cat", 
        "Lana Del Rey", "The Strokes", "Tame Impala", "Gorillaz", "Daft Punk", 
        "David Bowie", "Prince", "Michael Jackson", "Madonna", "Britney Spears",
        "System of a Down", "Radiohead", "Muse", "Florence + The Machine",
        "Depeche Mode", "The Cure", "New Order", "Joy Division", "Pearl Jam",
        "Soundgarden", "Alice in Chains", "Stone Temple Pilots", "Rammstein",
        "Justice", "The Chemical Brothers", "The Prodigy", "Massive Attack",
        "Portishead", "Bjork", "Aphex Twin", "Boards of Canada", "Kraftwerk"
    ]

    # --- LISTA DE GENEROS ---
    LISTA_GENEROS = [
        "Rock", "Pop", "Hip Hop", "Reggaeton", "Jazz", 
        "Electronic", "Metal", "Latin", "K-Pop", "Indie", 
        "RnB", "Country", "Classical", "Trap", "Disco", "Blues"
    ]

    # --- MAPEO DE GENEROS ---
    GENRE_MAP = {
        "Hip Hop": "hip-hop", "Reggaeton": "reggaeton", "K-Pop": "kpop",
        "RnB": "rnb", "Latin": "latin", "Electronic": "electronic",
        "Indie": "indie", "Metal": "metal", "Rock": "rock",
        "Pop": "pop", "Jazz": "jazz", "Country": "country",
        "Classical": "classical", "Trap": "trap", "Disco": "disco"
    }

wikipedia.set_lang("es")

# =============================================================================
# [SECCION 2] INICIALIZACION DE SISTEMA
# =============================================================================

class SystemBootloader:
    @staticmethod
    def initialize():
        for d in [Config.DISK_CACHE_DIR, Config.LOG_DIR]:
            os.makedirs(d, exist_ok=True)
        print(f"[BOOT] Sistema iniciado v{Config.VERSION}")

SystemBootloader.initialize()

# =============================================================================
# [SECCION 3] LOGGING
# =============================================================================

def setup_logger():
    logger = logging.getLogger("LegatumCore")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(asctime)s | %(levelname)s | %(message)s'))
        logger.addHandler(handler)
    return logger

logger = setup_logger()

# =============================================================================
# [SECCION 4] SEGURIDAD
# =============================================================================

class RequestThrottler:
    def __init__(self): self.clients = {}
    def allow_request(self, ip): return True

throttler = RequestThrottler()

# =============================================================================
# [SECCION 5] UTILIDADES
# =============================================================================

class DataSanitizer:
    @staticmethod
    def normalize_search_query(query: str) -> str:
        return re.sub(r'[^a-z0-9]', '_', query.strip().lower()) if query else "unknown"

# =============================================================================
# [SECCION 6] MODELOS DE DATOS
# =============================================================================

@dataclass
class TrackInfo:
    name: str
    external_urls: Dict[str, str] = field(default_factory=dict)
    video_id: Optional[str] = None

@dataclass
class AlbumInfo:
    name: str
    images: List[Dict[str, str]]
    release_date: str = ""

@dataclass
class ArtistProfile:
    name: str
    genres: List[str]
    images: List[Dict[str, str]]
    popularity: Any 
    followers: Dict[str, str]

@dataclass
class StandardResponse:
    info: ArtistProfile
    tracks: List[TrackInfo]
    albums: List[AlbumInfo]
    fuente: str
    modo_respaldo: bool

# =============================================================================
# [SECCION 7] MOCK ENGINE
# =============================================================================

class MockEngine:
    @staticmethod
    def generate_discovery_grid():
        return [{"nombre": "Artist Offline", "img": Config.PLACEHOLDER_IMG, "popularidad": 25} for _ in range(8)]

    @staticmethod
    def generate_artist_profile(name):
        return StandardResponse(
            info=ArtistProfile(name=name, genres=["Offline"], images=[{'url': Config.PLACEHOLDER_IMG}], popularity=25, followers={'total': '0'}),
            tracks=[], albums=[], fuente="Offline", modo_respaldo=True
        )

# =============================================================================
# [SECCION 8] CACHE & HTTP
# =============================================================================

class CacheManager:
    def __init__(self): self.store = {}
    def retrieve(self, key): 
        if key in self.store and time.time() < self.store[key][1]: return self.store[key][0]
        return None
    def store_data(self, key, data): self.store[key] = (data, time.time() + Config.CACHE_TTL)

sys_cache = CacheManager()

class HttpDriver:
    def __init__(self): self.session = requests.Session()
    def fetch(self, url, method='GET', params=None, data=None, headers=None, auth=None):
        for attempt in range(Config.MAX_RETRIES + 1):
            try:
                timeout = Config.TIMEOUT_REQUEST if method == 'GET' and 'search' in url else Config.TIMEOUT_QUICK
                if method == 'POST': resp = self.session.post(url, data=data, headers=headers, auth=auth, timeout=timeout)
                else: resp = self.session.get(url, params=params, headers=headers, timeout=timeout)
                
                resp.raise_for_status()
                return resp.json()
            except requests.exceptions.HTTPError as e:
                if resp.status_code == 401:
                    logger.error(f"Error 401 de autenticacion en {url}. No se reintenta.")
                    return None
                time.sleep(1)
            except Exception as e:
                time.sleep(1)
        return None

http_client = HttpDriver()

# =============================================================================
# [SECCION 9] DRIVERS DE API
# =============================================================================

class BaseDriver:
    @staticmethod
    def select_optimal_image(images: List[Dict]) -> str:
        if not images: return Config.PLACEHOLDER_IMG
        try:
            first_img = images[0]
            url = first_img.get('url') or first_img.get('#text')
            if url: return url
        except: pass
        return Config.PLACEHOLDER_IMG

class SpotifyClient(BaseDriver):
    def __init__(self):
        self.access_token = None
        self.token_expiry = 0

    def authorize(self):
        """Autenticacion REAL con Spotify."""
        if self.access_token and time.time() < self.token_expiry: return self.access_token
        
        auth_str = f"{Config.SPOTIFY_CLIENT_ID}:{Config.SPOTIFY_CLIENT_SECRET}"
        b64_auth = base64.b64encode(auth_str.encode()).decode()
        
        headers = {'Authorization': f'Basic {b64_auth}'}
        data = {'grant_type': 'client_credentials'}
        
        res = http_client.fetch(Config.URL_AUTH_SPOTIFY, method='POST', data=data, headers=headers)
        
        if res and 'access_token' in res:
            self.access_token = res['access_token']
            self.token_expiry = time.time() + res.get('expires_in', 3600) - 60
            logger.info(" Conexion Spotify Exitosa")
            return self.access_token
        
        logger.error(" Error de autenticacion Spotify - Revisa CLIENT ID / SECRET")
        return None

    def fetch_artist_quick(self, query: str):
        token = self.authorize()
        if not token: return None
        
        headers = {'Authorization': f'Bearer {token}'}
        data = http_client.fetch(Config.URL_BASE_SPOTIFY, params={'q': query, 'type': 'artist', 'limit': 1}, headers=headers)
        
        if data and data.get('artists', {}).get('items'):
            return data['artists']['items'][0]
        return None

    def find_artist(self, query: str):
        """
        Logica de Busqueda Inteligente v12.2:
        1. Detecta si es una busqueda compuesta ("Cancion - Artista") proveniente del autosuggest.
        2. Si es compuesta, intenta extraer el Artista directamente.
        3. Si falla o es busqueda simple, intenta buscar Artista exacto.
        4. Si falla, intenta buscar Track y extraer artista.
        """
        token = self.authorize()
        if not token: return None
        headers = {'Authorization': f'Bearer {token}'}
        
        artist_id = None
        artist_data = None

        # --- LOGICA MEJORADA: Deteccion de "Cancion - Artista" ---
        is_composite = " - " in query
        
        if is_composite:
            # Estrategia 1: Separar y buscar el artista (Parte derecha del guion)
            try:
                parts = query.split(" - ")
                potential_artist = parts[-1] # Tomamos lo que esta despues del ultimo guion
                logger.info(f" Input compuesto detectado. Intentando resolver artista directo: '{potential_artist}'")
                
                search_direct = http_client.fetch(Config.URL_BASE_SPOTIFY, params={'q': potential_artist, 'type': 'artist', 'limit': 1}, headers=headers)
                if search_direct and search_direct.get('artists', {}).get('items'):
                    artist_data = search_direct['artists']['items'][0]
                    artist_id = artist_data['id']
            except:
                pass

        # Estrategia 2: Busqueda estandar de Artista (Solo si no es compuesto o fallo lo anterior)
        # Si el usuario escribio "Telephones - Vacations", buscar eso como artista suele fallar,
        # asi que si detectamos compuesto y fallo la busqueda directa, es mejor saltar a Track.
        if not artist_id and not is_composite:
            logger.info(f" Buscando '{query}' como Artista...")
            search_artist = http_client.fetch(Config.URL_BASE_SPOTIFY, params={'q': query, 'type': 'artist', 'limit': 1}, headers=headers)
            
            if search_artist and search_artist.get('artists', {}).get('items'):
                artist_data = search_artist['artists']['items'][0]
                artist_id = artist_data['id']

        # Estrategia 3: Busqueda por TRACK (Red de seguridad y resolucion de canciones)
        if not artist_id:
            logger.info(f" Buscando '{query}' como Track para extraer artista...")
            search_track = http_client.fetch(Config.URL_BASE_SPOTIFY, params={'q': query, 'type': 'track', 'limit': 1}, headers=headers)
            
            if search_track and search_track.get('tracks', {}).get('items'):
                track_item = search_track['tracks']['items'][0]
                if track_item.get('artists'):
                    artist_id = track_item['artists'][0]['id']
                    logger.info(f" Track encontrado: {track_item['name']}. Redirigiendo a: {track_item['artists'][0]['name']}")
                    
                    # Fetch manual del perfil del artista
                    artist_resp = http_client.fetch(f"{Config.URL_ARTIST_BASE}{artist_id}", headers=headers)
                    if artist_resp:
                        artist_data = artist_resp

        if not artist_id or not artist_data:
            return None
        
        # Carga de datos finales
        aid = artist_id
        tracks_data = http_client.fetch(f"{Config.URL_ARTIST_BASE}{aid}/top-tracks", params={'market': 'MX'}, headers=headers)
        albums_data = http_client.fetch(f"{Config.URL_ARTIST_BASE}{aid}/albums", params={'limit': 10, 'include_groups': 'album'}, headers=headers)
        
        tracks = [TrackInfo(name=t['name'], external_urls=t.get('external_urls', {})) for t in tracks_data.get('tracks', [])[:5]] if tracks_data else []
        albums = [AlbumInfo(name=a['name'], images=a.get('images', []), release_date=a.get('release_date', '')) for a in albums_data.get('items', [])] if albums_data else []
        img = self.select_optimal_image(artist_data.get('images', []))
        
        return StandardResponse(
            info=ArtistProfile(name=artist_data['name'], genres=artist_data.get('genres', [])[:3], images=[{'url': img}], popularity=artist_data.get('popularity', 0), followers={'total': artist_data.get('followers', {}).get('total', 0)}),
            tracks=tracks, albums=albums, fuente="Spotify", modo_respaldo=False
        )
        
    def get_search_suggestions(self, query: str):
        token = self.authorize()
        if not token: return []
        
        headers = {'Authorization': f'Bearer {token}'}
        params = {'q': query, 'type': 'track,artist', 'limit': 4}
        
        data = http_client.fetch(Config.URL_BASE_SPOTIFY, params=params, headers=headers)
        suggestions = []
        
        if data:
            if 'artists' in data and data['artists']['items']:
                for artist in data['artists']['items']:
                    suggestions.append({'type': 'artist', 'text': artist['name']})
            
            if 'tracks' in data and data['tracks']['items']:
                for track in data['tracks']['items']:
                    displayText = f"{track['name']} - {track['artists'][0]['name']}"
                    suggestions.append({'type': 'track', 'text': displayText})
                    
        unique_suggestions = []
        seen = set()
        for s in suggestions:
            if s['text'] not in seen:
                unique_suggestions.append(s)
                seen.add(s['text'])
                
        return unique_suggestions[:6]

class LastFMClient(BaseDriver):
    def find_artist(self, query: str):
        params = {'method': 'artist.getinfo', 'artist': query, 'api_key': Config.LASTFM_API_KEY, 'format': 'json', 'lang': 'es'}
        data = http_client.fetch(Config.LASTFM_BASE_URL, params=params)
        
        if not data or 'artist' not in data: return None
        art = data['artist']
        img = self.select_optimal_image(art.get('image', []))
        
        if img == Config.PLACEHOLDER_IMG or not img:
            logger.info(f" Rescatando imagen para {art['name']} desde Spotify...")
            sp = SpotifyClient()
            sp_data = sp.fetch_artist_quick(art['name'])
            if sp_data:
                sp_img = BaseDriver.select_optimal_image(sp_data.get('images', []))
                if sp_img != Config.PLACEHOLDER_IMG:
                    img = sp_img

        return StandardResponse(
            info=ArtistProfile(name=art['name'], genres=[], images=[{'url': img}], popularity=50, followers={'total': 'N/A'}),
            tracks=[], albums=[], fuente="Last.fm", modo_respaldo=True
        )

class YouTubeClient(BaseDriver):
    def get_video(self, query):
        params = {'part': 'snippet', 'q': query, 'key': Config.YOUTUBE_KEY, 'maxResults': 1, 'type': 'video'}
        data = http_client.fetch(Config.YOUTUBE_API_URL, params=params)
        return data['items'][0]['id']['videoId'] if data and 'items' in data and data['items'] else None

# =============================================================================
# [SECCION 10] LOGICA CENTRAL
# =============================================================================

class CoreLogic:
    def __init__(self):
        self.spotify = SpotifyClient()
        self.lastfm = LastFMClient()
        self.youtube = YouTubeClient()

    def resolve_artist_profile(self, query):
        cache_key = DataSanitizer.normalize_search_query(query)
        cached_data = sys_cache.retrieve(cache_key)
        if cached_data:
            logger.info(f" Respuesta de artista '{query}' servida desde cache.")
            data, bio, vid = cached_data
            return data, bio, vid, None
            
        data = self.spotify.find_artist(query)
        if not data:
            # Solo si falla la busqueda inteligente de Spotify vamos a LastFM
            data = self.lastfm.find_artist(query)
        
        if not data: return None, None, None, "No encontrado"

        bio = ""
        try: bio = wikipedia.summary(data.info.name, sentences=4)
        except: pass
        
        vid = self.youtube.get_video(f"{data.info.name} official video")
        
        result = (data, bio, vid)
        sys_cache.store_data(cache_key, result)
        
        return data, bio, vid, None

    def get_discovery_items(self):
        selection = random.sample(Config.POOL_ARTISTAS, 20)
        items = []
        for name in selection:
            img = Config.PLACEHOLDER_IMG
            pop = 50
            try:
                data = self.spotify.fetch_artist_quick(name)
                if data:
                    img = BaseDriver.select_optimal_image(data.get('images', []))
                    pop = data.get('popularity', 50)
            except: pass
            items.append({"nombre": name, "img": img, "popularidad": pop})
        return items

    def get_genre_collection(self, genre):
        tag = Config.GENRE_MAP.get(genre, genre.lower())
        params = {'method': 'tag.gettopartists', 'tag': tag, 'api_key': Config.LASTFM_API_KEY, 'format': 'json', 'limit': 24}
        res = http_client.fetch(Config.LASTFM_BASE_URL, params=params)
        
        collection = []
        if res and 'topartists' in res:
            for art in res['topartists']['artist']:
                name = art['name']
                img = Config.PLACEHOLDER_IMG
                pop = 50
                try:
                    s_data = self.spotify.fetch_artist_quick(name)
                    if s_data:
                        img = BaseDriver.select_optimal_image(s_data.get('images', []))
                        pop = s_data.get('popularity', 50)
                    else:
                        listeners = int(art.get('listeners', 0))
                        pop = min(100, int((listeners/2000000)*100)+25)
                except: pass
                collection.append({"name": name, "img": img, "popularity": pop})
        return collection if collection else MockEngine.generate_discovery_grid()

logic = CoreLogic()

# =============================================================================
# [SECCION 11] RUTAS FLASK
# =============================================================================

app = Flask(__name__)

@app.context_processor
def global_vars():
    return dict(placeholder_global=Config.PLACEHOLDER_IMG, year=datetime.now().year)

@app.route('/', methods=['GET', 'POST'])
def index():
    data, bio, vid, err = None, "", None, None
    if request.method == 'POST':
        q = request.form.get('artista')
        if q: data, bio, vid, err = logic.resolve_artist_profile(q)
    return render_template('index.html', datos=data, bio=bio, video_id=vid, error=err)

@app.route('/artistas')
def artists_view():
    data = logic.get_discovery_items()
    mode = request.args.get('orden')
    if mode == 'az': data.sort(key=lambda x: x['nombre'])
    elif mode == 'popularidad': data.sort(key=lambda x: x['popularidad'], reverse=True)
    return render_template('artistas.html', artistas=data)

@app.route('/generos')
def genres_view():
    data = [{"nombre": g, "imagen": url_for('static', filename=f'generos/{g.replace(" ","")}.png')} for g in Config.LISTA_GENEROS]
    return render_template('generos.html', generos=data)

@app.route('/generos/<nombre_genero>')
def genre_detail_view(nombre_genero):
    data = logic.get_genre_collection(nombre_genero)
    return render_template('generos_detalle.html', genero=nombre_genero, artistas=data)

@app.route('/autosuggest')
def autosuggest():
    query = request.args.get('q', '')
    if len(query) < 2: return jsonify([])
    suggestions = logic.spotify.get_search_suggestions(query)
    return jsonify(suggestions)

if __name__ == '__main__':
    print(" LEGATUM SYSTEM v12.2 ONLINE - http://127.0.0.1:5000")
    app.run(debug=True, port=5000)