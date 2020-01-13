DOCKER_IMAGE = openmaraude/api_taxi
VERSION = $(shell sed -En "s/^__version__[[:blank:]]*=[[:blank:]]*['\"]([0-9\.]+)['\"]/\\1/p" APITaxi/__init__.py)
GIT_TAG = $(shell git tag --points-at HEAD)

all:
	@echo "To build and push Docker image, run make release"
	@echo "Do not forget to update __version__"

release:
	@echo "${GIT_TAG}" | grep -q "${VERSION}" || (echo "Software version in APITaxi/__init__.py does not match the tag on HEAD. Please update __version__, and tag the current commit with \`git tag <version>\`." ; exit 1)
	docker build -t ${DOCKER_IMAGE}:${VERSION} -t ${DOCKER_IMAGE}:latest .
	docker push ${DOCKER_IMAGE}:${VERSION}
	docker push ${DOCKER_IMAGE}:latest
