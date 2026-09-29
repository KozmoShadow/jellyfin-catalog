"""Backend per AnimeWorld: ricerca, dettagli ed episodi (link .mp4 diretti).

La libreria `animeworld` fa da sé scraping e header: `Episodio.links` restituisce
già gli URL `.mp4` dei mirror, quindi non serve alcuna estrazione con browser.
"""

import animeworld as aw


def cerca_anime(query):
    """Cerca un anime per titolo. Restituisce la lista di dizionari di AnimeWorld."""
    if not query:
        return []
    return aw.find(query)


def dettagli_anime(link):
    """Restituisce nome, trama, copertina e metadati (voto, stato, studio...) di un anime."""
    anime = aw.Anime(link)
    return {
        "nome": anime.getName(),
        "trama": anime.getTrama(),
        "copertina": anime.getCover(),
        "info": anime.getInfo(),
    }


def episodi(link):
    """Restituisce la lista degli oggetti Episodio di un anime.

    Nota: va chiamata una sola volta per anime e riusata, perché ogni chiamata
    riscarica la pagina della serie.
    """
    return aw.Anime(link).getEpisodes()


def link_mp4(episodio):
    """Ritorna l'URL `.mp4` diretto di un episodio (primo mirror disponibile)."""
    for server in episodio.links:
        if getattr(server, "link", None):
            return server.link
    return None


def lista_episodi(link):
    """Restituisce i numeri di episodio disponibili, come stringhe (es. ['1', '2', ...])."""
    return [str(ep.number) for ep in episodi(link)]


def link_episodio(link, numero_episodio):
    """Risolve l'URL `.mp4` diretto di un episodio (primo mirror disponibile)."""
    for ep in episodi(link):
        if str(ep.number) == str(numero_episodio):
            return link_mp4(ep)
    return None
