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

st.write(
    "Cerca un anime per titolo, oppure esplora le **tendenze** con i filtri. "
    "I link sono già `.mp4` diretti."
)

query = st.text_input(
    "🔍 Cerca un anime...",
    value=query_iniziale,
    placeholder="Es. Jujutsu Kaisen, One Piece...",
)

# --- Modalità: ricerca testuale (AnimeWorld) oppure scoperta (AniList) ---
if query:
    with st.spinner("Ricerca su AnimeWorld..."):
        risultati = anime_api.cerca_anime_tollerante(query)

    if risultati:
        st.caption(f"Trovati {len(risultati)} risultati su AnimeWorld")
        mostra_griglia_anime(risultati)
    else:
        st.info("Nessun risultato su AnimeWorld. Prova con un altro titolo.")
    st.stop()

# --- Dati AniList (con cache in sessione: non si richiamano a ogni rerun) ---
if "anime_tag" not in st.session_state:
    st.session_state.anime_tag = anilist.get_tag()

anni = ["Tutti"] + list(range(2026, 1959, -1))
tag_label = {t: t for t in st.session_state.anime_tag}


def _scelte(chiave, etichette):
    """Etichette selezionate nella sessione, ripulite dagli elementi mai esistiti."""
    valide = set(etichette)
    return [e for e in st.session_state.get(chiave, []) if e in valide]


with st.sidebar:
    st.header("🔎 Filtri anime")

    st.multiselect("Genere", list(anilist.GENERI), key="anf_generi")
    st.multiselect(
        "Genere da escludere", list(anilist.GENERI), key="anf_generi_no"
    )
    st.multiselect("Formato", list(anilist.FORMATI), key="anf_formati")
    st.selectbox(
        "Stagione", ["Tutte"] + list(anilist.STAGIONI), key="anf_stagione"
    )
    st.selectbox("Anno di uscita", anni, key="anf_anno")
    st.selectbox(
        "Stato", ["Tutti"] + list(anilist.STATI), key="anf_stato"
    )
    st.selectbox(
        "Sorgente", ["Tutte"] + list(anilist.SORGENTI), key="anf_sorgente"
    )
    st.selectbox("Paese", ["Tutti"] + list(anilist.PAESI), key="anf_paese")
    st.multiselect(
        "Tag", list(tag_label), key="anf_tag",
        help="Tag AniList: scrivi per filtrare l'elenco.",
    )
    st.multiselect(
        "Tag da escludere", list(tag_label), key="anf_tag_no",
        help="Scarta gli anime che hanno questi tag.",
    )
    st.slider(
        "Voto minimo", 0.0, 10.0, 0.0, step=0.5, key="anf_voto",
        help="Da 1 a 100 sulla scala AniList.",
    )
    st.slider(
        "Popolarità minima", 0, 200000, 0, step=5000, key="anf_popolarita"
    )
    st.number_input(
        "Almeno N episodi", min_value=0, step=1, value=0, key="anf_episodi"
    )
    st.number_input(
        "Almeno N minuti a episodio", min_value=0, step=5, value=0, key="anf_durata"
    )
    st.selectbox(
        "Usciti dal", ["Sempre"] + list(range(2026, 1959, -1)), key="anf_dal"
    )
    st.selectbox("Ordina per", list(anilist.ORDINAMENTI), key="anf_ordina")
    st.text_input(
        "Titolo contiene", key="anf_titolo",
        placeholder="Es. gundam, isekai...",
    )

# --- Raccoglie i filtri attivi in un unico dizionario ---
def _val(chiave, ignorati=("Tutti", "Tutte")):
    v = st.session_state.get(chiave)
    return None if v in ignorati else v


filtri = {
    "generi": [anilist.GENERI[e] for e in _scelte("anf_generi", anilist.GENERI)],
    "generi_esclusi": [
        anilist.GENERI[e] for e in _scelte("anf_generi_no", anilist.GENERI)
    ],
    "formati": [anilist.FORMATI[e] for e in _scelte("anf_formati", anilist.FORMATI)],
    "stagione": anilist.STAGIONI.get(_val("anf_stagione")),
    "anno": _val("anf_anno"),
    "stato": [anilist.STATI[_val("anf_stato")]] if _val("anf_stato") else None,
    "sorgente": (
        [anilist.SORGENTI[_val("anf_sorgente")]] if _val("anf_sorgente") else None
    ),
    "paese": [anilist.PAESI[_val("anf_paese")]] if _val("anf_paese") else None,
    "tag": _scelte("anf_tag", tag_label),
    "tag_esclusi": _scelte("anf_tag_no", tag_label),
    "voto_min": st.session_state.get("anf_voto") or None,
    "popolarita_min": st.session_state.get("anf_popolarita") or None,
    "episodi_min": st.session_state.get("anf_episodi") or None,
    "durata_min": st.session_state.get("anf_durata") or None,
    "dal": _val("anf_dal", ("Sempre",)),
    "ricerca": st.session_state.get("anf_titolo") or None,
    "sort_by": anilist.ORDINAMENTI[st.session_state.get("anf_ordina", "Tendenza")],
}

n_filtri = sum(
    1
    for k, v in filtri.items()
    if k not in ("sort_by",) and v not in (None, [], "", 0)
)

# --- Paginazione: torna a pagina 1 quando cambiano i filtri ---
firma = tuple(
    (k, tuple(v) if isinstance(v, list) else v) for k, v in sorted(filtri.items())
)
if st.session_state.get("anime_firma") != firma:
    st.session_state.anime_firma = firma
    st.session_state.anime_page = 1
if "anime_page" not in st.session_state:
    st.session_state.anime_page = 1

risultati, ultima_pagina = anilist.discover(
    page=st.session_state.anime_page, per_page=30, **filtri
)

# AniList limita a 5000 risultati totali: teniamo la paginazione ragionevole
ultima_pagina = min(ultima_pagina, 100)

if n_filtri == 0 and st.session_state.anime_page == 1:
    st.subheader("🔥 Anime di tendenza")
else:
    st.subheader(
        f"Risultati ({n_filtri} filtr{'o' if n_filtri == 1 else 'i'}, "
        f"pagina {st.session_state.anime_page} di {ultima_pagina})"
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
