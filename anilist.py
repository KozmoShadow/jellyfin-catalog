"""Backend per AniList (GraphQL, nessuna chiave API).

Serve solo alla scoperta: popolari, filtri e ricerca per titolo. Il download
vero e proprio dei file resta su AnimeWorld (`anime_api`), perché AniList non
ospita video.
"""

import requests

API_URL = "https://graphql.anilist.co"

# AniList non ha un endpoint "generi": li restituisce così, come lista di stringhe.
_GENERI_QUERY = "{ GenreCollection }"

_MEDIA_FIELDS = """
    id
    title { romaji english }
    averageScore
    popularity
    episodes
    seasonYear
    format
    coverImage { large }
    genres
"""

_DISCOVER_QUERY = (
    """
    query($page:Int, $perPage:Int, $genre:[String], $year:Int, $score:Int, $sort:[MediaSort]) {
      Page(page:$page, perPage:$perPage) {
        pageInfo { currentPage lastPage }
        media(
          type: ANIME
          genre_in: $genre
          seasonYear: $year
          averageScore_greater: $score
          sort: $sort
          isAdult: false
        ) {
    """
    + _MEDIA_FIELDS
    + """
        }
      }
    }
    """
)

_CERCA_QUERY = (
    """
    query($titolo:String, $page:Int, $perPage:Int) {
      Page(page:$page, perPage:$perPage) {
        pageInfo { currentPage lastPage }
        media(type: ANIME, search: $titolo, isAdult: false) {
    """
    + _MEDIA_FIELDS
    + """
        }
      }
    }
    """
)


def _esegui(query, variabili=None):
    """Esegue una query GraphQL e restituisce il campo `data` (o None in caso di errore)."""
    try:
        risposta = requests.post(
            API_URL,
            json={"query": query, "variables": variabili or {}},
            timeout=20,
        )
        if risposta.status_code == 200:
            return risposta.json().get("data")
    except requests.RequestException:
        return None
    return None


def get_generi():
    """Restituisce i generi anime disponibili su AniList (lista di stringhe)."""
    dati = _esegui(_GENERI_QUERY)
    if not dati:
        return []
    # AniList non ha un flag per "adulti": lo escludiamo per non proporre
    # contenuti espliciti tra i filtri.
    return [g for g in dati.get("GenreCollection", []) if g != "Hentai"]


def discover(genere=None, anno=None, voto_min=None, sort_by="POPULARITY_DESC",
             page=1, per_page=30):
    """Elenca gli anime applicando i filtri del catalogo.

    voto_min è nella scala 0-10 (come TMDB); AniList usa 0-100, quindi viene
    moltiplicato per 10. Restituisce una tupla (risultati, ultima_pagina).
    """
    variabili = {"page": page, "perPage": per_page, "sort": [sort_by]}
    if genere:
        variabili["genre"] = [genere]
    if anno:
        variabili["year"] = anno
    if voto_min:
        variabili["score"] = int(voto_min * 10)

    dati = _esegui(_DISCOVER_QUERY, variabili)
    if not dati:
        return [], 1

    pagina = dati.get("Page", {})
    return pagina.get("media", []), pagina.get("pageInfo", {}).get("lastPage", 1)


def cerca(titolo, page=1, per_page=30):
    """Cerca anime per titolo. Restituisce una tupla (risultati, ultima_pagina)."""
    if not titolo:
        return [], 1

    dati = _esegui(_CERCA_QUERY, {"titolo": titolo, "page": page, "perPage": per_page})
    if not dati:
        return [], 1

    pagina = dati.get("Page", {})
    return pagina.get("media", []), pagina.get("pageInfo", {}).get("lastPage", 1)


def titolo_italiano(item):
    """Estrae il titolo da usare nelle ricerche AnimeWorld (inglese se c'è, altrimenti romaji)."""
    titolo = item.get("title") or {}
    return titolo.get("english") or titolo.get("romaji") or ""

