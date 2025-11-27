# =============================================================================
# LEGATUM MUSIC SYSTEM - CORE ENGINE (VERSION 12.0 REAL CONNECTION)
# =============================================================================
# Autor: Legatum Dev Team (Lead: Adrián Barrón Trujillo)
# Licencia: Proprietary Enterprise License
# Estado: Mission Critical / Production Ready
#
# CHANGELOG V12.0 (OFFICIAL API FIX):
# + [CRITICAL] Se han eliminado las URLs falsas de "googleusercontent".
# + [CRITICAL] Se han conectado los Endpoints OFICIALES de Spotify (api.spotify.com).
# + [LOGIC] Se ha forzado la "Misión de Rescate" de imágenes para que si Last.fm falla,
#           Spotify entre inmediatamente a buscar la foto en HD.
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
# [SECCIÓN 1] CONFIGURACIÓN MAESTRA (SYSTEM CONFIGURATION)
# =============================================================================

class Config:
    """
    Centro de Comando de Configuración.
    Define el comportamiento físico, lógico y las credenciales del sistema.
    """
    
    APP_NAME = "Legatum Music Search"
    VERSION = "12.0-Platinum"
    
    # --- CREDENCIALES DE APIS (OBLIGATORIO: VERIFICAR QUE ESTÉN ACTIVAS) ---
    # Si las imágenes siguen sin salir, es posible que estas claves hayan caducado
    # y necesites generar unas nuevas en developer.spotify.com
    
    # 1. SPOTIFY (Fuente de Alta Fidelidad)
    SPOTIFY_CLIENT_ID = 'c0df85c5327842fe8966ffdd1ba5a260'
    SPOTIFY_CLIENT_SECRET = '8182c8b561604f7990c0952d3d0cf88d'
    
    # --- [CORRECCIÓN CRÍTICA] URLs OFICIALES DE SPOTIFY ---
    # NO CAMBIAR ESTAS LÍNEAS BAJO NINGUNA CIRCUNSTANCIA
    URL_AUTH_SPOTIFY = 'https://accounts.spotify.com/api/token'
    URL_BASE_SPOTIFY = 'https://api.spotify.com/v1/search'
    URL_ARTIST_BASE = 'https://api.spotify.com/v1/artists/'
    
    # 2. LAST.FM
    LASTFM_API_KEY = '5dd2074bba107468fa58c78c4fdc0413'
    LASTFM_BASE_URL = 'http://ws.audioscrobbler.com/2.0/'
    
    # 3. YOUTUBE
    YOUTUBE_KEY = 'AIzaSyBUEWLmnvc4uufcxEszVP6TsEklgwdOqi4'
    YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3/search"
    
    # --- RECURSOS VISUALES ---
    # Imagen de estrella (placeholder) que sale cuando NO hay conexión
    PLACEHOLDER_IMG = "https://cdn-icons-png.flaticon.com/512/148/148841.png"
    
    # --- PARÁMETROS DE RED ---
    CACHE_TTL = 3600         
    DISK_CACHE_DIR = "legatum_secure_vault" 
    LOG_DIR = "legatum_audit_logs" 
    MAX_RETRIES = 2          
    TIMEOUT_REQUEST = 5     
    TIMEOUT_QUICK = 3        
    
    # --- CIRCUIT BREAKER ---
    CB_FAILURE_THRESHOLD = 5  
    CB_RECOVERY_TIMEOUT = 60 

    # --- SECURITY ---
    RATE_LIMIT_WINDOW = 60    
    RATE_LIMIT_MAX = 200      

    # --- MODO OFFLINE ---
    ENABLE_OFFLINE_MODE = True 

    # --- POOL DE ARTISTAS ---
    POOL_ARTISTAS = [
        "Kendrick Lamar", "The Weeknd", "Arctic Monkeys", "Dua Lipa", "Bad Bunny",
        "Coldplay", "Eminem", "Feid", "Guns N' Roses", "Harry Styles", 
        "Imagine Dragons", "J Balvin", "Karol G", "Luis Miguel", "Shakira", 
        "Taylor Swift", "Bruno Mars", "Ariana Grande", "Billie Eilish", "Drake", 
        "Ed Sheeran", "Post Malone", "Rihanna", "Justin Bieber", "Katy Perry", 
        "Queen", "Metallica", "AC/DC", "Daddy Yankee", "Rosalía", 
        "Maluma", "BTS", "Blackpink", "Anuel AA", "Ozuna", 
        "Juanes", "Cafe Tacvba", "Soda Stereo", "Panteón Rococó", "Mana", 
        "Reik", "Zoé", "Caifanes", "Molotov", "Enjambre", 
        "Siddhartha", "Camilo", "Rauw Alejandro", "Wisin y Yandel", "Don Omar", 
        "Tego Calderón", "50 Cent", "Snoop Dogg", "Dr. Dre", "Jay-Z", 
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

    # --- LISTA DE GÉNEROS ---
    LISTA_GENEROS = [
        "Rock", "Pop", "Hip Hop", "Reggaeton", "Jazz", 
        "Electronic", "Metal", "Latin", "K-Pop", "Indie", 
        "RnB", "Country", "Classical", "Trap", "Disco", "Blues"
    ]

    # --- MAPEO DE GÉNEROS ---
    GENRE_MAP = {
        "Hip Hop": "hip-hop", "Reggaeton": "reggaeton", "K-Pop": "kpop",
        "RnB": "rnb", "Latin": "latin", "Electronic": "electronic",
        "Indie": "indie", "Metal": "metal", "Rock": "rock",
        "Pop": "pop", "Jazz": "jazz", "Country": "country",
        "Classical": "classical", "Trap": "trap", "Disco": "disco"
    }

wikipedia.set_lang("es")

# =============================================================================
# [SECCIÓN 2] INICIALIZACIÓN DE SISTEMA
# =============================================================================

class SystemBootloader:
    @staticmethod
    def initialize():
        for d in [Config.DISK_CACHE_DIR, Config.LOG_DIR]:
            os.makedirs(d, exist_ok=True)
        print(f"[BOOT] Sistema iniciado v{Config.VERSION}")

SystemBootloader.initialize()

# =============================================================================
# [SECCIÓN 3] LOGGING
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
# [SECCIÓN 4] SEGURIDAD
# =============================================================================

class RequestThrottler:
    def __init__(self): self.clients = {}
    def allow_request(self, ip): return True # Simplificado para evitar bloqueos durante debug

throttler = RequestThrottler()

# =============================================================================
# [SECCIÓN 5] UTILIDADES
# =============================================================================

class DataSanitizer:
    @staticmethod
    def normalize_search_query(query: str) -> str:
        return re.sub(r'[^a-z0-9]', '_', query.strip().lower()) if query else "unknown"

# =============================================================================
# [SECCIÓN 6] MODELOS DE DATOS
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
# [SECCIÓN 7] MOCK ENGINE
# =============================================================================

class MockEngine:
    @staticmethod
    def generate_discovery_grid():
        # Devuelve datos falsos solo si todo falla
        return [{"nombre": "Artist Offline", "img": Config.PLACEHOLDER_IMG, "popularidad": 25} for _ in range(8)]

    @staticmethod
    def generate_artist_profile(name):
        return StandardResponse(
            info=ArtistProfile(name=name, genres=["Offline"], images=[{'url': Config.PLACEHOLDER_IMG}], popularity=25, followers={'total': '0'}),
            tracks=[], albums=[], fuente="Offline", modo_respaldo=True
        )

# =============================================================================
# [SECCIÓN 8] CACHE & HTTP
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
        try:
            if method == 'POST': resp = self.session.post(url, data=data, headers=headers, auth=auth, timeout=5)
            else: resp = self.session.get(url, params=params, headers=headers, timeout=5)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Error HTTP en {url}: {e}")
            return None

http_client = HttpDriver()

# =============================================================================
# [SECCIÓN 9] DRIVERS DE API (CORREGIDOS)
# =============================================================================

class BaseDriver:
    @staticmethod
    def select_optimal_image(images: List[Dict]) -> str:
        if not images: return Config.PLACEHOLDER_IMG
        # Intentar obtener la imagen más grande disponible
        try:
            # Ordenar por tamaño (Spotify usa 'width', LastFM 'size')
            # Estrategia Spotify: El primer elemento suele ser el más grande
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
        """Autenticación REAL con Spotify."""
        if self.access_token and time.time() < self.token_expiry: return self.access_token
        
        # Codificación base64 de credenciales para header estandar
        auth_str = f"{Config.SPOTIFY_CLIENT_ID}:{Config.SPOTIFY_CLIENT_SECRET}"
        b64_auth = base64.b64encode(auth_str.encode()).decode()
        
        headers = {'Authorization': f'Basic {b64_auth}'}
        data = {'grant_type': 'client_credentials'}
        
        res = http_client.fetch(Config.URL_AUTH_SPOTIFY, method='POST', data=data, headers=headers)
        
        if res and 'access_token' in res:
            self.access_token = res['access_token']
            self.token_expiry = time.time() + res.get('expires_in', 3600) - 60
            logger.info("✅ Conexión Spotify Exitosa")
            return self.access_token
        
        logger.error("❌ Error de autenticación Spotify - Revisa CLIENT ID / SECRET")
        return None

    def fetch_artist_quick(self, query: str):
        """Búsqueda rápida para obtener solo la imagen."""
        token = self.authorize()
        if not token: return None
        
        headers = {'Authorization': f'Bearer {token}'}
        data = http_client.fetch(Config.URL_BASE_SPOTIFY, params={'q': query, 'type': 'artist', 'limit': 1}, headers=headers)
        
        if data and data.get('artists', {}).get('items'):
            return data['artists']['items'][0]
        return None

    def find_artist(self, query: str):
        token = self.authorize()
        if not token: return None
        headers = {'Authorization': f'Bearer {token}'}
        
        # 1. Buscar ID
        search = http_client.fetch(Config.URL_BASE_SPOTIFY, params={'q': query, 'type': 'artist', 'limit': 1}, headers=headers)
        if not search or not search.get('artists', {}).get('items'): return None
        
        artist = search['artists']['items'][0]
        aid = artist['id']
        
        # 2. Tracks & Albums
        tracks_data = http_client.fetch(f"{Config.URL_ARTIST_BASE}{aid}/top-tracks", params={'market': 'MX'}, headers=headers)
        albums_data = http_client.fetch(f"{Config.URL_ARTIST_BASE}{aid}/albums", params={'limit': 10, 'include_groups': 'album'}, headers=headers)
        
        tracks = [TrackInfo(name=t['name'], external_urls=t.get('external_urls', {})) for t in tracks_data.get('tracks', [])[:5]] if tracks_data else []
        albums = [AlbumInfo(name=a['name'], images=a.get('images', []), release_date=a.get('release_date', '')) for a in albums_data.get('items', [])] if albums_data else []
        img = self.select_optimal_image(artist.get('images', []))
        
        return StandardResponse(
            info=ArtistProfile(name=artist['name'], genres=artist.get('genres', [])[:3], images=[{'url': img}], popularity=artist.get('popularity', 0), followers={'total': artist.get('followers', {}).get('total', 0)}),
            tracks=tracks, albums=albums, fuente="Spotify", modo_respaldo=False
        )

class LastFMClient(BaseDriver):
    def find_artist(self, query: str):
        # Esta función ahora intenta buscar en LastFM, pero si falla la imagen, pide ayuda a Spotify
        params = {'method': 'artist.getinfo', 'artist': query, 'api_key': Config.LASTFM_API_KEY, 'format': 'json', 'lang': 'es'}
        data = http_client.fetch(Config.LASTFM_BASE_URL, params=params)
        
        if not data or 'artist' not in data: return None
        art = data['artist']
        img = self.select_optimal_image(art.get('image', []))
        
        # --- RESCATE SPOTIFY ---
        # Si LastFM nos da la estrella (placeholder) o está vacío, llamamos a Spotify
        if img == Config.PLACEHOLDER_IMG or not img:
            logger.info(f"🔄 Rescatando imagen para {art['name']} desde Spotify...")
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
# [SECCIÓN 10] LOGICA CENTRAL
# =============================================================================

class CoreLogic:
    def __init__(self):
        self.spotify = SpotifyClient()
        self.lastfm = LastFMClient()
        self.youtube = YouTubeClient()

    def resolve_artist_profile(self, query):
        # Intenta Spotify primero (Alta calidad)
        data = self.spotify.find_artist(query)
        if not data:
            # Si falla, intenta LastFM
            data = self.lastfm.find_artist(query)
        
        if not data: return None, None, None, "No encontrado"

        # Enriquecimiento
        bio = ""
        try: bio = wikipedia.summary(data.info.name, sentences=4)
        except: pass
        
        vid = self.youtube.get_video(f"{data.info.name} official video")
        
        return data, bio, vid, None

    def get_discovery_items(self):
        # Grid de descubrimiento usando Spotify
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
        # 1. Obtener lista de nombres desde Last.fm (es bueno para géneros)
        tag = Config.GENRE_MAP.get(genre, genre.lower())
        params = {'method': 'tag.gettopartists', 'tag': tag, 'api_key': Config.LASTFM_API_KEY, 'format': 'json', 'limit': 24}
        res = http_client.fetch(Config.LASTFM_BASE_URL, params=params)
        
        collection = []
        if res and 'topartists' in res:
            for art in res['topartists']['artist']:
                name = art['name']
                img = Config.PLACEHOLDER_IMG
                pop = 50 # Default si falla la API
                
                # 2. OBLIGATORIO: Buscar imagen en Spotify para cada artista
                # Porque Last.fm ya no da imágenes buenas
                try:
                    s_data = self.spotify.fetch_artist_quick(name)
                    if s_data:
                        img = BaseDriver.select_optimal_image(s_data.get('images', []))
                        pop = s_data.get('popularity', 50)
                    else:
                        # Fallback a calculo manual si Spotify falla para este artista
                        listeners = int(art.get('listeners', 0))
                        pop = min(100, int((listeners/2000000)*100)+25)
                except: pass
                
                collection.append({"name": name, "img": img, "popularity": pop})
                
        return collection if collection else MockEngine.generate_discovery_grid()

logic = CoreLogic()

# =============================================================================
# [SECCIÓN 11] RUTAS FLASK
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

if __name__ == '__main__':
 print("🚀 LEGATUM SYSTEM v12.0 ONLINE - http://127.0.0.1:5000")
app.run(debug=True, port=5000)