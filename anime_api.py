"""Backend per AnimeWorld: ricerca, dettagli ed episodi (link .mp4 diretti).

La libreria `animeworld` fa da sé scraping e header: `Episodio.links` restituisce
già gli URL `.mp4` dei mirror, quindi non serve alcuna estrazione con browser.
"""

import re
from difflib import SequenceMatcher
from urllib.parse import urlparse

import animeworld as aw

_RE_PAGINA = re.compile(r"/play/([^/]+)")
_RE_VIDEO = re.compile(r"\.(mp4|mkv|m3u8|webm)(?:[?#].*)?$", re.IGNORECASE)
_RE_PARENTESI = re.compile(r"[\(\[\{].*?[\)\]\}]")
_RE_SPAZI = re.compile(r"\s+")


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


def _normalizza_titolo(titolo):
    """Normalizza un titolo per confronti e ricerche AnimeWorld.

    Toglie parentesi (es. `(ITA)`), punteggiatura e spazi doppi, così
    `The Seven Deadly Sins (ITA)` e il nome cartella `The Seven Deadly Sins ITA`
    danno lo stesso risultato.
    """
    if not titolo:
        return ""
    titolo = _RE_PARENTESI.sub(" ", titolo)
    titolo = re.sub(r"[^0-9A-Za-zÀ-ÿ]+", " ", titolo)
    return _RE_SPAZI.sub(" ", titolo).strip().lower()


def _punteggio_titolo(titolo, candidato):
    """Similarità 0-1 tra due titoli normalizzati (per scegliere il risultato migliore)."""
    a, b = _normalizza_titolo(titolo), _normalizza_titolo(candidato)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    if a in b or b in a:
        return 0.9
    return SequenceMatcher(None, a, b).ratio()


def cerca_anime_tollerante(query):
    """Cerca un anime provando più varianti del titolo, in ordine di specificità.

    AnimeWorld è sensibile a punteggiatura e parentesi (`One-Punch Man` non dà
    risultati, `One Punch Man` sì; `(ITA)` va incluso). Prova il titolo intero,
    poi ripulito, poi senza suffisso ITA e infine senza suffisso stagione.
    """
    if not query:
        return []
    varianti = []
    for v in (
        query.strip(),
        re.sub(r"\s+ITA\s*$", " (ITA)", query, flags=re.IGNORECASE).strip(),
        re.sub(r"[^0-9A-Za-zÀ-ÿ]+", " ", query).strip(),
        re.sub(r"[^0-9A-Za-zÀ-ÿ]+", " ", re.sub(r"\s*\(?\bITA\b\)?\s*$", " ", query, flags=re.IGNORECASE)).strip(),
        _RE_PARENTESI.sub(" ", query).strip(),
        re.sub(r"\s+Season\s+\d+.*$", "", query, flags=re.IGNORECASE).strip(),
        re.sub(r"\s+(Part|Parte)\s+\d+.*$", "", query, flags=re.IGNORECASE).strip(),
    ):
        normalizzata = _RE_SPAZI.sub(" ", v).strip()
        if normalizzata and normalizzata not in varianti:
            varianti.append(normalizzata)

    for variante in varianti:
        try:
            risultati = aw.find(variante)
        except Exception:
            risultati = []
        if risultati:
            return risultati
    return []


def _e_doppiaggio_ita(nome):
    """True se il nome AnimeWorld indica la versione doppiata in italiano."""
    nome = (nome or "").lower()
    return "(ita)" in nome or nome.rstrip().endswith(" ita")


def miglior_risultato(titolo, risultati):
    """Sceglie il risultato AnimeWorld più simile al titolo dato (o None).

    A parità di somiglianza preferisce la versione coerente col titolo: se la
    cartella non indica ITA, sceglie il SUB; se indica ITA, sceglie il doppiato.
    """
    if not risultati:
        return None
    vuole_ita = bool(re.search(r"\bita\b", titolo or "", re.IGNORECASE))

    def chiave(r):
        nome = r.get("name") or ""
        coerenza = 1 if _e_doppiaggio_ita(nome) == vuole_ita else 0
        return (_punteggio_titolo(titolo, nome), coerenza)

    return max(risultati, key=chiave)


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
    try:
        servers = list(episodio.links)
    except Exception:
        # Un server può sollevare durante la risoluzione: si prova comunque a
        # leggerne gli altri, ma se fallisce tutto l'episodio resta senza link.
        return None
    for server in servers:
        link = getattr(server, "link", None)
        if _e_url_video(link):
            return link
    return None


def motivo_link_mancante(episodio):
    """Spiega in una frase perché un episodio non ha prodotto un link video.

    Serve alla diagnostica della UI quando l'aggiunta fallisce senza un errore:
    distingue "nessun server", "pagina web invece del file" e "URL senza estensione".
    """
    if episodio is None:
        return "episodio assente nella lista AnimeWorld (numerazione diversa?)"
    try:
        servers = list(episodio.links)
    except Exception as e:
        return f"lettura server fallita ({type(e).__name__}: {e})"
    if not servers:
        return "AnimeWorld non ha restituito alcun server per l'episodio"
    url = getattr(servers[0], "link", None)
    if not url:
        return "il server non ha restituito un URL"
    if "animeworld.ac" in url:
        return "il server ha restituito una pagina web invece del file"
    if not _RE_VIDEO.search(url):
        return f"URL senza estensione video: {url[:80]}"
    return "nessun mirror valido"


def lista_episodi(link):
    """Restituisce i numeri di episodio disponibili, come stringhe (es. ['1', '2', ...])."""
    return [str(ep.number) for ep in episodi(link)]


def link_episodio(link, numero_episodio):
    """Risolve l'URL `.mp4` diretto di un episodio (primo mirror disponibile)."""
    for ep in episodi(link):
        if str(ep.number) == str(numero_episodio):
            return link_mp4(ep)
    return None
