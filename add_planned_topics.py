import os
import pandas as pd

BASE_DIR = "proiect_biologie"
INDEX_PATH = os.path.join(BASE_DIR, "index_continut.csv")

SUBIECTE_NOI = [
    ("Genetica", "Genomica functionala", "Analiza variatiei genomice la primate"),
    ("Genetica", "Epigenetica", "Mecanisme epigenetice in imunitate"),
    ("Zoologie", "Etologie", "Comportamentul social la corvide"),
    # adaugi aici cate vrei
]

def adauga_subiecte_planificate():
    if not os.path.exists(INDEX_PATH):
        print("Nu exista index_continut.csv.")
        return

    df = pd.read_csv(INDEX_PATH)

    randuri_noi = []
    for ramura, subramura, subcategorie in SUBIECTE_NOI:
        # evitam duplicatele
        if subcategorie in df["Subcategorie"].values:
            continue
        cale_relativa = os.path.join("articole", ramura, subcategorie.replace(" ", "_") + ".txt")
        randuri_noi.append(
            {
                "Ramura": ramura,
                "Subramura": subramura,
                "Subcategorie": subcategorie,
                "Status": "Planificat",
                "Cale_Fisier": cale_relativa,
            }
        )

    if not randuri_noi:
        print("Nu s-au gasit subiecte noi de adaugat.")
        return

    df_nou = pd.DataFrame(randuri_noi)
    df_final = pd.concat([df, df_nou], ignore_index=True)
    df_final.to_csv(INDEX_PATH, index=False, encoding="utf-8")

    print(f"S-au adaugat {len(randuri_noi)} subiecte noi cu Status = 'Planificat'.")

if __name__ == "__main__":
    adauga_subiecte_planificate()