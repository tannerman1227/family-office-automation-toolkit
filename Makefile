.PHONY: run test dashboard

run:
	python -m fotoolkit run-all

test:
	pytest

dashboard:
	streamlit run app/dashboard.py
