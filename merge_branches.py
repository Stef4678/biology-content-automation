import os
import shutil
import pandas as pd

BASE_DIR = "proiect_biologie"
ARTICLES_DIR = os.path.join(BASE_DIR, "articole")
INDEX_PATH = os.path.join(BASE_DIR, "index_continut.csv")

RAMURA_MAP = {
    "Biologia conservarii": "Biologia conservarii",
    "Biologia dezvoltarii": "Biologia dezvoltarii",
    "Biologie celulara": "Biologie celulara",
    "Biologie evolutiva": "Biologie evolutiva",
    "Biologie marina": "Biologie marina",
    "Biologie moleculara": "Biologie moleculara",
    "Botanica": "Botanica",
    "Evolutie": "Evolutie",
    "Genetica": "Genetica",
    "Neurostiinte": "Neurostiinte",
    "Biologia conserv?rii": "Biologia conservarii",
    "Biologia dezvolt?rii": "Biologia dezvoltarii",
    "Biologie celular?": "Biologie celulara",
    "Biologie evolutiv?": "Biologie evolutiva",
    "Biologie marin?": "Biologie marina",
    "Biologie molecular?": "Biologie moleculara",
    "Botanic?": "Botanica",
    "Evolu?ie": "Evolutie",
    "Genetic?": "Genetica",
    "Neuro?tiin?e": "Neurostiinte",
}

SUBRAMURA_MAP = {
    "Ecologie microbiana": "Ecologie microbiana",
    "Epigenetica": "Epigenetica",
    "Fiziologie comparata": "Fiziologie comparata",
    "Fotosinteza": "Fotosinteza",
    "Genetica populatiilor": "Genetica populatiilor",
    "Macroevolutie": "Macroevolutie",
    "Organogeneza": "Organogeneza",
    "Semnalizare celulara": "Semnalizare celulara",
    "Ecologie microbian?": "Ecologie microbiana",
    "Epigenetic?": "Epigenetica",
    "Fiziologie comparat?": "Fiziologie comparata",
    "Fotosintez?": "Fotosinteza",
    "Genetic? popula?iilor": "Genetica populatiilor",
    "Macroevolu?ie": "Macroevolutie",
    "Organogenez?": "Organogeneza",
    "Semnalizare celular?": "Semnalizare celulara",
}


def unifica_ramuri_si_fisiere():
    if not os.path.exists(INDEX_PATH):
        print("Nu exista index_continut.csv.")
        return

    df = pd.read_csv(INDEX_PATH)

    modificari = 0

    for idx, row in df.iterrows():
        # Ramura
        ramura_veche = row["Ramura"]
        ramura_noua = RAMURA_MAP.get(ramura_veche, ramura_veche)

        # Subramura
        subramura_veche = row["Subramura"]
        subramura_noua = SUBRAMURA_MAP.get(subramura_veche, subramura_veche)

        if ramura_noua != ramura_veche or subramura_noua != subramura_veche:
            cale_veche_rel = row["Cale_Fisier"]
            cale_veche_abs = os.path.join(BASE_DIR, cale_veche_rel)

            nume_fisier = os.path.basename(cale_veche_abs)
            cale_noua_rel = os.path.join("articole", ramura_noua, nume_fisier)

            df.at[idx, "Ramura"] = ramura_noua
            df.at[idx, "Subramura"] = subramura_noua
            df.at[idx, "Cale_Fisier"] = cale_noua_rel

            modificari += 1

    if modificari == 0:
        print("Nu s-au gasit ramuri/subramuri de unificat in index.")
    else:
        df.to_csv(INDEX_PATH, index=False, encoding="utf-8")
        print(f"S-au actualizat {modificari} randuri in index_continut.csv (Ramura/Subramura + Cale_Fisier).")

    # Mutare fisiere pe disk, la fel ca in versiunea anterioara, doar pe RAMURA_MAP
    if not os.path.exists(ARTICLES_DIR):
        print("Nu exista directorul de articole pe disk.")
        return

    mutari = 0
    for ramura_veche, ramura_noua in RAMURA_MAP.items():
        if ramura_veche == ramura_noua:
            continue

        dir_vechi = os.path.join(ARTICLES_DIR, ramura_veche)
        dir_nou = os.path.join(ARTICLES_DIR, ramura_noua)

        if not os.path.exists(dir_vechi):
            continue

        os.makedirs(dir_nou, exist_ok=True)

        for fname in os.listdir(dir_vechi):
            src = os.path.join(dir_vechi, fname)
            dst = os.path.join(dir_nou, fname)
            if os.path.exists(dst):
                print(f"Atentie: fisier deja exista la destinatie, sar: {dst}")
                continue
            shutil.move(src, dst)
            mutari += 1

        if not os.listdir(dir_vechi):
            os.rmdir(dir_vechi)
            print(f"S-a sters folderul vechi gol: {dir_vechi}")

    print(f"S-au mutat {mutari} fisiere .txt intre ramuri conform RAMURA_MAP.")


if __name__ == "__main__":
    unifica_ramuri_si_fisiere()