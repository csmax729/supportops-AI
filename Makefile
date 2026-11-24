install:
	uv sync --frozen --python 3.11
api:
	uv run uvicorn backend.main:create_app --factory
ui:
	uv run streamlit run frontend/app.py
test:
	uv run pytest -q
