PANDOC ?= pandoc
PYTHON ?= python3
SOURCE := INTERRUPTIBLE-UNIVERSES-PAPER-DRAFT.md
OUTPUT := ../output/pdf/INTERRUPTIBLE-UNIVERSES-PRE-RESULTS-DRAFT.pdf

.PHONY: all figures clean

all: $(OUTPUT)

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

clean:
	rm -rf tmp/pdfs
	rm -f ../output/pdf/INTERRUPTIBLE-UNIVERSES-PRE-RESULTS-DRAFT.pdf
