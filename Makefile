all:
	@echo "To make a tag, run make tag"

tag:
	git tag $(shell printf "$$(date '+%Y%m%d')-%03d" $$(($$(git tag --list "$$(date '+%Y%m%d')-*" --sort -version:refname | head -1 | awk -F- '{print $$2}')+1)))
