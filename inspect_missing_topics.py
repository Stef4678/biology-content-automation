import os
import pandas as pd

BASE_DIR = "proiect_biologie"
INDEX_PATH = os.path.join(BASE_DIR, "index_continut.csv")

SUBIECTE_LIPSA = [
    "Adaptări la variațiile de maree",
    "Adaptări respiratorii la scufundare",
    "Boli neurodegenerative și proteostază",
    "Cinetica enzimatică și inhibiție",
    "Cortexul cerebral: arii și funcții",
    "Cromozomi artificiali",
    "Căi de semnalizare prin receptori nucleari",
    "Echinodermele: simetrie și sistemul acvifer",
    "Efectele poluanților asupra ecosistemelor",
    "Embriogeneză la angiosperme",
    "Evoluția genomului: duplicări genice și poliploidie",
    "Fermentații și produse alimentare",
    "Fiziologia sistemului cardiovascular: inima și circulația",
    "Fiziologia sistemului muscular: contracția musculară",
    "Heritabilitatea trăsăturilor complexe",
    "Hormoni vegetali: auxine, gibereline, citochinine, acid abscisic, etilenă",
    "Istoria populațiilor post-glaciare",
    "Mecanisme de evaziune imună",
    "Mecanisme moleculare ale HIV/SIDA",
    "Organele vegetative: rădăcina și tulpina",
    "Proboscidienii: evoluția elefanților",
    "Procese de fosilizare",
    "Punctele de control G1/S si G2/M",
    "Sociobiologia insectelor sociale",
    "Specii invazive: impact și control",
    "Teoria selecției rudeniei",
    "Termoreglare și răspuns la frig/caldură",
    "Tesuturi conductoare: xilem si floem",
]


def print_safe(text: str):
    try:
        print(text)
    except UnicodeEncodeError:
        safe = text.encode("ascii", "replace").decode("ascii")
        print(safe)


def inspecteaza_si_fixeaza(fixeaza: bool = True):
    if not os.path.exists(INDEX_PATH):
        print_safe("Nu exista index_continut.csv.")
        return

    df = pd.read_csv(INDEX_PATH)

    if "Subcategorie" not in df.columns or "Status" not in df.columns or "Cale_Fisier" not in df.columns:
        print_safe("Indexul nu contine coloanele 'Subcategorie', 'Status' si/sau 'Cale_Fisier'.")
        return

    print_safe("=== Inspectie subiecte fara fisier .txt pe disk ===\n")
    modificari = 0

    for subiect in SUBIECTE_LIPSA:
        rows = df[df["Subcategorie"] == subiect]
        if rows.empty:
            print_safe(f"[WARN] Subiectul NU exista in index: {subiect}")
            continue

        print_safe(f"Subiect: {subiect}")
        for idx, row in rows.iterrows():
            ramura = row.get("Ramura", "")
            subramura = row.get("Subramura", "")
            status = row.get("Status", "")
            cale = row.get("Cale_Fisier", "")
            print_safe(f"  Ramura    : {ramura}")
            print_safe(f"  Subramura : {subramura}")
            print_safe(f"  Status    : {status}")
            print_safe(f"  Cale_Fisier: {cale}")

            # Mod 'fix': daca este marcat Finalizat, dar fisierul lipseste, il resetam la Planificat
            if fixeaza and status == "Finalizat":
                df.at[idx, "Status"] = "Planificat"
                # optional: golim Cale_Fisier ca sa fie regenerata curat
                # df.at[idx, "Cale_Fisier"] = ""
                modificari += 1
                print_safe("  [FIX] Status schimbat din 'Finalizat' in 'Planificat' pentru regenerare.")

        print_safe("")

    if fixeaza and modificari > 0:
        df.to_csv(INDEX_PATH, index=False, encoding="utf-8")
        print_safe(f"Au fost resetate {modificari} randuri din 'Finalizat' in 'Planificat' pentru subiectele lipsa.")
    elif fixeaza:
        print_safe("Nu au fost gasite randuri 'Finalizat' de resetat pentru subiectele lipsa.")


if __name__ == "__main__":
    # seteaza fixeaza=True pentru a aplica modificari, False pentru doar inspectie
    inspecteaza_si_fixeaza(fixeaza=True)