import os
import re
import json
import time
import unicodedata
import pandas as pd
from typing import List
from pathlib import Path
from threading import Lock
from concurrent.futures import ThreadPoolExecutor, as_completed

from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from openai import OpenAI

# ==========================================
# 0. PRINT SAFE (fara UnicodeEncodeError)
# ==========================================

def print_safe(text: str):
    """Print robust, care nu crapa pe diacritice in CP1252."""
    try:
        print(text)
    except UnicodeEncodeError:
        safe = text.encode("ascii", "replace").decode("ascii")
        print(safe)


# ==========================================
# 1. UTILITARE JSON ROBUSTE
# ==========================================

def curata_json_brut(text: str) -> str:
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start:end + 1]

    cleaned_chars = []
    for ch in text:
        if ch in ("\n", "\r", "\t"):
            cleaned_chars.append(ch)
        elif ord(ch) < 32:
            continue
        else:
            cleaned_chars.append(ch)
    return "".join(cleaned_chars)


def parse_json_safe(text: str) -> dict:
    cleaned = curata_json_brut(text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON invalid chiar si dupa curatare: {e}")


# ==========================================
# 2. CONFIGURARE API ȘI TIPURI PYDANTIC
# ==========================================

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
if not DEEPSEEK_API_KEY:
    raise RuntimeError("Lipseste DEEPSEEK_API_KEY in environment.")

client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com",
)

PRIMARY_MODEL = "deepseek-v4-flash"

BASE_DIR = "proiect_biologie"
ARTICLES_DIR = os.path.join(BASE_DIR, "articole")
INDEX_PATH = os.path.join(BASE_DIR, "index_continut.csv")
os.makedirs(ARTICLES_DIR, exist_ok=True)

MAX_WORKERS = 4
ARTICLES_PAUSE_SECONDS = 0.5

write_lock = Lock()


class SubramuraSchema(BaseModel):
    nume_subramura: str
    subcategorii: List[str] = Field(description="Lista cu exact 3 subcategorii sau subiecte specifice")


class RamuraSchema(BaseModel):
    nume_ramura: str
    subramuri: List[SubramuraSchema]


class StructuraBiologieSchema(BaseModel):
    ramuri: List[RamuraSchema]


class SectiuneArticol(BaseModel):
    subtitlu: str = Field(description="Subtitlul sectiunii curente")
    continut: str = Field(description="Continutul detaliat al sectiunii, cuprinzator.")


class ArticolBiologieSchema(BaseModel):
    titlu: str = Field(description="Titlul principal al articolului, optimizat SEO")
    introducere: str = Field(description="Introducere captivanta in subiect.")
    sectiuni: List[SectiuneArticol] = Field(description="Lista cu exact 3 sectiuni detaliate.")
    concluzie: str = Field(description="Concluzia articolului.")


class SubiectNouSchema(BaseModel):
    ramura: str = Field(description="Ramura mare din biologie unde se potriveste subiectul")
    subramura: str = Field(description="Subramura specifica")
    subcategorie: str = Field(description="Numele subiectului nou propus pentru articol")


class ListaLipsuriSchema(BaseModel):
    subiecte_noi: List[SubiectNouSchema] = Field(
        description="Lista cu subiecte fundamentale care lipseau"
    )


# ==========================================
# 3. NORMALIZARE NUME RAMURA (anti-foldere duplicate)
# ==========================================

def normalize_ramura(nume: str) -> str:
    """
    Normalizeaza numele de ramura:
    - elimina diacritice,
    - reduce spatii multiple,
    Astfel, 'Biologie moleculară' si 'Biologie moleculara' devin aceeasi forma.
    """
    if not isinstance(nume, str):
        nume = str(nume)
    nfkd = unicodedata.normalize("NFKD", nume)
    no_diacritics = "".join(ch for ch in nfkd if not unicodedata.combining(ch))
    no_diacritics = " ".join(no_diacritics.split()).strip()
    return no_diacritics


# ==========================================
# 4. LOGICĂ DE SIGURANȚĂ ȘI REÎNCERCARE
# ==========================================

class DeepSeekAPIError(Exception):
    pass


def curata_nume_fisier(nume_subcategorie: str) -> str:
    nume_sigur = nume_subcategorie.replace(" ", "_")
    nume_sigur = re.sub(r'[\\/*?:"<>|]', "", nume_sigur)
    return f"{nume_sigur}.txt"


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=20),
    retry=retry_if_exception_type(DeepSeekAPIError),
    before_sleep=lambda retry_state: print_safe(
        f" -> Server aglomerat (Cod {getattr(retry_state.outcome.exception, 'status_code', 'Nedefinit')}). "
        "Se reincearca automat..."
    ),
)
def apeleaza_deepseek_cu_retry(prompt: str) -> str:
    system_msg = (
        "Esti un model care intoarce RIGUROS un singur obiect json valid. "
        "Nu include niciun text in afara json-ului."
    )

    try:
        response = client.chat.completions.create(
            model=PRIMARY_MODEL,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
    except Exception as e:
        raise DeepSeekAPIError(f"Eroare la request DeepSeek: {e}")

    try:
        content = response.choices[0].message.content
    except Exception as e:
        raise DeepSeekAPIError(f"Raspuns DeepSeek neasteptat: {e}")

    return content


def executa_apel(prompt: str) -> str:
    try:
        return apeleaza_deepseek_cu_retry(prompt)
    except Exception as e:
        mesaj = (
            f" -> [Eroare Critica] Generarea a esuat dupa 5 reincercari cu "
            f"{PRIMARY_MODEL}: {e}"
        )
        print_safe(mesaj)
        raise


# ==========================================
# 5. GENERARE STRUCTURA
# ==========================================

def genereaza_structura_ierarhica():
    print_safe("[1/4] Se genereaza structura ierarhica a biologiei (DeepSeek V4 Flash)...")
    prompt = """
Esti un profesor universitar de biologie. Genereaza o structura ierarhica detaliata pentru o enciclopedie.

Alege exact 3 ramuri mari ale biologiei (ex: Zoologie, Botanica, Genetica).
Pentru fiecare ramura mare, adauga exact 3 subramuri importante.
Pentru fiecare subramura, adauga exact 3 subcategorii specifice care pot deveni subiecte independente de articole.

Reguli suplimentare:
- Scrie numele RAMURILOR fara diacritice, folosind doar litere simple.
- Subramurile si subiectele pot avea diacritice.

Returneaza STRICT un obiect json valid, conform urmatorului EXEMPLU de schema (NU schimba numele cheilor principale):

{
  "ramuri": [
    {
      "nume_ramura": "Zoologie",
      "subramuri": [
        {
          "nume_subramura": "Mammifere",
          "subcategorii": [
            "Fiziologia mammiferelor",
            "Ecologia mammiferelor",
            "Evolutia mammiferelor"
          ]
        }
      ]
    }
  ]
}

Nu include text in afara json-ului.
"""
    raw_json = executa_apel(prompt)
    data = parse_json_safe(raw_json)

    if "ramuri_mari" in data and "ramuri" not in data:
        data["ramuri"] = data["ramuri_mari"]
        del data["ramuri_mari"]

    struct = StructuraBiologieSchema.model_validate(data)
    return struct.model_dump()


def creeaza_sistem_indexare(structura_json):
    print_safe("[2/4] Se creeaza fisierul index CSV si directoarele...")
    date_tabel = []

    for ramura in structura_json["ramuri"]:
        r_nume_raw = ramura["nume_ramura"]
        r_nume = normalize_ramura(r_nume_raw)
        os.makedirs(os.path.join(ARTICLES_DIR, r_nume), exist_ok=True)

        for subramura in ramura["subramuri"]:
            s_nume = subramura["nume_subramura"]

            for subcategorie in subramura["subcategorii"]:
                nume_fisier = curata_nume_fisier(subcategorie)
                cale_relativa = os.path.join("articole", r_nume, nume_fisier)

                date_tabel.append(
                    {
                        "Ramura": r_nume,
                        "Subramura": s_nume,
                        "Subcategorie": subcategorie,
                        "Status": "Planificat",
                        "Cale_Fisier": cale_relativa,
                    }
                )

    df = pd.DataFrame(date_tabel)
    df.to_csv(INDEX_PATH, index=False, encoding="utf-8")
    print_safe(f"-> Index initial salvat in: {INDEX_PATH}")
    return df


# ==========================================
# 6. GENERARE ARTICOLE
# ==========================================

def genereaza_articol_structurat(ramura: str, subramura: str, subcategorie: str) -> str:
    prompt = f"""
Esti un scriitor stiintific specializat in biologie. Scrie un articol detaliat si riguros.

Detalii subiect:
- Ramura generala: {ramura}
- Domeniu specific: {subramura}
- Subiectul exact al articolului: {subcategorie}

Reguli:
- Foloseste doar date stiintifice reale si demonstrate academic.
- Nu folosi diacritice in textul generat pentru a evita problemele de codare.
- Returneaza STRICT un obiect json valid conform urmatorului exemplu de schema:

{{
  "titlu": "Titlu articol",
  "introducere": "Text introductiv",
  "sectiuni": [
    {{
      "subtitlu": "Subtitlu sectiune 1",
      "continut": "Continut detaliat 1"
    }},
    {{
      "subtitlu": "Subtitlu sectiune 2",
      "continut": "Continut detaliat 2"
    }},
    {{
      "subtitlu": "Subtitlu sectiune 3",
      "continut": "Continut detaliat 3"
    }}
  ],
  "concluzie": "Text de concluzie"
}}

Nu include text in afara json-ului.
"""
    raw_json = executa_apel(prompt)

    try:
        data = parse_json_safe(raw_json)
    except ValueError as e:
        raise RuntimeError(f"JSON invalid pentru articol '{subcategorie}': {e}")

    articol = ArticolBiologieSchema.model_validate(data)
    date_articol = articol.model_dump()

    text_markdown = f"# {date_articol['titlu']}\n\n"
    text_markdown += f"{date_articol['introducere']}\n\n"

    for sectiune in date_articol["sectiuni"]:
        text_markdown += f"## {sectiune['subtitlu']}\n\n"
        text_markdown += f"{sectiune['continut']}\n\n"

    text_markdown += "## Concluzie\n\n"
    text_markdown += f"{date_articol['concluzie']}\n"
    return text_markdown


def proceseaza_un_articol(index, row):
    if row["Status"] == "Finalizat":
        return index, "skip", None

    try:
        text_articol = genereaza_articol_structurat(
            row["Ramura"], row["Subramura"], row["Subcategorie"]
        )
        cale_completa_fisier = os.path.join(BASE_DIR, row["Cale_Fisier"])
        os.makedirs(os.path.dirname(cale_completa_fisier), exist_ok=True)

        with write_lock:
            with open(cale_completa_fisier, "w", encoding="utf-8") as f:
                f.write(text_articol)

        return index, "ok", None
    except Exception as e:
        return index, "err", str(e)


def ruleaza_automatizarea_in_masa():
    if not os.path.exists(INDEX_PATH):
        return

    df = pd.read_csv(INDEX_PATH)
    planificate = df[df["Status"] == "Planificat"]
    total_articole = len(df)
    ramase = len(planificate)

    if ramase == 0:
        print_safe("[3/4] Toate articolele din tabel sunt deja generate!")
        return

    print_safe(f"[3/4] Se proceseaza articolele. Mai sunt {ramase} din {total_articole} planificate...")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {
            ex.submit(proceseaza_un_articol, index, row): index
            for index, row in planificate.iterrows()
        }

        for fut in as_completed(futures):
            index, status, err = fut.result()
            df.at[index, "Status"] = "Finalizat" if status == "ok" else "Eroare"
            df.to_csv(INDEX_PATH, index=False, encoding="utf-8")

            if ARTICLES_PAUSE_SECONDS:
                time.sleep(ARTICLES_PAUSE_SECONDS)

            if err:
                subiect = str(df.at[index, "Subcategorie"])
                mesaj_err = str(err)
                mesaj_log = f" -> [Eroare Subiect] '{subiect}': {mesaj_err}"
                print_safe(mesaj_log)


# ==========================================
# 7. AUDIT LIPSE (subiecte noi, fara duplicate)
# ==========================================

def auditeaza_lipsuri_si_sugereaza():
    print_safe("\n[4/4] Se ruleaza modulul de audit. Se cauta lipsuri si se extinde indexul...")
    df = pd.read_csv(INDEX_PATH)

    subcategorii_existente = df["Subcategorie"].tolist()
    subiecte_existente = set(subcategorii_existente)
    lista_subiecte_text = "\n".join([f"- {s}" for s in subcategorii_existente])

    prompt = f"""
Sunt un creator de continut si am generat articole pe urmatoarele subiecte din biologie:
{lista_subiecte_text}

Analizeaza critic aceasta lista. Identifica ce ramuri fundamentale sau concepte cheie lipsesc cu desavarsire.
Propune exact 15 subiecte complet noi, importante si de nisa, care trebuie adaugate neaparat in faza urmatoare.

Returneaza STRICT un obiect json valid conform urmatorului exemplu de schema:

{{
  "subiecte_noi": [
    {{
      "ramura": "Genetica",
      "subramura": "Genomica functionala",
      "subcategorie": "Reglarea epigenetica la plante"
    }}
  ]
}}

Nu include text in afara json-ului.
"""
    raw_json = executa_apel(prompt)

    try:
        data = parse_json_safe(raw_json)
    except ValueError as e:
        raise RuntimeError(f"JSON invalid pentru audit de lipsuri: {e}")

    lista = ListaLipsuriSchema.model_validate(data)
    date_lipsuri = lista.model_dump()

    cale_raport = os.path.join(BASE_DIR, "raport_audit.txt")
    with open(cale_raport, "w", encoding="utf-8") as f:
        f.write("=== SUBIECTE NOI DETECTATE SI INCLUSE IN PLANIFICARE ===\n\n")
        for s in date_lipsuri["subiecte_noi"]:
            f.write(f"-> [{s['ramura']} -> {s['subramura']}]: {s['subcategorie']}\n")

    print_safe(f"-> Raportul vizual a fost salvat pe disk in: {cale_raport}")

    randuri_noi = []
    for s in date_lipsuri["subiecte_noi"]:
        subiect = s["subcategorie"]

        # 1) nu adaugam daca exista deja ca subcategorie in CSV, indiferent de Status
        if subiect in subiecte_existente:
            continue

        ramura_norm = normalize_ramura(s["ramura"])
        nume_fisier = curata_nume_fisier(subiect)
        cale_relativa = os.path.join("articole", ramura_norm, nume_fisier)
        cale_abs = os.path.join(BASE_DIR, cale_relativa)

        # 2) nu adaugam daca fisierul exista deja pe disc
        if os.path.exists(cale_abs):
            continue

        randuri_noi.append(
            {
                "Ramura": ramura_norm,
                "Subramura": s["subramura"],
                "Subcategorie": subiect,
                "Status": "Planificat",
                "Cale_Fisier": cale_relativa,
            }
        )

    if randuri_noi:
        df_nou = pd.DataFrame(randuri_noi)
        df_final = pd.concat([df, df_nou], ignore_index=True)
        df_final.to_csv(INDEX_PATH, index=False, encoding="utf-8")
        print_safe(
            f"-> SUCCES: S-au adaugat {len(randuri_noi)} subiecte noi in {INDEX_PATH} cu statusul 'Planificat'."
        )
        print_safe("Data viitoare cand pornesti scriptul, acesta le va genera automat.")
    else:
        print_safe("-> Audit finalizat. Nu s-au gasit subiecte complet noi de adaugat.")


# ==========================================
# 8. EXECUTOR PRINCIPAL
# ==========================================

if __name__ == "__main__":
    if not os.path.exists(INDEX_PATH):
        print_safe("-> Prima rulare: se genereaza structura cu DeepSeek V4 Flash...")
        structura = genereaza_structura_ierarhica()
        creeaza_sistem_indexare(structura)
    else:
        print_safe("-> S-a detectat un proiect existent. Se scaneaza fisierele...")

    ruleaza_automatizarea_in_masa()
    auditeaza_lipsuri_si_sugereaza()

    print_safe("\nProces complet terminat cu succes cu DeepSeek V4 Flash!")