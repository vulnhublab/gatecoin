.PHONY: all docs microcoin apidocs clean mrproper

DOCS_SRC := docs
BUILD_DIR := build
DOCS_BUILD_DIR := $(BUILD_DIR)/docs
DATADIR:=microcoin/data

all: docs webui flake8

pip-install:
	pip install .

pip-install-dev:
	pip install -e .[dev] -r requirements-dev.txt

docs: pydocs jsdocs

pydocs: apidocs
	sphinx-build -b html $(DOCS_SRC) $(DOCS_BUILD_DIR)

apidocs:
	sphinx-apidoc -o $(DOCS_SRC)/api microcoin/

jsdocs:
	cd microcoin/webui/microcoin/ && npm run docs

clean:
	python setup.py clean --all
	rm -vrf $(BUILD_DIR) ./dist ./*.pyc ./*.tgz ./*.egg-info

mrproper: clean

bandit:
	bandit -s B101 -r microcoin/

pylint:
	pylint microcoin/

ssl_cert:
	openssl req -x509 -newkey rsa:4096 -nodes -out $(DATADIR)/cert.pem -keyout $(DATADIR)/key.pem -days 365

flake8:
	flake8 microcoin/

webui:
	python setup.py compile_webui

