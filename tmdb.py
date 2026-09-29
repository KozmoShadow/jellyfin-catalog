import requests

from config import TMDB_API_KEY

API_KEY = TMDB_API_KEY
BASE_URL = "https://api.themoviedb.org/3"

def cerca_serie(titolo):
    """Cerca una serie TV per nome e restituisce i risultati principali."""
    url = f"{BASE_URL}/search/multi?api_key={API_KEY}&query={titolo}&language=it-IT"
    response = requests.get(url)
    
    if response.status_code == 200:
        return response.json().get("results", [])
    return []

def get_dettagli_stagione(tmdb_id, numero_stagione):
    """Ottiene la lista degli episodi e i dettagli di una specifica stagione."""
    url = f"{BASE_URL}/tv/{tmdb_id}/season/{numero_stagione}?api_key={API_KEY}&language=it-IT"
    response = requests.get(url)
    
    if response.status_code == 200:
        return response.json()
    return None

def get_numero_stagioni(tmdb_id):
    """Restituisce il numero totale di stagioni di una serie TV."""
    url = f"{BASE_URL}/tv/{tmdb_id}?api_key={API_KEY}&language=it-IT"
    response = requests.get(url)
    
    if response.status_code == 200:
        return response.json().get("number_of_seasons")
    return None

IMG_BASE_URL = "https://image.tmdb.org/t/p/w500"

def cerca_multimediale(query, page=1):
    """Cerca film, serie TV o persone su TMDB supportando la paginazione."""
    if not query:
        return []
    url = f"https://api.themoviedb.org/3/search/multi?api_key={API_KEY}&language=it-IT&query={query}&page={page}"
    res = requests.get(url)
    if res.status_code == 200:
        data = res.json()
        return data.get("results", []), data.get("total_pages", 1)
    return [], 1

def get_tmdb_popular(media_type):
    """Recupera i contenuti popolari (movie o tv) da TMDB combinando le pagine."""
    results = []
    
    # TMDB dà 20 risultati per pagina, quindi prendiamo la pagina 1 e la pagina 2
    for page in [1, 2]:
        url = f"https://api.themoviedb.org/3/{media_type}/popular?api_key={API_KEY}&language=it-IT&page={page}"
        res = requests.get(url)
        
        if res.status_code == 200:
            results.extend(res.json().get("results", []))
            
    return results[:36]

def get_tmdb_details(media_type, media_id):
    """Recupera i dettagli completi di un film o serie TV tramite ID."""
    url = f"https://api.themoviedb.org/3/{media_type}/{media_id}?api_key={API_KEY}&language=it-IT"
    res = requests.get(url)
    if res.status_code == 200:
        return res.json()
    return None

def get_tmdb_videos(media_type, media_id):
    """Recupera i video (trailer, teaser...) di un film o serie TV."""
    url = f"https://api.themoviedb.org/3/{media_type}/{media_id}/videos"
    params = {"api_key": API_KEY, "language": "it-IT"} # o en-US come fallback
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json().get("results", [])
    return []

def get_tmdb_credits(media_type, media_id):
    """Recupera i crediti (cast e crew) di un film o serie TV."""
    url = f"{BASE_URL}/{media_type}/{media_id}/credits"
    params = {"api_key": API_KEY, "language": "it-IT"}
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()
    return None

def get_generi(media_type="movie"):
    """Restituisce la lista dei generi TMDB per 'movie' o 'tv' come lista di dizionari."""
    url = f"{BASE_URL}/genre/{media_type}/list"
    params = {"api_key": API_KEY, "language": "it-IT"}
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json().get("genres", [])
    return []

def discover_movie(genere_id=None, anno=None, voto_min=None, min_voti=None,
                   sort_by="popularity.desc", page=1):
    """
    Cerca film tramite /discover/movie applicando i filtri del catalogo.

    Parametri:
        genere_id: id del genere TMDB (with_genres)
        anno: anno di uscita (primary_release_year)
        voto_min: voto medio minimo (vote_average.gte)
        min_voti: numero minimo di voti (vote_count.gte), utile per scartare
                  titoli con pochissimi voti che falsano il voto medio
        sort_by: ordinamento TMDB (es. popularity.desc, vote_average.desc,
                 primary_release_date.desc, revenue.desc)
        page: pagina dei risultati

    Restituisce una tupla (risultati, total_pages).
    """
    url = f"{BASE_URL}/discover/movie"
    params = {
        "api_key": API_KEY,
        "language": "it-IT",
        "sort_by": sort_by,
        "page": page,
        "include_adult": "false",
    }
    if genere_id:
        params["with_genres"] = genere_id
    if anno:
        params["primary_release_year"] = anno
    if voto_min:
        params["vote_average.gte"] = voto_min
    if min_voti:
        params["vote_count.gte"] = min_voti

    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        return data.get("results", []), data.get("total_pages", 1)
    return [], 1