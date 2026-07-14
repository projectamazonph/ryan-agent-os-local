.PHONY: test compile verify install

test:
	PYTHONPATH=src python -m unittest discover -s tests -v

compile:
	PYTHONPATH=src python -m compileall -q src

verify: test compile

install:
	./scripts/install.sh
