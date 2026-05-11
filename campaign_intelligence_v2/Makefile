.PHONY: install seed dev run clean

install:
	pip install -r requirements.txt

seed:
	python db/seed.py

dev:
	uvicorn main:app --reload --host 0.0.0.0 --port 8000

run:
	uvicorn main:app --host 0.0.0.0 --port 8000

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; true
	rm -f db/retailco_intel.db
