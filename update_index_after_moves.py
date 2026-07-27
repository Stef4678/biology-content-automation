import os
import pandas as pd

BASE_DIR = "proiect_biologie"
ARTICLES_DIR = os.path.join(BASE_DIR, "articole")
INDEX_PATH = os.path.join(BASE_DIR, "index_continut.csv")


def construieste_map_subiect_cale_ramura():
    """
    Scaneaza proiect_biologie/articole si construieste un mapping:
    Subcategorie -> (Ramura_noua, cale_noua_rel)
    Presupunem ca numele fisierului (fara .txt) corespunde Subcategoriei
    cu spatii sau underscore-uri.
    """
    mapping = {}

    if not os.path.exists(ARTICLES_DIR):
        print("Nu exista directorul 'articole'.")
        return mapping

    for ramura_dir in os.listdir(ARTICLES_DIR):
        ramura_path = os.path.join(ARTICLES_DIR, ramura_dir)
        if not os.path.isdir(ramura_path):
            continue

        for fname in os.listdir(ramura_path):
            if not fname.lower().endswith(".txt"):
                continue

            name_no_ext = fname[:-4]  # fara .txt
            # Subiectul in CSV de obicei e cu spatii, fisierul poate avea underscore
            subiect_plain = name_no_ext.replace("_", " ")

            cale_relativa = os.path.join("articole", ramura_dir, fname)
            mapping[subiect_plain] = (ramura_dir, cale_relativa)

    return mapping


def actualizeaza_index_dupa_mutari():
    if not os.path.exists(INDEX_PATH):
        print("Nu exista index_continut.csv.")
        return

    df = pd.read_csv(INDEX_PATH)

    if "Subcategorie" not in df.columns or "Cale_Fisier" not in df.columns or "Ramura" not in df.columns:
        print("Indexul nu contine coloanele 'Subcategorie', 'Ramura' si/sau 'Cale_Fisier'.")
        return

    subiect_map = construieste_map_subiect_cale_ramura()
    if not subiect_map:
        print("Nu s-au gasit fisiere .txt in 'articole' pentru mapare.")
        return

    modificari = 0
    lipsa = []

    for idx, row in df.iterrows():
        subiect = str(row["Subcategorie"])
        if subiect in subiect_map:
            ramura_noua, cale_noua_rel = subiect_map[subiect]

            # daca ramura sau calea s-au schimbat fata de ce e in CSV, actualizam
            if row["Ramura"] != ramura_noua or row["Cale_Fisier"] != cale_noua_rel:
                df.at[idx, "Ramura"] = ramura_noua
                df.at[idx, "Cale_Fisier"] = cale_noua_rel
                modificari += 1
        else:
            lipsa.append(subiect)

    df.to_csv(INDEX_PATH, index=False, encoding="utf-8")
    print(f"S-au actualizat {modificari} randuri (Ramura + Cale_Fisier) pe baza mutarilor manuale.")

    if lipsa:
        print("Atentie: pentru urmatoarele subiecte nu s-a gasit fisier .txt pe disk:")
        for s in sorted(set(lipsa)):
            print(f"  - {s}")


if __name__ == "__main__":
    actualizeaza_index_dupa_mutari()