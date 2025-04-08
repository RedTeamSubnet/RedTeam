.PHONY: help clean get-version test bump-version build docs changelog all

help:
	@echo "make help         -- show this help"
	@echo "make clean        -- clean leftovers and build files"
	@echo "make get-version  -- get current version"
	@echo "make test         -- run tests"
	@echo "make bump-version -- bump version"
	@echo "make build        -- build python package"
	@echo "make docs         -- build documentation"
	@echo "make changelog    -- update changelog"
	@echo "make all          -- clean, get-version, test, build"

clean:
	./scripts/clean.sh -a

get-version:
	./scripts/get-version.sh

test:
	./scripts/test.sh $(MAKEFLAGS)

bump-version:
	./scripts/bump-version.sh $(MAKEFLAGS)

build:
	./scripts/build.sh $(MAKEFLAGS)

docs:
	./scripts/docs.sh $(MAKEFLAGS)

changelog:
	./scripts/changelog.sh $(MAKEFLAGS)

all: clean get-version test build
