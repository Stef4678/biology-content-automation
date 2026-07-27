# Biology Content Automation

An automated Python pipeline for generating, indexing, validating, repairing, and organizing structured biology articles with the DeepSeek API.

The project creates a hierarchical biology content plan, generates structured articles in Markdown-style text format, tracks their status in a CSV index, retries failed requests, audits the topic plan for gaps, and provides maintenance tools for branch normalization and reporting.

## Features

- Generates a biology taxonomy with branches, sub-branches, and article topics
- Creates and maintains a CSV content index
- Generates structured biology articles through the DeepSeek API
- Validates model output with Pydantic schemas
- Uses JSON output mode for structured API responses
- Cleans malformed JSON responses before validation
- Processes articles concurrently with up to four workers
- Retries failed API calls with exponential backoff
- Tracks article status as `Planificat`, `Finalizat`, or `Eroare`
- Retries articles with `Eroare` status through a dedicated recovery script
- Audits the existing plan and suggests new biology topics
- Detects similar branch and sub-branch names
- Merges duplicate branch names and updates file paths
- Updates the CSV index after manual file moves
- Generates progress, distribution, and error statistics

## Project Structure

```text
biology-content-automation/
├── generator.py
├── orchestrator.py
├── retry_errors.py
├── inspect_missing_topics.py
├── add_planned_topics.py
├── detect_similar_branches.py
├── merge_branches.py
├── branch_merge_orchestrator.py
├── update_index_after_moves.py
├── generate_statistics.py
├── requirements.txt
├── README.md
├── .gitignore
└── proiect_biologie/
    └── .gitkeep
```

Generated articles, the CSV index, and generated reports are created automatically inside `proiect_biologie/`. They are excluded from Git by default.

## Requirements

- Python 3.10 or newer
- A DeepSeek API key

Install dependencies:

```bash
pip install -r requirements.txt
```

## API Key Setup

The application reads the API key from the `DEEPSEEK_API_KEY` environment variable.

### Windows PowerShell

```powershell
$env:DEEPSEEK_API_KEY="your_deepseek_api_key"
```

### Windows Command Prompt

```cmd
set DEEPSEEK_API_KEY=your_deepseek_api_key
```

Do not hard-code the API key in Python files or upload it to GitHub.

## Quick Start

Set the API key, then run the main generator:

```bash
python generator.py
```

**Important:** on the first use, run `generator.py` before `orchestrator.py`.

On the first run, `generator.py` creates:

- `proiect_biologie/index_continut.csv`
- A hierarchy of biology branches, sub-branches, and article topics
- The `proiect_biologie/articole/` directory
- Initial article files for topics marked as `Planificat`

On later runs, it processes all topics marked as `Planificat`, updates their status, and audits the index for additional topic suggestions.

## Automated Workflow

After the first run has created `proiect_biologie/index_continut.csv`, run the orchestrator:

```bash
python orchestrator.py
```

The orchestrator:

1. Reads the CSV index.
2. Runs `generator.py` when planned topics exist.
3. Runs `retry_errors.py` when records have `Eroare` status.
4. Repeats the workflow for up to `MAX_CICLURI`.
5. Stops when no planned or failed articles remain, or when `PRAG_TOTAL` is reached.

If the CSV index does not exist yet, the orchestrator stops without running the generator. Run `python generator.py` first.

## Content Index

The file `proiect_biologie/index_continut.csv` is the central data source for the pipeline.

| Column | Description |
|---|---|
| `Ramura` | Main biology branch |
| `Subramura` | Specific biology sub-branch |
| `Subcategorie` | Article topic |
| `Status` | `Planificat`, `Finalizat`, or `Eroare` |
| `Cale_Fisier` | Relative path of the generated article |

### Status Values

| Status | Meaning |
|---|---|
| `Planificat` | The topic is waiting to be generated |
| `Finalizat` | The article was generated successfully |
| `Eroare` | Article generation failed and can be retried |

## Utility Scripts

| Script | Purpose |
|---|---|
| `generator.py` | Main script: creates the initial content structure, generates planned articles, and suggests new topics through an audit step. |
| `orchestrator.py` | Runs the generator in cycles and triggers retries for failed articles. Use it only after the initial generator run has created the CSV index. |
| `retry_errors.py` | Regenerates only articles whose index status is `Eroare`. |
| `inspect_missing_topics.py` | Checks a manually maintained list of existing topics and resets matching `Finalizat` entries to `Planificat` for regeneration. It does not discover or add new topics. |
| `add_planned_topics.py` | Adds manually selected new topics to the CSV index with `Planificat` status while preventing duplicates. |
| `detect_similar_branches.py` | Detects branch and sub-branch names that become equivalent after basic normalization, including diacritics and parentheses. |
| `branch_merge_orchestrator.py` | Runs similarity detection, extracts proposed mappings, writes them to a report, injects mappings into `merge_branches.py`, and runs the merge. |
| `merge_branches.py` | Applies branch/sub-branch mapping rules, updates CSV paths, and moves article files between branch folders. |
| `update_index_after_moves.py` | Scans article folders and synchronizes branch names and file paths in the CSV index after manual file moves. |
| `generate_statistics.py` | Produces a statistics report with article totals, statuses, branch distributions, folder counts, and failed topics. |

## Commands

### Initialize or continue generation

```bash
python generator.py
```

Use this command for the first run and whenever you want to generate all topics with `Planificat` status.

### Run automated cycles

```bash
python orchestrator.py
```

Run this only after `generator.py` has created `proiect_biologie/index_continut.csv`.

### Retry failed articles

```bash
python retry_errors.py
```

This processes only rows where `Status = Eroare`.

### Add manual topics

Edit the `SUBIECTE_NOI` list in `add_planned_topics.py`, then run:

```bash
python add_planned_topics.py
```

Each entry requires a branch, a sub-branch, and an article topic:

```python
SUBIECTE_NOI = [
    ("Genetica", "Genomica functionala", "Analiza variatiei genomice la primate"),
]
```

The script adds non-duplicate topics to the index with `Status = Planificat`.

### Regenerate selected topics

Edit the `SUBIECTE_LIPSA` list in `inspect_missing_topics.py`, then run:

```bash
python inspect_missing_topics.py
```

The topic title must already exist exactly in `index_continut.csv`. Matching rows marked `Finalizat` are reset to `Planificat` so that `generator.py` can regenerate them.

### Generate statistics

```bash
python generate_statistics.py
```

This creates:

```text
proiect_biologie/statistici_articole.txt
```

### Detect similar branches

```bash
python detect_similar_branches.py
```

This prints suggested `RAMURA_MAP` and `SUBRAMURA_MAP` mappings based on normalized duplicate names.

### Detect and merge similar branches

```bash
python branch_merge_orchestrator.py
```

This command automatically runs branch detection and merge operations.

### Update the index after moves

```bash
python update_index_after_moves.py
```

Use this after manually moving article files between branch folders.

## Output

The generator stores article files in branch-specific folders:

```text
proiect_biologie/
├── index_continut.csv
└── articole/
    ├── Genetica/
    │   └── Analiza_variatiei_genomice_la_primate.txt
    └── Zoologie/
        └── Comportamentul_social_la_corvide.txt
```

Articles are saved as `.txt` files with Markdown-style headings.

## Generated Reports

The following files are created when their related scripts run:

```text
proiect_biologie/
├── raport_audit.txt
├── statistici_articole.txt
└── generated_branch_mapping.txt
```

- `raport_audit.txt` lists new topics suggested during the generator audit.
- `statistici_articole.txt` contains totals, status counts, branch distributions, folder counts, and failed topics.
- `generated_branch_mapping.txt` stores branch and sub-branch mappings proposed by similarity detection.

## Configuration

The main configuration in `generator.py` is:

```python
PRIMARY_MODEL = "deepseek-v4-flash"
BASE_DIR = "proiect_biologie"
MAX_WORKERS = 4
ARTICLES_PAUSE_SECONDS = 0.5
```

The orchestrator configuration is:

```python
MAX_CICLURI = 8
PRAG_TOTAL = None
```

Set `PRAG_TOTAL` to a number to stop automation after the index reaches a target number of articles.

## Recommended Workflow

1. Set `DEEPSEEK_API_KEY`.
2. Install dependencies with `pip install -r requirements.txt`.
3. Run `python generator.py` once to initialize the project.
4. Run `python orchestrator.py` for multi-cycle generation and automatic error recovery.
5. Run `python generate_statistics.py` to review progress.
6. Use `add_planned_topics.py` to add your own topics.
7. Use branch maintenance scripts only after backing up or committing your current work.

## Safety Notes

- Keep `DEEPSEEK_API_KEY` private.
- Generated content, the CSV index, and reports are excluded from Git by default.
- Review generated scientific content before publishing it as factual material.
- `inspect_missing_topics.py` uses a manually maintained list and can reset completed topics for regeneration.
- `branch_merge_orchestrator.py` can modify `merge_branches.py` automatically; commit or back up that file before running it.
- `merge_branches.py` can move article files and update the index; verify mappings before use.

## License

This project is intended for educational and portfolio purposes.
