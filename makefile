.PHONY: format
format:
	poetry run black .

.PHONY: docs
docs:
	cp Readme.md docs/index.md
	poetry run mkdocs build

.PHONY: docs-ga
docs-ga:
	cp Readme.md docs/index.md
	mkdocs build
