"""
Scraper pour les pages "script" du wiki Love and Deepspace (LADS).

Le HTML est récupéré via FlareSolverr (pour passer Cloudflare) en appelant
l'API MediaWiki `action=parse`, puis transformé en un transcript texte
linéaire (narration / dialogues / choix / messages téléphone / etc.).
"""

import json
from urllib.parse import unquote

import requests
from bs4 import BeautifulSoup, Tag

from app.config import settings

FLARESOLVERR_URL = settings.flaresolverr_url
SEPARATOR = "—" * 30
HEADER_WIDTH = 50


# ---------------------------------------------------------------------------
# Récupération de la page
# ---------------------------------------------------------------------------

def _build_api_url(url: str) -> tuple[str, str]:
    """Construit l'URL de l'API MediaWiki `action=parse` à partir d'une URL de page.

    Retourne (api_url, url_normalisée).
    """
    if not url.startswith("http"):
        url = "https://" + url
    url = unquote(url)  # décoder %27 -> ' etc.

    page_name = url.split("/wiki/")[-1]
    base = url.split("/wiki/")[0]
    api_url = f"{base}/api.php?action=parse&page={page_name}&prop=text&format=json"
    return api_url, url


def _fetch_via_flaresolverr(api_url: str, timeout_ms: int = 120_000) -> dict:
    """Interroge FlareSolverr et retourne le JSON MediaWiki décodé.

    Lève une RuntimeError si FlareSolverr renvoie un statut différent de "ok".
    """
    response = requests.post(FLARESOLVERR_URL, json={
        "cmd": "request.get",
        "url": api_url,
        "maxTimeout": timeout_ms,
    })
    result = response.json()

    if result.get("status") != "ok":
        raise RuntimeError(f"FlareSolverr: {result}")

    html_content = result["solution"]["response"]

    # FlareSolverr enveloppe la réponse JSON brute dans un <pre> HTML.
    pre = BeautifulSoup(html_content, "html.parser").find("pre")
    if pre:
        html_content = pre.get_text()

    return json.loads(html_content)


# ---------------------------------------------------------------------------
# Petits utilitaires génériques
# ---------------------------------------------------------------------------

def get_text(el: Tag | None) -> str:
    return el.get_text(strip=True) if el else ""


def has_class(el: Tag, cls: str) -> bool:
    return cls in (el.get("class") or [])


def has_any_class(el: Tag, classes: set[str]) -> bool:
    return bool(classes & set(el.get("class") or []))


def is_element(node) -> bool:
    return hasattr(node, "name") and node.name is not None


def emit_header(lines: list, title_text: str) -> None:
    lines.append(f"\n{'=' * HEADER_WIDTH}")
    lines.append(f"  {title_text.upper()}")
    lines.append(f"{'=' * HEADER_WIDTH}\n")


def emit_narration(lines: list, el: Tag) -> None:
    text = get_text(el)
    if text:
        lines.append(f"[Narration] {text}\n")


def emit_dialogue(lines: list, el: Tag) -> None:
    """Bloc `lads-script-dialogue-container` standard (un seul texte, speaker + text)."""
    speaker = get_text(el.find("p", class_="speaker")) or "?"
    text = get_text(el.find("p", class_="text"))
    if not text:
        return
    prefix = "  " if has_class(el, "right") else ""
    lines.append(f"{prefix}{speaker} : {text}\n")


def emit_centered(lines: list, el: Tag) -> None:
    """<p> centré : italique = effet sonore (*texte*), sinon horodatage/indication ([texte])."""
    text = get_text(el)
    if not text:
        return
    if el.find("i"):
        lines.append(f"*{text}*\n")
    else:
        lines.append(f"\n[{text}]\n")


def emit_location(lines: list, el: Tag) -> None:
    text = get_text(el)
    if text:
        lines.append(f"\n[{text}]\n")


def emit_message_box(lines: list, el: Tag) -> None:
    """Div `background:rgb(...)` utilisée pour les messages système courts."""
    text = get_text(el.find("p"))
    if not text:
        return
    if len(text) < 50 and '"' not in text:
        lines.append(f"\n[{text}]\n")
    else:
        lines.append(f"\n[Message] {text}\n")


def emit_narration_large(lines: list, container: Tag) -> None:
    """Bloc `narrationLarge` (texte immersif), avec ou sans bordure décorative."""
    border = container.find("div", class_="lads-script-narrationLarge-border")
    target = border if border else container

    for child in target.children:
        if isinstance(child, str):
            text = child.strip()
            if text:
                lines.append(f"[Narration] {text}\n")
        elif is_element(child):
            if child.name == "p":
                text = get_text(child)
                if text:
                    lines.append(f"[Narration] {text}\n")
            elif has_class(child, "script-location"):
                emit_location(lines, child)


# ---------------------------------------------------------------------------
# Dispatch générique — utilisé pour le contenu principal du script, mais
# aussi récursivement à l'intérieur des overlays, choix (tabber),
# téléphone, caméra, etc. C'est ce dispatch unique qui remplace les
# multiples copies quasi identiques de la version d'origine.
# ---------------------------------------------------------------------------

def parse_element(lines: list, el) -> None:
    if not is_element(el):
        return

    style = el.get("style") or ""
    classes = " ".join(el.get("class") or [])

    if has_class(el, "lads-script-narration"):
        emit_narration(lines, el)

    elif has_class(el, "lads-script-narrationLarge-top") or has_class(el, "lads-script-narrationLarge-bottom"):
        return  # purement décoratif

    elif has_class(el, "lads-script-narrationLarge-container"):
        emit_narration_large(lines, el)

    elif has_class(el, "lads-script-dialogue-container"):
        emit_dialogue(lines, el)

    elif has_class(el, "script-location"):
        emit_location(lines, el)

    elif has_class(el, "lads-script-container"):
        # Un bloc de script complet peut être imbriqué au milieu d'un autre
        # (ex: une scène "Kindled" insérée dans le fil narratif principal).
        # On le traite ici, à sa place, plutôt que de le laisser être
        # ré-ajouté à la fin par la boucle de haut niveau.
        lines.extend(parse_script_container(el))

    elif has_class(el, "overlay"):
        inner = el.find("div", style=lambda s: s and "position:relative" in s) or el
        for child in inner.children:
            parse_element(lines, child)

    elif el.name == "div" and "position:relative" in style:
        for child in el.children:
            parse_element(lines, child)

    elif has_class(el, "phone"):
        parse_phone(lines, el)

    elif has_class(el, "camera"):
        parse_camera(lines, el)

    elif "tabber" in classes or el.find("div", class_="tabber"):
        tabber = el if "tabber" in classes else el.find("div", class_="tabber")
        if tabber:
            parse_tabber(lines, tabber)

    elif el.name == "div" and "background:rgb" in style:
        emit_message_box(lines, el)

    elif el.name == "hr":
        lines.append(f"\n{SEPARATOR}\n")

    elif el.name == "center":
        text = get_text(el.find("div"))
        if text:
            lines.append(f"\n{text}\n")

    elif el.name == "p" and "text-align:center" in style:
        emit_centered(lines, el)

    elif el.name == "p" and el.find("i"):
        text = get_text(el)
        if text and len(text) > 2:
            lines.append(f"*{text}*\n")

    elif el.name == "p":
        text = get_text(el)
        if "START OF KINDLED" in text or "END OF KINDLED" in text:
            lines.append(f"\n*** {text} ***\n")


def parse_tabber(lines: list, tabber: Tag) -> None:
    """Widget de choix. Un seul onglet = réponse directe, sinon liste numérotée."""
    tabs = tabber.find_all("a", class_="tabber__tab")
    panels = tabber.find_all("article", class_="tabber__panel")

    if len(tabs) <= 1:
        for panel in panels:
            for child in panel.children:
                parse_element(lines, child)
        return

    lines.append("\nChoices:\n")
    for i, (tab, panel) in enumerate(zip(tabs, panels), 1):
        lines.append(f"{i:02d}. {get_text(tab)}\n")
        for child in panel.children:
            parse_element(lines, child)
    lines.append(f"\n{SEPARATOR}\n")


def emit_phone_bubble(lines: list, el: Tag) -> None:
    """Dialogue dans une conversation téléphone : peut contenir plusieurs bulles
    de texte (on ignore les bulles de message vocal, sans transcription)."""
    speaker = get_text(el.find("p", class_="speaker")) or "?"

    texts = []
    for bubble in el.find_all("div", class_="text"):
        if bubble.find(class_="voiceMessageBars"):
            continue
        text = get_text(bubble)
        if text:
            texts.append(text)

    if not texts:
        text = get_text(el.find("p", class_="text"))
        if text:
            texts.append(text)

    prefix = "  " if has_class(el, "right") else ""
    for text in texts:
        lines.append(f"{prefix}{speaker} : {text}\n")


def parse_phone(lines: list, element: Tag) -> None:
    name = get_text(element.find("p", class_="name")) or "Conversation"
    is_call = element.find("p", class_="calling") is not None

    lines.append(f"\n[{'Appel avec' if is_call else 'Conversation avec'} {name}]\n")

    for child in element.children:
        if not is_element(child):
            continue
        style = child.get("style") or ""

        if child.name == "p" and "text-align:center" in style:
            text = get_text(child)
            if text:
                lines.append(f"[{text}]\n")
        elif has_class(child, "lads-script-narration"):
            emit_narration(lines, child)
        elif has_class(child, "lads-script-dialogue-container"):
            emit_phone_bubble(lines, child)
        elif "tabber" in " ".join(child.get("class") or []):
            parse_tabber(lines, child)

    lines.append(f"[Fin {'appel' if is_call else 'conversation'}]\n")


def parse_camera(lines: list, element: Tag) -> None:
    lines.append("\n[Enregistrement]\n")

    for child in element.children:
        if not is_element(child):
            continue
        if has_class(child, "lads-script-narration"):
            emit_narration(lines, child)
        elif has_class(child, "lads-script-dialogue-container"):
            emit_dialogue(lines, child)
        # les divs de mise en page ("display:grid") sont ignorées implicitement

    lines.append("[Fin enregistrement]\n")


# ---------------------------------------------------------------------------
# Parseurs de conteneurs de haut niveau
# ---------------------------------------------------------------------------

def parse_book_script(container: Tag) -> list[str]:
    """Page de type World Underneath (texte de livre en paragraphes)."""
    lines: list[str] = []

    title_tag = container.find("p", class_="title")
    if title_tag:
        for a in title_tag.find_all("a"):  # retirer le lien "Edit"
            a.decompose()
        emit_header(lines, get_text(title_tag))

    for el in container.children:
        if not is_element(el):
            continue
        if el.name == "br":
            lines.append("")
        elif el.name == "p" and not has_class(el, "title"):
            text = get_text(el)
            if text and len(text) > 2:
                lines.append(f"{text}\n")

    return lines


def parse_secret_time(container: Tag) -> list[str]:
    """Bloc Secret Time (monologue audio)."""
    lines: list[str] = []

    title_tag = container.find("p", class_="title")
    if title_tag:
        emit_header(lines, get_text(title_tag))

    audio_tag = container.find("p", class_="audio")
    if audio_tag:
        lines.append(f"[{get_text(audio_tag)}]\n")

    skip_classes = {"title", "audio", "lads-dynamic-image"}
    for el in container.children:
        if not is_element(el) or el.name != "p":
            continue
        if not has_any_class(el, skip_classes):
            text = get_text(el)
            if text:
                lines.append(f"{text}\n")

    return lines


def _is_hidden_div(div: Tag) -> bool:
    """Div d'accessibilité factice (ex: `aria-hidden="true"` + `display:none`)."""
    style = (div.get("style") or "").replace(" ", "")
    return div.get("aria-hidden") == "true" or "display:none" in style


def _find_script_content(container: Tag) -> Tag | None:
    """Localise le conteneur direct du contenu du script.

    Le cas le plus courant est `div.mw-collapsible-content`. Certaines pages
    (ex: les scripts "Kindled") n'ont pas ce conteneur : le contenu est
    simplement enveloppé dans un ou deux `<div>` sans classe. Dans ce cas,
    il faut ignorer les divs d'accessibilité cachés (souvent le tout premier
    enfant) et, le cas échéant, descendre d'un niveau supplémentaire quand
    ce div n'a lui-même qu'un unique enfant div sans classe.
    """
    collapsible = container.find("div", class_="mw-collapsible-content")
    if collapsible:
        return collapsible

    for child in container.children:
        if not is_element(child) or child.name != "div" or child.get("class"):
            continue
        if _is_hidden_div(child):
            continue

        element_children = [c for c in child.children if is_element(c)]
        if len(element_children) == 1 and element_children[0].name == "div" and not element_children[0].get("class"):
            return element_children[0]
        return child

    return None


def parse_script_container(container: Tag) -> list[str]:
    """Bloc de script principal (narration / dialogues / choix / téléphone / ...)."""
    lines: list[str] = []

    section_title = container.find("p", class_="script-title")
    if section_title:
        emit_header(lines, get_text(section_title))

    content = _find_script_content(container)
    if not content:
        return lines

    for element in content.children:
        parse_element(lines, element)

    return lines


# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------

def scrape_script(url: str) -> dict:
    api_url, clean_url = _build_api_url(url)
    print(f"[1] Envoi à FlareSolverr : {api_url}")

    try:
        data = _fetch_via_flaresolverr(api_url)
    except RuntimeError as exc:
        return {"title": "Erreur", "url": clean_url, "script": str(exc)}

    print("[2] Réponse FlareSolverr reçue")

    if "error" in data:
        return {"title": "Erreur", "url": clean_url, "script": data["error"]["info"]}

    html = data["parse"]["text"]["*"]
    title = data["parse"]["title"]
    print(f"[3] Parsing du script : {title}")

    soup = BeautifulSoup(html, "html.parser")
    lines: list[str] = []

    for container in soup.find_all("div", class_="lads-bookScript-worldUnderneath-container"):
        lines.extend(parse_book_script(container))

    for container in soup.find_all("div", class_="lads-secretTime-container"):
        lines.extend(parse_secret_time(container))

    # On ne traite que les conteneurs de premier niveau : un conteneur
    # imbriqué dans un autre (ex: une scène "Kindled" au milieu d'un
    # chapitre) est déjà géré à sa place par parse_element -> le retraiter
    # ici le dupliquerait et le ferait apparaître à la fin du transcript.
    all_script_containers = soup.find_all("div", class_="lads-script-container")
    top_level_containers = [
        c for c in all_script_containers
        if not c.find_parent("div", class_="lads-script-container")
    ]
    for container in top_level_containers:
        lines.extend(parse_script_container(container))

    print(f"[4] Terminé — {len(lines)} lignes extraites")

    return {
        "title": title,
        "url": clean_url,
        "script": "\n".join(lines),
    }