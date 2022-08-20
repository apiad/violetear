.PHONY: format
format:
	black .

.PHONY: format
test:
	black --check .
	pytest

.PHONY: docs
docs:
	cp Readme.md docs/index.md
	mkdocs build
