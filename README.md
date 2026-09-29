# VixSrc Media Center

Catalogo personale per Jellyfin: recupera i metadati da TMDB e genera
automaticamente file `.m3u8` / `.strm` per la libreria locale, tramite una
dashboard Streamlit.

## Struttura

```
.
├── dashboard/
│   ├── Home.py            # Home: ricerca + slider film/serie + scheda dettagli
│   └── pages/
│       ├── Film.py        # Catalogo film con filtri
│       └── Serie TV.py    # Catalogo serie TV con filtri
├── config.py              # Carica i segreti dal file .env
├── estrattore.py          # Estrazione dei flussi video/audio (Playwright)
├── file_manager.py        # Creazione/rimozione file .m3u8/.strm e refresh Jellyfin
├── paths.py               # Percorsi di libreria e configurazione Jellyfin
├── tmdb.py                # Client TMDB (ricerca, popolari, discover, dettagli)
├── ui_components.py       # Componenti UI condivisi (griglia + scheda dettagli)
├── requirements.txt
└── .env.example           # Template per le variabili d'ambiente
```

## Setup

1. Installa le dipendenze:

   ```bash
   pip install -r requirements.txt
   ```

2. Copia `.env.example` in `.env` e inserisci le tue chiavi:

   ```bash
   cp .env.example .env
   ```

   ```
   TMDB_API_KEY=...
   JELLYFIN_URL=http://localhost:8096
   JELLYFIN_API_KEY=...
   SERIES_PATH=C:/percorso/verso/Serie
   FILMS_PATH=C:/percorso/verso/Film
   ANIME_PATH=C:/percorso/verso/Anime
   ```

   `SERIES_PATH`, `FILMS_PATH` e `ANIME_PATH` sono opzionali: se li ometti, il
   catalogo viene salvato nelle cartelle `Serie`, `Film` e `Anime` dentro il
   progetto.

3. Avvia la dashboard dalla cartella `dashboard/`:

   ```bash
   streamlit run dashboard/Home.py
   ```

## Note

- Il file `.env` non è versionato: non committare mai le chiavi API.
- I file `.m3u8` / `.strm` vengono scritti nelle cartelle definite da `SERIES_PATH`,
  `FILMS_PATH` e `ANIME_PATH` nel `.env` (in `paths.py` ci sono solo i default).
- Le pagine **Film** e **Serie TV** usano l'endpoint `/discover` di TMDB con
  filtri per genere, anno, voto e ordinamento.
- La **Home** mostra tre slider orizzontali (Film, Serie TV e Anime Popolari).
  Lo slider anime usa AniList come le altre sezioni anime; cliccando una card
  si apre la ricerca corrispondente su AnimeWorld.
- La pagina **Anime** ha due modalità: ricerca per titolo direttamente su AnimeWorld,
  oppure esplorazione con **filtri** (genere, anno, voto, ordinamento) e sezione
  **popolari**. Questi ultimi dati vengono da **AniList** (GraphQL, nessuna chiave
  API), perché la libreria `animeworld` offre solo la ricerca.
  I file `.strm` puntano agli URL `.mp4` diretti di AnimeWorld. Cliccando una card
  AniList si cerca automaticamente l'anime su AnimeWorld, così il download resta
  a un click di distanza.
  Ogni anime è una serie con una sola stagione (`Season 01`), salvo importare
  stagioni separate nella stessa cartella indicando il numero desiderato.
- La gestione Jellyfin è per contenuto: un film è un singolo file, mentre per le
  serie si aggiungono/rimuovono **intere stagioni** (`Stagione N`), con i singoli
  episodi (`S01E01`) disponibili come opzione.
