import os
import json
import time
import pandas as pd
from typing import List
from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from openai import OpenAI

# --------- CONFIG COMUNA CU SCRIPTUL PRINCIPAL ---------

BASE_DIR = "proiect_biologie"
INDEX_PATH = os.path.join(BASE_DIR, "index_continut.csv")

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
if not DEEPSEEK_API_KEY:
    raise RuntimeError("Lipseste DEEPSEEK_API_KEY in environment.")

client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com",
)

PRIMARY_MODEL = "deepseek-v4-flash"


# --------- PRINT SAFE (fara UnicodeEncodeError) ---------

def print_safe(text: str):
    """Print robust, care nu crapa pe diacritice in CP1252."""
    try:
        print(text)
    except UnicodeEncodeError:
        safe = text.encode("ascii", "replace").decode("ascii")
        print(safe)


# --------- UTILITARE JSON ROBUSTE ---------

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


# --------- SCHEMAS PENTRU ARTICOL ---------

class SectiuneArticol(BaseModel):
    subtitlu: str = Field(description="Subtitlul sectiunii curente")
    continut: str = Field(description="Continutul detaliat al sectiunii, cuprinzator.")


class ArticolBiologieSchema(BaseModel):
    titlu: str = Field(description="Titlul principal al articolului, optimizat SEO")
    introducere: str = Field(description="Introducere captivanta in subiect.")
    sectiuni: List[SectiuneArticol] = Field(description="Lista cu exact 3 sectiuni detaliate.")
    concluzie: str = Field(description="Concluzia articolului.")


# --------- RETRY API ---------

class DeepSeekAPIError(Exception):
    pass


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=20),
    retry=retry_if_exception_type(DeepSeekAPIError),
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


# --------- GENERARE ARTICOL CU PROMPT MAI STRICT ---------

def genereaza_articol_structurat_retry(ramura: str, subramura: str, subcategorie: str) -> str:
    prompt = f"""
Esti un scriitor stiintific specializat in biologie. Scrie un articol detaliat si riguros.

Detalii subiect:
- Ramura generala: {ramura}
- Domeniu specific: {subramura}
- Subiectul exact al articolului: {subcategorie}

Reguli:
- Foloseste doar date stiintifice reale si demonstrate academic.
- Nu folosi diacritice in textul generat pentru a evita problemele de codare.
- Returneaza STRICT un singur obiect JSON valid, fara text inainte sau dupa.
- NU include comentarii, exemple suplimentare sau markup. Doar JSON.

Schema:

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

Nu include text in afara JSON-ului.
"""
    raw_json = apeleaza_deepseek_cu_retry(prompt)

    data = parse_json_safe(raw_json)
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


# --------- SCRIPT PRINCIPAL PENTRU RETRY ERORI ---------

def ruleaza_retry_erori():
    if not os.path.exists(INDEX_PATH):
        print_safe("Nu exista index_continut.csv. Nimic de refacut.")
        return

    df = pd.read_csv(INDEX_PATH)
    erori = df[df["Status"] == "Eroare"]

    if erori.empty:
        print_safe("Nu exista articole cu Status = 'Eroare'.")
        return

    total_erori = len(erori)
    print_safe(f"Se reiau {total_erori} articole marcate cu 'Eroare'...\n")

    for idx, row in erori.iterrows():
        subiect = str(row["Subcategorie"])
        # log robust pentru subiect
        print_safe(f" -> Retry articol: '{subiect}'...")

        try:
            text_articol = genereaza_articol_structurat_retry(
                row["Ramura"],
                row["Subramura"],
                subiect,
            )

            cale_completa_fisier = os.path.join(BASE_DIR, row["Cale_Fisier"])
            os.makedirs(os.path.dirname(cale_completa_fisier), exist_ok=True)

            with open(cale_completa_fisier, "w", encoding="utf-8") as f:
                f.write(text_articol)

            df.at[idx, "Status"] = "Finalizat"
            df.to_csv(INDEX_PATH, index=False, encoding="utf-8")
            print_safe(f"    [OK] '{subiect}' marcat ca Finalizat.")
            time.sleep(1.0)

        except Exception as e:
            # nu lasam encoding-ul sa ne opreasca
            mesaj = f"    [FAIL] '{subiect}' ramane Eroare: {e}"
            print_safe(mesaj)
            # Status ramane "Eroare" pentru vizibilitate

    print_safe("Retry erori terminat.")


if __name__ == "__main__":
    ruleaza_retry_erori()