"""Componenti UI condivisi tra le pagine Streamlit (griglia risultati + scheda dettagli)."""

import html
import urllib.parse

import streamlit as st
import streamlit.components.v1 as components

import tmdb
import anime_api
import anilist
import paths
from file_manager import (
    verifica_presenza_jellyfin,
    crea_cartella_film,
    crea_file_serie,
    rimuovi_cartella_film,
    rimuovi_cartella_serie,
    verifica_presenza_episodio,
    verifica_presenza_stagione,
    rimuovi_episodio,
    rimuovi_stagione,
    crea_file_anime,
    salva_origine_stagione_anime,
    verifica_presenza_episodio_anime,
    verifica_presenza_stagione_anime,
    rimuovi_episodio_anime,
    rimuovi_stagione_anime,
    rinfresca_libreria_jellyfin,
)
from estrattore import estrai_flussi


_GRID_STYLE = """
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

    html_code = _GRID_STYLE

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


_ANIME_GRID_STYLE = """
    body { background-color: transparent; color: white; font-family: sans-serif; margin: 0; }
    .grid-container { display: flex; flex-wrap: wrap; gap: 18px; justify-content: flex-start; }
    .grid-item { flex: 0 0 180px; width: 180px; }
    .grid-item a { text-decoration: none; color: inherit; display: block; }
    .grid-item img {
        width: 180px; height: 270px; object-fit: cover; border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3); transition: transform 0.2s;
    }
    .grid-item img:hover { transform: scale(1.03); }
    .grid-title {
        font-size: 13px; font-weight: 600; margin-top: 6px; line-height: 1.25;
        overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
    }
    .grid-meta { font-size: 11px; color: #a0a0a0; margin-top: 2px; }
    .grid-type {
        font-size: 10px; color: #ff4b4b; text-transform: uppercase;
        font-weight: bold; margin-top: 1px;
    }
    """


def _link_scheda_anime(titolo, link_aw, copertina):
    """Costruisce l'href verso la scheda dettaglio della pagina /Anime."""
    return (
        f"/Anime?link={urllib.parse.quote(link_aw, safe='')}"
        f"&titolo={urllib.parse.quote(titolo)}"
        f"&copertina={urllib.parse.quote(copertina or '', safe='')}"
    )


def _card_anime(titolo, img_url, riga_meta, riga_tipo, href):
    """Costruisce l'HTML di una singola card anime."""
    titolo_sicuro = html.escape(titolo)
    return f"""
        <div class="grid-item">
            <a href="{href}" target="vixsrc_details">
                <img src="{html.escape(img_url, quote=True)}" alt="{titolo_sicuro}">
                <div class="grid-title" title="{titolo_sicuro}">{titolo_sicuro}</div>
                <div class="grid-meta">{riga_meta}</div>
                <div class="grid-type">{riga_tipo}</div>
            </a>
        </div>
        """


def mostra_griglia_anime(items):
    """Griglia dei risultati AnimeWorld (nome + anno + doppiaggio).

    Le card hanno il titolo sotto la copertina, quindi non serve `components.html`
    con altezza fissa: l'HTML viene inserito inline (`st.html`) e cresce da solo.
    """
    if not items:
        st.info("Nessun risultato trovato.")
        return

    html_code = f"<style>{_ANIME_GRID_STYLE}</style><div class='grid-container'>"

    for item in items:
        titolo = item.get("name") or "Senza titolo"
        img_url = item.get("image") or "https://via.placeholder.com/180x270?text=No+Image"
        pezzi = []
        if item.get("year"):
            pezzi.append(str(item["year"]))
        pezzi.append("ITA" if item.get("dub") else "SUB ITA")
        riga_meta = " &bull; ".join(pezzi)
        href = _link_scheda_anime(titolo, item.get("link", ""), img_url)
        html_code += _card_anime(titolo, img_url, riga_meta, "AnimeWorld", href)

    html_code += "</div>"
    st.html(html_code)


def mostra_griglia_scoperta_anime(items):
    """Griglia dei risultati AniList: cliccando si cerca l'anime su AnimeWorld.

    AniList non ospita video, quindi la card non apre direttamente la scheda:
    porta alla ricerca su AnimeWorld col titolo tradotto.
    """
    if not items:
        st.info("Nessun risultato trovato.")
        return

    html_code = f"<style>{_ANIME_GRID_STYLE}</style><div class='grid-container'>"

    for item in items:
        titolo = anilist.titolo_italiano(item) or "Senza titolo"
        img_url = (item.get("coverImage") or {}).get("large") \
            or "https://via.placeholder.com/180x270?text=No+Image"
        pezzi = [str(item["seasonYear"])] if item.get("seasonYear") else []
        if item.get("averageScore"):
            pezzi.append(f"⭐ {item['averageScore'] / 10:.1f}")
        if item.get("episodes"):
            pezzi.append(f"{item['episodes']} ep")
        riga_meta = " &bull; ".join(pezzi)
        href = f"/Anime?cerca={urllib.parse.quote(titolo)}"
        html_code += _card_anime(titolo, img_url, riga_meta, "AniList", href)

    html_code += "</div>"
    st.html(html_code)


_SLIDER_STYLE = """
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
    """


def mostra_slider_orizzontale(titolo_sezione, cards):
    """Riga a scorrimento orizzontale di card (copertina + titolo + riga info).

    `cards` è una lista di dizionari con chiavi: titolo, img, href, meta.
    """
    st.subheader(titolo_sezione)

    if not cards:
        st.info("Nessun contenuto disponibile.")
        return

    html_code = _SLIDER_STYLE + "<div class='scroll-container'>"

    for card in cards:
        titolo = html.escape(card.get("titolo") or "Senza titolo")
        img_url = html.escape(card.get("img") or "", quote=True)
        href = card.get("href", "")
        meta = card.get("meta", "")
        html_code += f"""
        <div class="scroll-item">
            <a href="{href}" target="vixsrc_details">
                <img src="{img_url}" alt="{titolo}">
                <div class="scroll-title" title="{titolo}">{titolo}</div>
                <div class="scroll-year">{meta}</div>
            </a>
        </div>
        """

    html_code += "</div>"
    components.html(html_code, height=290, scrolling=False)


def card_da_tmdb(item):
    """Converte un risultato TMDB nella card dello slider."""
    poster_path = item.get("poster_path")
    anno = (item.get("release_date") or item.get("first_air_date") or "")[:4]
    m_type = item.get("media_type") or ("tv" if "name" in item else "movie")
    return {
        "titolo": item.get("title") or item.get("name") or "Senza titolo",
        "img": f"{tmdb.IMG_BASE_URL}{poster_path}" if poster_path else "",
        "href": f"/?id={item.get('id')}&type={m_type}",
        "meta": f"({anno})",
    }


def card_da_anilist(item):
    """Converte un risultato AniList nella card dello slider.

    Il click porta alla ricerca su AnimeWorld (stesso flusso della griglia anime).
    """
    titolo = anilist.titolo_italiano(item) or "Senza titolo"
    pezzi = [str(item["seasonYear"])] if item.get("seasonYear") else []
    if item.get("averageScore"):
        pezzi.append(f"⭐ {item['averageScore'] / 10:.1f}")
    return {
        "titolo": titolo,
        "img": (item.get("coverImage") or {}).get("large") or "",
        "href": f"/Anime?cerca={urllib.parse.quote(titolo)}",
        "meta": " &bull; ".join(pezzi),
    }


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
    """Gestione Jellyfin per una serie, a livello di stagione (con episodio singolo come opzione)."""
    st.subheader("⚙️ Gestione File Jellyfin")

    stagioni = tmdb.get_stagioni(content_id)
    if not stagioni:
        st.info("Nessuna stagione disponibile per questa serie.")
        return

    opzioni_stagioni = {}
    for s in stagioni:
        nome = s.get("name") or f"Stagione {s['season_number']}"
        num_ep = s.get("episode_count")
        etichetta = f"{nome} ({num_ep} episodi)" if num_ep else nome
        opzioni_stagioni[etichetta] = s["season_number"]
    nome_stagione = st.selectbox("Stagione", list(opzioni_stagioni.keys()))
    stagione_num = opzioni_stagioni[nome_stagione]

    dettagli_stagione = tmdb.get_dettagli_stagione(content_id, stagione_num) or {}
    # get_dettagli_stagione restituisce l'intero oggetto stagione: gli episodi sono in "episodes"
    episodi = dettagli_stagione.get("episodes", [])
    if not episodi:
        st.info("Nessun episodio disponibile per questa stagione.")
        return

    numeri_episodi = [e.get("episode_number") or 0 for e in episodi]
    titoli_episodi = {e.get("episode_number") or 0: e.get("name") or "Senza titolo" for e in episodi}

    gia_presenti = verifica_presenza_stagione(content_id, titolo, stagione_num, numeri_episodi)
    mancanti = [n for n in numeri_episodi if n not in gia_presenti]

    st.caption(
        f"Episodi in questa stagione: **{len(numeri_episodi)}** — "
        f"in libreria: **{len(gia_presenti)}** — mancanti: **{len(mancanti)}**"
    )

    col_j1, col_j2 = st.columns(2)

    with col_j1:
        if not mancanti:
            st.button("✅ Stagione completa", use_container_width=True, disabled=True)
        else:
            if st.button(f"➕ Aggiungi stagione intera ({len(mancanti)} episodi)", use_container_width=True):
                _aggiungi_stagione(content_id, titolo, stagione_num, mancanti)

    with col_j2:
        if st.button("🗑️ Rimuovi stagione intera", use_container_width=True, disabled=not gia_presenti):
            try:
                rimuovi_stagione(content_id, titolo, stagione_num)
                rinfresca_libreria_jellyfin()
                st.warning(f"Stagione {stagione_num:02d} rimossa.")
                st.rerun()
            except Exception as e:
                st.error(f"Errore durante la rimozione della stagione: {e}")

    with st.expander("🎬 Gestione singolo episodio"):
        opzioni_episodi = {
            f"{n:02d} - {titoli_episodi[n]}": n for n in numeri_episodi
        }
        etichette = list(opzioni_episodi.keys())

        indice_default = 0
        for i, etichetta in enumerate(etichette):
            if opzioni_episodi[etichetta] not in gia_presenti:
                indice_default = i
                break

        etichetta_scelta = st.selectbox("Episodio", etichette, index=indice_default)
        episodio_num = opzioni_episodi[etichetta_scelta]
        gia_presente = episodio_num in gia_presenti

        col_e1, col_e2 = st.columns(2)
        with col_e1:
            if st.button("➕ Aggiungi episodio", use_container_width=True, disabled=gia_presente):
                _aggiungi_stagione(content_id, titolo, stagione_num, [episodio_num])
        with col_e2:
            if st.button("🗑️ Rimuovi episodio", use_container_width=True, disabled=not gia_presente):
                try:
                    rimuovi_episodio(content_id, titolo, stagione_num, episodio_num)
                    rinfresca_libreria_jellyfin()
                    st.warning(f"S{stagione_num:02d}E{episodio_num:02d} rimosso.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Errore durante la rimozione: {e}")

    st.markdown("---")
    if st.button("🗑️ Rimuovi l'intera serie da Jellyfin", use_container_width=True):
        try:
            rimuovi_cartella_serie(content_id, titolo)
            rinfresca_libreria_jellyfin()
            st.warning(f"Serie '{titolo}' rimossa.")
            st.rerun()
        except Exception as e:
            st.error(f"Errore durante la rimozione della serie: {e}")


def _aggiungi_stagione(content_id, titolo, stagione_num, numeri_episodi):
    """Aggiunge a Jellyfin una lista di episodi di una stagione, saltando quelli presenti."""
    totale = len(numeri_episodi)
    barra = st.progress(0.0, text=f"Preparazione di {totale} episodi...")
    aggiunti, falliti = 0, 0

    for i, episodio_num in enumerate(numeri_episodi, start=1):
        if verifica_presenza_episodio(content_id, titolo, stagione_num, episodio_num):
            continue

        barra.progress(i / totale, text=f"Episodio {int(episodio_num):02d} ({i}/{totale})...")
        try:
            url_pagina = f"https://vixsrc.to/tv/{content_id}/{stagione_num}/{episodio_num}?lang=it"
            video_link, audio_link = estrai_flussi(url_pagina)
            if video_link:
                crea_file_serie(content_id, titolo, stagione_num, episodio_num, video_link, audio_link)
                aggiunti += 1
            else:
                falliti += 1
        except Exception:
            falliti += 1

    barra.empty()

    if aggiunti:
        rinfresca_libreria_jellyfin()

    if falliti:
        st.warning(f"{aggiunti} episodi aggiunti, {falliti} non riusciti.")
    else:
        st.success(f"{aggiunti} episodi aggiunti e libreria Jellyfin aggiornata!")
    st.rerun()


# ==========================================
# ⛩️ ANIME (scheda dettaglio + gestione Jellyfin)
# ==========================================

def render_scheda_anime(link_anime, titolo_sessione, copertina_sessione):
    """Scheda dettaglio di un anime: info, trama e gestione Jellyfin a stagioni.

    titolo_sessione/copertina_sessione arrivano dalla card cliccata e servono per
    mostrare subito qualcosa mentre si caricano i dettagli dall'API.
    """
    try:
        dettagli = anime_api.dettagli_anime(link_anime)
    except Exception as e:
        st.error(f"Impossibile caricare i dettagli dell'anime: {e}")
        st.stop()

    titolo = dettagli["nome"] or titolo_sessione or "Senza titolo"
    info = dettagli.get("info", {}) or {}
    copertina = dettagli.get("copertina") or copertina_sessione

    col_poster, col_info = st.columns([1, 2.5], gap="large")

    with col_poster:
        if copertina:
            st.image(copertina, use_container_width=True)
        else:
            st.image("https://via.placeholder.com/300x450?text=No+Image", use_container_width=True)

    with col_info:
        st.title(titolo)

        badges = []
        if info.get("Voto"):
            badges.append(f"⭐ **{info['Voto']}**")
        if info.get("Genere"):
            badges.append(f"🎭 {', '.join(info['Genere'])}")
        if info.get("Stato"):
            badges.append(f"📌 {info['Stato']}")
        if info.get("Episodi"):
            badges.append(f"🎞️ {info['Episodi']} episodi")
        if badges:
            st.markdown(" &nbsp;&bull;&nbsp; ".join(badges))

        st.markdown("### Trama")
        st.write(dettagli.get("trama") or "Trama non disponibile.")

        extra = []
        for chiave, prefisso in [("Studio", "🏢 Studio"), ("Durata", "⏱️ Durata"),
                                 ("Data di Uscita", "📅 Uscita"), ("Audio", "🔊 Audio")]:
            if info.get(chiave):
                extra.append(f"{prefisso}: {info[chiave]}")
        if extra:
            st.caption(" &nbsp;&bull;&nbsp; ".join(extra))

    st.markdown("---")

    # Gli episodi li scarichiamo una sola volta e li teniamo per contare
    # quanto episodi sono presenti in libreria per la stagione scelta.
    try:
        episodi = anime_api.episodi(link_anime)
    except Exception as e:
        st.error(f"Impossibile caricare gli episodi: {e}")
        st.stop()

    if not episodi:
        st.info("Nessun episodio disponibile per questo anime.")
        st.stop()

    _gestione_anime(titolo, episodi, link_anime)


def _gestione_anime(titolo, episodi, link_anime=None):
    """Gestione Jellyfin per un anime: stagione unica (Season 01) di default."""
    st.subheader("⚙️ Gestione File Jellyfin")

    # Il messaggio dell'ultima aggiunta/rimozione viene salvato in session_state
    # perché `st.rerun()` azzera gli elementi creati nello stesso run: senza
    # questo, l'esito (compreso "0 aggiunti") sparisce subito.
    esito = st.session_state.pop("anime_msg", None)
    if esito:
        testo, livello = esito
        (st.success if livello == "ok" else st.warning)(testo)

    # Mappa numero -> oggetto Episodio, così i link si risolvono senza riscaricare
    # la lista episodi a ogni click (una sola richiesta per episodio, non due).
    mappa_episodi = {str(ep.number): ep for ep in episodi}
    numeri_episodi = list(mappa_episodi.keys())

    # Nome cartella + numero stagione: di solito un anime AnimeWorld è una serie
    # unica (Season 01). Se l'anime ha stagioni separate sul sito, si importano
    # nella stessa cartella indicando qui il numero di stagione desiderato.
    col_a, col_b = st.columns([2, 1])
    with col_a:
        titolo_cartella = st.text_input(
            "📁 Nome serie (cartella principale)",
            value=titolo,
            help="Tutte le stagioni importate con questo nome finiscono nella stessa cartella.",
        )
    with col_b:
        stagione_num = st.number_input("Stagione n°", min_value=1, max_value=99, value=1)

    st.caption(f"Percorso: `{paths.anime_path}/{titolo_cartella}/Season {int(stagione_num):02d}`")

    gia_presenti = verifica_presenza_stagione_anime(titolo_cartella, stagione_num, numeri_episodi)
    mancanti = [n for n in numeri_episodi if n not in gia_presenti]

    st.caption(
        f"Episodi disponibili: **{len(numeri_episodi)}** — "
        f"in libreria: **{len(gia_presenti)}** — mancanti: **{len(mancanti)}**"
    )

    col_j1, col_j2 = st.columns(2)

    with col_j1:
        if not mancanti:
            st.button("✅ Stagione completa", use_container_width=True, disabled=True)
        else:
            if st.button(f"➕ Aggiungi stagione intera ({len(mancanti)} episodi)", use_container_width=True):
                _aggiungi_stagione_anime(titolo_cartella, stagione_num, mancanti, mappa_episodi, link_anime)

    with col_j2:
        if st.button("🗑️ Rimuovi stagione intera", use_container_width=True, disabled=not gia_presenti):
            try:
                rimuovi_stagione_anime(titolo_cartella, stagione_num)
                rinfresca_libreria_jellyfin()
                st.warning(f"Season {int(stagione_num):02d} rimossa.")
                st.rerun()
            except Exception as e:
                st.error(f"Errore durante la rimozione della stagione: {e}")

    with st.expander("🎬 Gestione singolo episodio"):
        episodio_num = st.selectbox("Episodio", numeri_episodi, format_func=lambda n: f"Episodio {n}")
        gia_presente = episodio_num in gia_presenti

        col_e1, col_e2 = st.columns(2)
        with col_e1:
            if st.button("➕ Aggiungi episodio", use_container_width=True, disabled=gia_presente):
                _aggiungi_stagione_anime(titolo_cartella, stagione_num, [episodio_num], mappa_episodi, link_anime)
        with col_e2:
            if st.button("🗑️ Rimuovi episodio", use_container_width=True, disabled=not gia_presente):
                try:
                    rimuovi_episodio_anime(titolo_cartella, stagione_num, episodio_num)
                    rinfresca_libreria_jellyfin()
                    st.warning(f"S{int(stagione_num):02d}E{int(episodio_num):02d} rimosso.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Errore durante la rimozione: {e}")

    st.markdown("---")
    if st.button("🗑️ Rimuovi l'intera serie da Jellyfin", use_container_width=True):
        try:
            rimuovi_stagione_anime(titolo_cartella, stagione_num)
            rinfresca_libreria_jellyfin()
            st.warning(f"Serie '{titolo_cartella}' rimossa.")
            st.rerun()
        except Exception as e:
            st.error(f"Errore durante la rimozione della serie: {e}")


def _aggiungi_stagione_anime(titolo, stagione_num, numeri_episodi, mappa_episodi, link_anime=None):
    """Crea i file .strm di una stagione anime risolvendo i link .mp4, saltando i presenti."""
    totale = len(numeri_episodi)
    barra = st.progress(0.0, text=f"Preparazione di {totale} episodi...")
    aggiunti, falliti = 0, 0
    ultimo_errore = None

    for i, episodio_num in enumerate(numeri_episodi, start=1):
        if verifica_presenza_episodio_anime(titolo, stagione_num, episodio_num):
            continue

        barra.progress(i / totale, text=f"Episodio {episodio_num} ({i}/{totale})...")
        try:
            link = anime_api.link_mp4(mappa_episodi.get(episodio_num))
            if link:
                crea_file_anime(titolo, stagione_num, episodio_num, link)
                aggiunti += 1
            else:
                falliti += 1
        except Exception as e:
            ultimo_errore = f"{type(e).__name__}: {e}"
            falliti += 1

    barra.empty()

    # Ricorda la pagina AnimeWorld della stagione: la manutenzione la userà per
    # rigenerare gli episodi senza ambiguità tra più stagioni.
    if aggiunti and link_anime:
        try:
            salva_origine_stagione_anime(titolo, stagione_num, anime_api.link_pagina_anime(link_anime))
        except Exception:
            pass

    # Il refresh Jellyfin non deve bloccare il risultato: senza Jellyfin
    # configurato i file sono comunque già stati creati sul disco.
    try:
        rinfresca_libreria_jellyfin()
    except Exception:
        pass

    percorso = f"{paths.anime_path}/{titolo}/{f'Season {int(stagione_num):02d}'}"
    if falliti:
        dettaglio = f" Ultimo errore: {ultimo_errore}." if ultimo_errore else ""
        st.session_state["anime_msg"] = (
            f"{aggiunti} episodi aggiunti, {falliti} non riusciti.{dettaglio}",
            "warn",
        )
    elif aggiunti == 0:
        st.session_state["anime_msg"] = (
            "Nessun nuovo episodio da aggiungere: erano già tutti presenti "
            f"in `{percorso}`.",
            "warn",
        )
    else:
        st.session_state["anime_msg"] = (
            f"{aggiunti} episodi aggiunti in `{percorso}`.",
            "ok",
        )
    st.rerun()
