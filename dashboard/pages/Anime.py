import sys
from pathlib import Path

# Aggiunge la radice del progetto al path per importare i moduli di backend
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st

import anime_api
import anilist
from ui_components import (
    mostra_griglia_anime,
    mostra_griglia_scoperta_anime,
    render_scheda_anime,
)

st.set_page_config(
    page_title="Catalogo Anime",
    page_icon="⛩️",
    layout="wide",
)

# ==========================================
# 📄 SCHEDA DETTAGLI (SE UN ANIME È STATO CLICCATO)
# ==========================================
link_anime = st.query_params.get("link")
if link_anime:
    if st.button("⬅️ Torna al catalogo"):
        st.query_params.clear()
        st.rerun()

    render_scheda_anime(
        link_anime,
        st.query_params.get("titolo", ""),
        st.query_params.get("copertina", ""),
    )
    st.stop()

# ==========================================
# ⛩️ CATALOGO ANIME
# ==========================================
st.title("⛩️ Catalogo Anime")

# Un titolo può arrivare dalla barra di ricerca della Home o da una card AniList
# (es. /Anime?cerca=Jujutsu Kaisen). In quel caso la pagina cerca da sola su
# AnimeWorld, così il flusso "scopri su AniList → scarica" ha un solo click.
query_iniziale = st.query_params.get("cerca", "")

ORDINAMENTI = {
    "Popolarità": "POPULARITY_DESC",
    "Voto medio": "SCORE_DESC",
    "Più recenti": "START_DATE_DESC",
    "Più vecchi": "START_DATE_ASC",
}

st.write(
    "Cerca un anime per titolo, oppure esplora i **popolari** e usa i filtri. "
    "I link sono già `.mp4` diretti."
)

query = st.text_input(
    "🔍 Cerca un anime...",
    value=query_iniziale,
    placeholder="Es. Jujutsu Kaisen, One Piece...",
)

# --- Modalità: ricerca testuale oppure esplorazione con filtri ---
if query:
    with st.spinner("Ricerca su AnimeWorld..."):
        risultati = anime_api.cerca_anime(query)

    if risultati:
        st.caption(f"Trovati {len(risultati)} risultati su AnimeWorld")
        mostra_griglia_anime(risultati)
    else:
        st.info("Nessun risultato su AnimeWorld. Prova con un altro titolo.")
    st.stop()

# --- Filtri nella sidebar (solo in modalità esplorazione) ---
if "anime_generi" not in st.session_state:
    st.session_state.anime_generi = anilist.get_generi()
mappa_generi = st.session_state.anime_generi

with st.sidebar:
    st.header("🔎 Filtri anime")

    genere_scelto = st.selectbox("Genere", ["Tutti"] + mappa_generi)

    anno_corrente = 2026
    anni = ["Tutti"] + list(range(anno_corrente, 1959, -1))
    anno_scelto = st.selectbox("Anno di uscita", anni)

    voto_min = st.slider("Voto minimo", 0.0, 10.0, 0.0, step=0.5)

    ordinamento_scelto = st.selectbox("Ordina per", list(ORDINAMENTI.keys()))

# --- Paginazione: torna a pagina 1 quando cambiano i filtri ---
filtri_correnti = (genere_scelto, anno_scelto, voto_min, ordinamento_scelto)
if st.session_state.get("anime_filtri") != filtri_correnti:
    st.session_state.anime_filtri = filtri_correnti
    st.session_state.anime_page = 1
if "anime_page" not in st.session_state:
    st.session_state.anime_page = 1

risultati, ultima_pagina = anilist.discover(
    genere=genere_scelto if genere_scelto != "Tutti" else None,
    anno=anno_scelto if anno_scelto != "Tutti" else None,
    voto_min=voto_min if voto_min > 0 else None,
    sort_by=ORDINAMENTI[ordinamento_scelto],
    page=st.session_state.anime_page,
)

# AniList limita a 5000 risultati totali: teniamo la paginazione ragionevole
ultima_pagina = min(ultima_pagina, 100)

etichetta_filtri = []
if genere_scelto != "Tutti":
    etichetta_filtri.append(genere_scelto)
if anno_scelto != "Tutti":
    etichetta_filtri.append(str(anno_scelto))
if voto_min > 0:
    etichetta_filtri.append(f"⭐ {voto_min:g}+")
suffisso = f" — {', '.join(etichetta_filtri)}" if etichetta_filtri else ""

if not etichetta_filtri and st.session_state.anime_page == 1:
    st.subheader("🔥 Anime Popolari")
else:
    st.subheader(
        f"Risultati{suffisso} (Pagina {st.session_state.anime_page} di {ultima_pagina})"
    )

st.caption("Clicca una card per cercarla su AnimeWorld e scaricarla.")

mostra_griglia_scoperta_anime(risultati)

if ultima_pagina > 1:
    col_prec, col_info, col_succ = st.columns([1, 2, 1])

    with col_prec:
        if st.session_state.anime_page > 1:
            if st.button("⬅️ Precedente"):
                st.session_state.anime_page -= 1
                st.rerun()

    with col_info:
        st.markdown(
            f"<div style='text-align: center; margin-top: 5px;'>Pagina "
            f"<b>{st.session_state.anime_page}</b> di <b>{ultima_pagina}</b></div>",
            unsafe_allow_html=True,
        )

    with col_succ:
        if st.session_state.anime_page < ultima_pagina:
            if st.button("Successivo ➡️"):
                st.session_state.anime_page += 1
                st.rerun()
