.PHONY: help clean get-version test bump-version build release changelog diagrams docs all

help:
	@echo "make help         -- show this help"
	@echo "make clean        -- clean leftovers and build files"
	@echo "make get-version  -- get current version"
	@echo "make test         -- run tests"
	@echo "make bump-version -- bump version"
	@echo "make build        -- build python package"
	@echo "make release      -- create github release"
	@echo "make changelog    -- update changelog"
	@echo "make diagrams     -- generate diagrams"
	@echo "make docs         -- build documentation"
	@echo "make all          -- clean, get-version, test, build"


clean:
	./scripts/clean.sh $(MAKEFLAGS)

get-version:
	./scripts/get-version.sh

test:
	./scripts/test.sh $(MAKEFLAGS)

bump-version:
	./scripts/bump-version.sh $(MAKEFLAGS)

build:
	./scripts/build.sh $(MAKEFLAGS)

release:
	./scripts/release.sh $(MAKEFLAGS)

changelog:
	./scripts/changelog.sh $(MAKEFLAGS)

diagrams:
	./scripts/diagrams.sh $(MAKEFLAGS)

docs:
	./scripts/docs.sh $(MAKEFLAGS)

all: clean get-version test build
