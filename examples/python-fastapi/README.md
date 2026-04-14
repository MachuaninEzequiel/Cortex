# Python FastAPI

Mini FastAPI app for testing the Cortex DevSecDocOps pipeline.

```bash
pip install -e ".[dev]"
pytest
ruff check .
uvicorn src.main:app --reload
```
