.PHONY: setup run test check deploy-dry-run

setup:
	python3 -m venv .venv
	.venv/bin/pip install -r requirements-dev.txt

run:
	.venv/bin/streamlit run app.py

test:
	PYTHONPATH=. PYTHONPYCACHEPREFIX=/tmp/trailsignal-pycache .venv/bin/pytest -q

check: test
	PYTHONPYCACHEPREFIX=/tmp/trailsignal-pycache .venv/bin/python -m py_compile core.py app.py

deploy-dry-run:
	sh deploy/endpoint-dry-run.sh

