docker-compose down
docker-compose build
docker rmi $(docker images -q -f dangling=true)
docker-compose up