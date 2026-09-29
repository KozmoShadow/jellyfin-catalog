from pathlib import Path
import shutil
import paths
import requests


def _titolo_pulito(titolo):
    """Rimuove i caratteri non validi per i nomi di file/cartelle."""
    return "".join(c for c in titolo if c.isalnum() or c in (' ', '-', '_')).strip()


def _nome_cartella_film(tmdb_id, titolo, anno):
    """Nome cartella film coerente tra creazione, verifica e rimozione."""
    titolo_pulito = _titolo_pulito(titolo)
    if anno:
        return f"[{tmdb_id}] - {titolo_pulito} ({anno})"
    return f"[{tmdb_id}] - {titolo_pulito}"


def crea_file_serie(tmdb_id, nome_serie, stagione_num, episodio_num, video_link, audio_link):
    """Crea la struttura di cartelle e i file .m3u8 / .strm per un episodio di una serie."""
    nome_pulito = _titolo_pulito(nome_serie)

    # 1. Percorsi cartelle (es: /Media/Serie TV/1234 - Breaking Bad/Stagione 1/)
    cartella_serie = Path(paths.series_path) / f"{tmdb_id} - {nome_pulito}"
    cartella_stagione = cartella_serie / f"Stagione {stagione_num}"
    cartella_stagione.mkdir(parents=True, exist_ok=True)

    # Nomi file basati su numero episodio (es: S01E01)
    ep_str = f"S{int(stagione_num):02d}E{int(episodio_num):02d}"

    # 2. File .m3u8 con i link estratti (Jellyfin/FFmpeg lo legge come playlist)
    percorso_m3u8 = cartella_stagione / f"{nome_pulito} - {ep_str}.m3u8"
    with open(percorso_m3u8, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        if video_link:
            f.write(f'#EXT-X-STREAM-INF:BANDWIDTH=8000000,AUDIO="audio"\n{video_link}\n')
        if audio_link:
            f.write(f'#EXT-X-MEDIA:TYPE=AUDIO,GROUP-ID="audio",NAME="Italiano",DEFAULT=YES,URI="{audio_link}"\n')

    # 3. File .strm che punta al .m3u8 servito dal server locale
    percorso_strm = cartella_stagione / f"{nome_pulito} - {ep_str}.strm"
    with open(percorso_strm, "w", encoding="utf-8") as f:
        f.write(
            f"http://localhost:8008/{tmdb_id} - {nome_pulito}/Stagione {stagione_num}/"
            f"{nome_pulito} - {ep_str}.m3u8"
        )

    print(f"Generato con successo: {ep_str} per la serie '{nome_serie}'")


def crea_cartella_film(tmdb_id, titolo_film, anno_uscita, video_link, audio_link):
    """Crea la cartella per il film seguendo la convenzione [TMDB_ID] - [Titolo] (Anno)."""
    titolo_pulito = _titolo_pulito(titolo_film)
    nome_cartella = _nome_cartella_film(tmdb_id, titolo_film, anno_uscita)

    percorso_film = Path(paths.films_path) / nome_cartella
    percorso_film.mkdir(parents=True, exist_ok=True)

    # File .m3u8
    percorso_m3u8 = percorso_film / f"{titolo_pulito} ({anno_uscita}).m3u8"
    with open(percorso_m3u8, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        if video_link:
            f.write(f'#EXT-X-STREAM-INF:BANDWIDTH=8000000,AUDIO="audio"\n{video_link}\n')
        if audio_link:
            f.write(f'#EXT-X-MEDIA:TYPE=AUDIO,GROUP-ID="audio",NAME="Italiano",DEFAULT=YES,URI="{audio_link}"\n')

    # File .strm
    percorso_strm = percorso_film / f"{titolo_pulito} ({anno_uscita}).strm"
    with open(percorso_strm, "w", encoding="utf-8") as f:
        f.write(f"http://localhost:8001/{nome_cartella}/{titolo_pulito} ({anno_uscita}).m3u8")

    print(f"Generato con successo: {titolo_film} ({anno_uscita if anno_uscita else 'N/A'})")


def verifica_presenza_jellyfin(content_type, tmdb_id, titolo, anno):
    """Verifica se il contenuto è già presente in libreria (stessa convenzione della creazione)."""
    if content_type == "movie":
        titolo_pulito = _titolo_pulito(titolo)
        nome_cartella = _nome_cartella_film(tmdb_id, titolo, anno)
        file_path = Path(paths.films_path) / nome_cartella / f"{titolo_pulito} ({anno}).strm"
        return file_path.exists()
    else:
        # Schema serie coerente con crea_file_serie: "{tmdb_id} - {titolo}"
        dir_path = Path(paths.series_path) / f"{tmdb_id} - {_titolo_pulito(titolo)}"
        return dir_path.exists()


def rimuovi_cartella_film(tmdb_id, titolo_film, anno_uscita):
    """Rimuove l'intera cartella del film (con .strm e .m3u8)."""
    nome_cartella = _nome_cartella_film(tmdb_id, titolo_film, anno_uscita)
    percorso_film = Path(paths.films_path) / nome_cartella

    if percorso_film.exists() and percorso_film.is_dir():
        shutil.rmtree(percorso_film)
        print(f"Rimosso con successo dal disco: {titolo_film}")


def rimuovi_cartella_serie(tmdb_id, nome_serie):
    """Rimuove l'intera cartella della serie (con tutte le stagioni/episodi)."""
    cartella_serie = Path(paths.series_path) / f"{tmdb_id} - {_titolo_pulito(nome_serie)}"

    if cartella_serie.exists() and cartella_serie.is_dir():
        shutil.rmtree(cartella_serie)
        print(f"Rimosso con successo dal disco: {nome_serie}")


def _percorso_episodio(tmdb_id, nome_serie, stagione_num, episodio_num):
    nome_pulito = _titolo_pulito(nome_serie)
    ep_str = f"S{int(stagione_num):02d}E{int(episodio_num):02d}"
    cartella_stagione = (
        Path(paths.series_path) / f"{tmdb_id} - {nome_pulito}" / f"Stagione {stagione_num}"
    )
    return cartella_stagione / f"{nome_pulito} - {ep_str}"


def verifica_presenza_episodio(tmdb_id, nome_serie, stagione_num, episodio_num):
    """Verifica se il singolo episodio è già presente in libreria."""
    return _percorso_episodio(tmdb_id, nome_serie, stagione_num, episodio_num).with_suffix(".strm").exists()


def rimuovi_episodio(tmdb_id, nome_serie, stagione_num, episodio_num):
    """Rimuove i file .strm e .m3u8 del singolo episodio."""
    base = _percorso_episodio(tmdb_id, nome_serie, stagione_num, episodio_num)
    for ext in (".strm", ".m3u8"):
        percorso = base.with_suffix(ext)
        if percorso.exists():
            percorso.unlink()
            print(f"Rimosso: {percorso.name}")


def _cartella_stagione(tmdb_id, nome_serie, stagione_num):
    return (
        Path(paths.series_path)
        / f"{tmdb_id} - {_titolo_pulito(nome_serie)}"
        / f"Stagione {stagione_num}"
    )


def verifica_presenza_stagione(tmdb_id, nome_serie, stagione_num, episodi):
    """Restituisce la lista dei numeri di episodio già presenti per una stagione."""
    return [
        n for n in episodi
        if verifica_presenza_episodio(tmdb_id, nome_serie, stagione_num, n)
    ]


def rimuovi_stagione(tmdb_id, nome_serie, stagione_num):
    """Rimuove l'intera cartella di una stagione.

    Se non restano altre stagioni, elimina anche la cartella della serie,
    così `verifica_presenza_jellyfin` ("serie in libreria") resta coerente.
    """
    cartella_stagione = _cartella_stagione(tmdb_id, nome_serie, stagione_num)
    if cartella_stagione.exists() and cartella_stagione.is_dir():
        shutil.rmtree(cartella_stagione)
        print(f"Rimosso con successo dal disco: Stagione {stagione_num} di '{nome_serie}'")

    cartella_serie = Path(paths.series_path) / f"{tmdb_id} - {_titolo_pulito(nome_serie)}"
    if cartella_serie.exists() and not any(p.is_dir() for p in cartella_serie.iterdir()):
        shutil.rmtree(cartella_serie)
        print(f"Rimosso con successo dal disco: '{nome_serie}' (nessuna stagione rimasta)")


def _percorso_episodio_anime(titolo, stagione_num, episodio_num):
    nome_pulito = _titolo_pulito(titolo)
    ep_str = f"S{int(stagione_num):02d}E{int(episodio_num):02d}"
    cartella_stagione = (
        Path(paths.anime_path) / nome_pulito / f"Season {int(stagione_num):02d}"
    )
    return cartella_stagione / f"{nome_pulito} - {ep_str}"


def crea_file_anime(titolo, stagione_num, episodio_num, link_stream):
    """Crea il file .strm di un episodio anime puntando all'URL mp4 diretto."""
    nome_pulito = _titolo_pulito(titolo)
    base = _percorso_episodio_anime(titolo, stagione_num, episodio_num)
    base.parent.mkdir(parents=True, exist_ok=True)

    with open(base.with_suffix(".strm"), "w", encoding="utf-8") as f:
        f.write(link_stream + "\n")

    print(f"Generato con successo: {base.name}.strm per l'anime '{titolo}'")


def verifica_presenza_episodio_anime(titolo, stagione_num, episodio_num):
    """Verifica se il singolo episodio anime è già presente in libreria."""
    return _percorso_episodio_anime(titolo, stagione_num, episodio_num).with_suffix(".strm").exists()


def verifica_presenza_stagione_anime(titolo, stagione_num, episodi):
    """Restituisce i numeri di episodio già presenti per una stagione anime."""
    return [
        n for n in episodi
        if verifica_presenza_episodio_anime(titolo, stagione_num, n)
    ]


def rimuovi_episodio_anime(titolo, stagione_num, episodio_num):
    """Rimuove il file .strm del singolo episodio anime."""
    percorso = _percorso_episodio_anime(titolo, stagione_num, episodio_num).with_suffix(".strm")
    if percorso.exists():
        percorso.unlink()
        print(f"Rimosso: {percorso.name}")


def rimuovi_stagione_anime(titolo, stagione_num):
    """Rimuove l'intera cartella di una stagione anime.

    Se non restano altre stagioni, elimina anche la cartella della serie.
    """
    nome_pulito = _titolo_pulito(titolo)
    cartella_stagione = Path(paths.anime_path) / nome_pulito / f"Season {int(stagione_num):02d}"
    if cartella_stagione.exists() and cartella_stagione.is_dir():
        shutil.rmtree(cartella_stagione)
        print(f"Rimosso con successo dal disco: Season {int(stagione_num):02d} di '{titolo}'")

    cartella_serie = Path(paths.anime_path) / nome_pulito
    if cartella_serie.exists() and not any(p.is_dir() for p in cartella_serie.iterdir()):
        shutil.rmtree(cartella_serie)
        print(f"Rimosso con successo dal disco: '{titolo}' (nessuna stagione rimasta)")


def rinfresca_libreria_jellyfin():
    """Invia un comando di scansione/refresh globale o mirato alle librerie di Jellyfin."""
    try:
        url = f"{paths.JELLYFIN_URL}/Library/Refresh"
        headers = {
            "Authorization": f"MediaBrowser Token=\"{paths.JELLYFIN_API_KEY}\""
        }
        response = requests.post(url, headers=headers)
        if response.status_code == 204:  # 204 No Content è la risposta standard di successo
            return True
        else:
            print(f"Errore refresh Jellyfin: {response.status_code}")
            return False
    except Exception as e:
        print(f"Eccezione durante il refresh di Jellyfin: {e}")
        return False
