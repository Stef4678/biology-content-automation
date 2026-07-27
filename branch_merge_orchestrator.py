import os
import subprocess
import re
import textwrap

BASE_DIR = "proiect_biologie"
DETECT_SCRIPT = "detect_similar_branches.py"
UNIFICA_SCRIPT = "merge_branches.py"
UNIFICA_PATH = os.path.join(".", UNIFICA_SCRIPT)
MAP_OUTPUT_PATH = os.path.join(BASE_DIR, "generated_branch_mapping.txt")


def print_safe(text: str):
    try:
        print(text)
    except UnicodeEncodeError:
        safe = text.encode("ascii", "replace").decode("ascii")
        print(safe)


def ruleaza_script_capture(nume_script: str) -> str:
    print_safe(f"\n=== Rulare script: {nume_script} ===")
    result = subprocess.run(
        ["python", nume_script],
        capture_output=True,
        text=True,
    )
    if result.stderr:
        print_safe(f"=== STDERR {nume_script} ===")
        print_safe(result.stderr)
    print_safe(f"=== Output {nume_script} (capturat) ===")
    print_safe(result.stdout)
    return result.stdout


def extrage_blocuri_map(output_text: str):
    ramura_pattern = r"RAMURA_MAP\s*=\s*\{[^}]*\}"
    subramura_pattern = r"SUBRAMURA_MAP\s*=\s*\{[^}]*\}"

    ramura_match = re.search(ramura_pattern, output_text, re.DOTALL)
    subramura_match = re.search(subramura_pattern, output_text, re.DOTALL)

    ramura_text = ramura_match.group(0) if ramura_match else None
    subramura_text = subramura_match.group(0) if subramura_match else None

    return ramura_text, subramura_text


def salveaza_blocuri_in_fisier(ramura_text: str, subramura_text: str):
    os.makedirs(BASE_DIR, exist_ok=True)
    with open(MAP_OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write("=== Blocuri generate de detect_similar_branches.py ===\n\n")
        if ramura_text:
            f.write("# RAMURA_MAP sugerat:\n")
            f.write(textwrap.dedent(ramura_text))
            f.write("\n\n")
        else:
            f.write("# RAMURA_MAP nu a fost gasit in output.\n\n")

        if subramura_text:
            f.write("# SUBRAMURA_MAP sugerat:\n")
            f.write(textwrap.dedent(subramura_text))
            f.write("\n\n")
        else:
            f.write("# SUBRAMURA_MAP nu a fost gasit in output.\n\n")

    print_safe(f"Blocurile RAMURA_MAP/SUBRAMURA_MAP au fost salvate in: {MAP_OUTPUT_PATH}")


def injecteaza_blocuri_in_unifica(ramura_text: str, subramura_text: str):
    if not os.path.exists(UNIFICA_PATH):
        print_safe(f"Nu exista {UNIFICA_PATH}. Nu pot injecta mapping-urile.")
        return False

    with open(UNIFICA_PATH, "r", encoding="utf-8") as f:
        code = f.read()

    modified = False

    if ramura_text:
        # Inlocuim blocul existent RAMURA_MAP
        ramura_pattern = r"RAMURA_MAP\s*=\s*\{[^}]*\}"
        if re.search(ramura_pattern, code, re.DOTALL):
            code = re.sub(ramura_pattern, textwrap.dedent(ramura_text), code, count=1, flags=re.DOTALL)
            modified = True
        else:
            # daca nu exista, il adaugam dupa importuri
            insert_point = code.find("\n\n")
            if insert_point != -1:
                new_block = "\n\n" + textwrap.dedent(ramura_text) + "\n\n"
                code = code[:insert_point] + new_block + code[insert_point:]
                modified = True

    if subramura_text:
        subramura_pattern = r"SUBRAMURA_MAP\s*=\s*\{[^}]*\}"
        if re.search(subramura_pattern, code, re.DOTALL):
            code = re.sub(subramura_pattern, textwrap.dedent(subramura_text), code, count=1, flags=re.DOTALL)
            modified = True
        else:
            insert_point = code.find("RAMURA_MAP")
            if insert_point != -1:
                # adaugam SUBRAMURA_MAP imediat dupa RAMURA_MAP
                end_ramura = code.find("\n", insert_point)
                new_block = "\n\n" + textwrap.dedent(subramura_text) + "\n\n"
                code = code[:end_ramura] + new_block + code[end_ramura:]
                modified = True

    if modified:
        with open(UNIFICA_PATH, "w", encoding="utf-8") as f:
            f.write(code)
        print_safe(f"RAMURA_MAP/SUBRAMURA_MAP au fost injectate automat in {UNIFICA_PATH}.")
    else:
        print_safe("Nu s-a modificat merge_branches.py (nu s-au gasit locuri potrivite pentru injectie).")

    return modified


def ruleaza_unifica_ramuri():
    print_safe(f"\n=== Rulare script: {UNIFICA_SCRIPT} ===")
    result = subprocess.run(
        ["python", UNIFICA_SCRIPT],
        capture_output=True,
        text=True,
    )
    if result.stderr:
        print_safe(f"=== STDERR {UNIFICA_SCRIPT} ===")
        print_safe(result.stderr)
    print_safe(f"=== Output {UNIFICA_SCRIPT} ===")
    print_safe(result.stdout)


def orchestrare_unificare():
    # 1. ruleaza detect_similar_branches.py
    output = ruleaza_script_capture(DETECT_SCRIPT)

    # 2. extrage blocurile RAMURA_MAP / SUBRAMURA_MAP
    ramura_text, subramura_text = extrage_blocuri_map(output)

    if not ramura_text and not subramura_text:
        print_safe("Nu s-au gasit blocuri RAMURA_MAP/SUBRAMURA_MAP in output. Oprire.")
        return

    # 3. salveaza blocurile intr-un fisier de referinta
    salveaza_blocuri_in_fisier(ramura_text, subramura_text)

    # 4. injecteaza blocurile direct in merge_branches.py
    ok = injecteaza_blocuri_in_unifica(ramura_text, subramura_text)
    if not ok:
        print_safe("Injectia in merge_branches.py nu a reusit. Verifica fisierul manual.")
        return

    # 5. ruleaza merge_branches.py
    ruleaza_unifica_ramuri()

    print_safe("\nOrchestrare unificare ramuri/subramuri terminata.")


if __name__ == "__main__":
    orchestrare_unificare()