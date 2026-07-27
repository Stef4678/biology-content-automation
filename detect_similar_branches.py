import os
import unicodedata
import pandas as pd
from collections import defaultdict

BASE_DIR = "proiect_biologie"
INDEX_PATH = os.path.join(BASE_DIR, "index_continut.csv")


def print_safe(text: str):
    """Print robust, care nu crapa pe diacritice in CP1252."""
    try:
        print(text)
    except UnicodeEncodeError:
        safe = text.encode("ascii", "replace").decode("ascii")
        print(safe)


def normalize_text_basic(text: str) -> str:
    """Normalizare de baza: elimina diacritice, reduce spatii si pune litere mici."""
    if not isinstance(text, str):
        text = str(text)
    nfkd = unicodedata.normalize("NFKD", text)
    no_diacritics = "".join(ch for ch in nfkd if not unicodedata.combining(ch))
    no_diacritics = " ".join(no_diacritics.split()).strip().lower()
    return no_diacritics


def strip_paranteze(text: str) -> str:
    """Elimina continutul dintre paranteze, pentru a obtine 'nucleul' denumirii."""
    out = []
    depth = 0
    for ch in text:
        if ch == "(":
            depth += 1
        elif ch == ")":
            if depth > 0:
                depth -= 1
        else:
            if depth == 0:
                out.append(ch)
    return "".join(out)


def normalize_for_group(text: str) -> str:
    """
    Normalizare pentru detectarea 'dublurilor':
    - elimina diacritice
    - elimina continutul dintre paranteze
    - reduce spatii si lower-case
    """
    base = strip_paranteze(text)
    return normalize_text_basic(base)


def detecteaza_grupuri(col_name: str, df: pd.DataFrame):
    valori = sorted(set(df[col_name].dropna().tolist()))
    grupuri = defaultdict(list)

    for v in valori:
        key = normalize_for_group(v)
        grupuri[key].append(v)

    return grupuri


def detecteaza_ramuri_si_subramuri_similare():
    if not os.path.exists(INDEX_PATH):
        print_safe("Nu exista index_continut.csv.")
        return

    df = pd.read_csv(INDEX_PATH)

    if "Ramura" not in df.columns or "Subramura" not in df.columns:
        print_safe("Indexul nu contine coloanele 'Ramura' si/sau 'Subramura'.")
        return

    grupuri_ramura = detecteaza_grupuri("Ramura", df)
    grupuri_subramura = detecteaza_grupuri("Subramura", df)

    print_safe("=== Grupuri de RAMURI cu forma normalizata similara (ignorand diacritice/paranteze) ===\n")
    candidat_map_ramura = []

    for key, lista in grupuri_ramura.items():
        if len(lista) <= 1:
            continue

        print_safe(f"Forma normalizata: '{key}'")
        for r in lista:
            print_safe(f"  - {r}")
        print_safe("")

        canon = lista[0]
        for r in lista:
            if r != canon:
                candidat_map_ramura.append((r, canon))

    print_safe("=== Grupuri de SUBRAMURI cu forma normalizata similara (ignorand diacritice/paranteze) ===\n")
    candidat_map_subramura = []

    for key, lista in grupuri_subramura.items():
        if len(lista) <= 1:
            continue

        print_safe(f"Forma normalizata: '{key}'")
        for s in lista:
            print_safe(f"  - {s}")
        print_safe("")

        canon = lista[0]
        for s in lista:
            if s != canon:
                candidat_map_subramura.append((s, canon))

    if not candidat_map_ramura and not candidat_map_subramura:
        print_safe("Nu s-au gasit 'dubluri' evidente nici la Ramura, nici la Subramura.")
        return

    print_safe("=== Propuneri RAMURA_MAP pentru merge_branches.py ===\n")
    if candidat_map_ramura:
        print_safe("RAMURA_MAP = {")
        canon_set_r = {canon for _, canon in candidat_map_ramura}
        for canon in sorted(canon_set_r):
            print_safe(f'    "{canon}": "{canon}",')
        for veche, noua in candidat_map_ramura:
            print_safe(f'    "{veche}": "{noua}",')
        print_safe("}\n")
    else:
        print_safe("(Nu exista propuneri pentru RAMURA_MAP.)\n")

    print_safe("=== Propuneri SUBRAMURA_MAP pentru merge_branches.py ===\n")
    if candidat_map_subramura:
        print_safe("SUBRAMURA_MAP = {")
        canon_set_s = {canon for _, canon in candidat_map_subramura}
        for canon in sorted(canon_set_s):
            print_safe(f'    "{canon}": "{canon}",')
        for veche, noua in candidat_map_subramura:
            print_safe(f'    "{veche}": "{noua}",')
        print_safe("}\n")
    else:
        print_safe("(Nu exista propuneri pentru SUBRAMURA_MAP.)\n")

    print_safe("Copiaza blocurile RAMURA_MAP si SUBRAMURA_MAP in merge_branches.py sau lasa orchestratorul sa le injecteze automat.")


if __name__ == "__main__":
    detecteaza_ramuri_si_subramuri_similare()