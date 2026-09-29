"""Backend per AniList (GraphQL, nessuna chiave API).

Serve solo alla scoperta: tendenze, filtri, ricerca per titolo e tag. Il download
vero e proprio dei file resta su AnimeWorld (`anime_api`), perché AniList non
ospita video.
"""

import requests
import streamlit as st

API_URL = "https://graphql.anilist.co"

# Timeout della richiesta GraphQL: evita che l'app resti appesa se l'API è lenta.
TIMEOUT = 20

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

# Etichette italiane -> valori accettati dall'API. Servono solo a rendere i
# menu comprensibili: le query viaggiano sempre coi valori AniList.
GENERI = {
    "Azione": "Action",
    "Avventura": "Adventure",
    "Commedia": "Comedy",
    "Dramma": "Drama",
    "Ecchi": "Ecchi",
    "Fantasy": "Fantasy",
    "Horror": "Horror",
    "Mahou Shoujo": "Mahou Shoujo",
    "Mecha": "Mecha",
    "Musica": "Music",
    "Mistero": "Mystery",
    "Psicologico": "Psychological",
    "Romantico": "Romance",
    "Fantascienza": "Sci-Fi",
    "Slice of Life": "Slice of Life",
    "Sport": "Sports",
    "Soprannaturale": "Supernatural",
    "Thriller": "Thriller",
}

FORMATI = {
    "Serie TV": "TV",
    "Serie TV corta": "TV_SHORT",
    "Film": "MOVIE",
    "Special": "SPECIAL",
    "OVA": "OVA",
    "ONA": "ONA",
    "Musica": "MUSIC",
}

STATI = {
    "In corso": "RELEASING",
    "Concluso": "FINISHED",
    "Non ancora uscito": "NOT_YET_RELEASED",
    "In pausa": "HIATUS",
    "Cancellato": "CANCELLED",
}

STAGIONI = {
    "Inverno": "WINTER",
    "Primavera": "SPRING",
    "Estate": "SUMMER",
    "Autunno": "FALL",
}

SORGENTI = {
    "Originale": "ORIGINAL",
    "Manga": "MANGA",
    "Light novel": "LIGHT_NOVEL",
    "Visual novel": "VISUAL_NOVEL",
    "Web novel": "WEB_NOVEL",
    "Novel": "NOVEL",
    "Videogioco": "VIDEO_GAME",
    "Anime": "ANIME",
    "Doujinshi": "DOUJINSHI",
    "Live action": "LIVE_ACTION",
    "Altro": "OTHER",
}

PAESI = {
    "Giappone": "JP",
    "Corea del Sud": "KR",
    "Cina": "CN",
    "Taiwan": "TW",
    "Stati Uniti": "US",
}

ORDINAMENTI = {
    "Tendenza": "TRENDING_DESC",
    "Popolarità": "POPULARITY_DESC",
    "Voto medio": "SCORE_DESC",
    "Preferiti": "FAVOURITES_DESC",
    "Più recenti": "START_DATE_DESC",
    "Più vecchi": "START_DATE_ASC",
    "Titolo (A-Z)": "TITLE_ROMAJI",
    "Più episodi": "EPISODES_DESC",
}

_TAG_QUERY = "{ MediaTagCollection { name category rank isGeneralSpoiler } }"


def _esegui(query, variabili=None):
    """Esegue una query GraphQL e restituisce il campo `data` (o None in caso di errore)."""
    try:
        risposta = requests.post(
            API_URL,
            json={"query": query, "variables": variabili or {}},
            timeout=TIMEOUT,
        )
        if risposta.status_code == 200:
            return risposta.json().get("data")
    except requests.RequestException:
        return None
    return None


@st.cache_data(ttl=86400, show_spinner=False)
def get_generi():
    """Restituisce i generi anime disponibili su AniList (lista di stringhe)."""
    return list(GENERI.values())


@st.cache_data(ttl=86400, show_spinner=False)
def get_tag():
    """Restituisce i tag AniList utilizzabili come filtro (lista ordinata di nomi).

    Esclude i contenuti sessuali e i tag che spoilerano la trama: non hanno senso
    come filtro di scoperta.
    """
    dati = _esegui(_TAG_QUERY)
    if not dati:
        return []
    tag = dati.get("MediaTagCollection", [])
    return sorted(
        {
            t["name"]
            for t in tag
            if t.get("category") != "Sexual Content" and not t.get("isGeneralSpoiler")
        }
    )


def _discover_query(filtri):
    """Costruisce la query GraphQL di scoperta a partire dai filtri attivi.

    Ogni filtro diventa una variabile dichiarata solo se presente, così la query
    resta valida anche con un solo filtro o con nessuno.
    """
    dichiarazioni = ["$page:Int", "$perPage:Int", "$sort:[MediaSort]"]
    variabili = {"page": filtri["page"], "perPage": filtri["per_page"],
                 "sort": [filtri["sort"]]}
    argomenti = ["type: ANIME", "isAdult: false", "sort: $sort"]

    def aggiungi(chiave, nome_var, tipo, argomento):
        valore = filtri.get(chiave)
        if valore in (None, [], ""):
            return
        dichiarazioni.append(f"${nome_var}:{tipo}")
        variabili[nome_var] = valore
        argomenti.append(f"{argomento}: ${nome_var}")

    aggiungi("generi", "generi", "[String]", "genre_in")
    aggiungi("generi_esclusi", "generi_esclusi", "[String]", "genre_not_in")
    aggiungi("formati", "formati", "[MediaFormat]", "format_in")
    aggiungi("stato", "stato", "[MediaStatus]", "status_in")
    aggiungi("sorgente", "sorgente", "[MediaSource]", "source_in")
    aggiungi("paese", "paese", "[CountryCode]", "countryOfOrigin_in")
    aggiungi("tag", "tag", "[String]", "tag_in")
    aggiungi("tag_esclusi", "tag_esclusi", "[String]", "tag_not_in")
    aggiungi("stagione", "stagione", "MediaSeason", "season")
    aggiungi("anno", "anno", "Int", "seasonYear")
    aggiungi("ricerca", "ricerca", "String", "search")
    aggiungi("voto_min", "voto_min", "Int", "averageScore_greater")
    aggiungi("popolarita_min", "popolarita_min", "Int", "popularity_greater")
    aggiungi("episodi_min", "episodi_min", "Int", "episodes_greater")
    aggiungi("durata_min", "durata_min", "Int", "duration_greater")
    aggiungi("dal", "dal", "FuzzyDateInt", "startDate_greater")

    query = f"""
    query({", ".join(dichiarazioni)}) {{
      Page(page:$page, perPage:$perPage) {{
        pageInfo {{ currentPage lastPage total }}
        media({", ".join(argomenti)}) {{ {_MEDIA_FIELDS} }}
      }}
    }}
    """
    return query, variabili


@st.cache_data(ttl=600, show_spinner=False)
def discover(genere=None, anno=None, voto_min=None, sort_by="TRENDING_DESC",
             page=1, per_page=30, generi=None, generi_esclusi=None, formati=None,
             stagione=None, stato=None, sorgente=None, paese=None, tag=None,
             tag_esclusi=None, popolarita_min=None, episodi_min=None, durata_min=None,
             dal=None, ricerca=None):
    """Elenca gli anime applicando i filtri del catalogo.

    Supporta sia la firma semplice (`genere`, `anno`, `voto_min`) sia il
    multifiltro (`generi`, `formati`, `stato`, ...). `genere` (singolo) resta per
    compatibilità con la Home; `generi` (lista) è la versione nuova.

    voto_min è nella scala 0-10 (come TMDB); AniList usa 0-100, quindi viene
    moltiplicato per 10. Restituisce una tupla (risultati, ultima_pagina).
    """
    if genere and not generi:
        generi = [genere]

    filtri = {
        "page": page,
        "per_page": per_page,
        "sort": sort_by,
        "generi": generi,
        "generi_esclusi": generi_esclusi,
        "formati": formati,
        "stagione": stagione,
        "stato": stato,
        "sorgente": sorgente,
        "paese": paese,
        "tag": tag,
        "tag_esclusi": tag_esclusi,
        "anno": anno,
        "ricerca": ricerca,
        "voto_min": int(voto_min * 10) if voto_min else None,
        "popolarita_min": popolarita_min,
        "episodi_min": episodi_min,
        "durata_min": durata_min,
        "dal": dal,
    }
    query, variabili = _discover_query(filtri)

    dati = _esegui(query, variabili)
    if not dati:
        return [], 1

    pagina = dati.get("Page", {})
    return pagina.get("media", []), pagina.get("pageInfo", {}).get("lastPage", 1)


@st.cache_data(ttl=300, show_spinner=False)
def cerca(titolo, page=1, per_page=30):
    """Cerca anime per titolo. Restituisce una tupla (risultati, ultima_pagina)."""
    if not titolo:
        return [], 1

    query = f"""
    query($titolo:String, $page:Int, $perPage:Int) {{
      Page(page:$page, perPage:$perPage) {{
        pageInfo {{ currentPage lastPage }}
        media(type: ANIME, search: $titolo, isAdult: false) {{ {_MEDIA_FIELDS} }}
      }}
    }}
    """
    dati = _esegui(query, {"titolo": titolo, "page": page, "perPage": per_page})
    if not dati:
        return [], 1

    pagina = dati.get("Page", {})
    return pagina.get("media", []), pagina.get("pageInfo", {}).get("lastPage", 1)


def titolo_italiano(item):
    """Estrae il titolo da usare nelle ricerche AnimeWorld (inglese se c'è, altrimenti romaji)."""
    titolo = item.get("title") or {}
    return titolo.get("english") or titolo.get("romaji") or ""
