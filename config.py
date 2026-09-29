"""Configurazione centralizzata: legge i segreti dal file .env (non versionato)."""

import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    # Se python-dotenv non è installato, si usano le variabili d'ambiente di sistema.
    pass

TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")
JELLYFIN_URL = os.getenv("JELLYFIN_URL", "http://localhost:8096")
JELLYFIN_API_KEY = os.getenv("JELLYFIN_API_KEY", "")

# Cartelle di destinazione del catalogo (relative al progetto se non specificate).
SERIES_PATH = os.getenv("SERIES_PATH", "Serie")
FILMS_PATH = os.getenv("FILMS_PATH", "Film")
ANIME_PATH = os.getenv("ANIME_PATH", "Anime")
