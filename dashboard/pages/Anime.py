import sys
from pathlib import Path

# Aggiunge la radice del progetto al path per importare i moduli di backend
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st

import anime_api
from ui_components import mostra_griglia_anime, render_scheda_anime

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
# ⛩️ CATALOGO ANIME (RICERCA)
# ==========================================
st.title("⛩️ Catalogo Anime")

st.write("Cerca un anime per titolo e aggiungilo a Jellyfin. I link sono già `.mp4` diretti.")

query = st.text_input("🔍 Cerca un anime...", placeholder="Es. Jujutsu Kaisen, One Piece...")

if query:
    with st.spinner("Ricerca su AnimeWorld..."):
        risultati = anime_api.cerca_anime(query)

    if risultati:
        st.caption(f"Trovati {len(risultati)} risultati")
        mostra_griglia_anime(risultati)
    else:
        st.info("Nessun risultato trovato.")
else:
    st.info("Inserisci un titolo per iniziare la ricerca.")
