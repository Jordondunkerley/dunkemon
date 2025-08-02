# Dunkemon Game

This directory contains a fully‑playable monster‑battling RPG inspired by the
classic handheld games of the early 2000s.  The goal of this project is to
provide a self‑contained starting point for a role‑playing adventure with
turn‑based battles, collectible monsters and a simple overworld.  It is
designed to be easily extended with your own characters, sprites and
storylines.

All logic is implemented in **pure Python** using only the standard library,
so the game runs on any modern Python interpreter without extra
dependencies.  The display uses the `curses` module to draw colourful
characters on the terminal, making it suitable for both desktop and remote
environments.  While this cannot exactly match the visuals of a GBA game,
the structure of the overworld and battle system mirrors the feel of
``Pokémon Emerald``, allowing you to plug in your own artwork later on.

## Features

* **Overworld exploration**: Move around a tile‑based map using the arrow
  keys.  Different tiles represent grass, water, paths, buildings and more.
* **Random encounters**: Step into tall grass to meet wild monsters.  Each
  area has its own encounter table, which you can customize in
  `data/areas.json`.
* **Turn‑based battles**: Fight wild monsters using up to four moves per
  creature.  Damage calculations take level, statistics, elemental types
  and random variance into account.  Type effectiveness and Same Type Attack
  Bonus (STAB) are implemented as in the official games.
* **Party management**: Catch defeated monsters with capturable items and
  build a team.  Your party persists across battles and can be healed at
  special locations.
* **Save and load**: Save your progress to `save.json` at any time and
  continue where you left off.

## How to run

1. Make sure you have Python 3.8 or later installed.  No additional
   dependencies are required.
2. From the repository root run the following command:

   ```sh
   python dunkemon_game/main.py
   ```

   The game will start in your terminal.  Use the arrow keys to move and
   follow the on‑screen prompts during battles.

## Customization

All game data is defined in JSON files under the `data/` directory.  You can
add your own monster species in `species.json`, moves in `moves.json`, and
area encounter tables in `areas.json`.  The map itself is stored as a plain
text file at `maps/overworld.txt`; simply edit this file to change the
layout.

To replace the ASCII sprites with real artwork, implement the optional
`SpriteRenderer` class in `graphics.py` and swap out the glyphs for
image loading and blitting using a framework such as `pygame` or a web
technology of your choice.

## Disclaimer

This project is **not affiliated with, endorsed by, or sponsored by
Nintendo, Game Freak, or The Pokémon Company**.  It is an original work
intended for educational purposes, inspired by the mechanics of classic
monster‑collecting RPGs.  All names and artwork provided here are
original and free to use; please respect the intellectual property of
others when adding your own content.