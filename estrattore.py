"""Estrazione dei flussi video/audio da una pagina vixsrc tramite Playwright.

Il browser headless viene creato una volta per thread e riutilizzato tra le
chiamate: aprire e chiudere Chromium per ogni episodio era la parte più lenta
dell'aggiunta di una serie intera. Lo stato vive in una variabile per-thread,
quindi non serve alcun lock: Streamlit esegue ogni sessione in un thread suo.
"""

import threading

from playwright.sync_api import sync_playwright

# Attese esplicite: `timeout=0` in Playwright significa "per sempre", quindi un
# selettore che non compare più bloccherebbe l'operazione senza errore.
TIMEOUT_NAVIGAZIONE = 30_000   # ms, caricamento pagina
TIMEOUT_IMPOSTAZIONI = 5_000   # ms, pulsante Settings nel player
TIMEOUT_QUALITA = 5_000        # ms, pulsante 1080p
ATTESA_RETE = 2_000            # ms, dopo l'avvio del player
ATTESA_FINALE = 4_000          # ms, per intercettare le richieste dei flussi

_stato = threading.local()


def _avvia_playwright():
    """Crea (una volta per thread) Playwright, browser e contesto riutilizzabili."""
    p = sync_playwright().start()
    try:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
    except Exception:
        # Lancio fallito (es. binari mancanti): non lasciare Playwright appeso.
        try:
            p.stop()
        except Exception:
            pass
        raise
    return p, browser, context


def _stato_thread():
    """Restituisce lo stato per il thread corrente, creandolo se serve."""
    stato = getattr(_stato, "valore", None)
    if stato is None:
        stato = _avvia_playwright()
        _stato.valore = stato
    return stato


def _scarta_stato():
    """Chiude lo stato del thread: usato quando il browser risulta morto."""
    stato = getattr(_stato, "valore", None)
    _stato.valore = None
    if not stato:
        return
    p, browser, _ = stato
    try:
        browser.close()
    except Exception:
        pass
    try:
        p.stop()
    except Exception:
        pass


def _chiudi_risorse():
    """Chiude browser e Playwright del thread (chiamare a fine lavoro)."""
    _scarta_stato()


def estrai_flussi(url_pagina):
    """Apre `url_pagina`, seleziona 1080p se disponibile e restituisce (video, audio)."""
    try:
        return _estrai_una_volta(url_pagina)
    except Exception:
        # Il browser potrebbe essere morto (o mai avviato per colpa dei binari):
        # si butta lo stato e si riprova una volta da zero. Se anche il secondo
        # tentativo fallisce, l'eccezione risale al chiamante.
        _scarta_stato()
        return _estrai_una_volta(url_pagina)


def _estrai_una_volta(url_pagina):
    video_link_1080 = None
    video_link_720 = None
    audio_link = None

    def handle_response(response):
        nonlocal video_link_1080, video_link_720, audio_link
        url = response.url
        if "type=video" in url and "rendition=1080" in url:
            video_link_1080 = url
        elif "type=video" in url and "rendition=720" in url:
            video_link_720 = url
        elif "type=audio&rendition" in url:
            audio_link = url

    _, _, context = _stato_thread()
    page = context.new_page()
    page.on("response", handle_response)

    try:
        page.goto(url_pagina, timeout=TIMEOUT_NAVIGAZIONE)
        page.wait_for_timeout(ATTESA_RETE)

        try:
            frame = page.frame_locator("iframe").first

            settings_btn = frame.get_by_role("button", name="Settings")
            settings_btn.wait_for(state="visible", timeout=TIMEOUT_IMPOSTAZIONI)
            settings_btn.click()

            page.wait_for_timeout(ATTESA_RETE)

            quality_btn = frame.locator("[aria-label='1080p']")
            quality_btn.wait_for(state="visible", timeout=TIMEOUT_QUALITA)
            quality_btn.click()
        except Exception:
            # Player con layout diverso o 1080p assente: si prosegue con quello
            # che le risposte di rete hanno già fornito (es. 720p).
            pass

        page.wait_for_timeout(ATTESA_FINALE)
    finally:
        page.close()

    final_video = video_link_1080 if video_link_1080 else video_link_720
    return final_video, audio_link
