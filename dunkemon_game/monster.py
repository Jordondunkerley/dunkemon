import math
import random
from typing import Dict, List, Optional

from .move import Move
from . import utils


class Monster:
    """Represents an individual monster (similar to a Pokémon).

    Each monster has a species, level, current HP, a set of moves and
    calculated statistics based off of its species' base stats.  Monsters
    may also be affected by status conditions such as poison.
    """

    def __init__(self, species: str, level: int, species_data: Dict, moves_data: Dict):
        self.species = species
        self.level = level
        self.types: List[str] = species_data["types"]
        self.base_stats: Dict[str, int] = species_data["base_stats"]
        # Calculate actual stats at this level
        self.stats: Dict[str, int] = utils.calculate_stats(self.base_stats, level)
        self.max_hp: int = self.stats["hp"]
        self.current_hp: int = self.max_hp
        # Status condition: None, 'Poison'
        self.status: Optional[str] = None
        # Learn moves up to this level
        self.moves: List[Move] = []
        moveset = species_data.get("moveset", {})
        # Sort moves by level so early moves come first
        for move_name, learn_level in sorted(moveset.items(), key=lambda item: item[1]):
            if level >= learn_level and move_name in moves_data:
                self.moves.append(Move(move_name, moves_data[move_name]))
        # Ensure at most 4 moves
        self.moves = self.moves[:4]

    def apply_status_effects(self) -> List[str]:
        """Apply end‑of‑turn status effects.  Returns a list of messages."""
        msgs: List[str] = []
        if self.status == "Poison":
            # Lose 1/8 of max HP each turn
            damage = max(1, self.max_hp // 8)
            self.current_hp = max(0, self.current_hp - damage)
            msgs.append(f"{self.species} is hurt by poison!")
            if self.current_hp == 0:
                msgs.append(f"{self.species} fainted!")
        return msgs

    def is_fainted(self) -> bool:
        return self.current_hp <= 0

    def heal(self):
        self.current_hp = self.max_hp
        self.status = None
        for move in self.moves:
            move.restore_pp()

    def select_move(self, index: int) -> Optional[Move]:
        if index < 0 or index >= len(self.moves):
            return None
        return self.moves[index]

    def as_dict(self) -> Dict:
        """Serialize the monster for saving."""
        return {
            "species": self.species,
            "level": self.level,
            "current_hp": self.current_hp,
            "status": self.status,
            "moves": [move.as_dict() for move in self.moves],
        }

    @classmethod
    def from_dict(cls, data: Dict, species_data: Dict, moves_data: Dict):
        species_name = data["species"]
        level = data["level"]
        species_info = species_data[species_name]
        monster = cls(species_name, level, species_info, moves_data)
        monster.current_hp = data.get("current_hp", monster.max_hp)
        monster.status = data.get("status")
        # Restore PP of moves
        saved_moves = data.get("moves", [])
        for saved in saved_moves:
            name = saved.get("name")
            for move in monster.moves:
                if move.name == name:
                    move.current_pp = saved.get("current_pp", move.pp)
        return monster