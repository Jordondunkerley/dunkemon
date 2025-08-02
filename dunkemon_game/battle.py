import random
from typing import List, Tuple, Optional, Dict

from .monster import Monster
from .move import Move
from . import utils


class Battle:
    """Handle logic for a battle between the player and an opponent.

    The battle maintains two parties of monsters.  It exposes methods to
    perform player and opponent attacks, attempt captures, check for
    victory or defeat, and apply end‑of‑turn status effects.  This
    class contains no user‑interaction code; prompting and display
    should be handled by the caller.
    """

    def __init__(self, player_party: List[Monster], opponent_party: List[Monster], is_trainer: bool = False):
        # Shallow copy lists to avoid modifying original outside of battle
        self.player_party: List[Monster] = player_party
        self.opponent_party: List[Monster] = opponent_party
        self.is_trainer = is_trainer

    def get_active(self, party: List[Monster]) -> Optional[int]:
        for i, mon in enumerate(party):
            if not mon.is_fainted():
                return i
        return None

    def player_active_index(self) -> Optional[int]:
        return self.get_active(self.player_party)

    def opponent_active_index(self) -> Optional[int]:
        return self.get_active(self.opponent_party)

    def is_over(self) -> bool:
        return self.player_active_index() is None or self.opponent_active_index() is None

    def player_attack(self, move_index: int) -> List[str]:
        """Perform the player's attack with the chosen move.  Returns log messages."""
        logs: List[str] = []
        p_idx = self.player_active_index()
        o_idx = self.opponent_active_index()
        if p_idx is None or o_idx is None:
            return logs
        attacker = self.player_party[p_idx]
        defender = self.opponent_party[o_idx]
        move = attacker.select_move(move_index)
        if move is None:
            logs.append(f"{attacker.species} has no such move!")
            return logs
        if move.current_pp <= 0:
            logs.append(f"No PP left for {move.name}!")
            return logs
        move.use_pp()
        logs.append(f"{attacker.species} used {move.name}!")
        # Check hit
        if not move.hit():
            logs.append("It missed!")
            return logs
        # Calculate damage
        dmg = utils.damage_calculation(attacker, defender, move)
        defender.current_hp = max(0, defender.current_hp - dmg)
        logs.append(f"It dealt {dmg} damage!")
        # Check effect
        if move.effect == "Poison" and random.random() < 0.3:
            if defender.status is None:
                defender.status = "Poison"
                logs.append(f"{defender.species} was poisoned!")
        if defender.current_hp <= 0:
            logs.append(f"{defender.species} fainted!")
        return logs

    def opponent_attack(self) -> List[str]:
        """Opponent AI selects a random move and attacks.  Returns log messages."""
        logs: List[str] = []
        o_idx = self.opponent_active_index()
        p_idx = self.player_active_index()
        if o_idx is None or p_idx is None:
            return logs
        attacker = self.opponent_party[o_idx]
        defender = self.player_party[p_idx]
        # Choose a random available move with PP
        available_moves = [m for m in attacker.moves if m.current_pp > 0]
        if not available_moves:
            logs.append(f"{attacker.species} has no moves left!")
            return logs
        move = random.choice(available_moves)
        move.use_pp()
        logs.append(f"Foe {attacker.species} used {move.name}!")
        if not move.hit():
            logs.append("It missed!")
            return logs
        dmg = utils.damage_calculation(attacker, defender, move)
        defender.current_hp = max(0, defender.current_hp - dmg)
        logs.append(f"It dealt {dmg} damage!")
        # Apply effect
        if move.effect == "Poison" and random.random() < 0.3:
            if defender.status is None:
                defender.status = "Poison"
                logs.append(f"{defender.species} was poisoned!")
        if defender.current_hp <= 0:
            logs.append(f"{defender.species} fainted!")
        return logs

    def apply_status_effects(self) -> List[str]:
        """Apply end of turn status effects to both active monsters."""
        msgs: List[str] = []
        for party in (self.player_party, self.opponent_party):
            idx = self.get_active(party)
            if idx is not None:
                msgs.extend(party[idx].apply_status_effects())
        return msgs

    def attempt_capture(self, ball_bonus: float = 1.0) -> Tuple[bool, List[str]]:
        """Attempt to capture the opponent's active monster.

        Returns a tuple (success, messages).  The ball_bonus modifies the
        likelihood of capture.  This is only available in wild battles.
        """
        logs: List[str] = []
        if self.is_trainer:
            logs.append("You can't capture a trainer's monster!")
            return False, logs
        o_idx = self.opponent_active_index()
        if o_idx is None:
            logs.append("There is nothing to capture.")
            return False, logs
        target = self.opponent_party[o_idx]
        # Simple catch formula based on remaining HP
        hp_ratio = target.current_hp / target.max_hp
        # Base catch rate: easier if HP is low
        catch_prob = (1 - hp_ratio) * 0.8 * ball_bonus
        # Ensure some chance
        catch_prob = min(0.95, max(0.05, catch_prob))
        if random.random() < catch_prob:
            logs.append(f"Gotcha! {target.species} was caught!")
            # Transfer monster to player party
            self.player_party.append(target)
            # Remove from opponent party
            target.current_hp = 0
            return True, logs
        else:
            logs.append("Oh no! The monster broke free!")
            return False, logs