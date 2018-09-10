all:
	docker build -t python3-opencv3:latest -f ./python3-opencv3/Dockerfile . \
	&& docker-compose up