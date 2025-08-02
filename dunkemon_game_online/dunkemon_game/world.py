import json
import random
from typing import Dict, List, Tuple, Optional

from .monster import Monster
from .move import Move
from . import utils


TILE_MAPPING = {
    '#': 'wall',
    '.': 'normal',
    '=': 'path',
    '~': 'water',
    '^': 'cave',
    'P': 'start',
    'C': 'center',
    'T': 'trainer'
}


class Trainer:
    """Represents an NPC trainer on the map with a fixed party."""

    def __init__(self, position: Tuple[int, int], party: List[Monster]):
        self.position = position
        self.party = party
        self.defeated: bool = False


class World:
    def __init__(self, species_data: Dict, moves_data: Dict, area_data: Dict):
        self.species_data = species_data
        self.moves_data = moves_data
        self.area_data = area_data
        self.map: List[List[str]] = []
        self.width: int = 0
        self.height: int = 0
        self.player_x: int = 0
        self.player_y: int = 0
        self.player_party: List[Monster] = []
        # Items: potions and balls
        self.items: Dict[str, int] = {"Potion": 3, "NetBall": 5}
        # Trainers keyed by position
        self.trainers: Dict[Tuple[int, int], Trainer] = {}

    def load_map(self, path: str):
        """Load map from a text file.  Finds player start and trainers."""
        with open(path, 'r') as f:
            lines = [line.rstrip('\n') for line in f]
        self.height = len(lines)
        self.width = max(len(line) for line in lines)
        self.map = []
        for y, line in enumerate(lines):
            row = []
            for x, ch in enumerate(line):
                if ch == 'P':
                    self.player_x = x
                    self.player_y = y
                    row.append('.')  # replace start with normal ground
                elif ch == 'T':
                    # Trainer placeholder; actual trainer parties will be assigned later
                    row.append('.')
                    # Create a trainer with a simple random party
                    party = [utils.generate_monster(random.choice(list(self.species_data.keys())), 3, 6,
                                                   self.species_data, self.moves_data) for _ in range(2)]
                    self.trainers[(x, y)] = Trainer((x, y), party)
                else:
                    row.append(ch)
            # Fill missing cells with wall
            while len(row) < self.width:
                row.append('#')
            self.map.append(row)

    def tile(self, x: int, y: int) -> str:
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.map[y][x]
        return '#'

    def set_tile(self, x: int, y: int, ch: str):
        if 0 <= x < self.width and 0 <= y < self.height:
            self.map[y][x] = ch

    def is_walkable(self, x: int, y: int) -> bool:
        ch = self.tile(x, y)
        return TILE_MAPPING.get(ch, 'wall') not in ('wall')

    def area_key(self, tile_ch: str) -> str:
        """Return the area key for random encounters based on a tile character."""
        tile_type = TILE_MAPPING.get(tile_ch, 'normal')
        # Map tile types to area_data keys
        if tile_type in self.area_data:
            return tile_type
        return 'normal'

    def maybe_trigger_encounter(self) -> Optional[Monster]:
        """Possibly trigger a wild encounter based on current tile.

        Returns a wild Monster or None if no encounter.
        """
        tile_ch = self.tile(self.player_x, self.player_y)
        key = self.area_key(tile_ch)
        # Only random encounters on certain terrains (exclude path)
        if key not in self.area_data:
            return None
        # 10% chance for encounter
        if random.random() < 0.10:
            options = self.area_data[key]
            selection = utils.weighted_choice(options)
            species_name = selection["species"]
            min_level = selection["min_level"]
            max_level = selection["max_level"]
            return utils.generate_monster(species_name, min_level, max_level,
                                           self.species_data, self.moves_data)
        return None

    def move_player(self, dx: int, dy: int):
        """Attempt to move the player by (dx, dy)."""
        new_x = self.player_x + dx
        new_y = self.player_y + dy
        if self.is_walkable(new_x, new_y):
            # Interactions: heal at center, trainer battle
            tile_ch = self.tile(new_x, new_y)
            self.player_x = new_x
            self.player_y = new_y
            # Check center
            if tile_ch == 'C':
                for mon in self.player_party:
                    mon.heal()
                # When healing, print message via return value (handled in main)
                return 'healed'
            # Check trainer
            pos = (new_x, new_y)
            if pos in self.trainers and not self.trainers[pos].defeated:
                return self.trainers[pos]
        return None

    def remove_trainer(self, trainer: Trainer):
        """Mark a trainer as defeated and remove them from the map."""
        trainer.defeated = True
        x, y = trainer.position
        # Remove trainer symbol on the map (already replaced with '.' on load)
        self.set_tile(x, y, '.')