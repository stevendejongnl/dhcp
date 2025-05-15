IMAGE_NAME=dhcp-app

build:
	docker build -t $(IMAGE_NAME) .

run: build
	docker run --rm \
	-e API_TOKEN=$(API_TOKEN) \
	-e HOST=$(HOST) \
	-v ./data:/app/data \
	$(IMAGE_NAME)  $(filter-out $@,$(MAKECMDGOALS))

%::
	@: