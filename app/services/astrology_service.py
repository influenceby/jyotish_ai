import requests

from app.config import ASTROLOGY_API_KEY


class AstrologyService:

    BASE_URL = "https://json.astrologyapi.com/v1"

    def __init__(self):
        self.headers = {
            "Content-Type": "application/json",
            "x-astrologyapi-key": ASTROLOGY_API_KEY
        }

    def call_api(self, endpoint: str, payload: dict):
        """
        Generic method to call AstrologyAPI endpoints.
        """

        url = f"{self.BASE_URL}/{endpoint}"

        try:
            response = requests.post(
                url,
                json=payload,
                headers=self.headers,
                timeout=30
            )

            response.raise_for_status()

            return response.json()

        except requests.exceptions.RequestException as e:

            print(f"AstrologyAPI Error: {e}")

            if response is not None:
                print(response.text)

            raise


astrology_service = AstrologyService()
