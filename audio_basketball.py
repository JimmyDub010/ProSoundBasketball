import pygame
import random
import math
import time
import struct
import io
import wave
import wave
import os
from accessible_output2.outputs.auto import Auto

# ==================================================================================
# CONFIGURATION & CONSTANTS
# ==================================================================================
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

COURT_WIDTH = 1000
COURT_HEIGHT = 600
HOOP_LEFT_POS = (-400, 0)
HOOP_RIGHT_POS = (400, 0)
THREE_POINT_RADIUS = 250
DUNK_RANGE = 50

PLAYER_SPEED = 5
BALL_SPEED = 12
PASS_SPEED = 15

TEAM_HOME = 0
TEAM_AWAY = 1

# ==================================================================================
# AUDIO GENERATOR
# ==================================================================================
class AudioGenerator:
    """Generates game sounds procedurally to avoid external assets."""
    
    @staticmethod
    def load_sound(name, generator_func):
        """Loads a sound from 'sounds/{name}.ogg' or generates it if missing."""
        path = os.path.join("sounds", f"{name}.ogg")
        if os.path.exists(path):
            try:
                print(f"Loading custom sound: {path}")
                return pygame.mixer.Sound(path)
            except Exception as e:
                print(f"Failed to load {path}, generating instead. Error: {e}")
        
        return generator_func()

    @staticmethod
    def _create_sound(data, framerate=44100):
        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(framerate)
            wav_file.writeframes(data)
        
        buffer.seek(0)
        return pygame.mixer.Sound(buffer)

    @staticmethod
    def generate_tone(frequency, duration, volume=0.5):
        framerate = 44100
        n_frames = int(framerate * duration)
        data = bytearray()
        
        for i in range(n_frames):
            t = i / framerate
            val = int(32767 * volume * math.sin(2 * math.pi * frequency * t))
            data.extend(struct.pack('<h', val))
            
        return AudioGenerator._create_sound(data, framerate)

    @staticmethod
    def generate_noise(duration, volume=0.5, decay=False, pitch_shift=1.0):
        framerate = 44100
        n_frames = int(framerate * duration)
        data = bytearray()
        
        for i in range(n_frames):
            progress = i / n_frames
            current_vol = volume
            if decay:
                current_vol *= (1 - progress)
            
            # Simple white noise
            val = int(32767 * current_vol * (random.random() * 2 - 1))
            data.extend(struct.pack('<h', val))
            
        return AudioGenerator._create_sound(data, framerate)

    @staticmethod
    def generate_dribble():
        # Short, low thud
        return AudioGenerator.generate_noise(0.1, volume=0.6, decay=True)

    @staticmethod
    def generate_shoot():
        # Whoosh sound
        return AudioGenerator.generate_noise(0.4, volume=0.4, decay=True)

    @staticmethod
    def generate_net_swish():
        # Soft, longer noise (NBA style)
        return AudioGenerator.generate_noise(0.5, volume=0.3, decay=True)

    @staticmethod
    def generate_net_chain():
        # Metallic rattle - higher pitch noise bursts
        framerate = 44100
        duration = 0.6
        n_frames = int(framerate * duration)
        data = bytearray()
        
        for i in range(n_frames):
            progress = i / n_frames
            vol = 0.4 * (1 - progress)
            # Modulate noise to sound rattling
            mod = math.sin(2 * math.pi * 50 * (i/framerate)) 
            val = int(32767 * vol * (random.random() * 2 - 1) * (0.5 + 0.5 * mod))
            data.extend(struct.pack('<h', val))
            
        return AudioGenerator._create_sound(data, framerate)

    @staticmethod
    def generate_rim_clank():
        # Sharp metallic hit
        return AudioGenerator.generate_tone(150, 0.1, volume=0.8)

    @staticmethod
    def generate_buzzer():
        # Loud square-ish wave
        framerate = 44100
        duration = 1.0
        n_frames = int(framerate * duration)
        data = bytearray()
        
        for i in range(n_frames):
            t = i / framerate
            # Square wave approx
            val = 32767 * 0.5 if math.sin(2 * math.pi * 200 * t) > 0 else -32767 * 0.5
            data.extend(struct.pack('<h', int(val)))
            
        return AudioGenerator._create_sound(data, framerate)

    @staticmethod
    def generate_beep():
        # High pitch beep for 3pt line
        return AudioGenerator.generate_tone(800, 0.1, volume=0.3)

    @staticmethod
    def generate_dunk():
        # Loud heavy impact
        return AudioGenerator.generate_noise(0.3, volume=0.9, decay=True)

# ==================================================================================
# MENU SYSTEM
# ==================================================================================
class Menu:
    def __init__(self, title, options, speaker, on_select=None):
        self.title = title
        self.options = options # List of (label, callback)
        self.speaker = speaker
        self.current_index = 0
        self.on_select_callback = on_select

    def navigate(self, direction):
        # direction: -1 for up, 1 for down
        self.current_index = (self.current_index + direction) % len(self.options)
        self.speak_current()

    def select(self):
        label, callback = self.options[self.current_index]
        if callback:
            callback()

    def speak_current(self):
        label, _ = self.options[self.current_index]
        self.speaker.speak(label, interrupt=True)

    def speak_title(self):
        self.speaker.speak(f"{self.title}. Use Up and Down arrows to navigate, Enter to select.", interrupt=True)


class Ball:
    def __init__(self):
        self.x = 0
        self.y = 0
        self.z = 0 # Height
        self.owner = None
        self.vx = 0
        self.vy = 0
        self.target_hoop = None
        self.in_air = False

    def update(self):
        if self.owner:
            self.x = self.owner.x
            self.y = self.owner.y
            self.in_air = False
        elif self.in_air:
            self.x += self.vx
            self.y += self.vy
            # Simple arrival check
            if self.target_hoop:
                dist = math.hypot(self.x - self.target_hoop[0], self.y - self.target_hoop[1])
                if dist < 20: # Increased tolerance
                    return "arrived"
        return None

class Player:
    def __init__(self, team, x, y, is_human=False):
        self.team = team
        self.x = x
        self.y = y
        self.is_human = is_human
        self.has_ball = False
        self.dribble_timer = 0
        self.teammate = None
        self.opponents = []

    def update(self, ball, hoop_pos, sounds, play_panned_func, listener_x):
        if self.has_ball:
            # Auto dribble sound
            if self.is_moving():
                self.dribble_timer -= 1
                if self.dribble_timer <= 0:
                    # sounds['dribble'].play()
                    play_panned_func('dribble', self.x, listener_x)
                    self.dribble_timer = 20 # Frames between dribbles
        
        if not self.is_human:
            return self.ai_update(ball, hoop_pos)
        return None

    def is_moving(self):
        # For human, checked via input. For AI, checked via velocity (simplified)
        return True # Simplified for audio cues

    def ai_update(self, ball, hoop_pos):
        # Simple AI
        speed = PLAYER_SPEED * 0.8
        
        if self.has_ball:
            # Move to hoop
            dx = hoop_pos[0] - self.x
            dy = hoop_pos[1] - self.y
            dist = math.hypot(dx, dy)
            
            if dist > 0:
                self.x += (dx/dist) * speed
                self.y += (dy/dist) * speed
                
            # Shoot if close enough (random chance)
            # High chance to dunk if close
            if dist < 50:
                if random.random() < 0.1: # 10% chance per frame to dunk
                    return "shoot"
            # Shot chance further out
            elif dist < 300:
                if random.random() < 0.02: # 2% chance per frame (~1 shot per sec if in range)
                    return "shoot"
            
            # Pass to teammate if they are closer to hoop
            if self.teammate and random.random() < 0.005: # Occasional pass
                # Check if teammate is closer
                t_dx = hoop_pos[0] - self.teammate.x
                t_dy = hoop_pos[1] - self.teammate.y
                t_dist = math.hypot(t_dx, t_dy)
                if t_dist < dist:
                    return "pass"
                
        else:
            # Defense / Chase ball
            target_x, target_y = ball.x, ball.y
            dx = target_x - self.x
            dy = target_y - self.y
            dist = math.hypot(dx, dy)
            
            if dist > 0:
                self.x += (dx/dist) * speed
                self.y += (dy/dist) * speed
                
            # Steal attempt
            if dist < 30 and ball.owner and ball.owner.team != self.team:
                if random.random() < 0.01: # Reduced back to 1%
                    return "steal"
        return None

class Game:
    def __init__(self):
        pygame.init()
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Audio Basketball 2v2")
        
        self.speaker = Auto()
        self.clock = pygame.time.Clock()
        
        # Generate Sounds
        print("Generating sounds...")
        self.sounds = {
            'dribble': AudioGenerator.load_sound('dribble', AudioGenerator.generate_dribble),
            'shoot': AudioGenerator.load_sound('shoot', AudioGenerator.generate_shoot),
            'net_chain': AudioGenerator.load_sound('net_chain', AudioGenerator.generate_net_chain),
            'net_nba': AudioGenerator.load_sound('net_nba', AudioGenerator.generate_net_swish),
            'rim': AudioGenerator.load_sound('rim', AudioGenerator.generate_rim_clank),
            'beep': AudioGenerator.load_sound('beep', AudioGenerator.generate_beep),
            'buzzer': AudioGenerator.load_sound('buzzer', AudioGenerator.generate_buzzer),
            'dunk': AudioGenerator.load_sound('dunk', AudioGenerator.generate_dunk),
            'locator': AudioGenerator.load_sound('locator', lambda: AudioGenerator.generate_tone(400, 0.05, 0.3))
        }
        print("Sounds ready.")

        self.state = "MENU"
        self.net_type = "NBA" # Default
        self.mode = "PLAY" # PLAY or PRACTICE
        
        self.score = {TEAM_HOME: 0, TEAM_AWAY: 0}
        self.time_remaining = 120 # Seconds
        self.steal_cooldown = 0
        
        self.players = []
        self.ball = Ball()
        self.setup_teams()

        # Menus
        self.main_menu = Menu("Main Menu", [
            ("Play Game", lambda: self.set_mode_and_advance("PLAY")),
            ("Practice Mode", lambda: self.set_mode_and_advance("PRACTICE")),
            ("Exit", lambda: self.quit_game())
        ], self.speaker)

        self.net_menu = Menu("Select Net Type", [
            ("NBA Net", lambda: self.set_net_and_start("NBA")),
            ("Chain Net", lambda: self.set_net_and_start("Chain"))
        ], self.speaker)
        
        self.current_menu = self.main_menu

    def set_mode_and_advance(self, mode):
        self.mode = mode
        self.state = "NET_SELECT"
        self.current_menu = self.net_menu
        self.current_menu.speak_title()

    def set_net_and_start(self, net_type):
        self.net_type = net_type
        self.state = "GAME"
        self.speak(f"{net_type} Net selected. Starting game.")
        self.reset_positions()

    def quit_game(self):
        pygame.event.post(pygame.event.Event(pygame.QUIT))


    def setup_teams(self):
        self.players = []
        # Home Team (Player is index 0)
        p1 = Player(TEAM_HOME, -200, 0, is_human=True)
        p2 = Player(TEAM_HOME, -200, 100)
        p1.teammate = p2
        p2.teammate = p1
        
        # Away Team
        p3 = Player(TEAM_AWAY, 200, 0)
        p4 = Player(TEAM_AWAY, 200, 100)
        p3.teammate = p4
        p4.teammate = p3
        
        self.players = [p1, p2, p3, p4]
        
        # Assign opponents
        p1.opponents = [p3, p4]
        p2.opponents = [p3, p4]
        p3.opponents = [p1, p2]
        p4.opponents = [p1, p2]
        
        # Give ball to human
        self.ball.owner = p1
        p1.has_ball = True

    def speak(self, text, interrupt=True):
        self.speaker.speak(text, interrupt=interrupt)

    def play_sound_panned(self, sound_name, source_x, listener_x):
        # Simple stereo panning
        # x range approx -500 to 500
        # pan -1.0 (left) to 1.0 (right)
        
        dx = source_x - listener_x
        # Max hearing distance approx 800
        pan = max(-1.0, min(1.0, dx / 500.0))
        
        # Volume falloff
        dist = abs(dx)
        vol = max(0.1, 1.0 - (dist / 1000.0))
        
        channel = pygame.mixer.find_channel()
        if channel:
            channel.set_volume(vol * (1.0 - pan), vol * (1.0 + pan)) # Left, Right
            channel.play(self.sounds[sound_name])

    def reset_positions(self):
        self.players[0].x, self.players[0].y = -200, 0
        self.players[1].x, self.players[1].y = -200, 100
        self.players[2].x, self.players[2].y = 200, 0
        self.players[3].x, self.players[3].y = 200, 100
        
        self.ball.owner = self.players[0]
        for p in self.players: p.has_ball = False
        self.players[0].has_ball = True
        self.ball.in_air = False

    def handle_shot(self, shooter):
        hoop = HOOP_RIGHT_POS if shooter.team == TEAM_HOME else HOOP_LEFT_POS
        dist = math.hypot(shooter.x - hoop[0], shooter.y - hoop[1])
        
        is_dunk = dist < DUNK_RANGE
        is_3pt = dist > THREE_POINT_RADIUS
        
        # Release ball
        shooter.has_ball = False
        self.ball.owner = None
        self.ball.in_air = True
        self.ball.target_hoop = hoop
        
        # Calculate velocity to hoop
        speed = BALL_SPEED
        dx = hoop[0] - shooter.x
        dy = hoop[1] - shooter.y
        d = math.hypot(dx, dy)
        
        if d > 0:
            self.ball.vx = (dx/d) * speed
            self.ball.vy = (dy/d) * speed
        else:
            self.ball.vx = 0
            self.ball.vy = 0
        
        self.sounds['shoot'].play()
        
        return is_dunk, is_3pt

    def score_basket(self, team, points, is_dunk):
        self.score[team] += points
        
        if is_dunk:
            self.sounds['dunk'].play()
            # Play net sound after small delay or simultaneously? Spec says dunk sound.
            # Let's play net sound too for satisfaction
            pygame.time.delay(200)
        
        if self.net_type == "Chain":
            self.sounds['net_chain'].play()
        else:
            self.sounds['net_nba'].play()
            
        self.speak(f"Score! {points} points.")
        pygame.time.delay(1000)
        self.reset_positions()
        
        # Switch possession (give to other team) if not practice
        if self.mode != "PRACTICE":
            if team == TEAM_HOME:
                self.ball.owner = self.players[2] # Away player
            else:
                self.ball.owner = self.players[0] # Home player
            
            for p in self.players: p.has_ball = False
            self.ball.owner.has_ball = True
        
        if self.ball.owner.team == TEAM_HOME:
            self.speak("Your ball")
        else:
            self.speak("Opponent ball")

    def run(self):
        self.current_menu.speak_title()
        
        running = True
        last_time_update = time.time()
        
        while running:
            dt = self.clock.tick(FPS)
            current_time = time.time()
            
            # Event Handling
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                        
                    if self.state in ["MENU", "NET_SELECT"]:
                        if event.key == pygame.K_UP:
                            self.current_menu.navigate(-1)
                        elif event.key == pygame.K_DOWN:
                            self.current_menu.navigate(1)
                        elif event.key == pygame.K_RETURN:
                            self.current_menu.select()
                            
                    elif self.state == "GAME":
                        human = self.players[0]
                        if event.key == pygame.K_s:
                            self.speak(f"Score: You {self.score[TEAM_HOME]}, Opponent {self.score[TEAM_AWAY]}")
                        elif event.key == pygame.K_t:
                            if self.mode == "PLAY":
                                mins = int(self.time_remaining // 60)
                                secs = int(self.time_remaining % 60)
                                self.speak(f"Time remaining: {mins} minutes {secs} seconds")
                            else:
                                self.speak("Unlimited time.")
                        elif event.key == pygame.K_n:
                            # Hoop locator
                            hoop = HOOP_RIGHT_POS
                            dist = math.hypot(human.x - hoop[0], human.y - hoop[1])
                            self.speak(f"Hoop distance {int(dist)}")
                            self.play_sound_panned('locator', hoop[0], human.x)
                            
                        elif event.key == pygame.K_SPACE:
                            if human.has_ball:
                                is_dunk, is_3pt = self.handle_shot(human)
                                # Store shot type in ball for scoring logic when it arrives
                                self.ball.shot_data = (TEAM_HOME, 3 if is_3pt else (2 if is_dunk else 2), is_dunk)
                                
                        elif event.key == pygame.K_p:
                            if human.has_ball and human.teammate:
                                # Pass
                                human.has_ball = False
                                self.ball.owner = human.teammate
                                human.teammate.has_ball = True
                                self.sounds['shoot'].play() # Pass sound (whoosh)
                                self.speak("Pass to teammate")
                                # Ensure teammate moves to hoop immediately
                                # AI update will handle this next frame

            # Game Logic
            if self.state == "GAME":
                human = self.players[0]
                if self.steal_cooldown > 0:
                    self.steal_cooldown -= 1
                
                # Timer
                if self.mode == "PLAY":
                    if current_time - last_time_update >= 1.0:
                        self.time_remaining -= 1
                        last_time_update = current_time
                        if self.time_remaining <= 0:
                            self.sounds['buzzer'].play()
                            self.speak("Game Over!")
                            pygame.time.delay(2000)
                            self.state = "MENU"
                            self.current_menu = self.main_menu
                            self.current_menu.speak_title()
                            self.time_remaining = 120
                            self.score = {TEAM_HOME: 0, TEAM_AWAY: 0}

                # Movement
                keys = pygame.key.get_pressed()
                move_x = 0
                move_y = 0
                if keys[pygame.K_LEFT]: move_x = -1
                if keys[pygame.K_RIGHT]: move_x = 1
                if keys[pygame.K_UP]: move_y = -1
                if keys[pygame.K_DOWN]: move_y = 1
                
                if move_x != 0 or move_y != 0:
                    human.x += move_x * PLAYER_SPEED
                    human.y += move_y * PLAYER_SPEED
                    
                    # Dribble sound logic
                    if human.has_ball:
                        human.dribble_timer -= 1
                        if human.dribble_timer <= 0:
                            self.sounds['dribble'].play()
                            human.dribble_timer = 15 # Faster dribble when moving
                
                # 3-Point Indicator
                hoop = HOOP_RIGHT_POS
                dist = math.hypot(human.x - hoop[0], human.y - hoop[1])
                if abs(dist - THREE_POINT_RADIUS) < 5: # Boundary check
                    if not hasattr(self, 'in_3pt_range'): self.in_3pt_range = False
                    
                    # Beep when crossing line
                    # Simple state toggle to avoid spamming
                    # Actually just play if near line?
                    # Spec: "A beep or indicator when the player is in 3-point range"
                    # Let's play it periodically if OUTSIDE 3pt range (which is good for 3 pointers)
                    # Or maybe just once when crossing.
                    pass 

                # Check 3pt range for audio feedback
                is_outside_3pt = dist > THREE_POINT_RADIUS
                if is_outside_3pt and human.has_ball:
                     if random.random() < 0.01: # Occasional beep
                         self.sounds['beep'].play()

                # Update Objects
                ball_res = self.ball.update()
                if ball_res == "arrived":
                    # Shot hit hoop
                    team, points, is_dunk = self.ball.shot_data
                    # Simple accuracy check
                    if random.random() > 0.3: # 70% accuracy
                        self.score_basket(team, points, is_dunk)
                    else:
                        self.sounds['rim'].play()
                        self.ball.in_air = False
                        self.ball.owner = None # Loose ball
                        
                        if self.mode == "PRACTICE":
                            self.speak("Miss.")
                            self.reset_positions()
                        else:
                            # Give to nearest player
                            self.ball.owner = self.players[1] # Teammate gets rebound for simplicity
                            self.ball.owner.has_ball = True
                            self.speak("Miss. Teammate rebound.")

                for p in self.players:
                    if self.mode == "PRACTICE" and p.team == TEAM_AWAY:
                        continue

                    action = p.update(self.ball, HOOP_LEFT_POS if p.team == TEAM_AWAY else HOOP_RIGHT_POS, self.sounds, self.play_sound_panned, human.x)
                    
                    if action == "shoot" and self.mode == "PLAY":
                        # AI Shoot
                        hoop = HOOP_LEFT_POS if p.team == TEAM_AWAY else HOOP_RIGHT_POS
                        dist = math.hypot(p.x - hoop[0], p.y - hoop[1])
                        is_dunk = dist < DUNK_RANGE
                        is_3pt = dist > THREE_POINT_RADIUS
                        
                        p.has_ball = False
                        self.ball.owner = None
                        self.ball.in_air = True
                        self.ball.target_hoop = hoop
                        
                        speed = BALL_SPEED
                        dx = hoop[0] - p.x
                        dy = hoop[1] - p.y
                        d = math.hypot(dx, dy)
                        
                        if d > 0:
                            self.ball.vx = (dx/d) * speed
                            self.ball.vy = (dy/d) * speed
                        else:
                            self.ball.vx = 0
                            self.ball.vy = 0
                        
                        self.ball.shot_data = (p.team, 3 if is_3pt else 2, is_dunk)
                        self.sounds['shoot'].play()

                    elif action == "steal" and self.mode == "PLAY":
                        # AI Steal
                        if self.steal_cooldown <= 0 and self.ball.owner and self.ball.owner != p:
                            self.ball.owner.has_ball = False
                            self.ball.owner = p
                            p.has_ball = True
                            self.steal_cooldown = 120 # 2 second cooldown
                            self.speak("Stolen!")

                    elif action == "pass" and self.mode == "PLAY":
                        # AI Pass
                        if p.has_ball and p.teammate:
                            p.has_ball = False
                            self.ball.owner = p.teammate
                            p.teammate.has_ball = True
                            self.sounds['shoot'].play()
                            self.speak("AI Pass")



        pygame.quit()

if __name__ == "__main__":
    try:
        game = Game()
        game.run()
    except Exception as e:
        with open("error.txt", "w") as f:
            import traceback
            traceback.print_exc(file=f)

