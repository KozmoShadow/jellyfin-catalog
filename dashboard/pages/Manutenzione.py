import sys
from pathlib import Path

# Aggiunge la radice del progetto al path per importare i moduli di backend
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

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
    "i mirror degli anime cambiano. Qui puoi controllare quali file della libreria "
    "non funzionano piu e rigenerarli."
)

# --- Stato dedicato, così i risultati sopravvivono ai rerun di Streamlit ---
if "manut_voci" not in st.session_state:
    st.session_state.manut_voci = []
if "manut_verificate" not in st.session_state:
    st.session_state.manut_verificate = False

EMOJI_TIPO = {"film": "🎞️", "serie": "📺", "anime": "⛩️"}


def _conteggi(voci):
    rotti = [v for v in voci if v.get("stato") == "rotto"]
    ok = [v for v in voci if v.get("stato") == "ok"]
    return ok, rotti


# ==========================================
# 1. SCANSIONE + VERIFICA
# ==========================================
col_scan, col_ver = st.columns(2)

with col_scan:
    if st.button("🔍 Scansiona il catalogo", use_container_width=True):
        with st.spinner("Cerco i file nelle librerie..."):
            st.session_state.manut_voci = manutenzione.scansiona_catalogo()
        st.session_state.manut_verificate = False
        st.success(f"Trovati {len(st.session_state.manut_voci)} file.")

with col_ver:
    if st.button(
        "🧪 Verifica i link",
        use_container_width=True,
        disabled=not st.session_state.manut_voci,
    ):
        barra = st.progress(0.0, text="Verifica in corso...")
        manutenzione.verifica_voci(
            st.session_state.manut_voci,
            progress_cb=lambda fatti, tot: barra.progress(
                fatti / tot, text=f"Verificati {fatti}/{tot}..."
            ),
        )
        barra.empty()
        st.session_state.manut_verificate = True
        st.rerun()

voci = st.session_state.manut_voci

if not voci:
    st.info("Premi **Scansiona il catalogo** per iniziare.")
    st.stop()

# Messaggi rimandati dopo un rerun (altrimenti spariscono)
if st.session_state.get("manut_msg"):
    testo, livello = st.session_state.pop("manut_msg")
    (st.success if livello == "ok" else st.warning)(testo)


def _riverifica(voci_da_verificare):
    """Ri-verifica i link delle voci indicate, aggiornando lo stato in sessione."""
    manutenzione.verifica_voci(voci_da_verificare)

# ==========================================
# 2. RIEPILOGO
# ==========================================
if st.session_state.manut_verificate:
    ok, rotti = _conteggi(voci)
    c1, c2, c3 = st.columns(3)
    c1.metric("File nel catalogo", len(voci))
    c2.metric("✅ Funzionanti", len(ok))
    c3.metric("❌ Da rigenerare", len(rotti))

    if rotti:
        # Raggruppa i rotti per tipo/opera per rigenerarli a blocchi
        gruppi = {}
        for v in rotti:
            chiave = (v["tipo"], v["titolo"])
            gruppi.setdefault(chiave, []).append(v)

        st.subheader("❌ File da rigenerare")
        for (tipo, titolo), gruppo in gruppi.items():
            episodi = ", ".join(f"E{v['episodio']:02d}" for v in gruppo if v.get("episodio"))
            etichetta = f"{EMOJI_TIPO.get(tipo, '📄')} {titolo}"
            if episodi:
                etichetta += f" — {episodi}"
            st.write(f"- {etichetta}")

        st.divider()
        st.subheader("🔧 Rigenerazione")

        col_a, col_b = st.columns(2)

        with col_a:
            if st.button(f"♻️ Rigenera tutti i {len(rotti)} file rotti", use_container_width=True):
                barra = st.progress(0.0, text="Rigenerazione in corso...")
                rigenerati, falliti = 0, 0
                toccati = []

                for i, (chiave, gruppo) in enumerate(gruppi.items(), start=1):
                    tipo, titolo = chiave
                    barra.progress(i / len(gruppi), text=f"{titolo}...")

                    if tipo == "anime":
                        esito_ok, esito_falliti, _ = manutenzione.rigenera_episodi_anime(titolo, gruppo)
                        rigenerati += esito_ok
                        falliti += esito_falliti
                        if esito_ok:
                            toccati.extend(gruppo)
                    elif tipo == "film":
                        esito_ok, _ = manutenzione.rigenera_film(gruppo[0])
                        rigenerati += 1 if esito_ok else 0
                        falliti += 0 if esito_ok else 1
                        if esito_ok:
                            toccati.append(gruppo[0])
                    else:
                        for voce in gruppo:
                            esito_ok, _ = manutenzione.rigenera_episodio_serie(voce)
                            rigenerati += 1 if esito_ok else 0
                            falliti += 0 if esito_ok else 1
                            if esito_ok:
                                toccati.append(voce)

                barra.empty()
                # Ri-verifica solo i file appena toccati, così il riepilogo si aggiorna
                if toccati:
                    _riverifica(toccati)
                st.session_state.manut_msg = (
                    (f"{rigenerati} file rigenerati." if not falliti
                     else f"{rigenerati} rigenerati, {falliti} non riusciti."),
                    "ok" if not falliti else "warn",
                )
                st.rerun()

        with col_b:
            if st.button("🗑️ Rimuovi tutti i file rotti", use_container_width=True):
                st.session_state.manut_conferma_rimozione = True

        if st.session_state.get("manut_conferma_rimozione"):
            st.warning(
                "Confermi di rimuovere i file segnalati come rotti? "
                "Verranno cancellati `.m3u8` e `.strm` (la cartella resta)."
            )
            if st.button("Sì, rimuovi i file rotti"):
                rimossi = 0
                for voce in rotti:
                    for percorso in (voce.get("file_media"), voce.get("file_strm")):
                        if percorso and Path(percorso).exists():
                            Path(percorso).unlink()
                            rimossi += 1
                st.session_state.manut_conferma_rimozione = False
                rinfresca_libreria_jellyfin()
                # Ri-scansiona: i file rimossi spariscono dal riepilogo
                st.session_state.manut_voci = manutenzione.scansiona_catalogo()
                st.session_state.manut_verificate = False
                st.session_state.manut_msg = (f"{rimossi} file rimossi.", "ok")
                st.rerun()
else:
    st.info("Premi **Verifica i link** per controllare quali file non funzionano piu.")

# ==========================================
# 3. DETTAGLIO COMPLETO
# ==========================================
with st.expander("📋 Dettaglio di tutti i file scansionati"):
    ordinate = sorted(
        voci,
        key=lambda v: (v.get("stato") != "rotto", v["tipo"], v["titolo"], v.get("episodio") or 0),
    )
    righe = []
    for v in ordinate:
        posizione = f"S{int(v['stagione']):02d}E{int(v['episodio']):02d}" if v.get("episodio") else "—"
        stato = {"ok": "✅ ok", "rotto": "❌ rotto", "vuoto": "⚠️ vuoto"}.get(v.get("stato"), "—")
        righe.append({
            "Tipo": v["tipo"],
            "Titolo": v["titolo"],
            "Posizione": posizione,
            "Stato": stato,
            "Link verificati": len(v.get("links", [])),
        })
    st.dataframe(righe, use_container_width=True, hide_index=True)
