"""Componenti UI condivisi tra le pagine Streamlit (griglia risultati + scheda dettagli)."""

import streamlit as st
import streamlit.components.v1 as components

import tmdb
from file_manager import (
    verifica_presenza_jellyfin,
    crea_cartella_film,
    crea_file_serie,
    rimuovi_cartella_film,
    rimuovi_cartella_serie,
    verifica_presenza_episodio,
    rimuovi_episodio,
    rinfresca_libreria_jellyfin,
)
from estrattore import estrai_flussi


def mostra_griglia(titolo_sezione, items, link_path="/", target="vixsrc_details"):
    """Renderizza una griglia di card cliccabili (poster + titolo + anno + tipo).

    link_path è la rotta a cui puntano le card (es. "/Film" per la pagina film).
    """
    st.subheader(titolo_sezione)

    if not items:
        st.info("Nessun risultato trovato.")
        return

    num_righe = (len(items) + 5) // 6
    altezza_box = num_righe * 218

    html_code = """
    <style>
    body {
        background-color: transparent;
        color: white;
        font-family: sans-serif;
        margin: 0;
        padding: 0;
    }
    .grid-container {
        display: flex;
        flex-wrap: wrap;
        gap: 16px;
        justify-content: flex-start;
        padding-bottom: 5px;
    }
    .grid-item {
        flex: 0 0 140px;
        text-align: center;
        margin-bottom: 15px;
    }
    .grid-item a {
        text-decoration: none;
        color: inherit;
        display: block;
    }
    .grid-item img {
        width: 140px;
        height: 210px;
        object-fit: cover;
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        transition: transform 0.2s;
    }
    .grid-item img:hover {
        transform: scale(1.03);
    }
    .grid-title {
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
    .grid-year {
        font-size: 11px;
        color: #a0a0a0;
        margin-top: 2px;
    }
    .grid-type {
        font-size: 10px;
        color: #ff4b4b;
        text-transform: uppercase;
        font-weight: bold;
        margin-top: 1px;
    }
    </style>

    <div class="grid-container">
    """

    for item in items:
        poster_path = item.get("poster_path")
        title = item.get("title") or item.get("name") or "Senza titolo"
        year = (item.get("release_date") or item.get("first_air_date") or "")[:4]
        media_type = item.get("media_type")
        if not media_type:
            media_type = "tv" if "name" in item else "movie"
        tipo_str = "Film" if media_type == "movie" else "Serie TV" if media_type == "tv" else ""

        if poster_path:
            img_url = f"{tmdb.IMG_BASE_URL}{poster_path}"
        else:
            img_url = "https://via.placeholder.com/140x210?text=No+Image"

        html_code += f"""
        <div class="grid-item">
            <a href="{link_path}?id={item.get('id')}&type={media_type}" target="{target}">
                <img src="{img_url}" alt="{title}">
                <div class="grid-title" title="{title}">{title}</div>
                <div class="grid-year">({year})</div>
                <div class="grid-type">{tipo_str}</div>
            </a>
        </div>
        """

    html_code += """
    </div>
    """

    components.html(html_code, height=altezza_box, scrolling=True)


def render_scheda_dettagli(content_type, content_id):
    """Renderizza la scheda di dettaglio (poster, badge, trailer, cast) e la gestione Jellyfin.

    Per le serie TV mostra il selettore stagione/episodio e la gestione Jellyfin
    avviene per singolo episodio (come da logica di crea_file_serie).
    """
    dettagli = tmdb.get_tmdb_details(content_type, content_id)

    if not dettagli:
        altri_tipo = "tv" if content_type == "movie" else "movie"
        dettagli = tmdb.get_tmdb_details(altri_tipo, content_id)
        content_type = altri_tipo

    if not dettagli:
        st.error("Impossibile caricare i dettagli del contenuto.")
        return

    titolo = dettagli.get("title") or dettagli.get("name") or "Senza titolo"
    anno = (dettagli.get("release_date") or dettagli.get("first_air_date") or "")[:4]
    overview = dettagli.get("overview") or "Nessuna descrizione disponibile."
    poster_path = dettagli.get("poster_path")
    vote_average = dettagli.get("vote_average", 0)
    genres = ", ".join([g["name"] for g in dettagli.get("genres", [])])

    # Durata (film) o numero di stagioni (serie TV)
    runtime_info = ""
    if content_type == "movie":
        runtime = dettagli.get("runtime")
        if runtime:
            runtime_info = f"⏱️ {runtime} min"
    else:
        seasons = dettagli.get("number_of_seasons")
        if seasons:
            runtime_info = f"📺 {seasons} Stagioni"

    cast_list = []
    credits = tmdb.get_tmdb_credits(content_type, content_id)
    if credits and "cast" in credits:
        cast_list = [actor["name"] for actor in credits["cast"][:5]]

    col_poster, col_info = st.columns([1, 2.5], gap="large")

    with col_poster:
        if poster_path:
            st.image(f"{tmdb.IMG_BASE_URL}{poster_path}", use_container_width=True)
        else:
            st.image("https://via.placeholder.com/300x450?text=No+Image", use_container_width=True)

    with col_info:
        st.title(f"{titolo} ({anno})" if anno else titolo)

        info_badges = []
        if vote_average > 0:
            info_badges.append(f"⭐ **{vote_average:.1f}/10**")
        if genres:
            info_badges.append(f"🎭 {genres}")
        if runtime_info:
            info_badges.append(runtime_info)

        if info_badges:
            st.markdown(" &nbsp;&bull;&nbsp; ".join(info_badges))

        videos = tmdb.get_tmdb_videos(content_type, content_id)
        trailer_key = None
        for v in videos:
            if v.get("site") == "YouTube" and v.get("type") == "Trailer":
                trailer_key = v.get("key")
                break

        if trailer_key:
            with st.expander("🎬 Guarda il Trailer"):
                st.video(f"https://www.youtube.com/watch?v={trailer_key}")

        st.markdown("### Trama")
        st.write(overview)

        if cast_list:
            st.markdown("### Cast Principale")
            st.write(", ".join(cast_list))

    st.markdown("---")

    if content_type == "movie":
        _gestione_film(content_id, titolo, anno)
    else:
        _gestione_serie(content_id, titolo)


def _gestione_film(content_id, titolo, anno):
    """Gestione Jellyfin per un film: aggiunge/rimuove l'intera cartella."""
    st.subheader("⚙️ Gestione File Jellyfin")

    gia_in_libreria = verifica_presenza_jellyfin("movie", content_id, titolo, anno)

    col_j1, col_j2 = st.columns(2)

    with col_j1:
        if gia_in_libreria:
            st.button("✅ Già in libreria", use_container_width=True, disabled=True)
        else:
            if st.button("➕ Aggiungi a Jellyfin", use_container_width=True):
                with st.spinner("Estrazione flussi e creazione in corso..."):
                    try:
                        url_pagina = f"https://vixsrc.to/movie/{content_id}?lang=it"
                        video_link, audio_link = estrai_flussi(url_pagina)

                        if video_link:
                            crea_cartella_film(content_id, titolo, anno, video_link, audio_link)
                            rinfresca_libreria_jellyfin()
                            st.success(f"'{titolo}' aggiunto e libreria Jellyfin aggiornata!")
                            st.rerun()
                        else:
                            st.error("Impossibile estrarre i flussi video dal link sorgente.")
                    except Exception as e:
                        st.error(f"Errore durante l'aggiunta: {e}")

    with col_j2:
        if st.button("🗑️ Rimuovi da Jellyfin", use_container_width=True, disabled=not gia_in_libreria):
            try:
                rimuovi_cartella_film(content_id, titolo, anno)
                rinfresca_libreria_jellyfin()
                st.warning(f"File rimosso per '{titolo}'.")
                st.rerun()
            except Exception as e:
                st.error(f"Errore durante la rimozione: {e}")


def _gestione_serie(content_id, titolo):
    """Gestione Jellyfin per una serie: seleziona stagione/episodio e agisce sull'episodio."""
    st.subheader("⚙️ Gestione File Jellyfin")

    stagioni = tmdb.get_stagioni(content_id)
    if not stagioni:
        st.info("Nessuna stagione disponibile per questa serie.")
        return

    opzioni_stagioni = {s.get("name") or f"Stagione {s['season_number']}": s["season_number"] for s in stagioni}
    nome_stagione = st.selectbox("Stagione", list(opzioni_stagioni.keys()))
    stagione_num = opzioni_stagioni[nome_stagione]

    dettagli_stagione = tmdb.get_dettagli_stagione(content_id, stagione_num) or {}
    # get_dettagli_stagione restituisce l'intero oggetto stagione: gli episodi sono in "episodes"
    episodi = dettagli_stagione.get("episodes", [])
    if not episodi:
        st.info("Nessun episodio disponibile per questa stagione.")
        return

    opzioni_episodi = {
        f"{int(e.get('episode_number') or 0):02d} - {e.get('name') or 'Senza titolo'}": (e.get("episode_number") or 0)
        for e in episodi
    }
    etichette = list(opzioni_episodi.keys())

    # Pre-selezione: primo episodio non ancora in libreria
    indice_default = 0
    for i, etichetta in enumerate(etichette):
        if not verifica_presenza_episodio(content_id, titolo, stagione_num, opzioni_episodi[etichetta]):
            indice_default = i
            break

    etichetta_scelta = st.selectbox("Episodio", etichette, index=indice_default)
    episodio_num = opzioni_episodi[etichetta_scelta]

    gia_presente = verifica_presenza_episodio(content_id, titolo, stagione_num, episodio_num)

    col_j1, col_j2 = st.columns(2)

    with col_j1:
        if st.button("➕ Aggiungi episodio a Jellyfin", use_container_width=True):
            with st.spinner("Estrazione flussi e creazione in corso..."):
                try:
                    url_pagina = f"https://vixsrc.to/tv/{content_id}/{stagione_num}/{episodio_num}?lang=it"
                    video_link, audio_link = estrai_flussi(url_pagina)

                    if video_link:
                        crea_file_serie(content_id, titolo, stagione_num, episodio_num, video_link, audio_link)
                        rinfresca_libreria_jellyfin()
                        st.success(f"S{stagione_num:02d}E{episodio_num:02d} aggiunto e libreria aggiornata!")
                        st.rerun()
                    else:
                        st.error("Impossibile estrarre i flussi video dal link sorgente.")
                except Exception as e:
                    st.error(f"Errore durante l'aggiunta: {e}")

    with col_j2:
        if st.button("🗑️ Rimuovi episodio", use_container_width=True, disabled=not gia_presente):
            try:
                rimuovi_episodio(content_id, titolo, stagione_num, episodio_num)
                rinfresca_libreria_jellyfin()
                st.warning(f"S{stagione_num:02d}E{episodio_num:02d} rimosso.")
                st.rerun()
            except Exception as e:
                st.error(f"Errore durante la rimozione: {e}")

    if gia_presente:
        st.caption(f"✅ S{stagione_num:02d}E{episodio_num:02d} è già presente in libreria.")

    st.markdown("---")
    if st.button("🗑️ Rimuovi l'intera serie da Jellyfin", use_container_width=True):
        try:
            rimuovi_cartella_serie(content_id, titolo)
            rinfresca_libreria_jellyfin()
            st.warning(f"Serie '{titolo}' rimossa.")
            st.rerun()
        except Exception as e:
            st.error(f"Errore durante la rimozione della serie: {e}")
