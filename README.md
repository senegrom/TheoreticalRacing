# Theoretical Racing

A Java Swing implementation of the classic pen-and-paper [Racetrack](https://en.wikipedia.org/wiki/Racetrack_(game)) game.

Players draw a track on a grid, place their cars in the start zone, then take turns racing by adjusting their velocity vector. Each turn you can change your velocity by at most 1 in each axis (horizontal and vertical). Your new position is your current position plus your velocity. Go off the track and you crash.

## How to Play

1. **Start dialog** -- Configure number of players (1-9), player names, colors, and grid/window size.
2. **Draw the track** -- Click grid points to draw the left border, press OK, then draw the right border. The first points of each border define the start line; the last points define the finish line.
3. **Place players** -- Click inside the start zone to place each player's car.
4. **Race** -- Each turn, click a direction button (NW/N/NE/W/-/E/SW/S/SE) to adjust your velocity by 1 in that direction. Click the same direction again to confirm the move. A preview path shows where you'll coast to if you stop accelerating.
5. **Win condition** -- Cross the finish line to place. Crash (leave the track or collide) and you're out. The game ends when all but one player has finished or crashed.

## Building

Requires JDK 8 or later.

```bash
# Compile
mkdir -p bin
javac -d bin -sourcepath src src/tr/main/Main.java

# Run
java -cp bin tr.main.Main

# Or run the pre-built JAR
java -jar theoreticRacing.jar
```

## Configuration

Settings are stored in `user.properties` (auto-saved on exit). Defaults are in `default.properties`.

| Property | Default | Description |
|---|---|---|
| `windowX` / `windowY` | 1600 / 900 | Window dimensions in pixels |
| `gameX` / `gameY` | 50 / 50 | Grid size (columns / rows) |
| `nPlayers` | 2 | Number of players |
| `maxPlayers` | 9 | Maximum players allowed |
| `playerNName` | Player N | Name for player N |
| `playerNColor` | (varies) | RGB color as `R G B` (e.g. `0 0 255`) |

## Project Structure

```
src/
  tr/
    main/
      Main.java          -- Entry point, loads properties and launches the game
    logic/
      RaceGame.java      -- Core game logic: track drawing, movement, collision detection
      GameState.java     -- Enum of game states (SETUP, DRAWTRACK, PLAY, etc.)
      Player.java        -- Player state: position, velocity, color, move history
      Track.java         -- Left and right track border point lists
    gui/
      GameUI.java        -- Main game window (JFrame) with grid, buttons, status bar
      RaceUI.java        -- Rendering: draws grid, track, players, velocity vectors
      Grid.java          -- JPanel that delegates painting to RaceUI
      StartDialog.java   -- Pre-game setup dialog for players and grid size
      GridListener.java  -- Mouse listener for grid clicks
      ExitListener.java  -- Window close / exit button handler
```

## License

See [LICENSE](LICENSE).
