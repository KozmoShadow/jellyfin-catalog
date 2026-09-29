import sys
from pathlib import Path

# Aggiunge la radice del progetto al path per importare i moduli di backend
sys.path.append(str(Path(__file__).resolve().parent.parent.parent.parent))

import streamlit as st

import manutenzione
from file_manager import rinfresca_libreria_jellyfin

st.set_page_config(
    page_title="Manutenzione catalogo",
    page_icon="🛠️",
    layout="wide",
)

st.title("🛠️ Manutenzione catalogo")

st.write(
    "I link di film e serie (firmati vixsrc) **scadono** col tempo, e a volte anche "
    "i mirror degli anime cambiano. Ogni sezione qui sotto controlla e rigenera "
    "solo una libreria."
)

# Una sezione indipendente per libreria: ognuna ha il suo stato.
SEZIONI = [
    {"chiave": "film", "titolo": "🎞️ Film", "scan": manutenzione.scansiona_film},
    {"chiave": "serie", "titolo": "📺 Serie TV", "scan": manutenzione.scansiona_serie},
    {"chiave": "anime", "titolo": "⛩️ Anime", "scan": manutenzione.scansiona_anime},
]

for sezione in SEZIONI:
    st.session_state.setdefault(f"manut_{sezione['chiave']}_voci", [])

# Quante verifiche in parallelo (piu alto = piu veloce ma piu aggressivo sui server)
MAX_WORKERS = 8


def _conteggi(voci):
    da_verificare = [v for v in voci if v.get("stato") == "da verificare"]
    rotti = [v for v in voci if v.get("stato") == "rotto"]
    ok = [v for v in voci if v.get("stato") == "ok"]
    return ok, rotti, da_verificare


def _verifica(voci, chiave):
    """Verifica in parallelo le voci indicate, con barra di avanzamento."""
    if not voci:
        return
    barra = st.progress(0.0, text="Verifica in corso...")
    manutenzione.verifica_voci(
        voci,
        max_workers=MAX_WORKERS,
        progress_cb=lambda fatti, tot: barra.progress(
            fatti / tot, text=f"Verificati {fatti}/{tot}..."
        ),
    )
    barra.empty()


def _selezione(voci, opera, stagioni, episodi, ambito):
    """Filtra le voci in base ai controlli della sezione."""
    sel = voci
    if opera != "Tutte":
        sel = [v for v in sel if v["titolo"] == opera]
    if stagioni:
        sel = [v for v in sel if v.get("stagione") in stagioni]
    if episodi:
        sel = [v for v in sel if v.get("episodio") in episodi]
    if ambito == "Solo i non ancora verificati":
        sel = [v for v in sel if v.get("stato") == "da verificare"]
    elif ambito == "Solo i file rotti":
        sel = [v for v in sel if v.get("stato") == "rotto"]
    return sel


def _rigenera_voce(tipo, voce):
    """Rigenera un singolo file. Per gli anime il gruppo intero è gestito a parte."""
    if tipo == "film":
        return manutenzione.rigenera_film(voce)
    return manutenzione.rigenera_episodio_serie(voce)


def _sezione(sezione):
    chiave = sezione["chiave"]
    prefisso = f"manut_{chiave}_"
    voci = st.session_state[prefisso + "voci"]

    # --- Messaggi rimandati dopo un rerun (altrimenti spariscono) ---
    if st.session_state.get(prefisso + "msg"):
        testo, livello = st.session_state.pop(prefisso + "msg")
        (st.success if livello == "ok" else st.warning)(testo)

    col_scan, col_ver = st.columns(2)

    with col_scan:
        if st.button("🔍 Scansiona", use_container_width=True, key=prefisso + "btn_scan"):
            with st.spinner("Cerco i file nella libreria..."):
                st.session_state[prefisso + "voci"] = sezione["scan"]()
            st.success(f"Trovati {len(st.session_state[prefisso + 'voci'])} file.")
            st.rerun()

    with col_ver:
        if st.button(
            "🧪 Verifica tutto",
            use_container_width=True,
            key=prefisso + "btn_ver",
            disabled=not voci,
        ):
            _verifica(voci, chiave)
            st.rerun()

    if not voci:
        st.info("Premi **Scansiona** per iniziare.")
        return

    ok, rotti, da_verificare = _conteggi(voci)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("File", len(voci))
    c2.metric("✅ Funzionanti", len(ok))
    c3.metric("❌ Da rigenerare", len(rotti))
    c4.metric("⏳ Da verificare", len(da_verificare))

    # ==========================================
    # CONTROLLO MIRATO (una sola opera/stagione)
    # ==========================================
    with st.expander("🎯 Controllo mirato (una sola opera, comodo con le serie lunghe)"):
        st.caption(
            "Per esempio su un anime con centinaia di episodi puoi controllare "
            "una sola stagione o un solo episodio, senza rifare tutto."
        )
        titoli = sorted({v["titolo"] for v in voci})
        opera = st.selectbox("Opera", ["Tutte"] + titoli, key=prefisso + "opera")

        stagioni_scelte, episodi_scelti = [], []
        if opera != "Tutte":
            stagioni = sorted({v["stagione"] for v in voci if v["titolo"] == opera and v.get("stagione")})
            if stagioni:
                stagioni_scelte = st.multiselect(
                    "Stagioni", stagioni, default=stagioni, key=prefisso + "stag"
                )
            if len(stagioni_scelte) == 1:
                stagione_unica = stagioni_scelte[0]
                episodi = sorted({
                    v["episodio"] for v in voci
                    if v["titolo"] == opera and v.get("stagione") == stagione_unica
                })
                if len(episodi) > 1:
                    episodi_scelti = st.multiselect(
                        "Episodi (opzionale)", episodi, default=[],
                        key=prefisso + "ep", help="Vuoto = tutti gli episodi della stagione.",
                    )

        ambito = st.radio(
            "Cosa controllare",
            ["Tutta la selezione", "Solo i non ancora verificati", "Solo i file rotti"],
            key=prefisso + "ambito",
        )

        selezione = _selezione(voci, opera, stagioni_scelte, episodi_scelti, ambito)
        st.caption(f"La selezione contiene **{len(selezione)}** file.")

        if st.button(
            f"🧪 Verifica selezione ({len(selezione)})",
            key=prefisso + "btn_ver_sel",
            disabled=not selezione,
        ):
            _verifica(selezione, chiave)
            st.rerun()

    # ==========================================
    # DETTAGLIO
    # ==========================================
    filtro_tabella = st.selectbox(
        "Mostra nella tabella",
        ["Rotti e da verificare", "Tutti", "Solo i file rotti", "Solo i non verificati"],
        key=prefisso + "filtro_tab",
    )
    if filtro_tabella == "Solo i file rotti":
        mostra = rotti
    elif filtro_tabella == "Solo i non verificati":
        mostra = da_verificare
    elif filtro_tabella == "Rotti e da verificare":
        mostra = rotti + da_verificare
    else:
        mostra = voci

    ordinate = sorted(
        mostra,
        key=lambda v: (v.get("stato") != "rotto", v["titolo"], v.get("episodio") or 0),
    )
    righe = []
    for v in ordinate:
        posizione = f"S{int(v['stagione']):02d}E{int(v['episodio']):02d}" if v.get("episodio") else "—"
        stato = {"ok": "✅ ok", "rotto": "❌ rotto", "vuoto": "⚠️ vuoto"}.get(v.get("stato"), "⏳ da verificare")
        righe.append({
            "Titolo": v["titolo"],
            "Posizione": posizione,
            "Stato": stato,
        })
    if righe:
        st.dataframe(righe, use_container_width=True, hide_index=True)
    else:
        st.success("Niente da mostrare con questo filtro. 🎉")

    # ==========================================
    # RIGENERAZIONE / RIMOZIONE DEI FILE ROTTI
    # ==========================================
    if not rotti:
        return

    st.divider()
    st.subheader("❌ File rotti")

    if chiave == "anime":
        # Gli episodi dello stesso titolo si rigenerano insieme (una ricerca AnimeWorld)
        gruppi = {}
        for v in rotti:
            gruppi.setdefault(v["titolo"], []).append(v)
        st.caption("Per gli anime, gli episodi dello stesso titolo si rigenerano insieme.")
        for titolo, gruppo in gruppi.items():
            episodi = ", ".join(f"E{v['episodio']:02d}" for v in gruppo if v.get("episodio"))
            cols = st.columns([3, 1, 1])
            cols[0].write(f"❌ **{titolo}** — {episodi}")
            if cols[1].button("♻️ Rigenera", key=f"{prefisso}rig_{titolo}"):
                with st.spinner(f"Rigenero {titolo}..."):
                    ok_n, falliti, _ = manutenzione.rigenera_episodi_anime(titolo, gruppo)
                if ok_n:
                    manutenzione.verifica_voci(gruppo)
                st.session_state[prefisso + "msg"] = (
                    f"{titolo}: {ok_n} rigenerati" + (f", {falliti} falliti." if falliti else "."),
                    "ok" if not falliti else "warn",
                )
                st.rerun()
            if cols[2].button("🗑️ Rimuovi", key=f"{prefisso}rm_{titolo}"):
                rimossi = 0
                for voce in gruppo:
                    for percorso in (voce.get("file_media"), voce.get("file_strm")):
                        if percorso and Path(percorso).exists():
                            Path(percorso).unlink()
                            rimossi += 1
                rinfresca_libreria_jellyfin()
                st.session_state[prefisso + "voci"] = sezione["scan"]()
                st.session_state[prefisso + "msg"] = (f"{titolo}: {rimossi} file rimossi.", "ok")
                st.rerun()
    else:
        for v in rotti:
            posizione = f"S{int(v['stagione']):02d}E{int(v['episodio']):02d}" if v.get("episodio") else ""
            etichetta = f"❌ **{v['titolo']}** {posizione}".strip()
            chiave_voce = f"{v['titolo']}_{v.get('stagione')}_{v.get('episodio')}"
            cols = st.columns([3, 1, 1])
            cols[0].write(etichetta)
            if cols[1].button("♻️ Rigenera", key=f"{prefisso}rig_{chiave_voce}"):
                with st.spinner(f"Rigenero {v['titolo']}..."):
                    esito_ok, messaggio = _rigenera_voce(chiave, v)
                if esito_ok:
                    manutenzione.verifica_voci([v])
                st.session_state[prefisso + "msg"] = (
                    f"{v['titolo']}: {'rigenerato.' if esito_ok else 'non riuscito (' + messaggio + ').'}",
                    "ok" if esito_ok else "warn",
                )
                st.rerun()
            if cols[2].button("🗑️ Rimuovi", key=f"{prefisso}rm_{chiave_voce}"):
                for percorso in (v.get("file_media"), v.get("file_strm")):
                    if percorso and Path(percorso).exists():
                        Path(percorso).unlink()
                rinfresca_libreria_jellyfin()
                st.session_state[prefisso + "voci"] = sezione["scan"]()
                st.session_state[prefisso + "msg"] = (f"{v['titolo']}: file rimosso.", "ok")
                st.rerun()


tab_film, tab_serie, tab_anime = st.tabs([s["titolo"] for s in SEZIONI])
for tab, sezione in zip([tab_film, tab_serie, tab_anime], SEZIONI):
    with tab:
        _sezione(sezione)
