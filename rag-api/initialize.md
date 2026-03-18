python -m uvicorn main:app --reload --port 8000
python -m uvicorn challenge_agent:app --reload --port 8001
python -m uvicorn validation_agent:app --reload --port 8002