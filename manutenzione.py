"""Manutenzione del catalogo: verifica e rigenerazione dei link nei file `.m3u8` / `.strm`.

I file di film e serie contengono URL firmati di vixsrc che prima o poi scadono;
quelli degli anime contengono URL `.mp4` dei mirror AnimeWorld. Questo modulo
scansiona le librerie, controlla che i link rispondano ancora e, dove possibile,
li rigenera.
"""

import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

import anime_api
import paths
from estrattore import estrai_flussi
from file_manager import (
    _titolo_pulito,
    crea_cartella_film,
    crea_file_serie,
    crea_file_anime,
    salva_origine_stagione_anime,
)

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

_URL_RE = re.compile(r"https?://[^\s\"']+")

_RE_FILM_DIR = re.compile(r"^\[(?P<id>\d+)\]\s*-\s*(?P<titolo>.+?)(?:\s*\((?P<anno>\d{4})\))?$")
_RE_SERIE_DIR = re.compile(r"^(?P<id>\d+)\s*-\s*(?P<nome>.+)$")
_RE_STAGIONE = re.compile(r"^(?:Stagione|Season)\s+(?P<num>\d+)$", re.IGNORECASE)
_RE_EPISODIO = re.compile(r"S(?P<s>\d{1,2})E(?P<e>\d{1,3})\.(?:m3u8|strm)$", re.IGNORECASE)


# ==========================================
# SCANSIONE
# ==========================================

def _estrai_url(percorso):
    """Restituisce gli URL contenuti in un file `.m3u8` o `.strm`."""
    percorso = Path(percorso)
    if not percorso.exists():
        return []
    testo = percorso.read_text(encoding="utf-8", errors="ignore")
    return _URL_RE.findall(testo)


def _voce(tipo, titolo, cartella, file_media, strm, file_verifica, **extra):
    voce = {
        "tipo": tipo,
        "titolo": titolo,
        "cartella": str(cartella),
        "file_media": str(file_media) if file_media else None,
        "file_strm": str(strm) if strm else None,
        # File da cui leggere i link da testare: il .m3u8 per film/serie (contiene
        # gli URL vixsrc), lo .strm per gli anime (contiene l'mp4 diretto).
        "file_verifica": str(file_verifica) if file_verifica else None,
        "links": [],
        "ok": None,
        "stato": "da verificare",
    }
    voce.update(extra)
    return voce


def scansiona_film():
    """Scansiona solo la libreria film."""
    voci = []
    radice = Path(paths.films_path)
    if not radice.exists():
        return voci

    for cartella in sorted(p for p in radice.iterdir() if p.is_dir()):
        match = _RE_FILM_DIR.match(cartella.name)
        if not match:
            continue
        m3u8 = next(cartella.glob("*.m3u8"), None)
        strm = next(cartella.glob("*.strm"), None)
        if not m3u8 and not strm:
            continue
        voci.append(_voce(
            "film", match.group("titolo"), cartella, m3u8, strm, m3u8 or strm,
            tmdb_id=int(match.group("id")),
            anno=match.group("anno"),
            stagione=None,
            episodio=None,
        ))
    return voci


def _scansiona_episodi(tipo, radice, con_id):
    """Scansiona serie TV (con id TMDB) o anime (senza id, cartella = titolo)."""
    voci = []
    radice = Path(radice)
    if not radice.exists():
        return voci

    for cartella in sorted(p for p in radice.iterdir() if p.is_dir()):
        tmdb_id, titolo = None, cartella.name
        if con_id:
            match = _RE_SERIE_DIR.match(cartella.name)
            if not match:
                continue
            tmdb_id, titolo = int(match.group("id")), match.group("nome")

        for stagione_dir in sorted(p for p in cartella.iterdir() if p.is_dir()):
            match_stag = _RE_STAGIONE.match(stagione_dir.name)
            if not match_stag:
                continue
            stagione = int(match_stag.group("num"))

            for file_media in sorted(stagione_dir.glob("*.m3u8")):
                match_ep = _RE_EPISODIO.search(file_media.name)
                if not match_ep:
                    continue
                strm = file_media.with_suffix(".strm")
                voci.append(_voce(
                    tipo, titolo, cartella, file_media, strm if strm.exists() else None,
                    file_media,
                    tmdb_id=tmdb_id,
                    anno=None,
                    stagione=stagione,
                    episodio=int(match_ep.group("e")),
                ))

            # Gli anime salvano solo il .strm, senza .m3u8
            if not con_id:
                for strm in sorted(stagione_dir.glob("*.strm")):
                    match_ep = _RE_EPISODIO.search(strm.name)
                    if not match_ep:
                        continue
                    voci.append(_voce(
                        tipo, titolo, cartella, strm, strm, strm,
                        tmdb_id=None,
                        anno=None,
                        stagione=stagione,
                        episodio=int(match_ep.group("e")),
                    ))
    return voci


def scansiona_serie():
    """Scansiona solo la libreria serie TV."""
    return _scansiona_episodi("serie", paths.series_path, con_id=True)


def scansiona_anime():
    """Scansiona solo la libreria anime."""
    return _scansiona_episodi("anime", paths.anime_path, con_id=False)


def scansiona_catalogo():
    """Restituisce la lista di tutti i file di catalogo trovati nelle tre librerie."""
    return scansiona_film() + scansiona_serie() + scansiona_anime()


# ==========================================
# VERIFICA DEI LINK
# ==========================================

def verifica_url(url, timeout=15):
    """Controlla se un URL risponde ancora: (ok, status_code).

    Usa una GET con `Range` (alcuni CDN non supportano HEAD) e uno User-Agent
    da browser. Qualsiasi risposta < 400 è considerata valida.
    """
    headers = {"User-Agent": _USER_AGENT, "Range": "bytes=0-1"}
    try:
        risposta = requests.get(url, headers=headers, timeout=timeout, stream=True)
        ok = risposta.status_code < 400
        status = risposta.status_code
        risposta.close()
        return ok, status
    except requests.RequestException as e:
        return False, type(e).__name__


def verifica_voci(voci, max_workers=6, progress_cb=None):
    """Verifica in parallelo i link di ogni voce, aggiornando `links`, `ok` e `stato`.

    progress_cb(fatti, totali) viene chiamato a ogni voce completata.
    """
    totale = len(voci)
    fatti = 0

    def _verifica_voce(voce):
        links = []
        for percorso in filter(None, [voce["file_verifica"]]):
            for url in _estrai_url(percorso):
                ok, status = verifica_url(url)
                links.append({"url": url, "ok": ok, "status": status})
        return links

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        for voce, links in zip(voci, pool.map(_verifica_voce, voci)):
            voce["links"] = links
            voce["ok"] = bool(links) and all(link["ok"] for link in links)
            voce["stato"] = "ok" if voce["ok"] else ("rotto" if links else "vuoto")
            fatti += 1
            if progress_cb:
                progress_cb(fatti, totale)

    return voci


# ==========================================
# RIGENERAZIONE
# ==========================================

def rigenera_film(voce):
    """Re-estrae i flussi da vixsrc e riscrive il file del film. Ritorna (ok, messaggio)."""
    try:
        video, audio = estrai_flussi(f"https://vixsrc.to/movie/{voce['tmdb_id']}?lang=it")
        if not video:
            return False, "nessun flusso video trovato"
        crea_cartella_film(voce["tmdb_id"], voce["titolo"], voce["anno"], video, audio)
        return True, "rigenerato"
    except Exception as e:
        return False, str(e)


def rigenera_episodio_serie(voce):
    """Re-estrae un singolo episodio di serie da vixsrc. Ritorna (ok, messaggio)."""
    try:
        url = f"https://vixsrc.to/tv/{voce['tmdb_id']}/{voce['stagione']}/{voce['episodio']}?lang=it"
        video, audio = estrai_flussi(url)
        if not video:
            return False, "nessun flusso video trovato"
        crea_file_serie(
            voce["tmdb_id"], voce["titolo"], voce["stagione"], voce["episodio"], video, audio
        )
        return True, "rigenerato"
    except Exception as e:
        return False, str(e)


def _origine_per_voci(voci):
    """Ricava la pagina AnimeWorld della stagione dal file `.animeworld` accanto ai file.

    Tutte le voci del gruppo stanno nella stessa cartella di stagione, quindi basta
    la prima. Ritorna None se non c'è (stagioni create prima di questa funzione).
    """
    from file_manager import NOME_FILE_ORIGINE
    for voce in voci:
        riferimento = voce.get("file_media") or voce.get("file_strm")
        if not riferimento:
            continue
        percorso = Path(riferimento).parent / NOME_FILE_ORIGINE
        if percorso.exists():
            contenuto = percorso.read_text(encoding="utf-8").strip()
            if contenuto:
                # Normalizza a pagina anime: file scritti a mano possono contenere
                # anche la parte con l'id dell'episodio.
                return anime_api.link_pagina_anime(contenuto)
    return None


def rigenera_episodi_anime(titolo, voci, link_anime=None):
    """Re-risolve da AnimeWorld gli episodi rotti di un anime.

    Usa la pagina AnimeWorld salvata per la stagione (`.animeworld`), così con più
    stagioni si ricaricano gli episodi giusti; se manca, ripiega sulla ricerca per
    titolo. Riscrive i `.strm` dei soli episodi passati. Ritorna (ok, falliti, messaggio).
    """
    link_anime = link_anime or _origine_per_voci(voci)

    if link_anime:
        try:
            episodi = anime_api.episodi(link_anime)
        except Exception as e:
            return 0, len(voci), f"lettura episodi fallita: {e}"
    else:
        # Fallback: nessun file di origine, si cerca per titolo (ambiguo con più stagioni)
        try:
            risultati = anime_api.cerca_anime_tollerante(titolo)
        except Exception as e:
            return 0, len(voci), f"ricerca AnimeWorld fallita: {e}"

        if not risultati:
            return 0, len(voci), "anime non trovato su AnimeWorld"

        migliore = anime_api.miglior_risultato(titolo, risultati)

        try:
            episodi = anime_api.episodi(migliore["link"])
        except Exception as e:
            return 0, len(voci), f"lettura episodi fallita: {e}"

        # Ricorda l'origine trovata, così la prossima volta è affidabile quanto
        # una stagione importata con questa versione del codice.
        link_anime = migliore.get("link")

    mappa = {str(ep.number): ep for ep in episodi}
    ok = falliti = 0
    for voce in voci:
        episodio = mappa.get(str(voce["episodio"]))
        try:
            link = anime_api.link_mp4(episodio) if episodio else None
        except Exception:
            # Un server può sollevare durante `episodio.links`: conta come fallito
            # invece di far esplodere l'intera rigenerazione.
            link = None
        if link:
            crea_file_anime(titolo, voce["stagione"], voce["episodio"], link)
            ok += 1
        else:
            falliti += 1

    # Salva l'origine ritrovata (se mancava) perché le prossime rigenerazioni
    # non dipendano più dalla ricerca per titolo.
    if ok and link_anime:
        for voce in voci:
            try:
                salva_origine_stagione_anime(
                    titolo, voce["stagione"], anime_api.link_pagina_anime(link_anime)
                )
                break
            except Exception:
                pass
    return ok, falliti, "rigenerato"
