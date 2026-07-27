import os
import subprocess
import time
import pandas as pd

BASE_DIR = "proiect_biologie"
INDEX_PATH = os.path.join(BASE_DIR, "index_continut.csv")

SCRIPT_PRINCIPAL = "generator.py"
SCRIPT_RETRY_ERORI = "retry_errors.py"

MAX_CICLURI = 8  # ajusteaza dupa nevoie
PRAG_TOTAL = None  # de ex. 100 daca vrei un cap superior, sau None pentru fara prag


def citeste_stat_index():
    if not os.path.exists(INDEX_PATH):
        return 0, 0, 0
    df = pd.read_csv(INDEX_PATH)
    total = len(df)
    planificat = len(df[df["Status"] == "Planificat"])
    eroare = len(df[df["Status"] == "Eroare"])
    return total, planificat, eroare


def print_safe(text: str):
    """Print robust, care nu crapa pe diacritice in CP1252."""
    try:
        print(text)
    except UnicodeEncodeError:
        safe = text.encode("ascii", "replace").decode("ascii")
        print(safe)


def ruleaza_script(nume_script: str) -> int:
    print_safe(f"\n=== Rulare script: {nume_script} ===")
    result = subprocess.run(
        ["python", nume_script],
        capture_output=True,
        text=True,
    )
    if result.stdout:
        print_safe(f"=== Output {nume_script} ===")
        print_safe(result.stdout)
    if result.stderr:
        print_safe(f"=== STDERR {nume_script} ===")
        print_safe(result.stderr)
    return result.returncode


def orchestrare():
    try:
        for ciclu in range(1, MAX_CICLURI + 1):
            total, planificat, eroare = citeste_stat_index()
            print_safe(
                f"\n[Ciclu {ciclu}] Index: total={total}, planificat={planificat}, eroare={eroare}"
            )

            # optional: oprire la un prag de articole
            if PRAG_TOTAL is not None and total >= PRAG_TOTAL:
                print_safe(
                    f"Total articole a ajuns la {total} (>= {PRAG_TOTAL}). Oprire orchestrare."
                )
                break

            # daca nu mai avem nici planificat, nici eroare -> gata
            if planificat == 0 and eroare == 0:
                print_safe(
                    "Nu mai exista articole planificate sau cu Eroare. Oprire orchestrare."
                )
                break

            # 1) rulam scriptul principal daca mai sunt planificate
            if planificat > 0:
                rc_main = ruleaza_script(SCRIPT_PRINCIPAL)
                if rc_main != 0:
                    print_safe(
                        f"{SCRIPT_PRINCIPAL} a esuat (returncode={rc_main}). Oprire orchestrare."
                    )
                    break

            # 2) rulam retry_errors.py doar daca mai sunt erori
            total2, planificat2, eroare2 = citeste_stat_index()
            if eroare2 > 0 and os.path.exists(SCRIPT_RETRY_ERORI):
                rc_retry = ruleaza_script(SCRIPT_RETRY_ERORI)
                if rc_retry != 0:
                    print_safe(
                        f"{SCRIPT_RETRY_ERORI} a esuat (returncode={rc_retry}). Nu mai incercam retry. Oprire orchestrare."
                    )
                    break

            # mic sleep intre cicluri
            time.sleep(5)

        print_safe("\nOrchestrare terminata.")
    except KeyboardInterrupt:
        print_safe("\nOrchestrare intrerupta manual (Ctrl+C).")


if __name__ == "__main__":
    orchestrare()