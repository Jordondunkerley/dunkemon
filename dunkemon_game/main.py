import curses
import json
import os
import sys
from typing import List, Optional

from .battle import Battle
from .monster import Monster
from .move import Move
from . import utils
from .world import World, Trainer
from . import online


DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
MAP_DIR = os.path.join(os.path.dirname(__file__), 'maps')
SAVE_FILE = os.path.join(os.path.dirname(__file__), 'save.json')


def load_json(path: str):
    with open(path, 'r') as f:
        return json.load(f)


class Game:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        curses.curs_set(0)
        curses.noecho()
        curses.cbreak()
        stdscr.keypad(True)
        # Initialize colors
        if curses.has_colors():
            curses.start_color()
            curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)  # default
            curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)  # grass
            curses.init_pair(3, curses.COLOR_BLUE, curses.COLOR_BLACK)   # water
            curses.init_pair(4, curses.COLOR_YELLOW, curses.COLOR_BLACK) # path
            curses.init_pair(5, curses.COLOR_MAGENTA, curses.COLOR_BLACK)# cave
            curses.init_pair(6, curses.COLOR_RED, curses.COLOR_BLACK)    # center
            curses.init_pair(7, curses.COLOR_CYAN, curses.COLOR_BLACK)   # trainer
            curses.init_pair(8, curses.COLOR_YELLOW, curses.COLOR_BLUE)  # player
        # Load data
        self.species_data = load_json(os.path.join(DATA_DIR, 'species.json'))
        self.moves_data = load_json(os.path.join(DATA_DIR, 'moves.json'))
        self.area_data = load_json(os.path.join(DATA_DIR, 'areas.json'))
        # Create world
        self.world = World(self.species_data, self.moves_data, self.area_data)
        self.world.load_map(os.path.join(MAP_DIR, 'overworld.txt'))
        # Initialize player party with a starter monster
        starter_name = 'Ignis'
        self.world.player_party = [Monster(starter_name, 5, self.species_data[starter_name], self.moves_data)]
        # Game state: 'explore' or 'battle'
        self.state = 'explore'
        self.battle: Optional[Battle] = None
        self.message_queue: List[str] = []

    def save_game(self):
        data = {
            'player_pos': [self.world.player_x, self.world.player_y],
            'player_party': [mon.as_dict() for mon in self.world.player_party],
            'items': self.world.items,
            'trainers': {f"{x},{y}": tr.defeated for (x, y), tr in self.world.trainers.items()}
        }
        # Attempt online save if enabled
        if online.is_online_mode():
            try:
                online.save_game(data)
                self.message_queue.append('Game saved to remote server.')
                return
            except Exception as e:
                # Fallback to local save
                self.message_queue.append(f'Online save failed: {e}. Saving locally.')
        # Local save fallback
        with open(SAVE_FILE, 'w') as f:
            json.dump(data, f)

    def load_game(self):
        # Attempt online load if enabled
        data = None
        if online.is_online_mode():
            try:
                data = online.load_game()
                self.message_queue.append('Loaded game from remote server.')
            except Exception as e:
                self.message_queue.append(f'Online load failed: {e}. Trying local save.')
        if data is None:
            if not os.path.exists(SAVE_FILE):
                self.message_queue.append('No save file found.')
                return
            with open(SAVE_FILE, 'r') as f:
                data = json.load(f)
            self.message_queue.append('Loaded game.')
        # Restore state from data
        self.world.player_x, self.world.player_y = data.get('player_pos', [self.world.player_x, self.world.player_y])
        # Load party
        self.world.player_party = []
        for mon_data in data.get('player_party', []):
            species = mon_data['species']
            mon = Monster.from_dict(mon_data, self.species_data, self.moves_data)
            self.world.player_party.append(mon)
        # Items
        self.world.items = data.get('items', self.world.items)
        # Restore trainers
        trainer_status = data.get('trainers', {})
        for pos_str, defeated in trainer_status.items():
            try:
                x_str, y_str = pos_str.split(',')
                pos = (int(x_str), int(y_str))
                if pos in self.world.trainers:
                    self.world.trainers[pos].defeated = defeated
            except Exception:
                continue

    def run(self):
        while True:
            self.stdscr.clear()
            if self.state == 'explore':
                self.draw_world()
                if self.message_queue:
                    self.draw_messages()
                self.stdscr.refresh()
                c = self.stdscr.getch()
                # If there are pending messages, any key dismisses them
                if self.message_queue:
                    self.message_queue.clear()
                    continue
                if c == curses.KEY_UP:
                    event = self.world.move_player(0, -1)
                    self.handle_world_event(event)
                elif c == curses.KEY_DOWN:
                    event = self.world.move_player(0, 1)
                    self.handle_world_event(event)
                elif c == curses.KEY_LEFT:
                    event = self.world.move_player(-1, 0)
                    self.handle_world_event(event)
                elif c == curses.KEY_RIGHT:
                    event = self.world.move_player(1, 0)
                    self.handle_world_event(event)
                elif c in (ord('s'), ord('S')):
                    self.save_game()
                    self.message_queue.append('Game saved.')
                elif c in (ord('l'), ord('L')):
                    self.load_game()
                elif c in (ord('q'), ord('Q')):
                    break
            elif self.state == 'battle':
                self.draw_battle()
                self.stdscr.refresh()
                # Handle message queue first
                if self.message_queue:
                    c = self.stdscr.getch()
                    self.message_queue.clear()
                    continue
                # Show choices: Fight, Bag, Switch, Run
                choice = self.battle_menu()
                if choice == 'fight':
                    self.handle_fight_menu()
                elif choice == 'bag':
                    self.handle_bag_menu()
                elif choice == 'switch':
                    self.handle_switch_menu()
                elif choice == 'run':
                    # Attempt to run if possible
                    if self.battle.is_trainer:
                        self.message_queue.append("Can't run from a trainer battle!")
                    else:
                        # 50% chance to escape
                        import random
                        if random.random() < 0.5:
                            self.message_queue.append("Got away safely!")
                            self.state = 'explore'
                            self.battle = None
                        else:
                            self.message_queue.append("Can't escape!")
                            # Opponent still attacks
                            logs = self.battle.opponent_attack()
                            self.message_queue.extend(logs)
                            self.message_queue.extend(self.battle.apply_status_effects())
                            self.check_battle_end()
                # After each action, check for end
            else:
                # Unknown state
                break

    def handle_world_event(self, event):
        """Handle events returned from moving in the world."""
        if event == 'healed':
            self.message_queue.append('Your party was fully healed!')
            return
        # Trainer battle
        if isinstance(event, Trainer):
            trainer = event
            self.message_queue.append('A trainer challenges you to a battle!')
            self.battle = Battle(self.world.player_party, trainer.party, is_trainer=True)
            self.state = 'battle'
            return
        # Random encounter
        wild_mon = self.world.maybe_trigger_encounter()
        if wild_mon:
            self.message_queue.append(f'A wild {wild_mon.species} appeared!')
            self.battle = Battle(self.world.player_party, [wild_mon], is_trainer=False)
            self.state = 'battle'

    def check_battle_end(self):
        """Check if the battle has ended and handle aftermath."""
        if self.battle is None:
            return
        if self.battle.is_over():
            # Determine winner
            if self.battle.player_active_index() is None:
                # All player's monsters fainted
                self.message_queue.append('You blacked out!')
                # Heal and return to start
                for mon in self.world.player_party:
                    mon.heal()
                # Reset position
                # Teleport to start (we know where start is from initial map load)
                # We'll just place player at starting coordinates from load_map
                # In this simple version we keep player where they fainted
                self.state = 'explore'
                self.battle = None
                return
            elif self.battle.opponent_active_index() is None:
                # Player won
                self.message_queue.append('You won the battle!')
                # If trainer battle, mark trainer as defeated
                if self.battle.is_trainer:
                    # Find which trainer this is by current player position
                    pos = (self.world.player_x, self.world.player_y)
                    trainer = self.world.trainers.get(pos)
                    if trainer:
                        self.world.remove_trainer(trainer)
                self.state = 'explore'
                self.battle = None
                return

    # Drawing functions
    def draw_world(self):
        """Draw the overworld map and status."""
        for y in range(self.world.height):
            for x in range(self.world.width):
                ch = self.world.tile(x, y)
                # Player
                if x == self.world.player_x and y == self.world.player_y:
                    color = curses.color_pair(8)
                    self.stdscr.addstr(y, x, '@', color)
                    continue
                # Determine color based on tile
                color = curses.color_pair(1)
                if ch == '.':
                    color = curses.color_pair(2)
                elif ch == '~':
                    color = curses.color_pair(3)
                elif ch == '=':
                    color = curses.color_pair(4)
                elif ch == '^':
                    color = curses.color_pair(5)
                elif ch == 'C':
                    color = curses.color_pair(6)
                elif ch == 'T' or (x, y) in self.world.trainers and not self.world.trainers[(x, y)].defeated:
                    color = curses.color_pair(7)
                    ch = 'T'
                elif ch == '#':
                    color = curses.color_pair(1)
                self.stdscr.addstr(y, x, ch, color)
        # Draw player party summary on bottom lines
        status_y = self.world.height + 1
        self.stdscr.addstr(status_y, 0, f"Party: ")
        for mon in self.world.player_party:
            fainted = ' (Fainted)' if mon.is_fainted() else ''
            self.stdscr.addstr(status_y, 7, f"{mon.species} L{mon.level} HP {mon.current_hp}/{mon.max_hp}{fainted}   ")
        status_y += 1
        # Items info
        self.stdscr.addstr(status_y, 0, f"Potions: {self.world.items.get('Potion',0)}   NetBalls: {self.world.items.get('NetBall',0)}")
        status_y += 1
        self.stdscr.addstr(status_y, 0, "Use arrow keys to move. Press S to save, L to load, Q to quit.")

    def draw_messages(self):
        """Display queued messages in a small window."""
        # We'll create a small window at bottom to display messages
        max_y, max_x = self.stdscr.getmaxyx()
        win_height = min(5, len(self.message_queue))
        start_y = max(0, max_y - win_height)
        for i, msg in enumerate(self.message_queue[-win_height:]):
            self.stdscr.addstr(start_y + i, 0, msg.ljust(max_x - 1)[:max_x - 1], curses.color_pair(1))

    # Battle drawing and menus
    def draw_battle(self):
        """Draw battle screen."""
        self.stdscr.erase()
        battle = self.battle
        if battle is None:
            return
        # Display opponent monster
        o_idx = battle.opponent_active_index()
        if o_idx is not None:
            foe = battle.opponent_party[o_idx]
            self.stdscr.addstr(1, 2, f"Foe {foe.species} L{foe.level}")
            self.stdscr.addstr(2, 2, f"HP: {foe.current_hp}/{foe.max_hp}")
        # Display player monster
        p_idx = battle.player_active_index()
        if p_idx is not None:
            me = battle.player_party[p_idx]
            self.stdscr.addstr(10, 2, f"{me.species} L{me.level}")
            self.stdscr.addstr(11, 2, f"HP: {me.current_hp}/{me.max_hp}")
            if me.status:
                self.stdscr.addstr(12, 2, f"Status: {me.status}")
        # Draw action menu options placeholder; handled in menu functions
        self.stdscr.addstr(14, 2, "What will you do?")
        # Draw messages if any
        if self.message_queue:
            for i, msg in enumerate(self.message_queue[-3:]):
                self.stdscr.addstr(16 + i, 2, msg)

    def battle_menu(self) -> str:
        """Display battle menu and return player's choice."""
        options = ['Fight', 'Bag', 'Switch', 'Run']
        idx = 0
        while True:
            # Draw options
            for i, option in enumerate(options):
                highlight = curses.A_REVERSE if i == idx else curses.A_NORMAL
                self.stdscr.addstr(15 + i, 4, option.ljust(10), highlight)
            c = self.stdscr.getch()
            if c == curses.KEY_UP:
                idx = (idx - 1) % len(options)
            elif c == curses.KEY_DOWN:
                idx = (idx + 1) % len(options)
            elif c in (curses.KEY_ENTER, 10, 13):
                return options[idx].lower()
            elif c == ord('q'):
                return 'run'

    def handle_fight_menu(self):
        battle = self.battle
        if battle is None:
            return
        p_idx = battle.player_active_index()
        if p_idx is None:
            return
        mon = battle.player_party[p_idx]
        moves = mon.moves
        idx = 0
        while True:
            # Draw moves
            self.stdscr.erase()
            self.draw_battle()
            self.stdscr.addstr(14, 2, "Choose a move:")
            for i, move in enumerate(moves):
                name = f"{move.name} PP {move.current_pp}/{move.pp}"
                highlight = curses.A_REVERSE if i == idx else curses.A_NORMAL
                self.stdscr.addstr(16 + i, 4, name.ljust(20), highlight)
            self.stdscr.refresh()
            c = self.stdscr.getch()
            if c == curses.KEY_UP:
                idx = (idx - 1) % len(moves)
            elif c == curses.KEY_DOWN:
                idx = (idx + 1) % len(moves)
            elif c in (curses.KEY_ENTER, 10, 13):
                # Perform attack
                logs = battle.player_attack(idx)
                self.message_queue.extend(logs)
                # Opponent acts if still alive
                if not battle.is_over():
                    logs2 = battle.opponent_attack()
                    self.message_queue.extend(logs2)
                    # Apply status
                    self.message_queue.extend(battle.apply_status_effects())
                self.check_battle_end()
                return
            elif c == ord('b'):
                return

    def handle_bag_menu(self):
        battle = self.battle
        if battle is None:
            return
        options = []
        if self.world.items.get('Potion', 0) > 0:
            options.append('Potion')
        if self.world.items.get('NetBall', 0) > 0:
            options.append('NetBall')
        options.append('Back')
        idx = 0
        while True:
            self.stdscr.erase()
            self.draw_battle()
            self.stdscr.addstr(14, 2, "Use which item?")
            for i, opt in enumerate(options):
                text = opt
                if opt == 'Potion':
                    text += f" x{self.world.items.get('Potion',0)}"
                elif opt == 'NetBall':
                    text += f" x{self.world.items.get('NetBall',0)}"
                highlight = curses.A_REVERSE if i == idx else curses.A_NORMAL
                self.stdscr.addstr(16 + i, 4, text.ljust(20), highlight)
            self.stdscr.refresh()
            c = self.stdscr.getch()
            if c == curses.KEY_UP:
                idx = (idx - 1) % len(options)
            elif c == curses.KEY_DOWN:
                idx = (idx + 1) % len(options)
            elif c in (curses.KEY_ENTER, 10, 13):
                choice = options[idx]
                if choice == 'Potion':
                    # Heal active monster
                    p_idx = battle.player_active_index()
                    if p_idx is not None:
                        mon = battle.player_party[p_idx]
                        if mon.current_hp < mon.max_hp:
                            heal_amount = min(20, mon.max_hp - mon.current_hp)
                            mon.current_hp += heal_amount
                            self.world.items['Potion'] -= 1
                            self.message_queue.append(f"Used Potion! Restored {heal_amount} HP.")
                            # Opponent acts
                            logs = battle.opponent_attack()
                            self.message_queue.extend(logs)
                            self.message_queue.extend(battle.apply_status_effects())
                            self.check_battle_end()
                            return
                        else:
                            self.message_queue.append("HP is already full!")
                            return
                elif choice == 'NetBall':
                    success, logs = battle.attempt_capture(ball_bonus=1.0)
                    self.message_queue.extend(logs)
                    self.world.items['NetBall'] -= 1
                    if success:
                        # End battle
                        self.state = 'explore'
                        self.battle = None
                        return
                    else:
                        # Opponent acts
                        logs2 = battle.opponent_attack()
                        self.message_queue.extend(logs2)
                        self.message_queue.extend(battle.apply_status_effects())
                        self.check_battle_end()
                        return
                elif choice == 'Back':
                    return
            elif c == ord('b'):
                return

    def handle_switch_menu(self):
        battle = self.battle
        if battle is None:
            return
        # List non‑fainted monsters not currently active
        p_idx = battle.player_active_index()
        options = []
        indices = []
        for i, mon in enumerate(battle.player_party):
            if i != p_idx and not mon.is_fainted():
                options.append(f"{mon.species} L{mon.level} HP {mon.current_hp}/{mon.max_hp}")
                indices.append(i)
        options.append('Back')
        idx = 0
        while True:
            self.stdscr.erase()
            self.draw_battle()
            self.stdscr.addstr(14, 2, "Switch to which?")
            for i, opt in enumerate(options):
                highlight = curses.A_REVERSE if i == idx else curses.A_NORMAL
                self.stdscr.addstr(16 + i, 4, opt.ljust(25), highlight)
            self.stdscr.refresh()
            c = self.stdscr.getch()
            if c == curses.KEY_UP:
                idx = (idx - 1) % len(options)
            elif c == curses.KEY_DOWN:
                idx = (idx + 1) % len(options)
            elif c in (curses.KEY_ENTER, 10, 13):
                if options[idx] == 'Back':
                    return
                # Perform switch
                new_idx = indices[idx]
                # Swap order to put selected monster first in party list
                battle.player_party[p_idx], battle.player_party[new_idx] = battle.player_party[new_idx], battle.player_party[p_idx]
                self.message_queue.append(f"You sent out {battle.player_party[p_idx].species}!")
                # Opponent gets a free hit after switching
                logs = battle.opponent_attack()
                self.message_queue.extend(logs)
                self.message_queue.extend(battle.apply_status_effects())
                self.check_battle_end()
                return
            elif c == ord('b'):
                return


def main(stdscr):
    game = Game(stdscr)
    game.run()


if __name__ == '__main__':
    curses.wrapper(main)