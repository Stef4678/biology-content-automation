# Biology Content Automation

An automated Python pipeline for generating, indexing, validating, repairing, and organizing structured biology articles with the DeepSeek API.

The project creates a hierarchical biology content plan, generates structured articles in Markdown format, tracks their status in a CSV index, retries failed requests, audits missing subjects, and provides maintenance tools for branch normalization and reporting.

## Features

- Generates a biology taxonomy with branches, sub-branches, and article topics
- Creates and maintains a CSV content index
- Generates structured biology articles through the DeepSeek API
- Validates model output with Pydantic schemas
- Uses JSON output mode for structured API responses
- Cleans malformed JSON responses before validation
- Processes articles concurrently with up to four workers
- Retries failed API calls with exponential backoff
- Marks articles as `Planificat`, `Finalizat`, or `Eroare`
- Retries failed articles with a dedicated recovery script
- Detects missing topics and adds new topics to the content plan
- Detects similar branch and sub-branch names
- Merges duplicate branch names and updates file paths
- Updates the index after manual file moves
- Generates progress and error statistics

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
    └── index_continut.csv
```

Generated articles and reports are created automatically inside `proiect_biologie/`.

## Requirements

- Python 3.10 or newer
- A DeepSeek API key

Install the dependencies:

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

Do not hard-code the API key in the Python files and never upload it to GitHub.

## Quick Start

Run the main generator:

```bash
python generator.py
```

On the first run, the script creates:

- `proiect_biologie/index_continut.csv`
- A hierarchy of biology branches and article topics
- The `proiect_biologie/articole/` directory

On later runs, it generates all topics marked as `Planificat` and then audits the index for missing topics.

## Automated Workflow

Use the main orchestrator to run the generator and retry failed articles for multiple cycles:

```bash
python orchestrator.py
```

The orchestrator runs `generator.py`, checks the CSV index, runs `retry_errors.py` when records have `Eroare` status, and stops when no planned or failed articles remain.

## Content Index

The file `proiect_biologie/index_continut.csv` is the central data source for the pipeline.

It contains the following columns:

| Column | Description |
|---|---|
| `Ramura` | Main biology branch |
| `Subramura` | Specific biology sub-branch |
| `Subcategorie` | Article topic |
| `Status` | `Planificat`, `Finalizat`, or `Eroare` |
| `Cale_Fisier` | Relative path of the generated article |

## Utility Scripts

| Script | Purpose |
|---|---|
| `generator.py` | Main script: creates the initial content structure, generates articles, and automatically suggests new topics through an audit step. |
| `orchestrator.py` | Runs the generator in cycles and automatically triggers retries for failed articles. |
| `retry_errors.py` | Regenerates only the articles whose index status is `Eroare` (Error). |
| `detect_similar_branches.py` | Detects similar branches and sub-branches, including differences caused by diacritics or parentheses. |
| `branch_merge_orchestrator.py` | Runs similarity detection, extracts the proposed mappings, injects them into the merge script, and executes the merge. |
| `merge_branches.py` | Merges branches and sub-branches according to mapping rules and moves article files into the correct directories. |
| `update_index_after_moves.py` | Synchronizes branch names and article paths in the index after article files have been moved manually. |
| `inspect_missing_topics.py` | Checks a manually maintained list of existing topics and resets matching entries from `Finalizat` (Completed) to `Planificat` (Planned) for regeneration. |
| `add_planned_topics.py` | Adds entirely new topics manually to the index with `Planificat` (Planned) status while preventing duplicates. |
| `generate_statistics.py` | Produces a statistics report with totals, statuses, branch distributions, and failed topics. |

## Commands

Generate or continue article creation:

```bash
python generator.py
```

Run the full generation and retry workflow:

```bash
python orchestrator.py
```

Retry failed articles only:

```bash
python retry_errors.py
```

Add manually selected topics:

```bash
python add_planned_topics.py
```

Generate statistics:

```bash
python generate_statistics.py
```

Detect and merge similar branches:

```bash
python branch_merge_orchestrator.py
```

Update the index after moving article files manually:

```bash
python update_index_after_moves.py
```

## Output

The generator saves articles as text files in branch-specific folders:

```text
proiect_biologie/
├── index_continut.csv
└── articole/
    ├── Genetica/
    │   └── Analiza_variatiei_genomice_la_primate.txt
    └── Zoologie/
        └── Comportamentul_social_la_corvide.txt
```

It also creates these reports when relevant:

```text
proiect_biologie/
├── raport_audit.txt
├── statistici_articole.txt
└── generated_branch_mapping.txt
```

## Configuration

The main configuration in `generator.py` is:

```python
PRIMARY_MODEL = "deepseek-v4-flash"
BASE_DIR = "proiect_biologie"
MAX_WORKERS = 4
ARTICLES_PAUSE_SECONDS = 0.5
```

The main orchestrator can be configured with:

```python
MAX_CICLURI = 8
PRAG_TOTAL = None
```

Set `PRAG_TOTAL` to a number if you want to stop automation after reaching a target number of indexed articles.

## Safety Notes

- Keep `DEEPSEEK_API_KEY` private.
- Generated articles and reports are excluded from Git by default.
- Review generated scientific content before publishing it as factual material.
- Run `branch_merge_orchestrator.py` only after committing or backing up `merge_branches.py`, because it can update that source file automatically.

## License

This project is intended for educational and portfolio purposes.
