import math
import random
from typing import Dict, List, Any


def calculate_stats(base_stats: Dict[str, int], level: int) -> Dict[str, int]:
    """Calculate a monster's actual stats at the given level.

    A simplified version of the official formula is used.  HP and other
    stats scale linearly with level.  Individual values and effort
    values are ignored for simplicity.
    """
    stats = {}
    # HP formula: ((2 * base_hp) * level) / 100 + level + 10
    hp = ((2 * base_stats["hp"]) * level) // 100 + level + 10
    stats["hp"] = hp
    # Other stats: ((2 * base_stat) * level) / 100 + 5
    for key in ["attack", "defense", "sp_atk", "sp_def", "speed"]:
        stats[key] = ((2 * base_stats[key]) * level) // 100 + 5
    return stats


def type_effectiveness(move_type: str, defender_types: List[str]) -> float:
    """Return the damage multiplier for an attacking move type against a list of defending types."""
    # Simplified type chart.  If an entry is missing, the multiplier is 1.0.
    chart: Dict[str, Dict[str, float]] = {
        "Fire": {"Grass": 2.0, "Water": 0.5, "Rock": 0.5, "Fire": 0.5},
        "Water": {"Fire": 2.0, "Rock": 2.0, "Water": 0.5, "Grass": 0.5},
        "Grass": {"Water": 2.0, "Rock": 2.0, "Grass": 0.5, "Fire": 0.5, "Poison": 0.5, "Flying": 0.5},
        "Electric": {"Water": 2.0, "Flying": 2.0, "Electric": 0.5, "Grass": 0.5},
        "Rock": {"Fire": 2.0, "Flying": 2.0, "Rock": 0.5},
        "Flying": {"Grass": 2.0, "Electric": 0.5, "Rock": 0.5, "Flying": 0.5},
        "Poison": {"Grass": 2.0, "Poison": 0.5, "Rock": 0.5},
        "Normal": {"Rock": 0.5}
    }
    multiplier = 1.0
    if move_type in chart:
        for d_type in defender_types:
            multiplier *= chart[move_type].get(d_type, 1.0)
    return multiplier


def weighted_choice(options: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Select an option from a list of dicts containing a 'weight' key."""
    total = sum(opt.get("weight", 1) for opt in options)
    r = random.uniform(0, total)
    upto = 0
    for opt in options:
        w = opt.get("weight", 1)
        if upto + w >= r:
            return opt
        upto += w
    return options[-1]


def damage_calculation(attacker, defender, move) -> int:
    """Compute the amount of damage inflicted by a move.

    The formula used is a simplified variant inspired by the official games.
    """
    level = attacker.level
    power = move.power
    # Select appropriate stats based on move category
    if move.category == "Physical":
        attack_stat = attacker.stats["attack"]
        defense_stat = defender.stats["defense"]
    else:
        attack_stat = attacker.stats["sp_atk"]
        defense_stat = defender.stats["sp_def"]
    base_damage = ((2 * level / 5 + 2) * power * (attack_stat / max(1, defense_stat)) / 50) + 2
    # STAB (Same Type Attack Bonus)
    stab = 1.5 if move.type in attacker.types else 1.0
    # Type effectiveness
    effectiveness = type_effectiveness(move.type, defender.types)
    # Random factor between 0.85 and 1.00
    random_factor = random.uniform(0.85, 1.0)
    damage = int(base_damage * stab * effectiveness * random_factor)
    return max(1, damage)


def generate_monster(species_name: str, min_level: int, max_level: int, species_data: Dict, moves_data: Dict):
    """Generate a Monster of the given species at a random level within the range."""
    level = random.randint(min_level, max_level)
    from .monster import Monster  # late import to avoid circular dependency
    species_info = species_data[species_name]
    return Monster(species_name, level, species_info, moves_data)