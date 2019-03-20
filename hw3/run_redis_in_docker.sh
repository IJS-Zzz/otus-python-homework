# Start Docker container with Redis database for testing App.
docker run -ti --rm --name redis_scoring_api -p 6379:6379 -d redis