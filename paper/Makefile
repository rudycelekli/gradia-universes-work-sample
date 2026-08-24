PANDOC ?= pandoc
PYTHON ?= python3
SOURCE := INTERRUPTIBLE-UNIVERSES-PAPER-DRAFT.md
OUTPUT := ../output/pdf/INTERRUPTIBLE-UNIVERSES-PRE-RESULTS-DRAFT.pdf
CONDITIONAL_SOURCE := CONDITIONALLY-APPROVED-PAPER-DRAFT.md
CONDITIONAL_OUTPUT := ../output/pdf/CONDITIONALLY-APPROVED-PRELIMINARY-RESULTS-DRAFT.pdf

.PHONY: all figures conditionally-approved papers clean

all: $(OUTPUT)

papers: $(OUTPUT) $(CONDITIONAL_OUTPUT)

conditionally-approved: $(CONDITIONAL_OUTPUT)

figures:
	$(PYTHON) make_figures.py

$(OUTPUT): $(SOURCE) preamble.tex hash-wrap.lua make_figures.py
	$(PYTHON) make_figures.py
	mkdir -p ../output/pdf tmp/pdfs
	$(PANDOC) $(SOURCE) \
		--from=markdown+tex_math_dollars+raw_tex+pipe_tables+yaml_metadata_block \
		--standalone \
		--pdf-engine=tectonic \
		--include-in-header=preamble.tex \
		--lua-filter=hash-wrap.lua \
		--toc --toc-depth=2 \
		--metadata=lang:en-US \
		--variable=fontsize:10pt \
		--output=$(OUTPUT)

$(CONDITIONAL_OUTPUT): $(CONDITIONAL_SOURCE) conditionally-approved-preamble.tex hash-wrap.lua
	mkdir -p ../output/pdf tmp/pdfs
	$(PANDOC) $(CONDITIONAL_SOURCE) \
		--from=markdown+tex_math_dollars+raw_tex+pipe_tables+yaml_metadata_block \
		--standalone \
		--pdf-engine=tectonic \
		--include-in-header=conditionally-approved-preamble.tex \
		--lua-filter=hash-wrap.lua \
		--toc --toc-depth=2 \
		--metadata=lang:en-US \
		--variable=fontsize:10pt \
		--output=$(CONDITIONAL_OUTPUT)

clean:
	rm -rf tmp/pdfs
	rm -f ../output/pdf/INTERRUPTIBLE-UNIVERSES-PRE-RESULTS-DRAFT.pdf
	rm -f ../output/pdf/CONDITIONALLY-APPROVED-PRELIMINARY-RESULTS-DRAFT.pdf
