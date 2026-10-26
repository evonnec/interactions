# Interactions

![CI](https://github.com/evonnec/interactions/actions/workflows/ci.yml/badge.svg)

A small command line tool that reads lists of drugs from STDIN and reports, for each line, the most
severe known drug-drug interaction.

## Overview

The company platform enables physicians to diagnose patients and prescribe medications for many
common conditions. When prescribing, physicians constantly look for drug interactions: risks that
arise when a patient's response to a drug is affected by other drugs, food, supplements,
environmental factors or disease. Before prescribing any medication, patients are asked which other
drugs they are currently taking, so that physicians can find potential risks introduced by a new
medication. This tool is a take-home exercise modeling that check.

## Problem statement

Given a file containing a list of drug-drug interactions (`interactions.json`), write a command line
program that accepts a space-separated list of drugs per line and determines whether there is a
risk of interaction between any drugs in the list.

- If multiple interactions are detected for a single line of input, return the most severe one.
- If multiple interactions have the same severity, return the one that appears first in
  `interactions.json`.
- Read input from STDIN and write output to STDOUT. Each input line generates one output line, in
  the same order, formatted as `{SEVERITY}: {interaction message}`, or `No interaction`.
- Output nothing else (no debugging information).
- Constraints: 1 to 20 medications per line; 1 to 10,000 lines per execution.

### Examples

Based on the `interactions.json` file in this repository.

Input:

```text
sildenafil tamsulosin valaciclovir
sildenafil ibuprofen
valaciclovir doxepin ticlopidine ibuprofen
```

Output:

```text
MODERATE: Sildenafil may potentiate the hypotensive effect of alpha blockers, resulting in symptomatic hypotension in some patients.
No interaction
MAJOR: Valaciclovir may decrease the excretion rate of Doxepin which could result in a higher serum level.
```

## Requirements

- Python 3.14
- [uv](https://docs.astral.sh/uv/) (it will install Python 3.14 for you)

## Installation

Create the virtual environment and install the package plus dev tools:

```sh
uv sync
```

Or install the `interactions` command as a standalone tool. The dataset is bundled in the package,
so the installed command works from any directory:

```sh
uv tool install .
```

## Usage

```sh
interactions [--data PATH] [--version] [--help] < input.txt
uv run interactions < input.txt      # from a checkout
python -m interactions < input.txt   # equivalent
```

STDIN is the interface: lines of space-separated drug names in, one result line per input line out,
streamed line by line. STDOUT carries results only; warnings and errors go to STDERR.

| Option | Meaning |
|---|---|
| `--data PATH` | Use this interactions JSON file |
| `--version` | Print the version and exit |
| `-h`, `--help` | Print usage and exit (never reads STDIN) |

The data file is chosen in this order: `--data PATH`; else `./interactions.json` if it exists in the
current directory; else the copy bundled in the package
(`src/interactions/data/interactions.json`). It is loaded and validated once, before STDIN is read,
so a bad file fails immediately even when STDIN is empty.

Exit codes: `0` success (also when the reader of STDOUT closes the pipe early, e.g. `| head -1`),
`1` data or input error (one `error: ...` line on STDERR, nothing on STDOUT), `2` usage error.
Positional arguments are not accepted; use shell redirection to read a file.

## Behavior and assumptions

Every behavioral claim here is covered by a test (`tests/test_contract.py`, `tests/test_cli.py`,
`tests/test_index.py`).

- **One line out per line in.** The result is the most severe interaction among all pairs of drugs
  on the line. If several interactions share the top severity, the one that appears first in the
  data file wins; the order of drugs on the input line does not matter.
- **Output format.** `MAJOR: <description>`, `MODERATE: <description>`, `MINOR: <description>`, or
  `No interaction`. A blank or whitespace-only line prints `No interaction`.
- **Matching is case-insensitive.** Drug names (in the data and on input) are normalized with one
  function: Unicode NFKC, strip, `casefold()`. `Sildenafil` and `SILDENAFIL` match `sildenafil`.
- **Tokenizing.** Lines are split on newlines only (`\n`, `\r\n`); within a line any whitespace
  (spaces, tabs, form feed, U+2028, ...) separates drug names. Repeated drugs on a line are ignored.
- **Unknown drugs are ignored.** A drug that is not in the dataset can never produce an
  interaction, so a line that contains only unknown drugs prints `No interaction`. This is
  indistinguishable from a real negative; see Limitations.
- **Pairwise only.** Every record names exactly two drugs.
- **Duplicate pairs in the data.** If the same unordered pair appears more than once, the highest
  severity wins, then the earliest in the file. A warning is printed on STDERR.
- **Input encoding is UTF-8.** Invalid bytes produce `error: input is not valid UTF-8` and exit 1.
  One UTF-8 byte-order mark at the very start of STDIN (written by Windows Notepad, PowerShell and
  Excel) is ignored. A U+FEFF anywhere else (for example the second file of `cat a.txt b.txt`) is an
  ordinary character and stays attached to the drug name next to it.
- **The spec limits (1-20 drugs per line, up to 10,000 lines) are not enforced.** Longer inputs work;
  per-line cost grows with the square of the number of distinct known drugs on the line.

## Data

`interactions.json` is an array of records with exactly these keys:

```json
{"drugs": ["sildenafil", "tamsulosin"], "severity": "moderate", "description": "..."}
```

`drugs` must hold two distinct, non-empty names without whitespace (distinct after normalization);
`severity` is `minor`, `moderate` or `major` (any case); `description` is a non-empty string.
Unknown keys, missing keys and any other shape are rejected at load time with a one-line error that
names the file and the record index, for example
`error: bad.json: record 3: unknown severity 'contraindicated'`, and exit code 1.

The repository root `interactions.json` (the exercise's file) and the bundled
`src/interactions/data/interactions.json` must be byte-identical; a test enforces it. To update the
dataset, change both files and run the tests.

## Design

```text
src/interactions/
  model.py     Severity (IntEnum), frozen slotted Interaction, normalize()
  data.py      load + validate the data file; DataError (the only module that reads the data file)
  index.py     InteractionIndex (pair index), parse_drugs, format_result, process_lines (pure)
  cli.py       argparse, data resolution, streaming STDIN to STDOUT, errors and exit codes
  __main__.py  python -m interactions
  data/interactions.json   bundled dataset
scripts/       gen_input.py (seeded sample input generator), bench.py (timing); not packaged
tests/         unit tests per module, CLI and end-to-end contract tests, property test
```

**Algorithm.** The data is loaded and validated once. `InteractionIndex.build` keeps, for each
unordered pair of drugs, the best record by (severity descending, file position ascending), and
builds an adjacency map `drug -> {partner: record}`. Writing the tie-break into that sort key makes
"first in the file" explicit. For each input line, `most_severe` takes the set of normalized drugs
and, for each drug, intersects its partners with the line's drugs, keeping the smallest key.

**Complexity.** With `I` interactions, `L` lines and `n` distinct drugs per line:
build is `O(I)` time and memory, once; each line costs at most `n^2 / 2` lookups (190 for 20
drugs), independent of `I`, so the total is `O(I + L * n^2)`. Reading the file once and replacing
the per-record scan removed the dependence of per-line cost on the data size.

**Performance.** `scripts/bench.py` times the CLI end to end (new interpreter, discarding output).
On an Apple Silicon laptop, 10,004 lines of 20 drugs from `input.txt`: about 1.5 s before this
refactor (data re-read and scanned per line) and about 0.12 s after, of which roughly 0.04 s is
interpreter startup and imports. A seeded random 10,000 x 20 input takes the same time.

**I/O is separated from logic.** `process_lines(lines, index)` is a pure generator from input lines
to result lines; only `data.py` (the data file) and `cli.py` (STDIN, STDOUT, STDERR) do I/O.

## Development

```sh
uv run pytest --cov=interactions --cov-report=term-missing   # tests and coverage
uv run ruff check .                                          # lint
uv run ruff format --check .                                 # formatting
uv run mypy src tests                                        # strict type check
uv run python scripts/bench.py                               # time the CLI on input.txt
uv run python scripts/gen_input.py --lines 10000 --seed 1 > big_input.txt
```

## Testing

- Unit tests for each module use a small hand-made dataset (`tests/data/mini_interactions.json`)
  and in-memory records; every test runs from an empty temporary working directory.
- `tests/test_contract.py` runs `python -m interactions` in a subprocess against the bundled data:
  the spec examples byte for byte (`tests/data/spec_examples.in/.out`), the one-line-per-input
  invariant (including `\f`, `\v`, `\x85` and U+2028 inside a line), the output grammar on a seeded
  10,000 x 20 generated input, help, version, error exit codes and a closed STDOUT pipe.
- `tests/test_property.py` compares the index with a brute-force reference
  (`tests/reference.py`) on seeded random data and inputs, including duplicate pairs and ties.
- Coverage is 100%.

## Limitations and future work

- Not a clinical decision tool. The dataset covers about 150 drugs and 152 pairs; `No interaction`
  only means that no record for a pair on the line was found.
- Unknown drugs (typos, brand names, other separators such as commas) silently give
  `No interaction`; reporting them on STDERR (and a `--strict` mode) is not implemented.
- No synonym or brand-name mapping.
- No provenance, version or checksum is recorded for the dataset.
- `input.txt` (10,004 lines, 4 distinct lines) is kept for the CI smoke test; use
  `scripts/gen_input.py` for realistic varied input.
- Interactions are pairwise only.

## Releases

See [docs/RELEASING.md](docs/RELEASING.md).
