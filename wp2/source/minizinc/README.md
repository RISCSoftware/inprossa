# OptDSL

OptDSL is a Python-based domain-specific language for formulating optimisation problems that can be translated into MiniZinc models.

## Requirements

- Python 3.10+
- MiniZinc installed on the system

## Installation

Create a virtual environment and install the Python dependencies:

```bash
python -m venv .venv
source .venv/bin/activate    # Linux/macOS
# .venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

Install MiniZinc separately from the official MiniZinc distribution and confirm it is available:

```bash
minizinc --version
```

## Running the main example

The main entry point is:

```bash
python main.py
```

To optimise your own OptDSL formulations replace the string in `main.py` with your formulation