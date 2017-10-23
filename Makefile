.PHONY: all test dist

all:
	echo "Usage: make test|dist"
	exit 1

test:
	python -m doctest regress/*.rst

dist:
	rm -Rf dist/ build/ *.egg-info
	pandoc --from=markdown --to=rst README.md -o README.rst
	python setup.py sdist bdist_wheel --universal
	rm -Rf build/ *.egg-info README.rst

