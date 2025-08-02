import random
from typing import Dict


class Move:
    """Represents a battle move used by monsters.

    Each move has a type, category (physical or special), power, accuracy and
    a possible secondary effect.  The current PP is tracked so that moves
    cannot be used indefinitely.
    """

    def __init__(self, name: str, data: Dict):
        self.name: str = name
        self.type: str = data.get("type", "Normal")
        self.category: str = data.get("category", "Physical")
        self.power: int = data.get("power", 0)
        self.accuracy: int = data.get("accuracy", 100)
        self.pp: int = data.get("pp", 20)
        self.priority: int = data.get("priority", 0)
        self.effect: str = data.get("effect", "None")
        self.current_pp: int = self.pp

    def hit(self) -> bool:
        """Return True if the move hits based on its accuracy."""
        if self.accuracy >= 100:
            return True
        return random.randint(1, 100) <= self.accuracy

    def restore_pp(self):
        """Restore PP to full."""
        self.current_pp = self.pp

    def use_pp(self) -> bool:
        """Decrement the PP and return True if the move is usable."""
        if self.current_pp <= 0:
            return False
        self.current_pp -= 1
        return True

    def as_dict(self) -> Dict:
        return {"name": self.name, "current_pp": self.current_pp}