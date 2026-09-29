import sys
from pathlib import Path

# Aggiunge la radice del progetto al path per importare i moduli di backend
sys.path.append(str(Path(__file__).resolve().parent.parent))

import streamlit as st

import tmdb
from ui_components import mostra_griglia, render_scheda_dettagli

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


def mostra_slider_orizzontale(titolo_sezione, items):
    """Renderizza una riga a scorrimento orizzontale di card (poster + titolo + anno)."""
    import streamlit.components.v1 as components

    st.subheader(titolo_sezione)

    if not items:
        st.info("Nessun contenuto disponibile.")
        return

    html_code = """
    <style>
    body {
        background-color: transparent;
        color: white;
        font-family: sans-serif;
        margin: 0;
        padding: 5px 0;
    }
    .scroll-container {
        display: flex;
        overflow-x: auto;
        gap: 16px;
        padding-bottom: 15px;
        scroll-behavior: smooth;
        align-items: flex-start;
    }
    .scroll-container::-webkit-scrollbar { height: 8px; }
    .scroll-container::-webkit-scrollbar-track {
        background: rgba(255,255,255,0.05);
        border-radius: 4px;
    }
    .scroll-container::-webkit-scrollbar-thumb {
        background: rgba(150,150,150,0.5);
        border-radius: 4px;
    }
    .scroll-item { flex: 0 0 140px; text-align: center; }
    .scroll-item a { text-decoration: none; color: inherit; display: block; }
    .scroll-item img {
        width: 140px;
        height: 210px;
        object-fit: cover;
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        transition: transform 0.2s;
    }
    .scroll-item img:hover { transform: scale(1.03); }
    .scroll-title {
        font-size: 12px;
        font-weight: 600;
        margin-top: 6px;
        line-height: 1.2;
        height: 28px;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .scroll-year { font-size: 11px; color: #a0a0a0; margin-top: 2px; }
    </style>

    <div class="scroll-container">
    """

    for item in items:
        poster_path = item.get("poster_path")
        title = item.get("title") or item.get("name") or "Senza titolo"
        year = (item.get("release_date") or item.get("first_air_date") or "")[:4]

        m_type = item.get("media_type")
        if not m_type:
            m_type = "tv" if "name" in item else "movie"

        img_url = f"{tmdb.IMG_BASE_URL}{poster_path}" if poster_path else "https://via.placeholder.com/140x210?text=No+Image"

        html_code += f"""
        <div class="scroll-item">
            <a href="/?id={item.get('id')}&type={m_type}" target="vixsrc_details">
                <img src="{img_url}" alt="{title}">
                <div class="scroll-title" title="{title}">{title}</div>
                <div class="scroll-year">({year})</div>
            </a>
        </div>
        """

    html_code += """
    </div>
    """

    components.html(html_code, height=290, scrolling=False)


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
            key="griglia_ricerca",
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
    mostra_slider_orizzontale("🔥 Film Popolari", popolari_film)

    st.divider()

    popolari_serie = tmdb.get_tmdb_popular("tv")
    mostra_slider_orizzontale("📺 Serie TV Popolari", popolari_serie)
