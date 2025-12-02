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
#
# CHANGELOG V12.3 (YOUTUBE MIX INTEGRATION):
# + [FEATURE] Agregado soporte para pestaña 'Mix' en StandardResponse.
# + [LOGIC] CoreLogic ahora inyecta un mix de videos de YouTube en la respuesta.
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
        "Beyonce", "Lady Gaga", "Sam Smith", "Demi Lovato", "Selena Gomez", "Halsey", "Sia", 
"P!nk", "Alicia Keys", "John Legend", "Maroon 5", "OneRepublic", "Charlie Puth", 
"Shawn Mendes", "Camila Cabello", "Fifth Harmony", "Little Mix", "One Direction", 
"Niall Horan", "Zayn", "Liam Payne", "Louis Tomlinson", "Jonas Brothers", "Nick Jonas", 
"Joe Jonas", "Miley Cyrus", "Avril Lavigne", "Kelly Clarkson", "Christina Aguilera", 
"Justin Timberlake", "Pharrell Williams", "Robin Thicke", "Usher", "Chris Brown", 
"Ne-Yo", "Jason Derulo", "Pitbull", "Sean Paul", "Flo Rida", "Akon", "T-Pain", 
"Ludacris", "Nelly", "Timbaland", "Missy Elliott", "Ciara", "Fergie", "The Black Eyed Peas", 
"Gwen Stefani", "No Doubt", "The Killers", "Kings of Leon", "Paramore", "Fall Out Boy", 
"Panic! At The Disco", "Twenty One Pilots", "My Chemical Romance", "Evanescence", 
"30 Seconds to Mars", "Bring Me The Horizon", "Slipknot", "Korn", "Limp Bizkit", 
"Papa Roach", "Disturbed", "Godsmack", "Avenged Sevenfold", "Five Finger Death Punch", 
"Pantera", "Slayer", "Megadeth", "Anthrax", "Motorhead", "Def Leppard", "Motley Crue", 
"Poison", "Whitesnake", "Deep Purple", "Rainbow", "Dio", "Alice Cooper", "Kiss", 
"Van Halen", "The Who", "The Doors", "Janis Joplin", "Jimi Hendrix", "Cream", 
"Eric Clapton", "Santana", "Fleetwood Mac", "Eagles", "Creedence Clearwater Revival", 
"The Beach Boys", "Simon & Garfunkel", "Bob Dylan", "Neil Young", "Bruce Springsteen", 
"Tom Petty", "Bryan Adams", "Rod Stewart", "Elton John", "Billy Joel", "Phil Collins", 
"Genesis", "Peter Gabriel", "Sting", "The Police", "Dire Straits", "Mark Knopfler", 
"Supertramp", "Electric Light Orchestra", "Toto", "Journey", "Foreigner", "Boston", 
"Chicago", "REO Speedwagon", "Styx", "Kansas", "Heart", "Pat Benatar", "Blondie", 
"Talking Heads", "The Clash", "Ramones", "Sex Pistols", "Iggy Pop", "Velvet Underground", 
"Lou Reed", "Patti Smith", "Morrissey", "The Smiths", "Blur", "Oasis", "Liam Gallagher", 
"Noel Gallagher's High Flying Birds", "The Verve", "Pulp", "Suede", "Placebo", 
"Franz Ferdinand", "Kaiser Chiefs", "The Kooks", "The Wombats", "Two Door Cinema Club", 
"Foster the People", "MGMT", "Empire of the Sun", "Phoenix", "Vampire Weekend", 
"Arcade Fire", "The National", "Bon Iver", "Fleet Foxes", "Mumford & Sons", "The Lumineers", 
"Hozier", "George Ezra", "Lewis Capaldi", "Sam Fender", "Tom Grennan", "Bastille", 
"Imagine Dragons", "X Ambassadors", "Kaleo", "The Black Keys", "Cage The Elephant", 
"Glass Animals", "Portugal. The Man", "alt-J", "The 1975", "Wallows", "Clairo", 
"Rex Orange County", "Joji", "Mac DeMarco", "Tame Impala", "King Gizzard & The Lizard Wizard", 
"Royal Blood", "Greta Van Fleet", "Maneskin", "Wolfmother", "Jet", "The Vines", 
"The Hives", "White Stripes", "Jack White", "The Raconteurs", "Dead Weather", 
"Queens of the Stone Age", "The Smashing Pumpkins", "Jane's Addiction", "Nine Inch Nails", 
"Marilyn Manson", "Rob Zombie", "Tool", "A Perfect Circle", "Deftones", "Incubus", 
"Audioslave", "Chris Cornell", "Temple of the Dog", "Mother Love Bone", "Bush", 
"Silverchair", "The Offspring", "Sum 41", "Good Charlotte", "Simple Plan", "Rise Against", 
"Bad Religion", "NOFX", "Rancid", "Pennywise", "Social Distortion", "Dropkick Murphys", 
"Flogging Molly", "Gogol Bordello", "Sublime", "311", "Incubus", "Hoobastank", 
"Chevelle", "Seether", "Staind", "Puddle of Mudd", "Nickelback", "Theory of a Deadman", 
"Shinedown", "Alter Bridge", "Breaking Benjamin", "Three Days Grace", "Skillet", 
"Starset", "Halestorm", "The Pretty Reckless", "In This Moment", "Lacuna Coil", 
"Nightwish", "Epica", "Within Temptation", "DragonForce", "Helloween", "Gamma Ray", 
"Stratovarius", "Sonata Arctica", "Blind Guardian", "Iced Earth", "Dream Theater", 
"Symphony X", "Opeth", "Mastodon", "Gojira", "Lamb of God", "Trivium", "Killswitch Engage", 
"Bullet For My Valentine", "All That Remains", "As I Lay Dying", "Parkway Drive", 
"Architects", "Bring Me The Horizon", "Asking Alexandria", "Black Veil Brides", 
"Pierce The Veil", "Sleeping With Sirens", "Falling In Reverse", "Escape The Fate", 
"A Day To Remember", "The Story So Far", "Neck Deep", "State Champs", "Knuckle Puck", 
"Real Friends", "Mayday Parade", "All Time Low", "Waterparks", "5 Seconds of Summer", 
"Yungblud", "Machine Gun Kelly", "Mod Sun", "blackbear", "Iann Dior", "24kGoldn", 
"The Kid LAROI", "Juice WRLD", "XXXTENTACION", "Lil Peep", "Trippie Redd", 
"Ski Mask The Slump God", "Lil Pump", "Smokepurpp", "6ix9ine", "Kodak Black", 
"NBA Youngboy", "DaBaby", "Roddy Ricch", "Lil Baby", "Gunna", "Young Thug", 
"Future", "Migos", "Quavo", "Offset", "Takeoff", "Gucci Mane", "2 Chainz", 
"Rick Ross", "Meek Mill", "Wale", "Big Sean", "Logic", "Joyner Lucas", "Hopsin", 
"Tech N9ne", "Machine Gun Kelly", "G-Eazy", "Macklemore", "Ryan Lewis", "NF", 
"Chance the Rapper", "Childish Gambino", "Tyler, The Creator", "Frank Ocean", 
"ASAP Rocky", "Kid Cudi", "Mac Miller", "Earl Sweatshirt", "Joey Bada$$", 
"J. Cole", "Kendrick Lamar", "Schoolboy Q", "Ab-Soul", "Jay Rock", "Isaiah Rashad", 
"Anderson .Paak", "Thundercat", "Kaytranada", "Flying Lotus", "Thundercat", 
"Kali Uchis", "Jorja Smith", "H.E.R.", "SZA", "Summer Walker", "Kehlani", 
"Tinashe", "Normani", "Chloe x Halle", "Solange", "Erykah Badu", "Lauryn Hill", 
"The Fugees", "Jill Scott", "Maxwell", "D'Angelo", "Boyz II Men", "TLC", 
"Destiny's Child", "En Vogue", "SWV", "Salt-N-Pepa", "Run-D.M.C.", "Public Enemy", 
"Beastie Boys", "N.W.A", "Ice Cube", "Eazy-E", "Nas", "Wu-Tang Clan", "Method Man", 
"Redman", "Busta Rhymes", "DMX", "Ja Rule", "Ashanti", "Jennifer Lopez", 
"Marc Anthony", "Ricky Martin", "Enrique Iglesias", "Chayanne", "Thalia", 
"Paulina Rubio", "Gloria Trevi", "Alejandra Guzman", "Belinda", "RBD", "Anahi", 
"Dulce Maria", "Maite Perroni", "Christian Chavez", "Christopher Uckermann", 
"Jesse & Joy", "Ha*Ash", "Paty Cantu", "Danna Paola", "Kenia Os", "Kim Loaiza", 
"JD Pantoja", "Mario Bautista", "CD9", "CNCO", "Abraham Mateo", "Becky G", 
"Natti Natasha", "Cazzu", "Nicki Nicole", "Maria Becerra", "Tini", "Lali", 
"Emilia", "Tiago PZK", "Duki", "Khea", "Trueno", "Wos", "Bizarrap", "Quevedo", 
"Saiko", "Mora", "Jhayco", "Myke Towers", "Sech", "Justin Quiles", "Lenny Tavarez", 
"Dalex", "Dimelo Flow", "Arcangel", "De La Ghetto", "Nicky Jam", "Zion & Lennox", 
"Plan B", "Chencho Corleone", "Maldy", "Jowell & Randy", "Alexis & Fido", 
"Yandel", "Wisin", "Ivy Queen", "Tito El Bambino", "Hector El Father", 
"Farruko", "Pedro Capo", "Camilo", "Manuel Turizo", "Sebastian Yatra", 
"Piso 21", "Morat", "Mau y Ricky", "Danny Ocean", "Lasso", "Micro TDH", 
"Big Soto", "Neutro Shorty", "Akapellah", "Lil Supa", "Canserbero", "Nach", 
"Kase.O", "Violadores del Verso", "SFDK", "Mala Rodriguez", "Residente", 
"Calle 13", "Visitante", "Ile", "Drexler", "Fito Paez", "Charly Garcia", 
"Luis Alberto Spinetta", "Gustavo Cerati", "Andres Calamaro", "Los Fabulosos Cadillacs", 
"Autenticos Decadentes", "Los Pericos", "Babasonicos", "Miranda!", "Tan Bionica", 
"Airbag", "Cuarteto de Nos", "No Te Va Gustar", "La Vela Puerca", "El Kuelgue", 
"Conociendo Rusia", "Bandalos Chinos", "Usted Senalemelo", "Porter", "Little Jesus", 
"Technicolor Fabrics", "Clubz", "Reyno", "Camilo Septimo", "Odisseo", 
"Comisario Pantera", "Los Daniels", "DLD", "La Gusana Ciega", "Jumbo", 
"Division Minuscula", "Insite", "Pxndx", "Allison", "Delux", "Tolidos", 
"Thermo", "Canseco", "Here Comes The Kraken", "Agora", "Mago de Oz", 
"Heroes del Silencio", "Bunbury", "Vetusta Morla", "Izal", "Love of Lesbian", 
"Lori Meyers", "Dorian", "La Casa Azul", "Sidonie", "Viva Suecia", "Arde Bogota", 
"Ginebras", "Rigoberta Bandini", "Amaia", "Aitana", "Lola Indigo", "Ana Mena", 
"Omar Montes", "C. Tangana", "Rosals", "Nathy Peluso", "Peso Pluma", 
"Natanael Cano", "Junior H", "Gabito Ballesteros", "Fuerza Regida", "Eslabon Armado", 
"Grupo Frontera", "Carin Leon", "Christian Nodal", "Angela Aguilar", "Pepe Aguilar", 
"Antonio Aguilar", "Vicente Fernandez", "Alejandro Fernandez", "Pedro Infante", 
"Jorge Negrete", "Jose Alfredo Jimenez", "Javier Solis", "Rocio Durcal", 
"Juan Gabriel", "Jose Jose", "Marco Antonio Solis", "Los Bukis", "Bronco", 
"Los Temerarios", "Los Tigres del Norte", "Los Tucanes de Tijuana", "Chalino Sanchez", 
"Valentin Elizalde", "Jenni Rivera", "Banda MS", "La Arrolladora Banda El Limon", 
"Banda El Recodo", "La Adictiva", "Calibre 50", "Julion Alvarez", "Alfredo Olivas", 
"El Fantasma", "Gerardo Ortiz", "Luis R Conriquez", "Marca Registrada", "Grupo Firme", 
"Yahritza y Su Esencia", "Ivan Cornejo", "DannyLux", "Ed Maverick", "Kevin Kaarl", 
"Bratty", "Renee", "Silvana Estrada", "Natalia Lafourcade", "Ximena Sarinata", 
"Carla Morrison", "Julieta Venegas", "Ely Guerra", "Hello Seahorse!", "Belanova", 
"Moenia", "Fobia", "Kinky", "Plastilina Mosh", "Control Machete", "Cartel de Santa", 
"Santa Fe Klan", "Gera MX", "Aleman", "Dharius", "C-Kan", "MC Davo", 
"Sabino", "Lng/SHT", "Charles Ans", "Nanpa Basico", "Caloncho", "Esteman", 
"Monsieur Perine", "Bomba Estereo", "Systema Solar", "ChocQuibTown", "Fonseca", 
"Carlos Vives", "Bacilos", "Diego Torres", "Ricardo Montaner", "Ricardo Arjona", 
"Sin Bandera", "Camila", "Leonel Garcia", "Noel Schajris", "Alexander Acha", 
"Kalimba", "OV7", "Kabah", "Magneto", "Mercurio", "Fey", "Jeans", "JNS"
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
    # [CAMBIO] Lista de videos para la pestaña 'Mix'
    mix_videos: List[Dict[str, str]] = field(default_factory=list)

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

        # Estrategia 2: Busqueda estandar de Artista
        if not artist_id and not is_composite:
            logger.info(f" Buscando '{query}' como Artista...")
            search_artist = http_client.fetch(Config.URL_BASE_SPOTIFY, params={'q': query, 'type': 'artist', 'limit': 1}, headers=headers)
            
            if search_artist and search_artist.get('artists', {}).get('items'):
                artist_data = search_artist['artists']['items'][0]
                artist_id = artist_data['id']

        # Estrategia 3: Busqueda por TRACK
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

    # [CAMBIO] Funcion para obtener mix de videos de un artista especifico
    def get_artist_mix(self, artist_name: str) -> List[Dict[str, str]]:
        """Busca videos musicales oficiales del artista para la seccion Mix."""
        query = f"{artist_name} official music video"
        # videoCategoryId=10 filtra solo Musica
        params = {
            'part': 'snippet', 
            'q': query, 
            'key': Config.YOUTUBE_KEY, 
            'maxResults': 8, # 8 videos para una grilla equilibrada
            'type': 'video', 
            'videoCategoryId': '10' 
        }
        data = http_client.fetch(Config.YOUTUBE_API_URL, params=params)
        
        mix_list = []
        if data and 'items' in data:
            for item in data['items']:
                if item['id'].get('videoId'):
                    mix_list.append({
                        'title': item['snippet']['title'],
                        'video_id': item['id']['videoId'],
                        'thumbnail': item['snippet']['thumbnails']['medium']['url']
                    })
        return mix_list

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

        # [CAMBIO] Inyeccion de videos del Mix de YouTube
        # Obtenemos los videos y los guardamos dentro del objeto data (StandardResponse)
        try:
            mix_videos = self.youtube.get_artist_mix(data.info.name)
            data.mix_videos = mix_videos
        except Exception as e:
            logger.error(f"Error obteniendo mix de youtube: {e}")
            data.mix_videos = []

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