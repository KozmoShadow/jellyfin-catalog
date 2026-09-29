"""Backend per AnimeWorld: ricerca, dettagli ed episodi (link .mp4 diretti).

La libreria `animeworld` fa da sé scraping e header: `Episodio.links` restituisce
già gli URL `.mp4` dei mirror, quindi non serve alcuna estrazione con browser.
"""

import re
from urllib.parse import urlparse

import animeworld as aw

_RE_PAGINA = re.compile(r"/play/([^/]+)")
_RE_VIDEO = re.compile(r"\.(mp4|mkv|m3u8|webm)(?:[?#].*)?$", re.IGNORECASE)


def link_pagina_anime(link):
    """Riduce un link AnimeWorld alla sola pagina dell'anime.

    Da `/play/<slug>.<id>/<id-episodio>` ricava `/play/<slug>.<id>`, che
    identifica la stagione e da cui si ricavano tutti gli episodi.
    """
    if not link:
        return None
    parti = urlparse(link)
    match = _RE_PAGINA.search(parti.path)
    if not match:
        return link
    return f"{parti.scheme}://{parti.netloc}/play/{match.group(1)}"


def _e_url_video(url):
    """True se l'URL punta direttamente a un file video (non a una pagina web)."""
    return bool(url) and "animeworld.ac" not in url and bool(_RE_VIDEO.search(url))


def cerca_anime(query):
    """Cerca un anime per titolo. Restituisce la lista di dizionari di AnimeWorld."""
    if not query:
        return []
    return aw.find(query)


def dettagli_anime(link):
    """Restituisce nome, trama, copertina e metadati (voto, stato, studio...) di un anime."""
    anime = aw.Anime(link)
    return {
        "nome": anime.getName(),
        "trama": anime.getTrama(),
        "copertina": anime.getCover(),
        "info": anime.getInfo(),
    }


def episodi(link):
    """Restituisce la lista degli oggetti Episodio di un anime.

    Nota: va chiamata una sola volta per anime e riusata, perché ogni chiamata
    riscarica la pagina della serie.
    """
    return aw.Anime(link).getEpisodes()


def link_mp4(episodio):
    """Ritorna l'URL `.mp4` diretto di un episodio (primo mirror valido).

    Se un server restituisse una pagina web (es. `animeworld.ac/play/...`)
    invece del file, viene scartato: nel `.strm` va scritta solo la sorgente video.
    """
    if episodio is None:
        return None
    for server in episodio.links:
        link = getattr(server, "link", None)
        if _e_url_video(link):
            return link
    return None


def lista_episodi(link):
    """Restituisce i numeri di episodio disponibili, come stringhe (es. ['1', '2', ...])."""
    return [str(ep.number) for ep in episodi(link)]


def link_episodio(link, numero_episodio):
    """Risolve l'URL `.mp4` diretto di un episodio (primo mirror disponibile)."""
    for ep in episodi(link):
        if str(ep.number) == str(numero_episodio):
            return link_mp4(ep)
    return None
