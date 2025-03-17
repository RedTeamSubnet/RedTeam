from fastapi import FastAPI
from challenge import Challenge

challenge = Challenge()

app = FastAPI()

app.add_api_route("/task", challenge.prepare_task, methods=["GET"])
app.add_api_route("/score", challenge.score_task, methods=["POST"])
app.add_api_route("/compare", challenge.compare, methods=["POST"])



@app.get("/health")
def health():
    return {"status": "healthy"}