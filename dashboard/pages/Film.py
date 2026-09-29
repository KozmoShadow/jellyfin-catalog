import sys
from pathlib import Path

# Aggiunge la radice del progetto al path per importare i moduli di backend
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st

import tmdb
from ui_components import mostra_griglia, render_scheda_dettagli

st.set_page_config(
    page_title="Catalogo Film",
    page_icon="🎞️",
    layout="wide",
)

# ==========================================
# 📄 SCHEDA DETTAGLI (SE UN FILM È STATO CLICCATO)
# ==========================================
content_id = st.query_params.get("id")
if content_id:
    content_type = st.query_params.get("type", "movie")

    if st.button("⬅️ Torna al catalogo"):
        st.query_params.clear()
        st.rerun()

    render_scheda_dettagli(content_type, content_id)
    st.stop()

# ==========================================
# 🎞️ CATALOGO FILM (FILTRI + GRIGLIA)
# ==========================================
st.title("🎞️ Catalogo Film")

# --- Opzioni di ordinamento (etichetta -> parametro TMDB) ---
ORDINAMENTI = {
    "Popolarità": "popularity.desc",
    "Voto medio": "vote_average.desc",
    "Più recenti": "primary_release_date.desc",
    "Più vecchi": "primary_release_date.asc",
    "Incasso": "revenue.desc",
}

# --- Generi TMDB (con cache in sessione per non richiamare l'API a ogni rerun) ---
if "film_generi" not in st.session_state:
    generi = tmdb.get_generi("movie")
    st.session_state.film_generi = {g["name"]: g["id"] for g in generi}
mappa_generi = st.session_state.film_generi

# --- Filtri nella sidebar ---
with st.sidebar:
    st.header("🔎 Filtri")

    genere_scelto = st.selectbox("Genere", ["Tutti"] + list(mappa_generi.keys()))

    anno_corrente = 2026
    anni = ["Tutti"] + list(range(anno_corrente, 1949, -1))
    anno_scelto = st.selectbox("Anno di uscita", anni)

    voto_min = st.slider("Voto minimo", 0.0, 10.0, 0.0, step=0.5)

    min_voti = st.select_slider(
        "Voti minimi",
        options=[0, 50, 100, 250, 500, 1000, 5000],
        value=0,
    )

    ordinamento_scelto = st.selectbox("Ordina per", list(ORDINAMENTI.keys()))

# --- Paginazione: torna a pagina 1 quando cambiano i filtri ---
filtri_correnti = (genere_scelto, anno_scelto, voto_min, min_voti, ordinamento_scelto)
if st.session_state.get("film_filtri") != filtri_correnti:
    st.session_state.film_filtri = filtri_correnti
    st.session_state.film_page = 1
if "film_page" not in st.session_state:
    st.session_state.film_page = 1

genere_id = mappa_generi.get(genere_scelto) if genere_scelto != "Tutti" else None
anno = None if anno_scelto == "Tutti" else anno_scelto
voto = voto_min if voto_min > 0 else None
voti = min_voti if min_voti > 0 else None

risultati, total_pages = tmdb.discover_movie(
    genere_id=genere_id,
    anno=anno,
    voto_min=voto,
    min_voti=voti,
    sort_by=ORDINAMENTI[ordinamento_scelto],
    page=st.session_state.film_page,
)

# TMDB limita la paginazione a 500 pagine
total_pages = min(total_pages, 500)

etichetta_filtri = []
if genere_scelto != "Tutti":
    etichetta_filtri.append(genere_scelto)
if anno_scelto != "Tutti":
    etichetta_filtri.append(str(anno_scelto))
if voto_min > 0:
    etichetta_filtri.append(f"⭐ {voto_min:g}+")
suffisso = f" — {', '.join(etichetta_filtri)}" if etichetta_filtri else ""

mostra_griglia(
    f"Risultati{suffisso} (Pagina {st.session_state.film_page} di {total_pages})",
    risultati,
    link_path="/Film",
)

if total_pages > 1:
    col_prec, col_info, col_succ = st.columns([1, 2, 1])

    with col_prec:
        if st.session_state.film_page > 1:
            if st.button("⬅️ Precedente"):
                st.session_state.film_page -= 1
                st.rerun()

    with col_info:
        st.markdown(
            f"<div style='text-align: center; margin-top: 5px;'>Pagina "
            f"<b>{st.session_state.film_page}</b> di <b>{total_pages}</b></div>",
            unsafe_allow_html=True,
        )

    with col_succ:
        if st.session_state.film_page < total_pages:
            if st.button("Successivo ➡️"):
                st.session_state.film_page += 1
                st.rerun()