# Pro Sound Basketball

A fully accessible, audio-only 2-on-2 basketball game written in Python.

## Features
- **Audio-Only Gameplay**: Navigate and play entirely using sound cues and text-to-speech.
- **Procedural Audio**: All sound effects (dribbling, shooting, net swishes) are generated in real-time.
- **2 Game Modes**:
  - **Play Mode**: Full 2-minute match with scoring and AI opponents.
  - **Practice Mode**: Unlimited time with no defenders to practice your shots.
- **Customizable Nets**: Choose between "Chain" or "NBA" net sounds.

## Requirements
- Python 3.x
- `pygame`
- `accessible_output2`

## Installation
1. Install Python.
2. Install the required libraries:
   ```bash
   pip install pygame accessible_output2
   ```

## How to Play
Run the game using Python:
```bash
python audio_basketball.py
```

### Controls
| Key | Action |
| --- | --- |
| **Arrow Keys** | Move Player |
| **Space** | Shoot (or Dunk if close) |
| **P** | Pass to Teammate |
| **S** | Announce Score |
| **N** | Announce Distance to Hoop (plays locator sound) |
| **T** | Announce Time Remaining |
| **ESC** | Quit Game |

### Menu Navigation
- The game starts in the Main Menu.
- Press **1** for **Play Mode**.
- Press **2** for **Practice Mode**.
- After selecting a mode, press **1** for **Chain Net** or **2** for **NBA Net**.

## Gameplay Tips
- **Dribbling**: You will hear a dribble sound when you move with the ball.
- **Locator**: Press **N** to hear a tone originating from the hoop's location. Use stereo headphones to orient yourself.
- **Shooting**:
  - **Dunk**: Get very close to the hoop (distance < 50) and press Space.
  - **3-Pointer**: Shoot from further away (distance > 250). You may hear a beep when near the 3-point line.
- **Defense**: In Play Mode, opponents will try to steal the ball. Listen for "Opponent ball" or "Stolen!" announcements.

## Custom Sounds
You can replace the default generated sounds with your own `.wav` files.
1. Create a folder named `sounds` in the same directory as the game.
2. Add `.wav` files with the following names:
   - `dribble.wav`
   - `shoot.wav`
   - `net_chain.wav`
   - `net_nba.wav`
   - `rim.wav`
   - `beep.wav`
   - `buzzer.wav`
   - `dunk.wav`
   - `locator.wav`
3. Restart the game. If a file is missing, the game will use the default generated sound.

## Credits
Created as a single-file Python project for accessible gaming.
