# AI Proof of Concept Demo

This repository contains a structured Python project for developing and testing AI/ML proof of concept demos.

## Project Structure

```
.
├── src/           # Source code
├── tests/         # Unit tests
├── data/          # Data files and datasets
├── models/        # Saved model files
├── notebooks/     # Jupyter notebooks for exploration
└── config/        # Configuration files
```

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Unix/macOS
# or
.\venv\Scripts\activate  # On Windows
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the root directory for environment variables:
```bash
cp .env.example .env
```

## Development

- Use `black` for code formatting
- Use `flake8` for linting
- Write tests in the `tests/` directory
- Use notebooks in the `notebooks/` directory for exploration

## Best Practices

1. Keep source code modular and well-documented
2. Use type hints for better code maintainability
3. Write unit tests for critical functionality
4. Version control your data and model files appropriately
5. Document your experiments and results 