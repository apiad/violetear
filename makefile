.PHONY: format
format:
	black violetear

.PHONY: test
test:
	black --check violetear
	pytest --doctest-modules violetear tests

.PHONY: test-loop
test-loop:
	black --check .
	pytest --doctest-modules violetear tests


.PHONY: docs
docs: examples
	cp Readme.md docs/index.md
	mkdocs build

.PHONY: illiterate
illiterate:
	illiterate preset build

.PHONY: examples
examples:
	(cd docs && python guide.py)
	(cd docs/examples && python animations.py)
	(cd docs/examples && python color_spaces.py)
	(cd docs/examples && python flex_grid.py)
	(cd docs/examples && python semantic_design.py)
