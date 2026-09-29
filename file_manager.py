from pathlib import Path
import shutil
import paths
import requests

def crea_file_serie(tmdb_id, nome_serie, stagione_num, episodio_num, video_link, audio_link):
    """
    Crea la struttura di cartelle e i file .m3u8 / .strm per Jellyfin.
    """
    # 1. Definisci i percorsi delle cartelle (es: /Media/Serie TV/Breaking Bad/Stagione 1/)
    cartella_serie = Path(paths.series_path) / f"{tmdb_id} - {nome_serie}"
    cartella_stagione = cartella_serie / f"Stagione {stagione_num}"
    
    # Crea le cartelle se non esistono
    cartella_stagione.mkdir(parents=True, exist_ok=True)
    
    # Nomi dei file basati sul numero episodio (es: S01E01)
    ep_str = f"S{int(stagione_num):02d}E{int(episodio_num):02d}"
    
    # 2. Crea il file .m3u8 con i link estratti
    # (Jellyfin/FFmpeg lo legge come playlist o flusso)
    percorso_m3u8 = cartella_stagione / f"{nome_serie} - {ep_str}.m3u8"
    with open(percorso_m3u8, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        if video_link:
            f.write(f'#EXT-X-STREAM-INF:BANDWIDTH=8000000,AUDIO="audio"\n{video_link}\n')
        if audio_link:
            f.write(f'#EXT-X-MEDIA:TYPE=AUDIO,GROUP-ID="audio",NAME="Italiano",DEFAULT=YES,URI="{audio_link}"\n')
        
    # 3. Crea il file .strm che punta al file .m3u8 (o direttamente al link)
    percorso_strm = cartella_stagione / f"{nome_serie} - {ep_str}.strm"
    with open(percorso_strm, "w", encoding="utf-8") as f:
        # Qui puoi decidere se mettere il percorso locale del .m3u8 o il link diretto
        f.write(str("http://localhost:8008/"+str(tmdb_id)+" - "+str(nome_serie)+"/Stagione "+str(stagione_num)+"/"+str(nome_serie)+" - "+str(ep_str)+".m3u8"))
        
    print(f"Generato con successo: {ep_str} per la serie '{nome_serie}'")

def crea_cartella_film(tmdb_id, titolo_film, anno_uscita, video_link, audio_link):
    """
    Crea la cartella per il film seguendo la convenzione [TMDB_ID] - [Titolo] (Anno)
    sfruttando i path centralizzati.
    """
    # Pulisce il titolo da caratteri non validi per i nomi delle cartelle
    titolo_pulito = "".join(c for c in titolo_film if c.isalnum() or c in (' ', '-', '_')).strip()
    
    # Costruisce il nome della cartella includendo l'anno se presente
    if anno_uscita:
        nome_cartella = f"[{tmdb_id}] - {titolo_pulito} ({anno_uscita})"
    else:
        nome_cartella = f"[{tmdb_id}] - {titolo_pulito}"

    # Percorso radice dei film preso da paths.py
    percorso_base_film = Path(paths.films_path)
    percorso_film = percorso_base_film / nome_cartella
    
    # Crea la cartella se non esiste
    percorso_film.mkdir(parents=True, exist_ok=True)
    
    # Crea e salva il file .m3u8 all'interno della cartella del film
    percorso_m3u8 = percorso_film / f"{titolo_pulito} ({anno_uscita}).m3u8"
    
    with open(percorso_m3u8, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        if video_link:
            f.write(f'#EXT-X-STREAM-INF:BANDWIDTH=8000000,AUDIO="audio"\n{video_link}\n')
        if audio_link:
            f.write(f'#EXT-X-MEDIA:TYPE=AUDIO,GROUP-ID="audio",NAME="Italiano",DEFAULT=YES,URI="{audio_link}"\n')

    # Crea e salva il file .strm
    percorso_strm = percorso_film / f"{titolo_pulito} ({anno_uscita}).strm"
    with open(percorso_strm, "w", encoding="utf-8") as f:
        f.write(f"http://localhost:8001/{nome_cartella}/{titolo_pulito} ({anno_uscita}).m3u8")
            
    print(f"Generato con successo: {titolo_film} ({anno_uscita if anno_uscita else 'N/A'})")

def verifica_presenza_jellyfin(content_type, tmdb_id, titolo, anno):
    # Puoi usare il tmdb_id nel nome del file o della cartella per renderlo unico al 100%
    # Esempio: "Titolo (Anno) [tmdb-12345]"
    safe_title = "".join([c for c in titolo if c.isalnum() or c in (' ', '-', '_')]).strip()
    
    if content_type == "movie":
        # Se nel tuo file manager salvi i file includendo l'ID o usando una struttura basata sull'ID:
        file_path = Path(paths.films_path) / f"[{tmdb_id}] - {safe_title} ({anno})" / f"{safe_title} ({anno}).strm"
        return file_path.exists()
    else:
        dir_path = Path(paths.series_path) / f"{safe_title} ({anno}) [{tmdb_id}]"
        return dir_path.exists()

def rimuovi_cartella_film(tmdb_id, titolo_film, anno_uscita):
    """
    Rimuove l'intera cartella del film basandosi sul TMDB ID e sulla struttura creata.
    """
    titolo_pulito = "".join(c for c in titolo_film if c.isalnum() or c in (' ', '-', '_')).strip()
    
    if anno_uscita:
        nome_cartella = f"[{tmdb_id}] - {titolo_pulito} ({anno_uscita})"
    else:
        nome_cartella = f"[{tmdb_id}] - {titolo_pulito}"

    percorso_base_film = Path(paths.films_path)
    percorso_film = percorso_base_film / nome_cartella
    
    # Se la cartella esiste, la elimina insieme a tutto il suo contenuto (.strm e .m3u8)
    if percorso_film.exists() and percorso_film.is_dir():
        shutil.rmtree(percorso_film)
        print(f"Rimosso con successo dal disco: {titolo_film}")

def rinfresca_libreria_jellyfin():
    """
    Invia un comando di scansione/refresh globale o mirato alle librerie di Jellyfin.
    """
    try:
        url = f"{paths.JELLYFIN_URL}/Library/Refresh"
        headers = {
            "Authorization": f"MediaBrowser Token=\"{paths.JELLYFIN_API_KEY}\""
        }
        response = requests.post(url, headers=headers)
        if response.status_code == 204: # 204 No Content è la risposta standard di successo di Jellyfin
            return True
        else:
            print(f"Errore refresh Jellyfin: {response.status_code}")
            return False
    except Exception as e:
        print(f"Eccezione durante il refresh di Jellyfin: {e}")
        return False