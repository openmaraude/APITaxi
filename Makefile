DOCKER_IMAGE = openmaraude/api_taxi

all:
	@echo "To build and push Docker image, run make release"

release:
	docker build -t ${DOCKER_IMAGE}:latest .
	docker push ${DOCKER_IMAGE}:latest
