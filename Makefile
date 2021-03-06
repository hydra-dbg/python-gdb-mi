.PHONY: all test dist upload

all:
	echo "Usage: make test|dist"
	exit 1

test:
	@byexample -l python --timeout 6 -- README.md regress/*.md

dist:
	rm -Rf dist/ build/ *.egg-info
	pandoc --from=markdown --to=rst README.md -o README.rst
	python setup.py sdist bdist_wheel --universal
	rm -Rf build/ *.egg-info README.rst

upload: dist
	twine upload dist/*.tar.gz dist/*.whl
