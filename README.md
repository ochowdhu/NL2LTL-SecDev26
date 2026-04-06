# Syntax Is Easy, Semantics Is Hard: Evaluating LLMs for LTL Translation

<p align="center">
  <a href="https://doi.org/10.1145/3805773.3806005"><img src="https://img.shields.io/badge/DOI-10.1145%2F3805773.3806005-blue" alt="DOI"></a>
  <a href="https://secdev.acm.org/2026/"><img src="https://img.shields.io/badge/Venue-ACM%20SecDev%202026-orange" alt="Venue"></a>
  <img src="https://img.shields.io/badge/Python-3.13%2B-green" alt="Python">
  <img src="https://img.shields.io/badge/License-CC%20BY--NC--ND%204.0-lightgrey" alt="License">
</p>

> **Priscilla Kyei Danso, Mohammad Saqib Hasan, Niranjan Balasubramanian, Omar Chowdhury**  
> Stony Brook University — `{pdanso, mdshasan, niranjan, omar}@cs.stonybrook.edu`  
> *Proceedings of the 2026 ACM Secure Development Conference (SecDev 2026), July 05–06, Montreal, QC, Canada*

---

## Overview

This repository contains the full benchmark, datasets, prompts, experiment code, and evaluation scripts for our paper. We systematically evaluate multiple Large Language Models (LLMs) on the task of translating natural language (NL) specifications into **Linear Temporal Logic (LTL)** formulas. Evaluation spans:

- **Six translation tasks:** WFF Classification, NL2PL (Propositional Logic), NL2FutureLTL, Trace Characterization, Trace Generation, NL2PastLTL
- **Three prompting strategies:** Minimal, Detailed, Python
- **Three learning approaches:** Zero-Shot, Zero-Shot Self-Refine, Few-Shot
- **Two correctness dimensions:** Syntactic correctness and semantic consistency

A key finding: LLMs learn LTL syntax relatively easily, but semantic correctness must be verified through model checking, that remains a significant challenge.

---

## Table of Contents

- [Repository Structure](#repository-structure)
- [Prerequisites](#prerequisites)
  - [Python Setup](#python-setup)
  - [OCaml and NuSMV Setup](#ocaml-and-nusmv-setup)
- [API Key Configuration](#api-key-configuration)
- [Datasets](#datasets)
- [Running Experiments](#running-experiments)
  - [NL2PL](#nl2pl-propositional-logic)
  - [NL2FutureLTL](#nl2futureltl)
  - [NL2PastLTL](#nl2pastltl)
  - [Trace Characterization](#trace-characterization)
  - [Trace Generation](#trace-generation)
- [Prompting Strategies](#prompting-strategies)
- [Supported Models](#supported-models)
- [Evaluation Metrics](#evaluation-metrics)
- [LTL Model Checker (OCaml)](#ltl-model-checker-ocaml)
- [Dashboard](#dashboard)
- [Citation](#citation)
- [License](#license)

---

## Repository Structure

```
NL2LTL-SecDev26/
│
├── LTL/                          # OCaml model checker for semantic evaluation
│   ├── corrected_version/
│   │   └── ltlutils/             # Core LTL utilities; compile-project script lives here
│   └── LTL_PARSER/               # LTL parser library
│
├── dashboard/                    # Streamlit interactive results dashboard
│
├── experiment/                   # Entry-point scripts for each benchmark task
│   ├── nl2pl.py                  # NL → Propositional Logic
│   ├── nl2futureltl.py           # NL → Future LTL
│   ├── nl2pastltl.py             # NL → Past LTL
│   ├── trace_characterization.py # Trace characterization benchmark
│   ├── trace_generation.py       # Trace generation benchmark
│   └── wff.py                    # Well-formedness checking
│
├── prompts/                      # Prompt templates, split by strategy
│   ├── minimal/                  # Minimal prompts (bare instruction only)
│   ├── detailed/                 # Detailed prompts (grammar + examples)
│   └── python/                   # Python-style AST prompts
│
├── scripts/                      # Helper utilities (not called directly)
│   ├── semantic_checker.py       # Calls NuSMV for semantic equivalence
│   ├── ltl_extractor.py          # Extracts LTL formulas from model outputs
│   ├── entail_equiv_analyzer.py  # Entailment and equivalence analysis
│   ├── trace_characterization_eval.py
│   ├── trace_satisfaction.py
│   ├── convert_ltl_to_ast.py
│   ├── load_data.py
│   └── save_results.py
│
├── input_data/                   # All datasets used in experiments 
│   ├── nl2ltl_finalized.csv      # Main NL2FutureLTL dataset
│   ├── nl2pl.csv / nl2pl_finalized.csv
│   ├── past_ltl.csv
│   ├── trace_characterization_littletrickylogic.csv
│   ├── wff_finalized.csv
│   └── python_exp/               # AST-formatted variants for Python prompts
│       ├── nl2ltl_finalized_ast.csv
│       ├── past_ast.csv
│       └── trace_ast_new.csv
│
├── output_data/                  # Experiment outputs (auto-created on run)
│   ├── minimal/
│   ├── detailed/
│   └── python/
│
├── handle_keys.py                # API key configuration
├── parse_prompt.py               # Prompt-to-API communication layer
├── parse_request.py              # Request parsing utilities
└── requirements.txt              # Python dependencies
```

---

## Prerequisites

### Python Setup

**Python 3.13+** is required.

```bash
git clone https://github.com/yourusername/NL2LTL-SecDev26.git
cd NL2LTL-SecDev26

# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate          # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### OCaml and NuSMV Setup

The semantic evaluation pipeline (`scripts/semantic_checker.py`) depends on a compiled OCaml binary that wraps the **NuSMV** model checker. This is required for any experiment that reports semantic correctness metrics. If you only want syntactic results, you can skip this section.

#### 1. Install OCaml via opam

```bash
# Install opam (follow instructions at https://opam.ocaml.org/doc/Install.html)
opam init
opam install dune
opam install merlin
opam install menhir
opam install ocaml-lsp-server
opam user-setup install
```

#### 2. Install NuSMV

Download the NuSMV binary for your OS from: https://nusmv.fbk.eu/downloads.html

Note the path to NuSMV's `bin/` folder — you will need it in the next step.

#### 3. Compile the OCaml LTL checker

```bash
cd LTL/corrected_version/ltlutils/

# Open compile-project and replace the placeholder NuSMV path with your own
# e.g. /usr/local/nusmv/bin  or  /Applications/NuSMV/bin
nano compile-project

# Make the script executable
chmod a+x compile-project

# Compile
./compile-project
dune build
```

To verify the build:
```bash
echo "equiv\nG(a -> F b)\nG(a -> F b)" | dune exec ./bin/main.exe
# Expected output: EQUIVALENT
```

---

## API Key Configuration

Open `handle_keys.py` and add your API keys for the providers you intend to use:

```python
OPENAI_API_KEY    = "sk-..."       # GPT-3.5-Turbo, GPT-4o, GPT-4o-Mini
ANTHROPIC_API_KEY = "sk-ant-..."   # Claude-3.5-Sonnet
GOOGLE_API_KEY    = "AIza..."      # Gemini-1.5-Flash, Gemini-1.5-Pro, Gemini-2.5-Flash
```

> **Security:** Never commit `handle_keys.py` with real keys. Add it to `.gitignore` or use environment variables instead. A `.env`-based alternative using `python-dotenv` is also supported if you prefer.

You do not need all three providers. Experiments will skip models whose keys are missing.

---

## Datasets

All datasets are in `input_data/`. The table below maps each experiment to its input file:

| Experiment | Standard dataset | Python/AST dataset |
|---|---|---|
| NL2FutureLTL | `nl2ltl_finalized.csv` | `python_exp/nl2ltl_finalized_ast.csv` |
| NL2PastLTL | `past_ltl.csv` | `python_exp/past_ast.csv` |
| NL2PL | `nl2pl_finalized.csv` | — |
| Trace Characterization | trace_characterization_littletrickylogic | `python_exp/trace_ast_new.csv` |
| Trace Generation | `nl2ltl_finalized.csv` | `python_exp/nl2ltl_finalized_ast.csv` |
| Well-Formedness | `wff_finalized.csv` | — |

The `python_exp/` variants contain AST (Abstract Syntax Tree) formatted LTL representations required by the Python prompting strategy.

---

## Running Experiments

All experiment scripts share the same two core arguments:

| Argument | Description | Values |
|---|---|---|
| `--dataset` | Path to input CSV | See table above |
| `--experiment_type` | Prompting strategy | `minimal`, `detailed`, `python` |
| `--experiment_name` | Name for the output folder | Any string; used to organise `output_data/` |

Results are saved to `output_data/<experiment_type>/<experiment_name>/`.

---

### NL2PL (Propositional Logic)

```bash
# Minimal
python experiment/nl2pl.py \
  --dataset input_data/nl2pl_finalized.csv \
  --experiment_type minimal \
  --experiment_name nl2pl_minimal

# Detailed
python experiment/nl2pl.py \
  --dataset input_data/nl2pl_finalized.csv \
  --experiment_type detailed \
  --experiment_name nl2pl_detailed
```

---

### NL2FutureLTL

```bash
# Minimal
python experiment/nl2futureltl.py \
  --dataset input_data/nl2ltl_finalized.csv \
  --experiment_type minimal \
  --experiment_name nl2futureltl_minimal

# Detailed
python experiment/nl2futureltl.py \
  --dataset input_data/nl2ltl_finalized.csv \
  --experiment_type detailed \
  --experiment_name nl2futureltl_detailed

# Python (uses AST dataset)
python experiment/nl2futureltl.py \
  --dataset input_data/python_exp/nl2ltl_finalized_ast.csv \
  --experiment_type python \
  --experiment_name nl2futureltl_python
```

---

### NL2PastLTL

```bash
# Python
python experiment/nl2pastltl.py \
  --dataset input_data/python_exp/past_ast.csv \
  --experiment_type python \
  --experiment_name nl2pastltl_python
```

---

### Trace Characterization

```bash
python experiment/trace_characterization.py \
  --dataset input_data/python_exp/trace_ast_new.csv \
  --experiment_type python \
  --experiment_name trace_char_python
```

---

### Trace Generation

```bash
python experiment/trace_generation.py \
  --dataset input_data/python_exp/nl2ltl_finalized_ast.csv \
  --experiment_type python \
  --experiment_name trace_gen_python
```

---

## Prompting Strategies

| Strategy | Description |
|---|---|
| **Minimal** | Bare instruction only — model name and task description with no additional context. Tests baseline LLM capability. |
| **Detailed** | Includes the full LTL grammar definition, operator semantics, and worked examples. Designed to reduce syntactic errors. |
| **Python** | Represents LTL formulas as Python AST objects. Leverages LLMs' strong code generation ability for structured formula output. |

Prompt templates are in `prompts/<strategy>/`. Each task has its own template file, e.g. `ltl_future_prompt_template.py`, `ltl_past_prompt_template.py`.

---

## Supported Models

| Model | Minimal | Detailed | Python |
|---|:---:|:---:|:---:|
| GPT-3.5-Turbo | ✓ | ✓ | |
| GPT-4o-Mini | ✓ | ✓ | |
| GPT-4o | ✓ | ✓ | |
| Claude-3.5-Sonnet | ✓ | ✓ | ✓ |
| Gemini-1.5-Flash | ✓ | ✓ | ✓ |
| Gemini-1.5-Pro | | | ✓ |
| Gemini-2.5-Flash | | | ✓ |

---

## Evaluation Metrics

### Syntactic Metrics

| Metric | Description |
|---|---|
| **Exact Match** | Formula string matches ground truth exactly |
| **Syntactic Correctness** | Formula parses without error under the LTL grammar |
| **Jaccard Similarity** | Word-level token overlap between predicted and ground-truth formula |
| **Levenshtein Distance** | Character-level edit distance, normalised |
| **F1 Score** | Token-level precision/recall harmonic mean |

### Semantic Metrics

| Metric | Description |
|---|---|
| **Equivalence Accuracy** | Formula is logically equivalent to ground truth (verified by NuSMV) |
| **Soundness (GT→Pred)** | Every trace satisfying ground truth also satisfies the prediction |
| **Completeness (Pred→GT)** | Every trace satisfying the prediction also satisfies ground truth |

> Semantic metrics require the compiled OCaml/NuSMV checker. See [OCaml and NuSMV Setup](#ocaml-and-nusmv-setup).

---

## LTL Model Checker (OCaml)

The `LTL/` directory contains a standalone OCaml tool for working with LTL formulas directly. It wraps NuSMV to perform model checking operations.

### Commands

Run any command with:
```bash
dune exec ./bin/main.exe < your_input_file
```

The input file must have the command on the first line, followed by formulas on separate lines, with **no blank lines** between them.

| Command | Arguments | Description |
|---|---|---|
| `equiv` | `f1`, `f2` | Check logical equivalence of two formulas |
| `check_future` | `f` | Verify formula uses only future temporal operators |
| `check_past` | `f` | Verify formula uses only past temporal operators |
| `positive_trace_gen` | `f` | Generate a satisfying trace for formula `f` |
| `negative_trace_gen` | `f` | Generate a falsifying trace for formula `f` |
| `print_formula` | `f` | Print formula `f` in NuSMV format |

### Example input file

```
equiv
G(a -> F b)
G(a -> F b)
```

Only the **first command** in the file is executed. See `LTL/corrected_version/ltlutils/inp_file` for more examples.

Traces are written to `<nusmv_bin_path>/trace.out`.

---

## Dashboard

An interactive Streamlit dashboard is included in `dashboard/` for exploring and comparing experimental results.

https://appexperimentdashboardpy-2qq8aouv7wkun3k9yzctqw.streamlit.app/


The dashboard lets you filter by model, prompting strategy, task, and learning approach, and displays accuracy, F1, and semantic metrics side by side.

---

## Citation

If you use this benchmark, dataset, or code in your work, please cite:

```bibtex
@inproceedings{danso2026syntax,
  title     = {Syntax Is Easy, Semantics Is Hard: Evaluating {LLM}s for {LTL} Translation},
  author    = {Danso, Priscilla Kyei and Hasan, Mohammad Saqib and
               Balasubramanian, Niranjan and Chowdhury, Omar},
  booktitle = {Proceedings of the 2026 ACM Secure Development Conference},
  series    = {SecDev 2026},
  year      = {2026},
  month     = {July},
  address   = {Montreal, QC, Canada},
  publisher = {ACM},
  doi       = {10.1145/3805773.3806005},
  isbn      = {979-8-4007-2602-6}
}
```

---

## License

This work is licensed under [CC BY-NC-ND 4.0](https://creativecommons.org/licenses/by-nc-nd/4.0/). You may share it with attribution, but may not use it for commercial purposes or distribute modified versions.

---

<p align="center">
  Stony Brook University · Department of Computer Science · 2026
</p>
