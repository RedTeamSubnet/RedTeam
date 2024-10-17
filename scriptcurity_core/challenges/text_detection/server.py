from fastapi import FastAPI
from .challenge import Challenge


class Server:
    """
    A class to manage the FastAPI server that exposes endpoints for interacting with the challenge.
    It handles the preparation of tasks and scoring of solutions via API routes.
    """

    def __init__(self, challenger: Challenge):
        """
        Initializes the FastAPI server and sets up API routes.
        The server has two main routes:
        - `/task` (GET): Retrieves a task prepared by the challenger.
        - `/score` (POST): Accepts input and output for scoring and returns the result.

        Args:
            challenger: An instance of the Challenge class, which provides task preparation and scoring logic.
        """
        self.app = FastAPI()
        self.challenger = challenger
        self.app.add_api_route("/task", self.challenger.prepare_task, methods=["GET"])
        self.app.add_api_route("/score", self.challenger.score_task, methods=["POST"])
