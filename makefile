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
	illiterate preset build
	mkdocs build

.PHONY: examples
examples:
	(cd docs && python styles.py)
	(cd docs/examples && python animations.py)
	(cd docs/examples && python color_spaces.py)
	(cd docs/examples && python fluid_grid.py)
