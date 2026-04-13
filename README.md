# Run Tests Locally

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
docker compose up -d
pytest
```

# Manual Checks

Go to localhost:8000/docs and use Swagger UI to test the endpoints.

# Docker Hub Repository

https://hub.docker.com/repository/docker/jl247/is601-module-12/general
