import sys
from pathlib import Path

# Aggiunge la radice del progetto al path per importare paths.py e tmdb.py
sys.path.append(str(Path(__file__).resolve().parent.parent))
import paths
import tmdb

import streamlit as st
import streamlit.components.v1 as components

from file_manager import verifica_presenza_jellyfin, crea_cartella_film, rimuovi_cartella_film, rinfresca_libreria_jellyfin
from estrattore import estrai_flussi

# Configurazione della pagina
st.set_page_config(
    page_title="VixSrc Media Center",
    page_icon="🎬",
    layout="wide"
)

# --- GESTIONE DEI PARAMETRI URL PER I DETTAGLI ---
query_params = st.query_params
content_id = query_params.get("id")
content_type = query_params.get("type", "movie")

# ==========================================
# 📄 PAGINA DEI DETTAGLI (SE UN ELEMENTO È CLICCATO)
# ==========================================
if content_id:
    if st.button("⬅️ Torna alla Home"):
        st.query_params.clear()
        st.rerun()

    dettagli = tmdb.get_tmdb_details(content_type, content_id)
    
    if not dettagli:
        altri_tipo = "tv" if content_type == "movie" else "movie"
        dettagli = tmdb.get_tmdb_details(altri_tipo, content_id)
        content_type = altri_tipo

    if dettagli:
        titolo = dettagli.get("title") or dettagli.get("name") or "Senza titolo"
        anno = (dettagli.get("release_date") or dettagli.get("first_air_date") or "")[:4]
        overview = dettagli.get("overview", "Nessuna descrizione disponibile.")
        poster_path = dettagli.get("poster_path")
        vote_average = dettagli.get("vote_average", 0)
        genres = ", ".join([g["name"] for g in dettagli.get("genres", [])])
        
        # Durata (per i film) o numero stagioni (per le serie TV)
        runtime_info = ""
        if content_type == "movie":
            runtime = dettagli.get("runtime")
            if runtime:
                runtime_info = f"⏱️ {runtime} min"
        else:
            seasons = dettagli.get("number_of_seasons")
            if seasons:
                runtime_info = f"📺 {seasons} Stagioni"

        # Recuperiamo anche il cast (crediti) se la funzione tmdb lo supporta
        cast_list = []
        try:
            credits = tmdb.get_tmdb_credits(content_type, content_id)
            if credits and "cast" in credits:
                cast_list = [actor["name"] for actor in credits["cast"][:5]] # Primi 5 attori
        except Exception:
            pass
        cast_str = ", ".join(cast_list) if cast_list else ""

        # Layout a due colonne per i dettagli (senza il banner gigante in alto)
        col_poster, col_info = st.columns([1, 2.5], gap="large")

        with col_poster:
            if poster_path:
                st.image(f"{tmdb.IMG_BASE_URL}{poster_path}", use_container_width=True)
            else:
                st.image("https://via.placeholder.com/300x450?text=No+Image", use_container_width=True)

        with col_info:
            st.title(f"{titolo} ({anno})")
            
            # Badge informativi (Rating, Genere, Durata)
            info_badges = []
            if vote_average > 0:
                info_badges.append(f"⭐ **{vote_average:.1f}/10**")
            if genres:
                info_badges.append(f"🎭 {genres}")
            if runtime_info:
                info_badges.append(runtime_info)
                
            if info_badges:
                st.markdown(" &nbsp;&bull;&nbsp; ".join(info_badges))
            
            # --- AGGIUNTA: SEZIONE TRAILER ---
            try:
                videos = tmdb.get_tmdb_videos(content_type, content_id)
                # Cerca prima un trailer ufficiale su YouTube in italiano o inglese
                trailer_key = None
                for v in videos:
                    if v.get("site") == "YouTube" and v.get("type") == "Trailer":
                        trailer_key = v.get("key")
                        break # Prende il primo utile
                
                if trailer_key:
                    # Usiamo un expander per mantenere la pagina pulita, 
                    # oppure un pulsante/container
                    with st.expander("🎬 Guarda il Trailer"):
                        st.video(f"https://www.youtube.com/watch?v={trailer_key}")
            except Exception:
                pass
            # ---------------------------------
            
            st.markdown("### Trama")
            st.write(overview)
            
            if cast_list:
                st.markdown("### Cast Principale")
                st.write(cast_str)
            
        st.markdown("---")
        
        # --- SEZIONE JELLYFIN CON CONTROLLO ESISTENZA E TMDB ID ---
        st.subheader("⚙️ Gestione File Jellyfin")
        
        # 1. Verifica se il film è già presente in libreria
        gia_in_libreria = verifica_presenza_jellyfin(content_type, content_id, titolo, anno)
        
        col_j1, col_j2 = st.columns(2)
        
        with col_j1:
            if gia_in_libreria:
                st.button("✅ Già in libreria", use_container_width=True, disabled=True)
            else:
                if st.button("➕ Aggiungi a Jellyfin", use_container_width=True):
                    with st.spinner("Estrazione flussi e creazione in corso..."):
                        try:
                            # Costruisce l'URL della sorgente usando il TMDB ID
                            # (Adatta "movie" o "tv" a seconda del content_type se necessario)
                            if content_type == "movie":
                                url_pagina = f"https://vixsrc.to/movie/{content_id}?lang=it"
                            else:
                                url_pagina = f"https://vixsrc.to/tv/{content_id}?lang=it"
                            
                            # Estrae i flussi audio e video
                            video_link, audio_link = estrai_flussi(url_pagina)
                            
                            if video_link:
                                # Chiama la tua funzione effettiva di creazione cartella/file
                                crea_cartella_film(content_id, titolo, anno, video_link, audio_link)

                                # --- ESEGUE IL REFRESH DI JELLYFIN ---
                                rinfresca_libreria_jellyfin()

                                st.success(f"'{titolo}' aggiunto e libreria Jellyfin aggiornata!")
                                st.rerun() # Ricarica per aggiornare immediatamente lo stato del bottone
                            else:
                                st.error("Impossibile estrarre i flussi video dal link sorgente.")
                        except Exception as e:
                            st.error(f"Errore durante l'aggiunta: {e}")
                    
        with col_j2:
            if st.button("🗑️ Rimuovi da Jellyfin", use_container_width=True, disabled=not gia_in_libreria):
                try:
                    # --- QUI METTI LA TUA FUNZIONE DI RIMOZIONE SE ESISTE ---
                    rimuovi_cartella_film(content_id, titolo, anno)

                    # --- ESEGUE IL REFRESH DI JELLYFIN ---
                    rinfresca_libreria_jellyfin()
                    
                    st.warning(f"File rimosso per '{titolo}'.")
                    st.rerun() # Ricarica per aggiornare lo stato
                except Exception as e:
                    st.error(f"Errore durante la rimozione: {e}")
                
    else:
        st.error("Impossibile caricare i dettagli del contenuto.")
        
    st.stop()


# ==========================================
# 🏠 HOME PAGE (SLIDER ORIZZONTALE + RICERCA)
# ==========================================
st.title("🎬 VixSrc Media Center")

# --- FUNZIONE PER RENDERIZZARE LO SCORRIMENTO ORIZZONTALE ---
def mostra_slider_orizzontale(titolo_sezione, items):
    st.subheader(titolo_sezione)
    
    if not items:
        st.info("Nessun contenuto disponibile.")
        return

    html_code = f"""
    <style>
    body {{
        background-color: transparent;
        color: white;
        font-family: sans-serif;
        margin: 0;
        padding: 5px 0;
    }}
    .scroll-container {{
        display: flex;
        overflow-x: auto;
        gap: 16px;
        padding-bottom: 15px;
        scroll-behavior: smooth;
        align-items: flex-start;
    }}
    .scroll-container::-webkit-scrollbar {{
        height: 8px;
    }}
    .scroll-container::-webkit-scrollbar-track {{
        background: rgba(255,255,255,0.05);
        border-radius: 4px;
    }}
    .scroll-container::-webkit-scrollbar-thumb {{
        background: rgba(150,150,150,0.5);
        border-radius: 4px;
    }}
    .scroll-item {{
        flex: 0 0 140px;
        text-align: center;
    }}
    .scroll-item a {{
        text-decoration: none;
        color: inherit;
        display: block;
    }}
    .scroll-item img {{
        width: 140px;
        height: 210px;
        object-fit: cover;
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        transition: transform 0.2s;
    }}
    .scroll-item img:hover {{
        transform: scale(1.03);
    }}
    .scroll-title {{
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
    }}
    .scroll-year {{
        font-size: 11px;
        color: #a0a0a0;
        margin-top: 2px;
    }}
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
        
        if poster_path:
            img_url = f"{tmdb.IMG_BASE_URL}{poster_path}"
        else:
            img_url = "https://via.placeholder.com/140x210?text=No+Image"
            
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


# --- FUNZIONE PER RENDERIZZARE LA GRIGLIA DI RICERCA ---
def mostra_griglia_ricerca(titolo_sezione, items):
    st.subheader(titolo_sezione)
    
    if not items:
        st.info("Nessun risultato trovato.")
        return

    num_righe = (len(items) + 5) // 6
    altezza_box = num_righe * 218

    html_code = f"""
    <style>
    body {{
        background-color: transparent;
        color: white;
        font-family: sans-serif;
        margin: 0;
        padding: 0;
    }}
    .grid-container {{
        display: flex;
        flex-wrap: wrap;
        gap: 16px;
        justify-content: flex-start;
        padding-bottom: 5px;
    }}
    .grid-item {{
        flex: 0 0 140px;
        text-align: center;
        margin-bottom: 15px;
    }}
    .grid-item a {{
        text-decoration: none;
        color: inherit;
        display: block;
    }}
    .grid-item img {{
        width: 140px;
        height: 210px;
        object-fit: cover;
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        transition: transform 0.2s;
    }}
    .grid-item img:hover {{
        transform: scale(1.03);
    }}
    .grid-title {{
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
    }}
    .grid-year {{
        font-size: 11px;
        color: #a0a0a0;
        margin-top: 2px;
    }}
    .grid-type {{
        font-size: 10px;
        color: #ff4b4b;
        text-transform: uppercase;
        font-weight: bold;
        margin-top: 1px;
    }}
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
            <a href="/?id={item.get('id')}&type={media_type}" target="vixsrc_details">
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


# --- 1. GESTIONE STATO PAGINA DI RICERCA ---
if "search_page" not in st.session_state:
    st.session_state.search_page = 1

query_ricerca = st.text_input("🔍 Cerca un film o una serie TV...", placeholder="Es. Interstellar, Breaking Bad...")

if "last_query" not in st.session_state:
    st.session_state.last_query = ""

if query_ricerca != st.session_state.last_query:
    st.session_state.search_page = 1
    st.session_state.last_query = query_ricerca

if query_ricerca:
    results, total_pages = tmdb.cerca_multimediale(query_ricerca, page=st.session_state.search_page)
    
    if results:
        mostra_griglia_ricerca(f"Risultati della ricerca per: '{query_ricerca}' (Pagina {st.session_state.search_page} di {total_pages})", results)
        
        if total_pages > 1:
            col_prec, col_info, col_succ = st.columns([1, 2, 1])
            
            with col_prec:
                if st.session_state.search_page > 1:
                    if st.button("⬅️ Precedente"):
                        st.session_state.search_page -= 1
                        st.rerun()
                        
            with col_info:
                st.markdown(f"<div style='text-align: center; margin-top: 5px;'>Pagina <b>{st.session_state.search_page}</b> di <b>{total_pages}</b></div>", unsafe_allow_html=True)
                
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