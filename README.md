# InProSSA - Industrial Problem Solving using Symbolic and Subsymblic AI

## Setup

### Install uv

**Linux/macOS:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows (PowerShell):**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Set up Python environment

After installing uv and cloning the repository:

```bash
cd inprossa
uv sync
```

This will create a virtual environment and install all dependencies.

# Structure

Every work packages has a specific directory.

Directory tree overview:
```
├───wp1
├───wp2
│   ├───formulation
│   ├───instances
│   └───source
│       ├───problemdatagenerator
|       └───simulator
|       └───optimiser
├───wp3
│   └───examples
├───wp4
└───wp5
```
