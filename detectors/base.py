from typing import Protocol, TypedDict


class Prediction(TypedDict):
    flagged: bool
    score: float


class Detector(Protocol):
    name: str

    def predict(self, text: str) -> Prediction:
        ...
