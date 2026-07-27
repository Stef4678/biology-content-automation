import os
import pandas as pd

BASE_DIR = "proiect_biologie"
ARTICLES_DIR = os.path.join(BASE_DIR, "articole")
INDEX_PATH = os.path.join(BASE_DIR, "index_continut.csv")
RAPORT_PATH = os.path.join(BASE_DIR, "statistici_articole.txt")


def genereaza_statistici():
    if not os.path.exists(INDEX_PATH):
        print(f"Nu exista {INDEX_PATH}.")
        return

    df = pd.read_csv(INDEX_PATH)

    total_articole = len(df)
    total_finalizat = len(df[df["Status"] == "Finalizat"])
    total_planificat = len(df[df["Status"] == "Planificat"])
    total_eroare = len(df[df["Status"] == "Eroare"])

    by_ramura = df.groupby("Ramura")["Subcategorie"].count().sort_values(ascending=False)
    by_subramura = df.groupby(["Ramura", "Subramura"])["Subcategorie"].count().sort_values(ascending=False)

    folder_counts = {}
    if os.path.exists(ARTICLES_DIR):
        for root, dirs, files in os.walk(ARTICLES_DIR):
            rel_root = os.path.relpath(root, ARTICLES_DIR)
            if rel_root == ".":
                continue
            txt_files = [f for f in files if f.lower().endswith(".txt")]
            folder_counts[rel_root] = len(txt_files)

    df_erori = df[df["Status"] == "Eroare"].copy()
    df_erori = df_erori.sort_values(["Ramura", "Subramura", "Subcategorie"])

    lines = []
    lines.append("=== STATISTICI ARTICOLE BIOLOGIE ===\n")
    lines.append(f"Director baza: {BASE_DIR}\n")
    lines.append(f"Index CSV: {INDEX_PATH}\n")

    lines.append("\n--- SUMAR GLOBAL ---\n")
    lines.append(f"Total articole (randuri in index): {total_articole}\n")
    lines.append(f" - Finalizat: {total_finalizat}\n")
    lines.append(f" - Planificat: {total_planificat}\n")
    lines.append(f" - Eroare: {total_eroare}\n")

    lines.append("\n--- Articole pe RAMURA (din index) ---\n")
    for ramura, count in by_ramura.items():
        lines.append(f" {ramura}: {count} articole\n")

    lines.append("\n--- Articole pe RAMURA / SUBRAMURA (din index) ---\n")
    for (ramura, subramura), count in by_subramura.items():
        lines.append(f" {ramura} / {subramura}: {count} articole\n")

    lines.append("\n--- Articole pe foldere (filesystem: proiect_biologie/articole) ---\n")
    if folder_counts:
        for folder, count in sorted(folder_counts.items()):
            lines.append(f" {folder}: {count} fisiere .txt\n")
    else:
        lines.append(" (Nu s-au gasit foldere sau fisiere .txt in ARTICLES_DIR.)\n")

    lines.append("\n--- Subiecte cu Status = 'Eroare' (pentru debugging) ---\n")
    if df_erori.empty:
        lines.append(" (Nu exista articole marcate cu 'Eroare'.)\n")
    else:
        max_list = 50
        for i, row in enumerate(df_erori.itertuples(index=False), start=1):
            if i > max_list:
                lines.append(f" ... (lista trunchiata la primele {max_list} erori)\n")
                break
            lines.append(
                f" [{i}] {row.Ramura} / {row.Subramura} -> {row.Subcategorie}\n"
            )

    with open(RAPORT_PATH, "w", encoding="utf-8") as f:
        f.writelines(lines)

    # --- Output sumar global in consola (PowerShell) ---
    print("\n--- SUMAR GLOBAL (consola) ---")
    print(f"Total articole (randuri in index): {total_articole}")
    print(f" - Finalizat: {total_finalizat}")
    print(f" - Planificat: {total_planificat}")
    print(f" - Eroare: {total_eroare}")
    print(f"\nRaport de statistici salvat in: {RAPORT_PATH}")


if __name__ == "__main__":
    genereaza_statistici()