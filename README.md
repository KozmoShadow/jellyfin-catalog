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
   ```

3. Avvia la dashboard dalla cartella `dashboard/`:

   ```bash
   streamlit run dashboard/Home.py
   ```

## Note

- Il file `.env` non è versionato: non committare mai le chiavi API.
- I file `.m3u8` / `.strm` vengono scritti nelle cartelle definite in `paths.py`.
- Le pagine **Film** e **Serie TV** usano l'endpoint `/discover` di TMDB con
  filtri per genere, anno, voto e ordinamento.
- La gestione Jellyfin è per contenuto: un film è un singolo file, mentre per le
  serie si aggiungono/rimuovono i **singoli episodi** (`S01E01`) nella cartella
  `Stagione N`.
