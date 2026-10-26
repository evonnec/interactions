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

Or install the `interactions` command as a standalone tool:

```sh
uv tool install .
```

## Usage

The program must be run from a directory that contains `interactions.json`; it is read from the
current working directory. Pipe a text file of drug lists into it:

```sh
uv run interactions < input.txt
```

`make_input_file.py` can generate a large sample input (1000 identical 20-drug lines):

```sh
uv run python -m interactions.make_input_file > big_input.txt
```

## Project layout

```text
.
├── interactions.json            # interaction data (read from the current directory)
├── input.txt                    # sample input
├── pyproject.toml               # packaging and tool configuration (uv_build)
├── src/interactions/
│   ├── __init__.py              # package version
│   ├── cli.py                   # STDIN/STDOUT entry point (`interactions` command)
│   ├── make_input_file.py       # sample input generator
│   ├── py.typed
│   └── lib/
│       └── interactions_logic.py  # data model, loading and matching
└── tests/
    ├── conftest.py              # shared fixtures (CWD helpers, CLI runner)
    ├── fixtures/interactions.json  # small dataset used by the unit and CLI tests
    ├── test_interactions_logic.py  # unit tests
    ├── test_cli.py              # end-to-end tests of cli.main()
    ├── test_golden.py           # spec examples against the real data, subprocess tests
    └── test_misc.py
```

## Development

```sh
uv run pytest --cov=interactions --cov-report=term-missing   # tests and coverage
uv run ruff check .                                          # lint
uv run ruff format --check .                                 # formatting
uv run mypy src tests                                        # strict type check
```

## Design overview

**Data model.** `Severity` is an `IntEnum` (`MINOR=1`, `MODERATE=2`, `MAJOR=3`) so severities
compare naturally, and its names are the output labels. `Interaction` is a frozen dataclass with
`drugs: tuple[str, ...]`, `severity` and `description`.

**Algorithm.** For each input line:

1. Split the line on whitespace into a set of drug names.
2. Load `interactions.json` and convert it to `Interaction` objects.
3. Keep every interaction whose drugs are all present in the line's set (a subset test).
4. Stable-sort the matches by descending severity, so equal severities keep file order.
5. Print exactly one line: the first element of that sorted list (the most severe interaction;
   among equal severities, the one that appears first in `interactions.json`), or
   `No interaction` if there are no matches.

**Complexity.** With `L` lines, `N` interactions in the file and `D` drugs per line, matching costs
`O(N * D)` per line after parsing. `interactions.json` is re-read and re-parsed for every input
line, so the total is `O(L * (N + N * D))`, dominated by file I/O and JSON parsing. Reading the file
once would be a straightforward improvement.

Matching is exact and case sensitive (`Sildenafil` does not match `sildenafil`), and repeated
drug names on a line are collapsed.

## Known limitations

- `interactions.json` is re-read for every input line.
- `interactions.json` must be in the current working directory; there is no option to point to a
  different file.
- Drug names are matched case sensitively with no normalization.
- A missing or malformed `interactions.json`, or an unknown severity value, raises an unhandled
  exception with a traceback rather than a friendly error.
- Blank input lines produce `No interaction`.

## Releases

See [docs/RELEASING.md](docs/RELEASING.md).
