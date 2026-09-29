import sys
from pathlib import Path

# Aggiunge la radice del progetto al path per importare i moduli di backend
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st

import tmdb
import anilist
from ui_components import (
    mostra_griglia,
    render_scheda_dettagli,
    mostra_slider_orizzontale,
    card_da_tmdb,
    card_da_anilist,
)

st.set_page_config(
    page_title="VixSrc Media Center",
    page_icon="🎬",
    layout="wide",
)

# ==========================================
# 📄 PAGINA DEI DETTAGLI (SE UN ELEMENTO È CLICCATO)
# ==========================================
content_id = st.query_params.get("id")
if content_id:
    content_type = st.query_params.get("type", "movie")

    if st.button("⬅️ Torna alla Home"):
        st.query_params.clear()
        st.rerun()

    render_scheda_dettagli(content_type, content_id)
    st.stop()


# ==========================================
# 🏠 HOME PAGE (RICERCA + SLIDER POPOLARI)
# ==========================================
st.title("🎬 VixSrc Media Center")


# --- 1. GESTIONE STATO PAGINA DI RICERCA ---
if "search_page" not in st.session_state:
    st.session_state.search_page = 1

query_ricerca = st.text_input(
    "🔍 Cerca un film o una serie TV...",
    placeholder="Es. Interstellar, Breaking Bad...",
)

if "last_query" not in st.session_state:
    st.session_state.last_query = ""

if query_ricerca != st.session_state.last_query:
    st.session_state.search_page = 1
    st.session_state.last_query = query_ricerca

if query_ricerca:
    results, total_pages = tmdb.cerca_multimediale(query_ricerca, page=st.session_state.search_page)

    if results:
        mostra_griglia(
            f"Risultati della ricerca per: '{query_ricerca}' (Pagina {st.session_state.search_page} di {total_pages})",
            results,
            link_path="/",
        )

        if total_pages > 1:
            col_prec, col_info, col_succ = st.columns([1, 2, 1])

            with col_prec:
                if st.session_state.search_page > 1:
                    if st.button("⬅️ Precedente"):
                        st.session_state.search_page -= 1
                        st.rerun()

            with col_info:
                st.markdown(
                    f"<div style='text-align: center; margin-top: 5px;'>Pagina "
                    f"<b>{st.session_state.search_page}</b> di <b>{total_pages}</b></div>",
                    unsafe_allow_html=True,
                )

            with col_succ:
                if st.session_state.search_page < total_pages:
                    if st.button("Successivo ➡️"):
                        st.session_state.search_page += 1
                        st.rerun()
    else:
        st.info("Nessun risultato trovato.")

    st.divider()

# --- 2 & 3. SEZIONI POPOLARI (MOSTRATE SOLO SE NON C'È UNA RICERCA ATTIVA) ---
if not query_ricerca:
    popolari_film = tmdb.get_tmdb_popular("movie")
    mostra_slider_orizzontale(
        "🔥 Film Popolari", [card_da_tmdb(i) for i in popolari_film]
    )

    st.divider()

    popolari_serie = tmdb.get_tmdb_popular("tv")
    mostra_slider_orizzontale(
        "📺 Serie TV Popolari", [card_da_tmdb(i) for i in popolari_serie]
    )

    st.divider()

    popolari_anime, _ = anilist.discover(sort_by="TRENDING_DESC", page=1, per_page=30)
    mostra_slider_orizzontale(
        "⛩️ Anime Popolari", [card_da_anilist(i) for i in popolari_anime]
    )
