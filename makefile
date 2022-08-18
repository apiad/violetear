.PHONY: format
format:
	poetry run black .

.PHONY: docs
docs:
	cp Readme.md docs/index.md
	(cd docs && poetry run python3 styles.py)
	poetry run mkdocs build

.PHONY: docs-ga
docs-ga:
	cp Readme.md docs/index.md
	(cd docs && python3 styles.py)
	mkdocs build
