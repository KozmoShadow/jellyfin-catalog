import sys
from pathlib import Path

# Aggiunge la radice del progetto al path per importare i moduli di backend
sys.path.append(str(Path(__file__).resolve().parent.parent))

import streamlit as st


st.set_page_config(
    page_title="VixSrc Media Center",
    page_icon="🎬",
    layout="wide",
)

# ==========================================
# 🧭 NAVIGAZIONE
# ==========================================
# Questo file è solo l'entry point: registra le pagine e delega l'esecuzione a
# st.navigation. Il contenuto della Home vive in viste/Home.py, così non c'è
# ricorsione. Manutenzione sta sotto la sezione "Serie TV".
_navigazione = st.navigation(
    {
        "": [
            st.Page("viste/Home.py", title="Home", icon="🏠", default=True),
            st.Page("viste/Film.py", title="Film", icon="🎞️", url_path="Film"),
            st.Page("viste/Serie TV.py", title="Serie TV", icon="📺", url_path="Serie_TV"),
            st.Page("viste/Anime.py", title="Anime", icon="⛩️", url_path="Anime"),
        ],
        "Serie TV": [
            st.Page("viste/Serie TV/2_Manutenzione.py", title="🛠️ Manutenzione"),
        ],
    }
)
_navigazione.run()
