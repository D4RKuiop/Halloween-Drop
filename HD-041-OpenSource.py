import json
import math
import random
import sys
from array import array
from pathlib import Path
import pygame

# Halloween Drop — Python 3.12 + Pygame
# Instale: py -3.12 -m pip install pygame
# Execute: py -3.12 halloween_drop.py
# Toda a arte é desenhada por código: nenhuma imagem externa é usada.

pygame.init()
W, H = 800, 600
SCALE = 2
LW, LH = W // SCALE, H // SCALE
screen = pygame.display.set_mode((W, H))
fullscreen=False
pygame.display.set_caption("Halloween Drop: Candy or Tricks!")
canvas = pygame.Surface((LW, LH))
clock = pygame.time.Clock()

BLACK = (12, 10, 24)
NIGHT = (20, 16, 42)
PURPLE = (48, 30, 75)
ORANGE = (255, 126, 30)
GOLD = (255, 190, 65)
WHITE = (245, 239, 220)
MINT = (93, 231, 167)
RED = (245, 70, 85)
PINK = (255, 105, 170)
BLUE = (105, 190, 255)
BROWN = (113, 61, 43)
GRAY = (150, 151, 174)
FONT = pygame.font.Font(None, 16)
BIG = pygame.font.Font(None, 36)
SMALL = pygame.font.Font(None, 12)
MENU_FONT = pygame.font.Font(None, 18)


MAX_FALL_SPEED = 235
PLAYER_BASE_SPEED = 145
PLAYER_ACCEL_LEVEL = 20
PLAYER_SPEED_STEP = 6
MAX_PLAYER_SPEED = 235
MAX_STAGE = 120
MAX_LIVES = 3
CANDY_PER_STAGE = 8
JUMP_VELOCITY = -330



# Procedural chiptune audio; no external sound or music files are needed.
SOUNDS = {}
MUSIC = None

def make_tone(frequency, duration, volume=0.18, waveform="square"):
    if not pygame.mixer.get_init():
        return None
    sample_rate = pygame.mixer.get_init()[0]
    total = max(1, int(sample_rate * duration))
    samples = array("h")
    for i in range(total):
        t = i / sample_rate
        phase = (t * frequency) % 1.0
        if waveform == "noise":
            value = random.uniform(-1.0, 1.0)
        elif waveform == "triangle":
            value = 4.0 * abs(phase - 0.5) - 1.0
        else:
            value = 1.0 if phase < 0.5 else -1.0
        attack = min(1.0, i / max(1, int(sample_rate * 0.008)))
        release = min(1.0, (total - i) / max(1, int(sample_rate * 0.035)))
        samples.append(int(32767 * volume * value * attack * release))
    return pygame.mixer.Sound(buffer=samples.tobytes())

def make_music(notes=None, beat=0.20):
    if not pygame.mixer.get_init():
        return None
    sample_rate=pygame.mixer.get_init()[0]
    notes=notes or [220,0,262,0,330,294,0,220,196,0,247,0,294,262,0,196]
    samples=array("h")
    count=int(sample_rate*beat)
    previous=next((float(n) for n in notes if n),220.0)
    for index,frequency in enumerate(notes):
        if frequency:
            previous=float(frequency)
        # Three simultaneous chiptune voices: lead pulse, chord pulse, and
        # triangle bass. This gives the soundtrack the fuller 16/32-bit feel.
        root=previous
        for i in range(count):
            t=i/sample_rate
            envelope=min(1.0,(count-i)/(sample_rate*0.025))
            lead=0.0
            if frequency:
                lead=1.0 if (t*frequency)%1.0<0.5 else -1.0
            chord_f=root*1.5 if index%4 in (0,2) else root*1.25
            chord=1.0 if (t*chord_f)%1.0<0.5 else -1.0
            bass_phase=((t*(root*0.5))%1.0)
            bass=4.0*abs(bass_phase-0.5)-1.0
            mixed=(lead*0.050+chord*0.018+bass*0.032)*envelope
            samples.append(max(-32767,min(32767,int(32767*mixed))))
    return pygame.mixer.Sound(buffer=samples.tobytes())

MUSIC_TRACKS={}
MUSIC_CHANNEL=None
CURRENT_MUSIC=None
AUDIO_READY=False

def setup_audio():
    global MUSIC_CHANNEL
    try:
        pygame.mixer.quit()
        pygame.mixer.init(frequency=22050,size=-16,channels=1,buffer=512)
        pygame.mixer.set_num_channels(16)
        SOUNDS["collect"]=make_tone(880,0.10,0.12,"triangle")
        SOUNDS["life"]=make_tone(150,0.34,0.19,"noise")
        SOUNDS["defeat"]=make_tone(110,0.65,0.20,"triangle")
        SOUNDS["victory"]=make_tone(660,0.45,0.16,"triangle")
        SOUNDS["sword"]=make_tone(520,0.16,0.14,"square")
        SOUNDS["hit"]=make_tone(260,0.10,0.16,"noise")
        SOUNDS["boss"]=make_tone(100,0.42,0.18,"square")
        SOUNDS["zap"]=make_tone(420,0.22,0.15,"noise")
        SOUNDS["jump"]=make_tone(420,0.12,0.13,"triangle")
        SOUNDS["howl"]=make_tone(115,0.52,0.20,"noise")
        SOUNDS["arm"]=make_tone(180,0.17,0.15,"noise")
        SOUNDS["arrow"]=make_tone(740,0.14,0.13,"triangle")
        SOUNDS["fire"]=make_tone(95,0.20,0.14,"noise")
        SOUNDS["heal"]=make_tone(740,0.24,0.16,"triangle")
        themes=[
            [220,0,262,0,330,294,0,220,196,0,247,0,294,262,0,196],
            [196,247,294,0,330,294,247,0,175,220,262,0,294,262,220,0],
            [147,0,196,220,0,262,220,196,131,0,175,196,0,220,196,175],
            [262,0,330,392,0,330,294,0,220,262,0,330,392,330,262,0],
            [175,208,0,262,233,0,208,175,156,0,208,233,0,262,233,208],
            [330,0,392,440,0,392,294,0,349,392,0,294,262,0,330,0],
            [123,0,164,196,0,220,196,164,110,0,147,164,0,196,164,147],
            [294,349,392,0,440,392,349,0,262,294,349,0,392,349,294,0],
            [164,155,0,147,164,0,138,147,0,164,155,0,123,138,0,147],
            [220,262,330,0,392,330,262,0,196,247,294,0,349,294,247,0],
            [139,175,208,0,262,208,175,0,131,165,196,0,247,196,165,0],
            [196,247,294,0,392,349,294,0,220,262,330,0,440,392,330,0],
        ]
        for index,theme in enumerate(themes,1):
            notes=theme+theme[8:]+theme[:8]
            MUSIC_TRACKS[f"stage_{index}"]=make_music(notes,0.16+(index%3)*0.015)
        multiplayer_themes={
            "versus":[392,0,392,523,0,440,392,0,330,392,0,523,587,0,523,440,392,0,330,0,294,330,392,0],
            "coop":[262,330,392,0,523,0,392,330,294,0,392,440,523,0,440,392,262,0,330,392,0,440,392,330],
            "endless":[147,0,220,0,294,220,0,196,164,0,247,0,330,247,196,0,131,0,196,220,0,262,220,196],
        }
        for mode,theme in multiplayer_themes.items():
            for variant in range(3):
                rotated=theme[variant*4:]+theme[:variant*4]
                transposed=[int(note*(1.0+variant*0.06)) if note else 0 for note in rotated]
                MUSIC_TRACKS[f"multi_{mode}_{variant+1}"]=make_music(transposed*3,0.145+variant*0.012)
        boss_themes={
            30:[110,0,110,147,0,110,165,0,147,0,123,0,98,110,0,0],
            60:[196,0,165,0,220,0,196,0,147,0,165,0,131,0,147,0],
            90:[98,0,123,98,0,147,0,123,82,0,110,0,123,0,98,0],
            120:[82,0,123,0,165,0,147,0,110,0,165,0,196,0,147,0],
        }
        for phase,theme in boss_themes.items():
            MUSIC_TRACKS[f"boss_{phase}"]=make_music(theme*3,0.22)
        MUSIC_TRACKS["ending"]=make_music([523,0,659,784,0,1047,784,659,587,0,784,988,0,1175,988,784]*3,0.24)
        MUSIC_CHANNEL=pygame.mixer.Channel(0)
    except pygame.error:
        SOUNDS.clear()
        MUSIC_TRACKS.clear()
        MUSIC_CHANNEL=None

def set_music(track):
    global CURRENT_MUSIC
    if track==CURRENT_MUSIC:
        return
    if MUSIC_CHANNEL and track in MUSIC_TRACKS and MUSIC_TRACKS[track]:
        MUSIC_CHANNEL.stop()
        MUSIC_CHANNEL.play(MUSIC_TRACKS[track],loops=-1)
        CURRENT_MUSIC=track

def set_stage_music(stage, mode="solo", endless=False):
    song_index=max(1,min(12,(max(1,min(MAX_STAGE,stage))-1)//10+1))
    if mode=="solo":
        set_music(f"stage_{song_index}")
    else:
        mood=(song_index-1)%3+1
        if mode in ("versus","pvp"):
            set_music(f"multi_versus_{mood}")
        else:
            set_music(f"multi_{'endless' if endless else 'coop'}_{mood}")

def set_boss_music(phase, mode="solo", endless=False):
    set_music(f"boss_{phase}")

def play_sound(name):
    sound=SOUNDS.get(name)
    if sound:
        sound.play()

def text(msg, x, y, font=FONT, color=WHITE, center=False):
    img = font.render(msg, False, color)
    rect = img.get_rect()
    rect.center = (int(x), int(y)) if center else (int(x), int(y))
    if not center:
        rect.topleft = (int(x), int(y))
    canvas.blit(img, rect)


def rect(color, x, y, w, h):
    pygame.draw.rect(canvas, color, (int(x), int(y), int(w), int(h)))


def background():
    canvas.fill(NIGHT)
    stars = random.Random(12)
    for _ in range(45):
        rect((65, 55, 100), stars.randrange(LW), stars.randrange(10, 175), 1, 1)
    pygame.draw.circle(canvas, GOLD, (340, 53), 20)
    pygame.draw.circle(canvas, NIGHT, (350, 46), 18)
    pygame.draw.polygon(canvas, PURPLE, [(0,190),(40,150),(80,190),(130,135),(180,190),(240,155),(300,190),(360,145),(430,190),(490,155),(550,190),(620,145),(690,190),(740,155),(800,190),(800,300),(0,300)])
    rect(BLACK, 0, 245, LW, LH - 245)
    for x, y, w, h in [(25,190,42,65),(95,210,50,45),(590,195,48,60),(680,205,62,50)]:
        rect((28,19,42), x,y,w,h)
        rect((90,51,68), x+7,y+9,7,9)
        rect((90,51,68), x+25,y+9,7,9)
        rect((255,95,45), x+16,y+31,9,12)
    rect((33,23,43), 0, 266, LW, 34)
    rect((67,39,53), 0, 266, LW, 2)
    for x in (35,370,735):
        rect((170,70,22),x,272,13,10); rect(ORANGE,x+2,270,9,12)
        rect(BLACK,x+4,274,2,3); rect(BLACK,x+8,274,2,3)
        rect(MINT,x+6,268,2,3)


def jack(x, y, palette="orange"):
    if palette == "blue":
        shadow, body, highlight, stripe, shade = (25,55,115), (40,105,205), (91,177,255), (137,207,255), (26,67,151)
    else:
        shadow, body, highlight, stripe, shade = (180,67,18), ORANGE, (255,151,35), (255,177,48), (205,78,20)
    rect(shadow,x+4,y+3,26,25); rect(body,x,y+5,34,22)
    rect(highlight,x+5,y+2,24,26); rect(stripe,x+9,y+4,5,20)
    rect(shade,x+25,y+7,4,17); rect((70,145,62),x+14,y-2,7,7)
    rect((42,91,45),x+16,y-4,4,4)
    rect(BLACK,x+7,y+10,7,6); rect(BLACK,x+21,y+10,7,6)
    rect(GOLD,x+9,y+11,3,3); rect(GOLD,x+23,y+11,3,3)
    rect(BLACK,x+8,y+20,19,5)
    for xx in (10,16,22): rect(WHITE,x+xx,y+20,3,3)
    rect((70,145,62),x+11,y+28,12,3)


SWEETS = ["bala", "pirulito", "chiclete", "urso"]
TRICKS = ["dentadura", "papel", "pote", "aranha"]


def draw_item(item):
    x, y, kind = int(item["x"]), int(item["y"]), item["kind"]
    if kind == "bala":
        rect((177,42,87),x,y+7,5,8); rect((177,42,87),x+16,y+7,5,8)
        rect(PINK,x+4,y+4,14,14); rect((227,57,133),x+6,y+3,10,16)
        rect(WHITE,x+7,y+6,3,4); rect((255,190,208),x+12,y+10,3,5)
    elif kind == "pirulito":
        rect((155,94,67),x+9,y+12,3,10); rect(WHITE,x+10,y+14,1,6)
        pygame.draw.circle(canvas,(147,35,65),(x+10,y+8),9)
        pygame.draw.circle(canvas,RED,(x+10,y+7),8); pygame.draw.circle(canvas,PINK,(x+10,y+7),5)
        rect(WHITE,x+6,y+4,3,3); rect((255,183,197),x+12,y+9,2,2)
    elif kind == "chiclete":
        # Tablete em embalagem dobrada, com varios gomos visiveis.
        rect((49,71,143),x+1,y+5,21,13); rect((50,128,188),x+2,y+4,18,13)
        pygame.draw.polygon(canvas,(78,167,218),[(x+2,y+4),(x+6,y+1),(x+18,y+1),(x+20,y+4)])
        rect((218,241,246),x+4,y+7,14,8)
        for gx in (x+5,x+9,x+13):
            rect((97,171,211),gx,y+8,3,6); rect((228,248,250),gx,y+8,2,1)
        rect((42,89,153),x+2,y+17,18,2)
        rect((78,167,218),x+1,y+7,2,7); rect((78,167,218),x+20,y+7,2,7)
    elif kind == "urso":
        # Silhueta lisa e brilhante de goma, sem textura de pelucia.
        pygame.draw.ellipse(canvas,(29,105,47),(x+4,y+7,14,14))
        pygame.draw.circle(canvas,(29,105,47),(x+6,y+5),4); pygame.draw.circle(canvas,(29,105,47),(x+16,y+5),4)
        pygame.draw.ellipse(canvas,(87,199,62),(x+5,y+7,12,13))
        pygame.draw.circle(canvas,(87,199,62),(x+6,y+5),3); pygame.draw.circle(canvas,(87,199,62),(x+16,y+5),3)
        pygame.draw.ellipse(canvas,(113,222,75),(x+7,y+3,2,3))
        rect((150,235,105),x+7,y+9,2,2); rect((150,235,105),x+14,y+9,2,2)
        rect((45,119,44),x+9,y+12,4,3); rect((150,235,105),x+10,y+12,2,1)
        rect((113,222,75),x+3,y+12,3,4); rect((113,222,75),x+17,y+12,3,4)
        rect((113,222,75),x+7,y+18,4,3); rect((113,222,75),x+13,y+18,4,3)
        rect((184,242,112),x+5,y+6,2,2)
    elif kind == "dentadura":
        rect((119,36,56),x+2,y+5,18,11); rect(WHITE,x+3,y+5,16,8)
        rect((210,215,225),x+4,y+12,14,4)
        for xx in (4,8,12,16): rect((208,211,224),x+xx,y+6,2,5)
        rect(WHITE,x+1,y+4,3,3); rect(WHITE,x+17,y+4,3,3)
        rect(RED,x+2,y+3,2,3); rect(RED,x+17,y+3,2,3)
    elif kind == "papel":
        rect((158,161,180),x+4,y+3,14,17); rect(WHITE,x+4,y+2,13,17)
        rect((213,218,229),x+6,y+4,9,2); rect((227,230,237),x+7,y+7,7,2)
        rect(WHITE,x+12,y+13,10,7); rect((210,215,225),x+14,y+14,6,4)
        rect((245,247,251),x+6,y+4,2,9)
    elif kind == "pote":
        # Pote de vidro vazio com tampa, gargalo e paredes transparentes.
        rect((117,67,150),x+3,y+2,16,3); rect((224,106,170),x+2,y+3,18,2)
        rect((103,63,136),x+5,y+5,12,3)
        rect((102,74,143),x+2,y+8,18,12); rect((174,134,199),x+4,y+8,14,10)
        rect((30,24,62),x+6,y+10,10,6)
        rect((209,190,224),x+3,y+9,2,9); rect((209,190,224),x+17,y+9,2,9)
        rect((225,210,235),x+5,y+18,12,2); rect((235,208,229),x+7,y+6,8,1)
        rect((251,240,248),x+5,y+11,1,4)
    elif kind == "aranha":
        # Oito pernas articuladas, corpo roxo e olhos vermelhos.
        leg=(19,14,30); shine=(110,76,125)
        legs=[
            ((x+7,y+8),(x+4,y+5),(x+1,y+4)), ((x+7,y+10),(x+3,y+10),(x+1,y+12)),
            ((x+7,y+13),(x+4,y+15),(x+2,y+18)), ((x+9,y+14),(x+7,y+18),(x+7,y+21)),
            ((x+15,y+8),(x+18,y+5),(x+21,y+4)), ((x+15,y+10),(x+19,y+10),(x+21,y+12)),
            ((x+15,y+13),(x+18,y+15),(x+20,y+18)), ((x+13,y+14),(x+15,y+18),(x+15,y+21)),
        ]
        for a,b,c in legs:
            pygame.draw.lines(canvas,leg,False,(a,b,c),2); pygame.draw.line(canvas,shine,a,b,1)
        pygame.draw.ellipse(canvas,(42,28,58),(x+6,y+7,11,10))
        pygame.draw.ellipse(canvas,(104,63,121),(x+7,y+5,8,7))
        rect((238,44,59),x+8,y+7,2,2); rect((238,44,59),x+13,y+7,2,2)
        rect(WHITE,x+8,y+7,1,1); rect(WHITE,x+13,y+7,1,1)
        rect(WHITE,x+10,y+12,1,2); rect(WHITE,x+12,y+12,1,2)
def new_item(level,lane=None):
    trick_chance = min(0.58, 0.32 + (level - 1) * 0.015)
    kind = random.choice(TRICKS if random.random() < trick_chance else SWEETS)
    low,high=lane if lane else (8,LW-28)
    return {"x": random.randint(int(low),int(high)), "y": -25, "kind": kind,
            "speed": min(MAX_FALL_SPEED, random.uniform(55,95) + level*7)}



BOSS_NAMES={30:"WEREWOLF",60:"GHOST",90:"ZOMBIE",120:"SKELETON"}
BOSS_HP={30:7,60:9,90:11,120:18}
BOSS_ORDER=(30,60,90,120)

def start_boss(g,phase):
    g["items"].clear()
    hp=BOSS_HP[phase]
    if g.get("mode")!="solo":
        hp=math.ceil(hp*1.5)
    g["boss"]={
        "phase":phase,"name":BOSS_NAMES[phase],"x":-55.0,"y":58.0,
        "vx":50.0,"hp":hp,"max_hp":hp,
        "intro_timer":5.0,"beam_mode":"idle","beam_timer":0.8,"beam_x":LW/2,
        "sword_timer":0.8,"charge_active":False,"charge_timer":1.2,
        "arm_timer":1.20,"arm_warning":0.0,"arm_target_x":LW/2,
        "arrow_timer":0.95,"arrow_warning":0.0,"arrow_target_x":LW/2,"dive_timer":2.1,
        "dive_active":False,"dive_x":LW/2,"dive_dir":1,
    }
    g["falling_swords"].clear()
    g["projectiles"].clear()
    g["arms"].clear()
    g["arrows"].clear()
    g["fires"].clear()
    g["swords"]=0
    g["message"]=f"{BOSS_NAMES[phase]} HAS ARRIVED!"
    g["message_time"]=2.5
    set_boss_music(phase,g.get("mode","solo"),g.get("coop_endless",False))
    play_sound("boss")

def lose_life(g,message="OUCH! -1 LIFE"):
    if g["invulnerability"]>0:
        return
    g["lives"]-=1
    g["invulnerability"]=1.0
    g["message"]=message
    g["message_time"]=0.8
    play_sound("life")

def damage_player(g,player_id,message="TRICK! -1 LIFE"):
    if player_id==1:
        lose_life(g,message)
        return
    if g.get("p2_invulnerability",0)>0 or g.get("p2_lives",0)<=0:
        return
    g["p2_lives"]-=1
    g["p2_invulnerability"]=1.0
    g["message"]=f"P2: {message}"
    g["message_time"]=0.8
    play_sound("life")

def boss_hit_players(g, hitbox, message):
    """Apply a boss collision to any active multiplayer player in its area."""
    players=[(1,g["player_x"],g["player_y"],g["lives"]),
             (2,g.get("p2_x",0),g.get("p2_y",0),g.get("p2_lives",0))]
    for player_id,x,y,lives in players:
        if lives>0 and pygame.Rect(int(x),int(y),34,34).colliderect(hitbox):
            damage_player(g,player_id,message)

def boss_target_x(g,boss_x):
    targets=[]
    if g.get("lives",0)>0:
        targets.append(g["player_x"]+17)
    if g.get("mode")!="solo" and g.get("p2_lives",0)>0:
        targets.append(g["p2_x"]+17)
    return min(targets,key=lambda value:abs(value-boss_x)) if targets else g["player_x"]+17

def draw_heart(x,y):
    x,y=int(x),int(y)
    # Chunky, glowing pixel heart with a dark outline and a small shine.
    pygame.draw.polygon(canvas,(100,24,54),[
        (x+2,y+5),(x+2,y+2),(x+6,y),(x+10,y+3),(x+14,y),
        (x+18,y+2),(x+18,y+6),(x+10,y+16)
    ])
    pygame.draw.polygon(canvas,(244,50,87),[
        (x+3,y+5),(x+3,y+3),(x+6,y+2),(x+10,y+6),(x+14,y+2),
        (x+17,y+3),(x+17,y+6),(x+10,y+14)
    ])
    rect((255,128,153),x+5,y+3,3,2)
    rect(WHITE,x+6,y+3,2,1)

def update_hearts(g,dt):
    g["heart_timer"]-=dt
    needs_heart=(g["lives"]>0 and g["lives"]<MAX_LIVES) or (g.get("mode")!="solo" and g.get("p2_lives",0)>0 and g.get("p2_lives",0)<MAX_LIVES)
    if needs_heart and g["heart_timer"]<=0 and not g["hearts"]:
        g["hearts"].append({"x":random.randint(18,LW-38),"y":-20,"speed":72})
        g["heart_timer"]=random.uniform(10,14)
    remaining=[]
    for heart in g["hearts"]:
        heart["y"]+=heart["speed"]*dt
        heart_rect=pygame.Rect(int(heart["x"]),int(heart["y"]),20,18)
        player_rects=[]
        if g["lives"]>0:
            player_rects.append((1,pygame.Rect(int(g["player_x"]),int(g["player_y"]),34,34)))
        if g.get("mode")!="solo" and g.get("p2_lives",0)>0:
            player_rects.append((2,pygame.Rect(int(g["p2_x"]),int(g["p2_y"]),34,34)))
        collected=False
        for player_id,player_rect in player_rects:
            life_key="lives" if player_id==1 else "p2_lives"
            if player_rect.colliderect(heart_rect) and g[life_key]<MAX_LIVES:
                g[life_key]=min(MAX_LIVES,g[life_key]+1)
                g["message"]=f"P{player_id} EXTRA LIFE!" if g.get("mode")!="solo" else "EXTRA LIFE!"
                g["message_time"]=1.1
                play_sound("heal")
                collected=True
                break
        if not collected and heart["y"]<LH+20:
            remaining.append(heart)
    g["hearts"]=remaining

def draw_sword(x,y):
    x,y=int(x),int(y)
    rect((54,52,74),x+8,y+1,5,18)
    rect((188,214,238),x+9,y+2,3,12)
    rect(WHITE,x+10,y+3,1,7)
    pygame.draw.polygon(canvas,(214,225,242),[(x+8,y+2),(x+13,y+2),(x+10,y-4)])
    rect(GOLD,x+5,y+13,11,2); rect(BROWN,x+9,y+15,3,5)
    rect((80,43,37),x+8,y+19,5,2)

def draw_arm(arm):
    x,y=int(arm["x"]),int(arm["y"])
    rect((29,75,52),x+2,y+5,13,8)
    rect((83,133,76),x+4,y+3,11,8)
    for dx in (4,7,10,13):
        rect((83,133,76),x+dx,y,3,6)
    rect((176,207,119),x+5,y+4,5,2)
    rect((37,68,45),x+1,y+11,15,3)

def draw_arrow(arrow):
    x,y=int(arrow["x"]),int(arrow["y"])
    rect((126,78,45),x-1,y+5,21,2)
    rect((213,225,232),x+5,y+4,11,3)
    pygame.draw.polygon(canvas,WHITE,[(x+18,y+3),(x+24,y+6),(x+18,y+9)])
    pygame.draw.polygon(canvas,(179,52,60),[(x,y+3),(x+6,y+6),(x,y+9)])
    if arrow.get("flaming"):
        rect(ORANGE,x+8,y+1,5,2); rect(GOLD,x+9,y+3,3,2)

def draw_fire(fire,anim_time):
    x=int(fire["x"])
    h=23+int((math.sin(anim_time*18)+1)*3)
    pygame.draw.polygon(canvas,(178,48,30),[(x-12,LH-38),(x-9,LH-h-18),(x-3,LH-h-8),(x,LH-h-25),(x+5,LH-h-10),(x+12,LH-38)])
    pygame.draw.polygon(canvas,(255,112,30),[(x-7,LH-38),(x-3,LH-h-12),(x+1,LH-h-4),(x+5,LH-h-14),(x+8,LH-38)])
    rect(GOLD,x-2,LH-38,4,8)

def draw_storm_cloud(x,y,flash=False,anim_time=0.0):
    """Small chunky pixel-art thundercloud placed above every boss bolt."""
    x=int(x); y=int(y+math.sin(anim_time*7)*1)
    outline=(38,37,61); shade=(84,91,123)
    body=(150,164,190) if flash else (121,134,165)
    highlight=(225,235,239) if flash else (178,193,211)
    # Dark stepped silhouette, then inset pixel blocks for volume.
    rect(outline,x-22,y+6,44,13); rect(outline,x-16,y+1,32,18)
    rect(outline,x-9,y-4,20,23); rect(outline,x+5,y+2,15,17)
    rect(shade,x-19,y+7,38,9); rect(shade,x-13,y+3,26,12)
    rect(body,x-15,y+6,30,9); rect(body,x-8,y+1,17,14)
    rect(body,x+6,y+6,11,9)
    rect(highlight,x-7,y+2,9,3); rect(highlight,x-14,y+7,8,2)
    if flash:
        rect(GOLD,x-2,y+17,5,3)
        rect(WHITE,x-1,y+17,2,2)

def draw_boss(boss,anim_time):
    cx=int(boss["x"])
    top=int(boss["y"]+math.sin(anim_time*3.2)*3)
    name=boss["name"]
    if name=="WEREWOLF":
        pygame.draw.ellipse(canvas,(45,31,54),(cx-17,top+24,34,26))
        pygame.draw.polygon(canvas,(65,48,60),[(cx-12,top+19),(cx-18,top-2),(cx-3,top+10)])
        pygame.draw.polygon(canvas,(65,48,60),[(cx+12,top+19),(cx+18,top-2),(cx+3,top+10)])
        pygame.draw.ellipse(canvas,(101,76,77),(cx-13,top+8,26,28))
        pygame.draw.polygon(canvas,(236,226,203),[(cx-10,top+12),(cx-4,top+14),(cx-9,top+21)])
        pygame.draw.polygon(canvas,(236,226,203),[(cx+10,top+12),(cx+4,top+14),(cx+9,top+21)])
        rect(RED,cx-10,top+20,4,3); rect(RED,cx+6,top+20,4,3)
        rect(WHITE,cx-6,top+29,4,4); rect(WHITE,cx+3,top+29,4,4)
    elif name=="GHOST":
        pygame.draw.ellipse(canvas,(185,219,231),(cx-17,top+6,34,39))
        pygame.draw.polygon(canvas,(185,219,231),[(cx-16,top+31),(cx-13,top+49),(cx-5,top+42),(cx,top+50),(cx+7,top+42),(cx+14,top+48),(cx+17,top+31)])
        pygame.draw.ellipse(canvas,(235,245,240),(cx-12,top+11,24,27))
        rect(BLACK,cx-10,top+23,5,8); rect(BLACK,cx+5,top+23,5,8)
        rect((105,77,109),cx-4,top+34,8,5)
    elif name=="ZOMBIE":
        pygame.draw.ellipse(canvas,(49,88,59),(cx-17,top+22,34,27))
        rect((46,89,56),cx-13,top+7,26,34)
        rect((35,59,47),cx-17,top+5,10,6); rect((37,62,47),cx-3,top+3,13,7)
        rect((105,146,88),cx-10,top+13,20,22)
        rect(BLACK,cx-10,top+17,6,7); rect(BLACK,cx+5,top+17,6,7)
        rect(GOLD,cx-9,top+18,3,3); rect(GOLD,cx+6,top+18,3,3)
        rect((76,39,39),cx-8,top+29,17,6)
        rect(WHITE,cx-5,top+29,3,3); rect(WHITE,cx+2,top+29,3,3)
        rect((153,74,76),cx+12,top+24,5,5)
    else:
        # Slim skeleton archer: visible skull, rib cage, joints, and separated bones.
        bone=(231,224,196); shadow=(157,146,119)
        pygame.draw.ellipse(canvas,shadow,(cx-9,top+1,18,17))
        pygame.draw.ellipse(canvas,bone,(cx-8,top,16,15))
        rect(BLACK,cx-5,top+5,3,5); rect(BLACK,cx+2,top+5,3,5)
        rect(RED,cx-4,top+6,2,2); rect(RED,cx+3,top+6,2,2)
        rect(shadow,cx-4,top+12,8,2); rect(bone,cx-3,top+11,6,2)
        rect(shadow,cx-2,top+17,4,22); rect(bone,cx-1,top+16,2,22)
        for yy,width in ((19,13),(24,15),(29,13),(34,10)):
            pygame.draw.arc(canvas,bone,(cx-width//2,top+yy-3,width,7),0.15,3.0,2)
        pygame.draw.line(canvas,shadow,(cx-5,top+19),(cx-12,top+29),3)
        pygame.draw.line(canvas,bone,(cx-5,top+18),(cx-12,top+28),2)
        pygame.draw.line(canvas,bone,(cx+5,top+19),(cx+11,top+27),2)
        rect(bone,cx-14,top+27,5,3); rect(bone,cx+9,top+26,5,3)
        pygame.draw.line(canvas,bone,(cx-5,top+38),(cx-8,top+48),3)
        pygame.draw.line(canvas,bone,(cx+5,top+38),(cx+8,top+48),3)
        rect(bone,cx-11,top+47,7,3); rect(bone,cx+5,top+47,7,3)
        pygame.draw.arc(canvas,(165,112,65),(cx+10,top+12,17,34),-1.5,1.5,2)
        rect(BROWN,cx+14,top+15,3,29)
    if int(anim_time*8)%2:
        rect(GOLD,cx-30,top+30,3,3); rect(GOLD,cx+27,top+26,3,3)

def draw_boss_scene(g):
    boss=g["boss"]
    for fire in g["fires"]:
        draw_fire(fire,g["anim_time"])
    draw_boss(boss,g["anim_time"])
    for arm in g["arms"]:
        draw_arm(arm)
    for arrow in g["arrows"]:
        draw_arrow(arrow)
    bar_x,bar_y,bar_w=117,34,166
    rect((21,12,29),bar_x-3,bar_y-3,bar_w+6,12)
    rect((93,32,46),bar_x,bar_y,bar_w,6)
    fill=int(bar_w*max(0,boss["hp"])/boss["max_hp"])
    if fill:
        rect(RED,bar_x,bar_y,fill,6); rect((255,129,76),bar_x,bar_y,fill,2)
    text(f"{boss['name']}  {boss['hp']}/{boss['max_hp']}",LW//2,47,SMALL,WHITE,True)
    if boss["name"] in ("GHOST","ZOMBIE","SKELETON"):
        if boss["beam_mode"]=="warning":
            bx=int(boss["beam_x"])
            draw_storm_cloud(bx,91,False,g["anim_time"])
            for yy in range(123,LH-35,9):
                rect((255,77,78) if (yy//9)%2 else GOLD,bx-2,yy,4,4)
            text("LIGHTNING!",bx,116,SMALL,GOLD,True)
        elif boss["beam_mode"]=="strike":
            bx=int(boss["beam_x"])
            draw_storm_cloud(bx,91,True,g["anim_time"])
            points=[(bx,109),(bx-8,127),(bx+5,143),(bx-7,161),(bx+7,179),(bx-3,199),(bx+3,218),(bx-3,LH-35)]
            pygame.draw.lines(canvas,(255,248,177),False,points,7)
            pygame.draw.lines(canvas,WHITE,False,points,3)
    if boss["name"]=="ZOMBIE" and boss.get("arm_warning",0)>0:
        tx=int(boss["arm_target_x"])
        for yy in range(123,LH-42,10):
            rect(RED if (yy//10)%2 else (255,135,78),tx-2,yy,4,5)
        rect((55,24,32),tx-21,119,42,10)
        text("ARMS INCOMING!",tx,124,SMALL,(255,153,91),True)
    if boss["name"]=="SKELETON" and boss.get("arrow_warning",0)>0:
        tx=int(boss["arrow_target_x"])
        for yy in range(128,LH-42,12):
            rect((255,167,74) if (yy//12)%2 else (143,74,51),tx-2,yy,4,5)
        rect((55,24,32),tx-24,LH-57,48,9)
        text("ARROW WARNING!",tx,LH-72,SMALL,(255,185,97),True)
    for sword in g["falling_swords"]:
        draw_sword(sword["x"],sword["y"])
    for projectile in g["projectiles"]:
        draw_sword(projectile["x"],projectile["y"])
    if boss["intro_timer"]>0:
        # Pixel-cinema intro: pulsing danger vignette, expanding letterbox,
        # scan-line flashes and a large boss title reveal.
        progress=1-boss["intro_timer"]/5.0
        bar_h=8+int(17*min(1,progress*3))
        rect((7,5,15),0,0,LW,bar_h); rect((7,5,15),0,LH-bar_h,LW,bar_h)
        if int(g["anim_time"]*12)%2==0:
            rect((42,13,23),0,bar_h,LW,2)
        if boss["intro_timer"]>4.55:
            rect((250,226,180),0,bar_h,LW,LH-2*bar_h)
        else:
            text("A SHADOW RISES...",LW//2,bar_h+16,MENU_FONT,GOLD,True)
            reveal=progress>0.42
            if reveal:
                title_y=LH//2-9+int(math.sin(g["anim_time"]*5)*2)
                text(boss["name"],LW//2,title_y+1,BIG,(96,30,38),True)
                text(boss["name"],LW//2,title_y,BIG,GOLD,True)
                text(f"STAGE {boss['phase']}  •  BOSS ENCOUNTER",LW//2,title_y+19,MENU_FONT,WHITE,True)
            text("PREPARE TO FIGHT",LW//2,LH-bar_h-16,SMALL,RED,True)
    elif boss["name"]=="WEREWOLF":
        text("JUMP: SPACE/W/UP  |  WOLF ROLL: JUMP",LW//2,LH-16,SMALL,GOLD,True)
    else:
        controls="P1: SPACE/S THROW" if g.get("mode")=="solo" else "P1: S THROW  |  P2: DOWN THROW"
        text(f"{controls}  |  SWORDS: {g['swords']}",LW//2,LH-16,SMALL,GOLD,True)

def update_boss(g,dt):
    boss=g["boss"]
    if boss is None or boss["intro_timer"]>0:
        return False
    name=boss["name"]
    boss["x"]+=boss["vx"]*dt
    if name=="WEREWOLF":
        if boss["charge_active"]:
            boss["y"]+=(LH-85-boss["y"])*min(1,dt*7)
            if boss["x"] < -45 or boss["x"] > LW+45:
                boss["charge_active"]=False
                boss["charge_timer"]=random.uniform(1.0,1.5)
                boss["y"]=58.0
            # Match the dangerous lower body rather than the transparent space
            # around the wolf's ears and animation silhouette.
            wolf_hit=pygame.Rect(int(boss["x"])-17,int(boss["y"])+23,34,28)
            boss_hit_players(g,wolf_hit,"THE WOLF HIT YOU!")
        else:
            boss["y"]+=(58.0-boss["y"])*min(1,dt*5)
            boss["x"]=max(50,min(LW-50,boss["x"]))
            boss["charge_timer"]-=dt
            if boss["charge_timer"]<=0:
                direction=1 if boss["x"]<LW/2 else -1
                boss["x"]=-35 if direction>0 else LW+35
                boss["vx"]=direction*245
                boss["charge_active"]=True
                play_sound("howl")
    else:
        if boss["x"]<65:
            boss["x"]=65; boss["vx"]=abs(boss["vx"])
        elif boss["x"]>LW-65:
            boss["x"]=LW-65; boss["vx"]=-abs(boss["vx"])

    if name in ("GHOST","ZOMBIE","SKELETON"):
        # Lightning uses a telegraphed random lane so it pressures without
        # tracking the player's position precisely.
        if boss["beam_mode"]=="idle":
            boss["beam_timer"]-=dt
            if boss["beam_timer"]<=0:
                boss["beam_x"]=random.randint(24,LW-24)
                boss["beam_mode"]="warning"; boss["beam_timer"]=0.48 if name!="GHOST" else 0.56
        else:
            boss["beam_timer"]-=dt
            if boss["beam_mode"]=="warning" and boss["beam_timer"]<=0:
                boss["beam_mode"]="strike"; boss["beam_timer"]=0.36; play_sound("zap")
            elif boss["beam_mode"]=="strike":
                boss_hit_players(g,pygame.Rect(int(boss["beam_x"])-18,120,36,LH-155),f"{name} LIGHTNING! -1")
                if boss["beam_timer"]<=0:
                    boss["beam_mode"]="idle"; boss["beam_timer"]=random.uniform(0.72,1.15) if name!="GHOST" else random.uniform(0.62,1.05)

        # Only the Ghost dives across the floor lane.
        if name=="GHOST":
            if not boss["dive_active"]:
                boss["dive_timer"]-=dt
                if boss["dive_timer"]<=0:
                    boss["dive_active"]=True
                    # The Ghost's floor ambush always enters from the right and sweeps left.
                    boss["dive_x"]=LW+35.0
                    boss["x"]=boss["dive_x"]
                    boss["dive_dir"]=-1
                    boss["dive_timer"]=random.uniform(2.5,3.5)
                    play_sound("howl" if name=="GHOST" else "arm")
            else:
                boss["y"]+=(LH-82-boss["y"])*min(1,dt*8)
                boss["dive_x"]+=boss["dive_dir"]*235*dt
                boss["x"]=boss["dive_x"]
                boss_hit_players(g,pygame.Rect(int(boss["x"])-17,int(boss["y"])+6,34,40),f"{name} AMBUSH! -1 LIFE")
                if boss["x"]<-45 or boss["x"]>LW+45:
                    boss["dive_active"]=False
                    boss["y"]=58.0
        else:
            boss["y"]+=(58.0-boss["y"])*min(1,dt*4)

    if name=="ZOMBIE":
        if boss.get("arm_warning",0)>0:
            boss["arm_warning"]-=dt
            if boss["arm_warning"]<=0:
                boss["arm_warning"]=0.0
                target=boss["arm_target_x"]
                flight=1.65
                dx=max(-110,min(110,(target-boss["x"])/flight))
                g["arms"].append({"x":boss["x"],"y":boss["y"]+40,"vx":dx,"vy":92})
                if len(g["arms"])<3:
                    g["arms"].append({"x":boss["x"]-8,"y":boss["y"]+40,"vx":-dx*0.55,"vy":100})
                boss["arm_timer"]=random.uniform(1.45,1.85)
                play_sound("arm")
        else:
            boss["arm_timer"]-=dt
            if boss["arm_timer"]<=0:
                # Lock a slightly inaccurate lane before a long warning so the
                # player has time to read and leave the attack path.
                target_x=boss_target_x(g,boss["x"])+random.randint(-54,54)
                target_x=_ai_clamp(target_x,28,LW-28)
                boss["arm_target_x"]=target_x
                boss["arm_warning"]=0.88
        # Resolve the projectiles against the same player hitbox used by the planner.
        alive=[]
        for arm in g["arms"]:
            arm["x"]+=arm["vx"]*dt; arm["y"]+=arm["vy"]*dt
            arm_rect=pygame.Rect(int(arm["x"]),int(arm["y"]),17,15)
            if any(lives>0 and pygame.Rect(int(px),int(py),34,34).colliderect(arm_rect)
                   for lives,px,py in ((g["lives"],g["player_x"],g["player_y"]),(g.get("p2_lives",0),g.get("p2_x",0),g.get("p2_y",0)))):
                boss_hit_players(g,arm_rect,"ZOMBIE ARM! -1 LIFE")
            elif arm["y"]<LH:
                alive.append(arm)
        g["arms"]=alive

    if name=="SKELETON":
        if boss.get("arrow_warning",0)>0:
            boss["arrow_warning"]-=dt
            if boss["arrow_warning"]<=0:
                boss["arrow_warning"]=0.0
                target=boss["arrow_target_x"]
                flight=1.12
                dx=max(-90,min(90,(target-boss["x"])/flight))
                g["arrows"].append({"x":boss["x"]+12,"y":boss["y"]+22,"vx":dx,"vy":130,"flaming":random.random()<0.40})
                boss["arrow_timer"]=random.uniform(1.25,1.65)
                play_sound("arrow")
        else:
            boss["arrow_timer"]-=dt
            if boss["arrow_timer"]<=0:
                # Show the lane first; the shot has intentional spread instead
                # of tracking Jack's exact position.
                target_x=boss_target_x(g,boss["x"])+random.randint(-82,82)
                boss["arrow_target_x"]=_ai_clamp(target_x,24,LW-24)
                boss["arrow_warning"]=0.82
        arrows=[]
        for arrow in g["arrows"]:
            arrow["x"]+=arrow["vx"]*dt; arrow["y"]+=arrow["vy"]*dt
            arrow_rect=pygame.Rect(int(arrow["x"]),int(arrow["y"]),22,10)
            struck=any(lives>0 and pygame.Rect(int(px),int(py),34,34).colliderect(arrow_rect)
                       for lives,px,py in ((g["lives"],g["player_x"],g["player_y"]),(g.get("p2_lives",0),g.get("p2_x",0),g.get("p2_y",0))))
            if struck:
                boss_hit_players(g,arrow_rect,"SKELETON ARROW! -1 LIFE")
            if struck or arrow["y"]>=LH-62:
                fire_x=max(17,min(LW-17,int(arrow["x"])))
                g["fires"].append({"x":fire_x,"timer":2.6 if arrow["flaming"] else 1.7})
                play_sound("fire")
            elif arrow["y"]<LH:
                arrows.append(arrow)
        g["arrows"]=arrows
        active=[]
        for fire in g["fires"]:
            fire["timer"]-=dt
            if fire["timer"]>0:
                active.append(fire)
        g["fires"]=active

    if name!="WEREWOLF" and not boss.get("dive_active",False):
        boss["x"]=max(58,min(LW-58,boss["x"]))
    boss["sword_timer"]-=dt
    if boss["sword_timer"]<=0 and g["swords"]+len(g["falling_swords"])<3:
        g["falling_swords"].append({"x":random.randint(20,LW-20),"y":-15,"speed":random.randint(95,135)})
        boss["sword_timer"]=random.uniform(1.15,1.75)
    left=[]
    for sword in g["falling_swords"]:
        sword["y"]+=sword["speed"]*dt
        sword_rect=pygame.Rect(int(sword["x"])-5,int(sword["y"])-3,16,25)
        collector=next((pid for pid,px,py,lives in ((1,g["player_x"],g["player_y"],g["lives"]),(2,g.get("p2_x",0),g.get("p2_y",0),g.get("p2_lives",0)))
                        if lives>0 and pygame.Rect(int(px),int(py),34,34).colliderect(sword_rect)),None)
        if collector is not None:
            g["swords"]=min(3,g["swords"]+1)
            g["message"]=f"P{collector} SWORD! PRESS S/DOWN"
            g["message_time"]=1.0
            play_sound("sword")
        elif sword["y"]<LH+15:
            left.append(sword)
    g["falling_swords"]=left
    for projectile in g["projectiles"][:]:
        difference=boss["x"]-projectile["x"]
        projectile["x"]+=max(-240*dt,min(240*dt,difference))
        projectile["y"]-=280*dt
        hitbox=pygame.Rect(int(boss["x"])-25,int(boss["y"])-2,50,52)
        if hitbox.colliderect(pygame.Rect(int(projectile["x"])-5,int(projectile["y"])-6,12,22)):
            boss["hp"]-=1; g["projectiles"].remove(projectile); play_sound("hit")
            if boss["hp"]<=0:
                return True
        elif projectile["y"]<-25:
            g["projectiles"].remove(projectile)
    return False

def reset_game():
    return {"player_x": LW//2-17, "items": [], "score": 0, "lives": 3,
            "spawn": 0.0, "level": 1, "message": "", "message_time": 0.0,
            "boss": None, "next_boss": 30, "falling_swords": [], "projectiles": [],
            "swords": 0, "invulnerability": 0.0, "anim_time": 0.0,
            "arms": [], "arrows": [], "fires": [], "player_y": LH-53,
            "jump_velocity": 0.0, "grounded": True, "death_recorded": False,
            "auto_throw_timer": 0.0, "heart_timer": 8.0, "hearts": [], "candy_timer": 30.0,
            "ai_replan": 0.0, "ai_target_x": LW//2, "ai_jump_timer": -1.0,
            "mode":"solo","p2_x":LW*3//4-17,"p2_y":LH-53,"p2_lives":3,
            "p2_score":0,"p2_invulnerability":0.0,"p2_jump_velocity":0.0,
            "p2_grounded":True,"p2_ai":False,"p2_ai_replan":0.0,
            "p2_ai_target_x":LW*3//4,"p2_ai_jump_timer":-1.0,"p2_auto_throw_timer":0.0,
            "coop_endless":False,"winner":None,"run_time":0.0,
            "pvp_swords":[],"pvp_lightnings":[],"pvp_sword_cd1":0.25,
            "pvp_sword_cd2":0.65,"pvp_lightning_cd1":0.0,"pvp_lightning_cd2":0.0}

def begin_final_cutscene(g,boss):
    colors=[GOLD,ORANGE,WHITE,(178,113,255),(115,209,255)]
    particles=[]
    for _ in range(76):
        angle=random.random()*math.tau
        speed=random.uniform(18,105)
        particles.append({"x":boss["x"],"y":boss["y"]+18,
            "vx":math.cos(angle)*speed,"vy":math.sin(angle)*speed-24,
            "life":random.uniform(2.0,5.2),"color":random.choice(colors),
            "size":random.choice((1,1,2,3))})
    g["final_boss_death"]={"boss":dict(boss),"timer":0.0,"particles":particles}
    g["victory_timer"]=0.0

MODE_OPTIONS=(
    ("SOLO STORY", "solo", False, False),
    ("1V1 - LOCAL VS LOCAL", "versus", False, False),
    ("1V1 - VS ARCADE AI", "versus", True, False),
    ("CO-OP - LOCAL / NORMAL", "coop", False, False),
    ("CO-OP - VS ARCADE AI / NORMAL", "coop", True, False),
    ("CO-OP - LOCAL / ENDLESS", "coop", False, True),
    ("CO-OP - VS ARCADE AI / ENDLESS", "coop", True, True),
    ("PVP DUEL - SWORDS + RANDOM LIGHTNING", "pvp", False, False),
)
versus_bosses_enabled=False
coop_bosses_enabled=False
versus_split_enabled=True
coop_split_enabled=True

def start_mode(selection):
    g=reset_game()
    _,mode,computer,endless=MODE_OPTIONS[selection%len(MODE_OPTIONS)]
    g["mode"]=mode
    g["p2_ai"]=computer
    g["coop_endless"]=endless
    g["multiplayer_bosses"]=(versus_bosses_enabled if mode=="versus" else coop_bosses_enabled if mode=="coop" else False)
    g["split_screen"]=(versus_split_enabled if mode=="versus" else coop_split_enabled if mode=="coop" else False)
    g["player_x"]=LW//4-17
    g["p2_x"]=LW*3//4-17
    g["ai_target_x"]=g["player_x"]+17
    g["p2_ai_target_x"]=g["p2_x"]+17
    if mode=="pvp":
        g["player_x"]=LW//2-17
        g["player_y"]=LH-52
        g["p2_x"]=LW//2-17
        g["p2_y"]=36
    return g

def pvp_throw_sword(g,player_id,manual=False):
    """Throw a vertical sword toward the opposing arena."""
    if g["lives" if player_id==1 else "p2_lives"]<=0:
        return
    cd_key=f"pvp_sword_cd{player_id}"
    if manual and g[cd_key]>0.18:
        return
    own_x=g["player_x"] if player_id==1 else g["p2_x"]
    own_y=g["player_y"] if player_id==1 else g["p2_y"]
    target_x=g["p2_x"]+17 if player_id==1 else g["player_x"]+17
    target_y=g["p2_y"]+17 if player_id==1 else g["player_y"]+17
    direction=-1 if player_id==1 else 1
    flight=max(0.25,abs(target_y-(own_y+17))/330)
    vx=_ai_clamp((target_x-(own_x+17))/flight,-105,105)
    sy=own_y-8 if player_id==1 else own_y+34
    g["pvp_swords"].append({"x":own_x+17,"y":sy,"vx":vx,"vy":direction*330,"owner":player_id})
    g[cd_key]=0.92
    play_sound("sword")

def pvp_cast_lightning(g,player_id):
    if g[f"pvp_lightning_cd{player_id}"]>0 or g["lives" if player_id==1 else "p2_lives"]<=0:
        return
    target_x=random.randint(22,LW-22)
    g["pvp_lightnings"].append({"owner":player_id,"x":target_x,"warning":0.55,"active":0.0,"resolved":False})
    g[f"pvp_lightning_cd{player_id}"]=4.0
    g["message"]=f"P{player_id} CALLED THE STORM!"
    g["message_time"]=0.8
    play_sound("zap")

def update_pvp_game(g,dt):
    global state
    g["anim_time"]+=dt
    g["run_time"]+=dt
    g["invulnerability"]=max(0,g["invulnerability"]-dt)
    g["p2_invulnerability"]=max(0,g["p2_invulnerability"]-dt)
    g["message_time"]=max(0,g["message_time"]-dt)
    g["pvp_lightning_cd1"]=max(0,g["pvp_lightning_cd1"]-dt)
    g["pvp_lightning_cd2"]=max(0,g["pvp_lightning_cd2"]-dt)

    keys=pygame.key.get_pressed()
    speed=PLAYER_BASE_SPEED
    if g["lives"]>0:
        dx=int(keys[pygame.K_d])-int(keys[pygame.K_a])
        dy=int(keys[pygame.K_s])-int(keys[pygame.K_w])
        g["player_x"]=_ai_clamp(g["player_x"]+dx*speed*dt,2,LW-36)
        g["player_y"]=_ai_clamp(g["player_y"]+dy*speed*dt,LH//2+12,LH-48)
    if g["p2_lives"]>0:
        dx=int(keys[pygame.K_RIGHT])-int(keys[pygame.K_LEFT])
        dy=int(keys[pygame.K_DOWN])-int(keys[pygame.K_UP])
        g["p2_x"]=_ai_clamp(g["p2_x"]+dx*speed*dt,2,LW-36)
        g["p2_y"]=_ai_clamp(g["p2_y"]+dy*speed*dt,24,LH//2-48)

    # Keep swords flying throughout the duel; F/Enter can launch between volleys.
    for player_id in (1,2):
        key=f"pvp_sword_cd{player_id}"
        g[key]=max(0,g[key]-dt)
        if g[key]<=0:
            pvp_throw_sword(g,player_id)

    swords=[]
    for sword in g["pvp_swords"]:
        sword["x"]+=sword["vx"]*dt
        sword["y"]+=sword["vy"]*dt
        target_id=2 if sword["owner"]==1 else 1
        target_x=g["p2_x"] if target_id==2 else g["player_x"]
        target_y=g["p2_y"] if target_id==2 else g["player_y"]
        if g["p2_lives" if target_id==2 else "lives"]>0 and pygame.Rect(int(target_x),int(target_y),34,34).colliderect(pygame.Rect(int(sword["x"])-5,int(sword["y"])-9,10,18)):
            before=g["p2_lives" if target_id==2 else "lives"]
            damage_player(g,target_id,"SWORD HIT! -1 LIFE")
            after=g["p2_lives" if target_id==2 else "lives"]
            if after<before:
                g["score" if target_id==2 else "p2_score"]+=1
                play_sound("hit")
        elif -24<sword["y"]<LH+24:
            swords.append(sword)
    g["pvp_swords"]=swords

    lightning_left=[]
    for bolt in g["pvp_lightnings"]:
        if bolt["warning"]>0:
            bolt["warning"]-=dt
            if bolt["warning"]<=0:
                bolt["warning"]=0.0
                bolt["active"]=0.22
                play_sound("zap")
        elif bolt["active"]>0:
            if not bolt["resolved"]:
                target_id=2 if bolt["owner"]==1 else 1
                tx=g["p2_x"] if target_id==2 else g["player_x"]
                ty=g["p2_y"] if target_id==2 else g["player_y"]
                target_lives=g["p2_lives"] if target_id==2 else g["lives"]
                if target_lives>0 and abs((tx+17)-bolt["x"])<31:
                    before=target_lives
                    damage_player(g,target_id,"LIGHTNING STRIKE! -1 LIFE")
                    after=g["p2_lives"] if target_id==2 else g["lives"]
                    if after<before:
                        g["score" if target_id==2 else "p2_score"]+=1
                bolt["resolved"]=True
            bolt["active"]-=dt
            if bolt["active"]>0:
                lightning_left.append(bolt)
    g["pvp_lightnings"]=lightning_left

    if g["lives"]<=0 or g["p2_lives"]<=0:
        g["winner"]=2 if g["lives"]<=0 and g["p2_lives"]>0 else 1 if g["p2_lives"]<=0 and g["lives"]>0 else None
        state="gameover"
        return

def draw_pvp_screen(g):
    canvas.fill((13,12,31))
    rect((18,25,53),0,0,LW,LH//2)
    rect((47,20,42),0,LH//2,LW,LH//2)
    for x in range(12,LW,32):
        rect((41,53,86),x,35+(x%5)*6,2,2)
        rect((86,46,68),x+13,LH//2+22+(x%4)*7,2,2)
    rect((181,104,83),0,LH//2-2,LW,4)
    text("P2  ARROWS + RIGHT SHIFT",LW//2,10,SMALL,(145,205,255),True)
    text(f"LIVES {g['p2_lives']}   SCORE {g['p2_score']}",LW//2,23,SMALL,WHITE,True)
    text(f"P1  WASD + LEFT SHIFT",LW//2,LH-12,SMALL,(255,176,100),True)
    text(f"LIVES {g['lives']}   SCORE {g['score']}",LW//2,LH-25,SMALL,WHITE,True)
    text("AUTO SWORDS  |  F / ENTER = EXTRA THROW",LW//2,LH//2,SMALL,GOLD,True)
    jack(int(g["p2_x"]),int(g["p2_y"]),palette="blue")
    jack(int(g["player_x"]),int(g["player_y"]))
    for sword in g["pvp_swords"]:
        sx,sy=int(sword["x"]),int(sword["y"])
        direction=-1 if sword["owner"]==1 else 1
        tip=sy+direction*10
        base=sy-direction*7
        pygame.draw.polygon(canvas,(236,229,204),[(sx,tip),(sx-4,base),(sx+4,base)])
        rect((155,109,79),sx-1,base,3,6)
        rect(GOLD,sx-6 if direction<0 else sx-5,base+4,12,2)
    for bolt in g["pvp_lightnings"]:
        x=int(bolt["x"])
        top,bottom=(19,LH//2-4) if bolt["owner"]==1 else (LH//2+4,LH-18)
        if bolt["warning"]>0:
            draw_storm_cloud(x,top+8,False,g["anim_time"])
            for yy in range(top+28,bottom,11):
                rect((255,157,94) if (yy//11)%2 else GOLD,x-2,yy,4,5)
            text("DANGER!",x,min(bottom-2,top+32),SMALL,GOLD,True)
        elif bolt["active"]>0:
            points=[(x,top+18),(x-7,top+32),(x+6,top+43),(x-6,top+58),(x+5,bottom-3)]
            pygame.draw.lines(canvas,(255,244,166),False,points,6)
            pygame.draw.lines(canvas,WHITE,False,points,2)
    if g["message_time"]>0:
        rect((13,9,24),LW//2-86,LH//2+8,172,17)
        text(g["message"],LW//2,LH//2+16,SMALL,GOLD,True)

def launch_selected_mode():
    global game,state
    game=start_mode(menu_selection)
    state="playing"
    set_stage_music(1,game["mode"],game["coop_endless"])

SAVE_PATH=(Path(sys.executable).resolve().with_name("halloween_save.json") if getattr(sys,"frozen",False) else Path(__file__).with_name("halloween_save.json"))
ACHIEVEMENTS=[
    ("sweet_tooth","Sweet Tooth","Collect 100 candies"),
    ("candy_king","Candy King","Collect 500 candies across runs"),
    ("stage_30","The First Showdown","Reach stage 30"),
    ("stage_60","Halfway to Doom","Reach stage 60"),
    ("first_boss","Monster Hunter","Defeat any boss"),
    ("all_bosses","Boss Breaker","Defeat all four bosses"),
    ("three_lives","Untouchable","Beat the game without losing a life"),
    ("three_deaths","Back from the Grave","Get a game over three times"),
    ("platinum","PLATINUM","Unlock every other achievement"),
]
ACHIEVEMENT_IDS=[item[0] for item in ACHIEVEMENTS]

def load_save():
    default={"unlocked":[],"total_candy":0,"max_stage":1,"bosses":[],"deaths":0}
    try:
        saved=json.loads(SAVE_PATH.read_text(encoding="utf-8"))
        if isinstance(saved,dict):
            for key,value in default.items():
                saved.setdefault(key,value)
            if not isinstance(saved["unlocked"],list): saved["unlocked"]=[]
            if not isinstance(saved["bosses"],list): saved["bosses"]=[]
            for key in ("total_candy","max_stage","deaths"):
                try: saved[key]=max(0,int(saved[key]))
                except (ValueError,TypeError): saved[key]=default[key]
            return saved
    except (OSError,ValueError,TypeError):
        pass
    return default

save_data=load_save()

def save_progress():
    try:
        SAVE_PATH.write_text(json.dumps(save_data,indent=2),encoding="utf-8")
    except OSError:
        pass

def check_achievements(g):
    unlocked=set(save_data["unlocked"])
    conditions={
        "sweet_tooth":save_data["total_candy"]>=100,
        "candy_king":save_data["total_candy"]>=500,
        "stage_30":save_data["max_stage"]>=30,
        "stage_60":save_data["max_stage"]>=60,
        "first_boss":len(save_data["bosses"])>=1,
        "all_bosses":all(phase in save_data["bosses"] for phase in BOSS_ORDER),
        "three_lives":g.get("victory") and g["lives"]==3,
        "three_deaths":save_data["deaths"]>=3,
    }
    new=[]
    for ach_id,title,description in ACHIEVEMENTS[:-1]:
        if conditions.get(ach_id,False) and ach_id not in unlocked:
            save_data["unlocked"].append(ach_id); unlocked.add(ach_id); new.append(title)
    if all(ach_id in unlocked for ach_id,_,_ in ACHIEVEMENTS[:-1]) and "platinum" not in unlocked:
        save_data["unlocked"].append("platinum"); new.append("PLATINUM!")
    if new:
        g["message"]="ACHIEVEMENT: "+new[0]
        g["message_time"]=2.4
        save_progress()

def draw_achievements():
    background()
    rect((16,12,31),25,27,LW-50,LH-54)
    rect(GOLD,25,27,LW-50,2)
    text("ACHIEVEMENTS",LW//2,44,BIG,GOLD,True)
    y=68
    got=set(save_data["unlocked"])
    for ach_id,title,description in ACHIEVEMENTS:
        color=GOLD if ach_id in got else GRAY
        mark="[X]" if ach_id in got else "[ ]"
        text(f"{mark} {title}",43,y,FONT,color)
        text(description,55,y+12,SMALL,WHITE if ach_id in got else GRAY)
        y+=20
    text(f"PLATINUM: {len(got)}/{len(ACHIEVEMENTS)}",LW//2,LH-41,FONT,MINT,True)
    text("ESC = BACK",LW//2,LH-25,SMALL,WHITE,True)

def hud(g):
    rect((15,12,30),0,0,LW,25)
    text(f"CANDY: {g['score']}",8,7,FONT,GOLD)
    text(f"STAGE: {g['level']}",112,7,FONT,MINT)
    text("LIVES:",205,7,FONT,WHITE)
    for i in range(3): rect(RED if i < g["lives"] else (70,54,70),249+i*12,8,8,8)
    text(f"SWEET:{max(0,math.ceil(g['candy_timer']))}s" if g["boss"] is None else "SWEET:--",282,7,SMALL,RED if g["candy_timer"]<=8 else GOLD)
    text("AUTO" if autoplay else "A-D",352,7,SMALL,MINT if autoplay else GRAY)

def menu_button(box,label,selected=False,hover=False):
    x,y,w,h=box
    base=(76,37,63) if selected or hover else (34,24,52)
    rect((9,6,20),x+2,y+3,w,h)
    rect(base,x,y,w,h)
    rect(ORANGE if selected else (101,70,117),x,y,w,2)
    rect((147,92,103) if hover else (72,53,89),x,y+h-2,w,2)
    rect((255,182,75) if selected else (118,80,93),x,y,2,h)
    text(label,x+w//2,y+h//2,MENU_FONT,WHITE if selected or hover else GRAY,True)

def menu():
    background()
    now=pygame.time.get_ticks()
    for bx,by in ((50,90),(340,104),(365,76)):
        rect(BLACK,bx,by,16,5); rect(BLACK,bx-5,by-4,7,6); rect(BLACK,bx+14,by-4,7,6)
        rect(RED,bx+3,by+1,2,2); rect(RED,bx+11,by+1,2,2)
    text("HALLOWEEN DROP!",LW//2+2,43,BIG,(86,34,52),True)
    text("HALLOWEEN DROP!",LW//2,40,BIG,ORANGE,True)
    text("TRICK OR TREAT ARCADE",LW//2,61,SMALL,MINT,True)
    bounce=int(math.sin(now/250)*2)
    jack(LW//2-17,88+bounce)
    mouse=pygame.mouse.get_pos()
    mx=int(mouse[0]*LW/max(1,screen.get_width()))
    my=int(mouse[1]*LH/max(1,screen.get_height()))
    if menu_page=="home":
        rect((13,10,27),52,141,LW-104,131)
        rect((111,74,111),52,141,LW-104,2)
        text(f"READY: {MODE_OPTIONS[menu_selection][0]}",LW//2,153,SMALL,GOLD,True)
        buttons=((100,166,200,26),(100,200,200,26),(100,234,200,26))
        labels=("PLAY","CHOOSE MODES","ACHIEVEMENTS")
        for index,(box,label) in enumerate(zip(buttons,labels)):
            hover=pygame.Rect(box).collidepoint(mx,my)
            menu_button(box,label,home_selection==index,hover)
        text("ARROWS + ENTER OR CLICK",LW//2,279,SMALL,GRAY,True)
    else:
        rect((13,10,27),18,28,LW-36,237)
        rect((111,74,111),18,28,LW-36,2)
        text("CHOOSE YOUR MODE",LW//2,40,MENU_FONT,GOLD,True)
        for index,(label,_,_,_) in enumerate(MODE_OPTIONS):
            y=54+index*12
            box=(35,y-5,LW-70,12)
            hover=pygame.Rect(box).collidepoint(mx,my)
            if index==menu_selection or hover:
                rect((61,31,48),*box)
                rect(ORANGE,35,y-5,2,12)
            text(label,LW//2,y,SMALL,WHITE if index==menu_selection else GRAY,True)
        text(f"1V1  BOSS [B: {'ON' if versus_bosses_enabled else 'OFF'}]",103,151,SMALL,GOLD if versus_bosses_enabled else GRAY,True)
        text(f"SPLIT [V: {'ON' if versus_split_enabled else 'OFF'}]",293,151,SMALL,MINT if versus_split_enabled else GRAY,True)
        text(f"CO-OP BOSS [O: {'ON' if coop_bosses_enabled else 'OFF'}]",106,166,SMALL,GOLD if coop_bosses_enabled else GRAY,True)
        text(f"SPLIT [C: {'ON' if coop_split_enabled else 'OFF'}]",293,166,SMALL,MINT if coop_split_enabled else GRAY,True)
        start_box=(84,185,232,24)
        back_box=(145,216,110,20)
        menu_button(start_box,"START MODE",True,pygame.Rect(start_box).collidepoint(mx,my))
        menu_button(back_box,"BACK",False,pygame.Rect(back_box).collidepoint(mx,my))
        if MODE_OPTIONS[menu_selection][1]=="pvp":
            text("P1 WASD / F + LSHIFT  |  P2 ARROWS / ENTER + RSHIFT",LW//2,247,SMALL,WHITE,True)
            text("SWORDS AUTO-FIRE  |  SHIFT CALLS RANDOM LIGHTNING",LW//2,259,SMALL,GOLD,True)
        else:
            text("P1 WASD + SPACE/W  |  P2 ARROWS + UP",LW//2,247,SMALL,WHITE,True)
            text("CLICK A MODE, THEN START  |  ESC TO BACK",LW//2,259,SMALL,GRAY,True)

def game_screen(g):
    background()
    hud(g)
    if g["boss"]:
        draw_boss_scene(g)
    else:
        for item in g["items"]:
            draw_item(item)
    for heart in g["hearts"]:
        draw_heart(heart["x"],heart["y"])
    player_y=g["player_y"]
    if g["invulnerability"] <= 0 or int(g["anim_time"]*12)%2 == 0:
        jack(int(g["player_x"]),player_y + (1 if int(g["anim_time"]*12)%2 else 0))
    if g["message_time"] > 0:
        message_y=LH-32 if g["boss"] else 46
        rect((16,12,31),LW//2-100,message_y-9,200,18)
        text(g["message"],LW//2,message_y,SMALL,GOLD,True)

def multiplayer_game_screen(g):
    if g["mode"]=="pvp":
        draw_pvp_screen(g)
        return
    background()
    mode=g["mode"]
    versus=mode=="versus"
    if versus:
        if g.get("split_screen",True):
            rect((112,70,87),LW//2-1,24,2,LH-24)
        text("P1",LW//4,13,FONT,PINK,True)
        text(f"{g['score']}  HP {g['lives']}",LW//4,26,SMALL,WHITE,True)
        text("P2  CPU" if g["p2_ai"] else "P2",LW*3//4,13,FONT,BLUE,True)
        text(f"{g['p2_score']}  HP {g['p2_lives']}",LW*3//4,26,SMALL,WHITE,True)
        text(f"STAGE {g['level']}",LW//2,13,SMALL,GOLD,True)
    else:
        if g.get("split_screen",False):
            rect((86,61,105),LW//2-1,24,2,LH-24)
        text(f"CO-OP{' ENDLESS' if g['coop_endless'] else ''}",8,8,FONT,GOLD)
        text(f"CANDY {g['score']}",130,8,FONT,MINT)
        text(f"STAGE {g['level']}",246,8,FONT,WHITE)
        text(f"P1:{g['lives']}  P2:{g['p2_lives']}",344,8,SMALL,BLUE)
    if g.get("boss"):
        draw_boss_scene(g)
    else:
        for item in g["items"]:
            draw_item(item)
    for heart in g["hearts"]:
        draw_heart(heart["x"],heart["y"])
    if g["lives"]>0 and (g["invulnerability"]<=0 or int(g["anim_time"]*12)%2==0):
        jack(int(g["player_x"]),int(g["player_y"]))
    if g["p2_lives"]>0 and (g["p2_invulnerability"]<=0 or int(g["anim_time"]*12)%2==0):
        jack(int(g["p2_x"]),int(g["p2_y"]),palette="blue")
    if g["message_time"]>0:
        rect((16,12,31),LW//2-105,LH-31,210,17)
        text(g["message"],LW//2,LH-23,SMALL,GOLD,True)

def multiplayer_game_over(g):
    background()
    if g["mode"] in ("versus","pvp"):
        if g.get("winner")==1:
            title,caption="PLAYER 1 WINS!","The last pumpkin standing!"
        elif g.get("winner")==2:
            title,caption="PLAYER 2 WINS!","The last pumpkin standing!"
        else:
            title,caption="DRAW!","Both players fell together."
    else:
        title="TEAM DEFEATED"
        caption="Both players are out of lives."
    jack(LW//2-17,112)
    rect((16,12,31),42,161,LW-84,104)
    rect(ORANGE,42,161,LW-84,2)
    text(title,LW//2,183,BIG,GOLD if g["winner"] else RED,True)
    text(caption,LW//2,211,FONT,WHITE,True)
    text(f"P1 {g['score']}  |  P2 {g['p2_score']}  |  STAGE {g['level']}",LW//2,231,SMALL,MINT,True)
    text("ENTER = PLAY AGAIN   ESC = MENU",LW//2,250,SMALL,GOLD,True)

def multiplayer_victory_screen(g):
    background()
    jack(LW//2-25,112); jack(LW//2+4,112)
    rect((16,12,31),35,160,LW-70,105)
    rect(GOLD,35,160,LW-70,2)
    text("TEAM SAVED HALLOWEEN!",LW//2,182,BIG,GOLD,True)
    text("You survived all 120 stages together!",LW//2,211,FONT,WHITE,True)
    text(f"TEAM CANDY: {g['score']}",LW//2,232,SMALL,MINT,True)
    text("ENTER = PLAY AGAIN   ESC = MENU",LW//2,250,SMALL,GOLD,True)

def game_over(g):
    background()
    jack(LW//2-17,124)
    rect((16,12,31),55,165,LW-110,94)
    rect((130,57,76),55,165,LW-110,2)
    text("GAME OVER",LW//2,187,BIG,RED,True)
    text(f"You collected {g['score']} candy!",LW//2,215,FONT,WHITE,True)
    text("ENTER = PLAY AGAIN   A = ACHIEVEMENTS",LW//2,240,SMALL,GOLD,True)

def pause_screen():
    shade=pygame.Surface((LW,LH),pygame.SRCALPHA)
    shade.fill((5,3,14,190))
    canvas.blit(shade,(0,0))
    box_w,box_h=250,112
    box_x=(LW-box_w)//2; box_y=(LH-box_h)//2
    rect((18,12,32),box_x,box_y,box_w,box_h)
    rect(ORANGE,box_x,box_y,box_w,2)
    rect((101,54,70),box_x,box_y+box_h-2,box_w,2)
    text("PAUSED",LW//2,box_y+18,BIG,GOLD,True)
    text("ESC / ENTER  -  RESUME",LW//2,box_y+56,FONT,WHITE,True)
    text("Q  -  MAIN MENU",LW//2,box_y+78,FONT,MINT,True)

def victory_screen(g):
    background()
    jack(LW//2-17,113)
    rect((16,12,31),42,163,LW-84,104)
    rect(GOLD,42,163,LW-84,2)
    text("YOU SAVED HALLOWEEN!",LW//2,185,BIG,GOLD,True)
    text("The Skeleton King has fallen!",LW//2,215,FONT,WHITE,True)
    text("You conquered all 120 stages!",LW//2,237,FONT,MINT,True)
    text("ENTER = PLAY AGAIN   A = ACHIEVEMENTS",LW//2,255,SMALL,GOLD,True)

def final_boss_cutscene(g):
    scene=g.get("final_boss_death")
    if not scene:
        background()
        return
    timer=scene["timer"]
    background()
    rect((7,5,16),0,0,LW,LH)
    cx,cy=LW//2,151
    for radius,color,width in ((54,(47,26,91),5),(40,(103,58,157),4),(26,(198,117,255),3)):
        pygame.draw.circle(canvas,color,(cx,cy),max(1,radius+int(math.sin(timer*3+radius)*3)),width)
    pygame.draw.ellipse(canvas,(23,13,49),(cx-37,cy-58,74,116))
    pygame.draw.ellipse(canvas,(88,44,130),(cx-25,cy-47,50,94),3)
    if timer<2.3:
        dead=dict(scene["boss"])
        dead["x"]=cx+math.sin(timer*7)*10
        dead["y"]=55+timer*25
        draw_boss(dead,timer*8)
        if timer<1.4 and int(timer*18)%2==0:
            rect(WHITE,0,0,LW,LH)
    if timer>1.2:
        beam_h=min(LH,int((timer-1.2)*105))
        rect((57,35,118),cx-12,LH-36-beam_h,24,beam_h)
        rect((157,106,224),cx-5,LH-36-beam_h,10,beam_h)
        rect(WHITE,cx-2,LH-36-beam_h,4,beam_h)
        for offset in (-1,1):
            pygame.draw.arc(canvas,(203,146,255),(cx-50,cy-42,100,84),timer+offset,timer+offset+2.2,2)
    for particle in scene["particles"]:
        if particle["life"]<=0:
            continue
        brightness=min(1.0,particle["life"]*0.7)
        color=tuple(int(channel*brightness) for channel in particle["color"])
        rect(color,particle["x"],particle["y"],particle["size"],particle["size"])
    if timer<1.5:
        caption="SKELETON DEFEATED!"
    elif timer<3.8:
        caption="THE CURSE IS BREAKING..."
    elif timer<5.8:
        caption="ANCIENT LIGHT RISES"
    else:
        caption="HALLOWEEN IS SAVED!"
        jack(cx-17,LH-59)
    rect((8,5,18),0,0,LW,27)
    rect((8,5,18),0,LH-27,LW,27)
    text("FINAL BOSS  /  SKELETON",LW//2,12,SMALL,GOLD,True)
    text(caption,LW//2,LH-13,MENU_FONT,WHITE,True)

def update_final_cutscene(g,dt):
    scene=g["final_boss_death"]
    scene["timer"]+=dt
    for particle in scene["particles"]:
        particle["x"]+=particle["vx"]*dt
        particle["y"]+=particle["vy"]*dt
        particle["vy"]-=8*dt
        particle["life"]-=dt

def _ai_overlap(ax,ay,aw,ah,bx,by,bw,bh):
    return ax < bx+bw and ax+aw > bx and ay < by+bh and ay+ah > by

def _ai_clamp(value,low,high):
    return max(low,min(high,value))

def arcade_ai_decision(g):
    """Receding-horizon arcade controller: predict collisions, pickups and boss attacks."""
    step=0.04
    horizon=2.40
    steps=int(horizon/step)
    player_speed=min(MAX_PLAYER_SPEED,PLAYER_BASE_SPEED+max(0,g["level"]-PLAYER_ACCEL_LEVEL+1)*PLAYER_SPEED_STEP)
    start_x=float(g["player_x"])
    start_y=float(g["player_y"])
    player_center=start_x+17
    move_min,move_max=g.get("ai_bounds",(2,LW-36))
    center_min,center_max=move_min+17,move_max+17
    boss=g["boss"]
    items=g["items"] if boss is None else []
    hearts=g["hearts"] if g["lives"]<MAX_LIVES else []
    falling_swords=g["falling_swords"] if boss and g["swords"]<3 else []
    targets=set(range(int(center_min),int(center_max)+1,24))
    targets.add(round(_ai_clamp(player_center,center_min,center_max)))
    for item in items:
        if item["y"]<LH-20:
            targets.add(round(item["x"]+11))
        if item["kind"] in TRICKS and item["y"]<LH+18:
            # Try lanes on either side as well as the exact hitbox lane.
            targets.add(round(item["x"]-25))
            targets.add(round(item["x"]+47))
    for heart in hearts:
        targets.add(round(heart["x"]+10))
    for sword in falling_swords:
        targets.add(round(sword["x"]+3))
    if boss and boss["name"] in ("GHOST","ZOMBIE","SKELETON") and boss["beam_mode"]=="warning":
        targets.update((round(boss["beam_x"]-46),round(boss["beam_x"]+46)))
    if boss and boss["name"]=="SKELETON" and boss.get("arrow_warning",0)>0:
        targets.update((round(boss["arrow_target_x"]-48),round(boss["arrow_target_x"]+48)))
    if boss and boss["name"]=="ZOMBIE" and boss.get("arm_warning",0)>0:
        targets.update((round(boss["arm_target_x"]-48),round(boss["arm_target_x"]+48)))
    targets={int(_ai_clamp(x,center_min,center_max)) for x in targets}

    jump_options=[None]
    trick_is_near=any(item["kind"] in TRICKS and item["y"]>LH-250 and item["y"]<LH+18
                      for item in items)
    if g["grounded"] and (boss or trick_is_near):
        jump_count=11 if boss else 8
        jump_options += [round(t,2) for t in (i*0.12 for i in range(jump_count)) if t<horizon]
    best_score=-float("inf")
    best_target=player_center
    best_jump=None
    invuln=g["invulnerability"]

    def wolf_x_at(t):
        if boss["charge_active"]:
            return boss["x"]+boss["vx"]*t
        delay=max(0,boss["charge_timer"])
        if t<delay:
            return _ai_clamp(boss["x"]+boss["vx"]*t,50,LW-50)
        direction=1 if boss["x"]<LW/2 else -1
        return (-35 if direction>0 else LW+35)+(245*direction)*(t-delay)

    def wolf_y_at(t):
        floor_y=LH-85
        if boss["charge_active"]:
            return floor_y+(boss["y"]-floor_y)*math.exp(-7*t)
        delay=max(0,boss["charge_timer"])
        if t<delay:
            return 58+(boss["y"]-58)*math.exp(-5*t)
        charge_age=t-delay
        return floor_y+(58-floor_y)*math.exp(-7*charge_age)

    def ghost_dive_y_at(t,dive_at=0.0,start_y=None):
        start_y=boss["y"] if start_y is None else start_y
        age=max(0,t-dive_at)
        floor_y=LH-82
        # update_boss moves the Ghost 32% toward the floor every 40 ms
        # prediction step; match that discrete motion instead of smoothing it
        # too slowly, or the AI underestimates the lower hitbox during dives.
        return floor_y+(start_y-floor_y)*(0.68**(age/step))

    def boss_x_at(t):
        if boss["name"]=="WEREWOLF":
            return wolf_x_at(t)
        raw=boss["x"]+boss["vx"]*t
        span=LW-130
        if span<=0:
            return LW/2
        phase=(raw-65)%(2*span)
        return 65+(phase if phase<=span else 2*span-phase)

    for target in targets:
        for jump_at in jump_options:
            px=start_x
            py=start_y
            vy=float(g["jump_velocity"])
            grounded=bool(g["grounded"])
            path=[]
            jumped=False
            for index in range(steps):
                t=(index+1)*step
                old_x=px
                destination=_ai_clamp(target-17,move_min,move_max)
                delta=destination-px
                px+=max(-player_speed*step,min(player_speed*step,delta))
                px=_ai_clamp(px,move_min,move_max)
                if jump_at is not None and not jumped and grounded and t+0.0001>=jump_at:
                    vy=float(JUMP_VELOCITY)
                    grounded=False
                    jumped=True
                if not grounded:
                    vy+=740*step
                    py+=vy*step
                    if py>=LH-53:
                        py=LH-53
                        vy=0
                        grounded=True
                # Skeleton flame columns stop the player; model that wall so the planner
                # does not repeatedly aim through a lane it cannot cross.
                if boss and boss["name"]=="SKELETON":
                    for fire in g["fires"]:
                        if py>=LH-84 and abs((px+17)-fire["x"])<23:
                            if old_x+17<fire["x"]:
                                px=max(2,fire["x"]-36)
                            else:
                                px=min(LW-36,fire["x"]+20)
                path.append((t,px,py,grounded))

            score=-abs(target-player_center)*0.025
            if jumped:
                score-=7.0
            picked_candy=set()
            hit_tricks=set()
            picked_hearts=set()
            picked_swords=set()

            for index,item in enumerate(items):
                if item["y"]>LH+12:
                    continue
                for t,px,py,_ in path:
                    iy=item["y"]+item["speed"]*t
                    exact_hit=_ai_overlap(px,py,34,34,item["x"],iy,22,22)
                    # Match the real collision rectangles first, then add only a
                    # small AI safety margin to account for movement between
                    # 40 ms prediction samples.
                    safe_hit=_ai_overlap(px-4,py-4,42,42,item["x"],iy,22,22)
                    if (exact_hit if item["kind"] in SWEETS else safe_hit):
                        if item["kind"] in SWEETS:
                            points=2 if item["kind"] in ("urso","pirulito") else 1
                            urgency=1.0+max(0,12-g["candy_timer"])*0.035
                            near_floor=0.70+1.30*_ai_clamp(iy/max(1,LH),0.0,1.0)
                            near_player=1.0+0.70/(1.0+abs(item["x"]+11-player_center)/42.0)
                            score+=points*72*urgency*near_floor*near_player/(1+0.16*t)
                            picked_candy.add(index)
                        else:
                            # Classify by the object's kind, then use its real
                            # rectangle against Jack's predicted rectangle. A
                            # trick collision is far more costly than any candy.
                            if t>=invuln:
                                # Survival is the top objective. A true hitbox
                                # overlap rules out this route decisively; a
                                # near miss still has a meaningful cost so the
                                # planner does not greedily chase candy beside
                                # a trick.
                                score-=30000 if exact_hit else 1400
                            else:
                                score-=18
                            hit_tricks.add(index)
                        break

            for index,heart in enumerate(hearts):
                for t,px,py,_ in path:
                    hy=heart["y"]+heart.get("speed",72)*t
                    if _ai_overlap(px,py,34,34,heart["x"],hy,20,18):
                        score+=(300+max(0,2-g["lives"])*90)/(1+0.10*t)
                        picked_hearts.add(index)
                        break

            if boss:
                for index,sword in enumerate(falling_swords):
                    for t,px,py,_ in path:
                        sy=sword["y"]+sword.get("speed",110)*t
                        if _ai_overlap(px,py,34,34,sword["x"]-5,sy-3,16,25):
                            score+=175/(1+0.10*t)
                            picked_swords.add(index)
                            break

                if boss["name"]=="WEREWOLF":
                    for t,px,py,_ in path:
                        wolf_hit_x=wolf_x_at(t)-17
                        wolf_hit_y=wolf_y_at(t)+23
                        if _ai_overlap(px,py,34,34,wolf_hit_x,wolf_hit_y,34,28):
                            score-=9000 if t>=invuln else 35
                elif boss["name"] in ("GHOST","ZOMBIE","SKELETON"):
                    beam_x=boss["beam_x"]
                    if boss["beam_mode"]=="warning":
                        strike_start=max(0,boss["beam_timer"])
                        strike_end=strike_start+0.36
                    elif boss["beam_mode"]=="strike":
                        strike_start=0.0
                        strike_end=max(0,boss["beam_timer"])
                    else:
                        # Its next lightning lane is intentionally random; wait
                        # for the visible warning instead of guessing a player lock.
                        strike_start=horizon+1.0
                        strike_end=strike_start+0.36
                    for t,px,py,_ in path:
                        # The beam is 36 px wide and Jack is 34 px wide, so
                        # their centers can overlap by as much as 35 px. Add a
                        # small reaction margin for the next planner update.
                        if strike_start<=t<=strike_end and abs(px+17-beam_x)<39:
                            score-=9000 if t>=invuln else 35
                    if boss["name"]=="GHOST" and boss.get("dive_active"):
                        for t,px,py,_ in path:
                            bx=boss["dive_x"]+boss["dive_dir"]*235*t
                            by=ghost_dive_y_at(t)+6
                            if _ai_overlap(px,py,34,34,bx-17,by,34,40):
                                score-=9000 if t>=invuln else 35
                    elif boss["name"]=="GHOST" and boss.get("dive_timer",99)<horizon:
                        dive_at=max(0,boss["dive_timer"])
                        dive_i=min(steps-1,max(0,int(dive_at/step)))
                        dive_start=LW+35.0
                        dive_dir=-1
                        for t,px,py,_ in path[dive_i:]:
                            bx=dive_start+dive_dir*235*(t-dive_at)
                            age=t-dive_at
                            by=(LH-82+(58.0-(LH-82))*(0.68**(age/step)))+6
                            if _ai_overlap(px,py,34,34,bx-17,by,34,40):
                                score-=9000 if t>=invuln else 35
                if boss["name"]=="ZOMBIE":
                    for arm in g["arms"]:
                        for t,px,py,_ in path:
                            ax=arm["x"]+arm["vx"]*t
                            ay=arm["y"]+arm["vy"]*t
                            if _ai_overlap(px-8,py-8,50,50,ax,ay,17,15):
                                score-=9000 if t>=invuln else 35
                                break
                    if boss.get("arm_warning",0)>0:
                        launch=max(0,boss["arm_warning"])
                        target_x=boss["arm_target_x"]
                    else:
                        cooldown=max(0,boss["arm_timer"])
                        launch=cooldown+0.88
                        cooldown_i=min(steps-1,max(0,int(launch/step)))
                        target_x=path[cooldown_i][1]+17
                    if launch<horizon:
                        launch_i=min(steps-1,max(0,int(launch/step)))
                        bx=boss_x_at(launch)
                        dx=_ai_clamp((target_x-bx)/1.65,-110,110)
                        for t,px,py,_ in path[launch_i:]:
                            flight=max(0,t-launch)
                            ax=bx+dx*flight
                            ay=boss["y"]+40+92*flight
                            ax2=bx-8-dx*0.55*flight
                            ay2=boss["y"]+40+100*flight
                            if (_ai_overlap(px-8,py-8,50,50,ax,ay,17,15)
                                    or _ai_overlap(px-8,py-8,50,50,ax2,ay2,17,15)):
                                score-=9000 if t>=invuln else 35
                                break
                if boss["name"]=="SKELETON":
                    for arrow in g["arrows"]:
                        for t,px,py,_ in path:
                            ax=arrow["x"]+arrow["vx"]*t
                            ay=arrow["y"]+arrow["vy"]*t
                            if _ai_overlap(px-6,py-6,46,46,ax,ay,22,10):
                                score-=9000 if t>=invuln else 35
                                break
                    if boss.get("arrow_warning",0)>0:
                        launch=max(0,boss["arrow_warning"])
                        target_x=boss["arrow_target_x"]
                    else:
                        launch=max(0,boss["arrow_timer"])+0.82
                        launch_i=min(steps-1,max(0,int(launch/step)))
                        target_x=path[launch_i][1]+17
                    if launch<horizon:
                        launch_i=min(steps-1,max(0,int(launch/step)))
                        bx=boss_x_at(launch)
                        dx=_ai_clamp((target_x-bx)/1.12,-90,90)
                        for t,px,py,_ in path[launch_i:]:
                            flight=max(0,t-launch)
                            ax=bx+12+dx*flight
                            ay=boss["y"]+22+130*flight
                            if _ai_overlap(px-6,py-6,46,46,ax,ay,22,10):
                                score-=9000 if t>=invuln else 35
                                break

            # Look just beyond the full simulation window to commit to a safe lane
            # early enough for fast objects and distant heart drops.
            end_x=path[-1][1]
            extra=1.25
            for index,item in enumerate(items):
                if index in picked_candy or item["kind"] not in SWEETS:
                    continue
                intercept=(LH-53-item["y"]-22)/max(1,item["speed"])
                if horizon<intercept<=horizon+extra:
                    projected=end_x+_ai_clamp((target-17-end_x),-player_speed*(intercept-horizon),player_speed*(intercept-horizon))
                    if abs((projected+17)-(item["x"]+11))<28:
                        points=2 if item["kind"] in ("urso","pirulito") else 1
                        near_player=1.0+0.70/(1.0+abs(item["x"]+11-player_center)/42.0)
                        near_floor=0.7+1.3*_ai_clamp(item["y"]/max(1,LH),0.0,1.0)
                        score+=points*52*near_player*near_floor/(1+0.20*(intercept-horizon))
            for index,item in enumerate(items):
                if index in hit_tricks or item["kind"] not in TRICKS:
                    continue
                intercept=(LH-53-item["y"]-22)/max(1,item["speed"])
                if horizon<intercept<=horizon+extra:
                    projected=end_x+_ai_clamp((target-17-end_x),-player_speed*(intercept-horizon),player_speed*(intercept-horizon))
                    horizontal_gap=abs((projected+17)-(item["x"]+11))
                    if horizontal_gap<28:
                        score-=30000 if intercept<=horizon+0.15 else 2200
                    elif horizontal_gap<36:
                        score-=900
            for index,heart in enumerate(hearts):
                if index in picked_hearts:
                    continue
                intercept=(LH-53-heart["y"]-18)/max(1,heart.get("speed",72))
                if horizon<intercept<=horizon+extra:
                    projected=end_x+_ai_clamp((target-17-end_x),-player_speed*(intercept-horizon),player_speed*(intercept-horizon))
                    if abs((projected+17)-(heart["x"]+10))<30:
                        score+=130+max(0,2-g["lives"])*40
            if score>best_score:
                best_score=score
                best_target=target
                best_jump=jump_at if jumped else None

    return best_target,best_jump
game=reset_game()
state="menu"
autoplay=False
menu_selection=0
menu_page="home"
home_selection=0
running=True
while running:
    dt=min(clock.tick(60)/1000.0,0.04)
    for event in pygame.event.get():
        if event.type==pygame.QUIT:
            running=False
        elif event.type==pygame.MOUSEBUTTONDOWN and event.button==1 and state=="menu":
            mx=int(event.pos[0]*LW/max(1,screen.get_width()))
            my=int(event.pos[1]*LH/max(1,screen.get_height()))
            if menu_page=="home":
                home_boxes=((100,166,200,26),(100,200,200,26),(100,234,200,26))
                for index,box in enumerate(home_boxes):
                    if pygame.Rect(box).collidepoint(mx,my):
                        home_selection=index
                        if index==0:
                            launch_selected_mode()
                        elif index==1:
                            menu_page="modes"
                        else:
                            state="achievements"
                        break
            else:
                for index in range(len(MODE_OPTIONS)):
                    if pygame.Rect(35,49+index*12,LW-70,12).collidepoint(mx,my):
                        menu_selection=index
                        break
                if pygame.Rect(30,144,176,16).collidepoint(mx,my):
                    versus_bosses_enabled=not versus_bosses_enabled
                elif pygame.Rect(208,144,162,16).collidepoint(mx,my):
                    versus_split_enabled=not versus_split_enabled
                elif pygame.Rect(30,159,176,16).collidepoint(mx,my):
                    coop_bosses_enabled=not coop_bosses_enabled
                elif pygame.Rect(208,159,162,16).collidepoint(mx,my):
                    coop_split_enabled=not coop_split_enabled
                elif pygame.Rect(84,185,232,24).collidepoint(mx,my):
                    launch_selected_mode()
                elif pygame.Rect(145,216,110,20).collidepoint(mx,my):
                    menu_page="home"
        elif event.type==pygame.KEYDOWN:
            if event.key==pygame.K_F11:
                fullscreen=not fullscreen
                if fullscreen:
                    screen=pygame.display.set_mode((0,0),pygame.FULLSCREEN)
                else:
                    screen=pygame.display.set_mode((W,H))
            elif event.key==pygame.K_ESCAPE:
                if state=="playing":
                    state="paused"
                    if MUSIC_CHANNEL:
                        MUSIC_CHANNEL.pause()
                elif state=="paused":
                    state="playing"
                    if MUSIC_CHANNEL:
                        MUSIC_CHANNEL.unpause()
                elif state=="achievements":
                    state="menu"
                    menu_page="home"
                elif state in ("gameover","victory"):
                    state="menu"
                    menu_page="home"
                elif state=="victory_cutscene":
                    state="victory"
                elif state=="menu" and menu_page=="modes":
                    menu_page="home"
                else:
                    running=False
            elif event.key==pygame.K_t:
                # SDL/pygame may expose right-side modifiers inconsistently;
                # use the event modifier mask so the chord works reliably.
                mods=event.mod | pygame.key.get_mods()
                ctrl_down=bool(mods & (pygame.KMOD_CTRL | pygame.KMOD_RCTRL | pygame.KMOD_LCTRL))
                shift_down=bool(mods & (pygame.KMOD_SHIFT | pygame.KMOD_RSHIFT | pygame.KMOD_LSHIFT))
                if ctrl_down and shift_down:
                    autoplay=not autoplay
                    game["ai_replan"]=0.0
                    game["ai_jump_timer"]=-1.0
                    if state=="menu" and autoplay:
                        game=reset_game(); state="playing"; set_stage_music(1)
                    game["message"]="ARCADE AI ON" if autoplay else "ARCADE AI OFF"
                    game["message_time"]=2.0
            elif state=="menu":
                if event.key in (pygame.K_UP,pygame.K_w):
                    if menu_page=="home": home_selection=(home_selection-1)%3
                    else: menu_selection=(menu_selection-1)%len(MODE_OPTIONS)
                elif event.key in (pygame.K_DOWN,pygame.K_s):
                    if menu_page=="home": home_selection=(home_selection+1)%3
                    else: menu_selection=(menu_selection+1)%len(MODE_OPTIONS)
                elif event.key in (pygame.K_RETURN,pygame.K_SPACE):
                    if menu_page=="modes":
                        launch_selected_mode()
                    elif home_selection==0:
                        launch_selected_mode()
                    elif home_selection==1:
                        menu_page="modes"
                    else:
                        state="achievements"
                elif menu_page=="modes" and event.key==pygame.K_b:
                    versus_bosses_enabled=not versus_bosses_enabled
                elif menu_page=="modes" and event.key==pygame.K_o:
                    coop_bosses_enabled=not coop_bosses_enabled
                elif menu_page=="modes" and event.key==pygame.K_v:
                    versus_split_enabled=not versus_split_enabled
                elif menu_page=="modes" and event.key==pygame.K_c:
                    coop_split_enabled=not coop_split_enabled
                elif event.key==pygame.K_a:
                    state="achievements"
            elif state in ("gameover","victory") and event.key in (pygame.K_RETURN,pygame.K_SPACE):
                launch_selected_mode()
            elif state=="paused":
                if event.key in (pygame.K_RETURN,pygame.K_SPACE):
                    state="playing"
                    if MUSIC_CHANNEL:
                        MUSIC_CHANNEL.unpause()
                elif event.key==pygame.K_q:
                    state="menu"
                    if MUSIC_CHANNEL:
                        MUSIC_CHANNEL.unpause()
                    set_stage_music(game["level"],game["mode"],game["coop_endless"])
            elif state=="playing":
                if game["mode"]=="pvp":
                    if event.key==pygame.K_f:
                        pvp_throw_sword(game,1,manual=True)
                    elif event.key==pygame.K_RETURN:
                        pvp_throw_sword(game,2,manual=True)
                    elif event.key==pygame.K_LSHIFT:
                        pvp_cast_lightning(game,1)
                    elif event.key==pygame.K_RSHIFT:
                        pvp_cast_lightning(game,2)
                if event.key in (pygame.K_SPACE,pygame.K_w,pygame.K_UP) and game["grounded"] and game["mode"]=="solo":
                    game["jump_velocity"]=JUMP_VELOCITY
                    game["grounded"]=False
                    play_sound("jump")
                elif game["mode"] not in ("solo","pvp") and event.key in (pygame.K_SPACE,pygame.K_w) and game["grounded"]:
                    game["jump_velocity"]=JUMP_VELOCITY
                    game["grounded"]=False
                    play_sound("jump")
                if game["mode"] not in ("solo","pvp") and event.key==pygame.K_UP and game["p2_grounded"] and not game["p2_ai"]:
                    game["p2_jump_velocity"]=JUMP_VELOCITY
                    game["p2_grounded"]=False
                    play_sound("jump")
                if game["boss"] and event.key in (pygame.K_SPACE,pygame.K_s) and game["swords"]>0:
                    game["swords"]-=1
                    game["projectiles"].append({"x":game["player_x"]+17,"y":game["player_y"]-8})
                    play_sound("sword")
                if game["boss"] and game["mode"]!="solo" and event.key==pygame.K_DOWN and not game["p2_ai"] and game["swords"]>0:
                    game["swords"]-=1
                    game["projectiles"].append({"x":game["p2_x"]+17,"y":game["p2_y"]-8})
                    play_sound("sword")
            elif state in ("gameover","victory") and event.key==pygame.K_a:
                state="achievements"

    if state=="playing" and game["mode"]=="pvp":
        update_pvp_game(game,dt)

    if state=="playing" and game["mode"]!="pvp":
        game["anim_time"]+=dt
        game["run_time"]+=dt
        progress_score=game["score"]+game["p2_score"] if game["mode"]=="versus" else game["score"]
        game["level"]=min(MAX_STAGE,1+progress_score//CANDY_PER_STAGE)
        if game["boss"] is None:
            set_stage_music(game["level"],game["mode"],game["coop_endless"])
        save_data["max_stage"]=max(save_data["max_stage"],game["level"])
        check_achievements(game)
        game["invulnerability"]=max(0,game["invulnerability"]-dt)
        game["p2_invulnerability"]=max(0,game["p2_invulnerability"]-dt)
        keys=pygame.key.get_pressed()
        if game["mode"]=="solo":
            move=int(keys[pygame.K_RIGHT] or keys[pygame.K_d])-int(keys[pygame.K_LEFT] or keys[pygame.K_a])
        else:
            move=int(keys[pygame.K_d])-int(keys[pygame.K_a])
        if autoplay and game["mode"]=="solo":
            game["ai_replan"]-=dt
            if game["ai_replan"]<=0:
                target_x,jump_delay=arcade_ai_decision(game)
                game["ai_target_x"]=target_x
                game["ai_replan"]=0.08
                # Keep a committed jump timing; only replace it when the new
                # prediction says an earlier jump is needed.
                if jump_delay is not None and (
                    game["ai_jump_timer"]<0 or jump_delay<game["ai_jump_timer"]-0.08
                ):
                    game["ai_jump_timer"]=jump_delay
            target_x=game["ai_target_x"]
            difference=target_x-(game["player_x"]+17)
            move=1 if difference>5 else -1 if difference < -5 else 0
            if game["ai_jump_timer"]>=0:
                if game["grounded"]:
                    game["ai_jump_timer"]-=dt
                    if game["ai_jump_timer"]<=0:
                        game["jump_velocity"]=JUMP_VELOCITY
                        game["grounded"]=False
                        game["ai_jump_timer"]=-1.0
                        play_sound("jump")
                else:
                    game["ai_jump_timer"]=-1.0
            game["auto_throw_timer"]=max(0,game["auto_throw_timer"]-dt)
            if (game["boss"] and game["boss"]["intro_timer"]<=0 and game["swords"]>0
                    and game["auto_throw_timer"]<=0
                    and (game["boss"]["name"]!="WEREWOLF" or game["grounded"])):
                game["swords"]-=1
                game["projectiles"].append({"x":game["player_x"]+17,"y":game["player_y"]-8})
                game["auto_throw_timer"]=0.24
                play_sound("sword")
        player_speed=min(MAX_PLAYER_SPEED,PLAYER_BASE_SPEED+max(0,game["level"]-PLAYER_ACCEL_LEVEL+1)*PLAYER_SPEED_STEP)
        old_x=game["player_x"]
        p1_bounds=(2,LW//2-36) if game.get("split_screen",False) else (2,LW-36)
        game["player_x"]=max(p1_bounds[0],min(p1_bounds[1],game["player_x"]+move*player_speed*dt))
        game["player_move"]=move
        if not game["grounded"]:
            game["jump_velocity"]+=740*dt
            game["player_y"]+=game["jump_velocity"]*dt
            if game["player_y"]>=LH-53:
                game["player_y"]=LH-53
                game["jump_velocity"]=0
                game["grounded"]=True

        if game["mode"]!="solo" and game["p2_lives"]>0:
            p2_speed=player_speed
            if game["p2_ai"]:
                game["p2_ai_replan"]-=dt
                if game["p2_ai_replan"]<=0:
                    view=dict(game)
                    view.update({"player_x":game["p2_x"],"player_y":game["p2_y"],
                        "lives":game["p2_lives"],"invulnerability":game["p2_invulnerability"],
                        "grounded":game["p2_grounded"],"jump_velocity":game["p2_jump_velocity"]})
                    if game.get("split_screen",False):
                        view["ai_bounds"]=(LW//2+2,LW-36)
                        view["items"]=[item for item in game["items"] if item["x"]>=LW//2]
                    target_x,jump_delay=arcade_ai_decision(view)
                    game["p2_ai_target_x"]=target_x
                    game["p2_ai_replan"]=0.08
                    if jump_delay is not None and (game["p2_ai_jump_timer"]<0 or jump_delay<game["p2_ai_jump_timer"]-0.08):
                        game["p2_ai_jump_timer"]=jump_delay
                difference=game["p2_ai_target_x"]-(game["p2_x"]+17)
                p2_move=1 if difference>5 else -1 if difference < -5 else 0
                if game["p2_ai_jump_timer"]>=0:
                    if game["p2_grounded"]:
                        game["p2_ai_jump_timer"]-=dt
                        if game["p2_ai_jump_timer"]<=0:
                            game["p2_jump_velocity"]=JUMP_VELOCITY
                            game["p2_grounded"]=False
                            game["p2_ai_jump_timer"]=-1.0
                    else:
                        game["p2_ai_jump_timer"]=-1.0
            else:
                p2_move=int(keys[pygame.K_RIGHT])-int(keys[pygame.K_LEFT])
            p2_bounds=(LW//2+2,LW-36) if game.get("split_screen",False) else (2,LW-36)
            p2_old_x=game["p2_x"]
            game["p2_x"]=max(p2_bounds[0],min(p2_bounds[1],game["p2_x"]+p2_move*p2_speed*dt))
            if not game["p2_grounded"]:
                game["p2_jump_velocity"]+=740*dt
                game["p2_y"]+=game["p2_jump_velocity"]*dt
                if game["p2_y"]>=LH-53:
                    game["p2_y"]=LH-53
                    game["p2_jump_velocity"]=0
                    game["p2_grounded"]=True
            if game["p2_ai"] and game["boss"] and game["boss"]["intro_timer"]<=0:
                game["p2_auto_throw_timer"]=max(0,game["p2_auto_throw_timer"]-dt)
                if game["swords"]>0 and game["p2_auto_throw_timer"]<=0:
                    game["swords"]-=1
                    game["projectiles"].append({"x":game["p2_x"]+17,"y":game["p2_y"]-8})
                    game["p2_auto_throw_timer"]=0.24
                    play_sound("sword")

        if game["boss"] is None and game["level"]>=game["next_boss"] and game["next_boss"] in BOSS_NAMES and (game["mode"]=="solo" or game.get("multiplayer_bosses",False)):
            start_boss(game,game["next_boss"])

        if game["boss"]:
            boss=game["boss"]
            if boss["intro_timer"]>0:
                boss["intro_timer"]=max(0,boss["intro_timer"]-dt)
                boss["x"]=min(LW/2,boss["x"]+145*dt)
            else:
                defeated=update_boss(game,dt)
                if defeated:
                    phase=boss["phase"]
                    save_data["bosses"]=sorted(set(save_data["bosses"]+[phase]))
                    save_progress()
                    game["boss"]=None
                    game["candy_timer"]=30.0
                    game["next_boss"]+=30
                    check_achievements(game)
                    if phase==120 and (game["mode"]=="solo" or (game["mode"]=="coop" and not game["coop_endless"])):
                        game["victory"]=True
                        check_achievements(game)
                        begin_final_cutscene(game,boss)
                        state="victory_cutscene"
                        set_music("ending")
                        play_sound("victory")
                    else:
                        if game["mode"]=="versus":
                            game["score"]+=15
                            game["p2_score"]+=15
                        else:
                            game["score"]+=30
                        game["message"]="BOSS DEFEATED! +30 CANDY"
                        game["message_time"]=2.0
                        save_progress()
                        check_achievements(game)
                        set_stage_music(game["level"],game["mode"],game["coop_endless"])
                        play_sound("defeat")
        else:
            game["spawn"]-=dt
            if game["spawn"]<=0:
                spawn_lane=random.choice(((8,LW//2-27),(LW//2+5,LW-28))) if game.get("split_screen",False) else None
                game["items"].append(new_item(game["level"],spawn_lane))
                game["spawn"]=max(0.22,0.80-game["level"]*0.03)
            remaining=[]
            for item in game["items"]:
                item["y"]+=item["speed"]*dt
                falling=pygame.Rect(int(item["x"]),int(item["y"]),22,22)
                player_hits=[]
                if game["lives"]>0 and pygame.Rect(int(game["player_x"]),int(game["player_y"]),34,34).colliderect(falling):
                    player_hits.append(1)
                if game["mode"]!="solo" and game["p2_lives"]>0 and pygame.Rect(int(game["p2_x"]),int(game["p2_y"]),34,34).colliderect(falling):
                    player_hits.append(2)
                if player_hits:
                    player_id=player_hits[0]
                    if item["kind"] in SWEETS:
                        points=2 if item["kind"] in ("urso","pirulito") else 1
                        score_key="p2_score" if game["mode"]=="versus" and player_id==2 else "score"
                        game[score_key]+=points
                        if game["mode"] in ("solo","coop"):
                            game["candy_timer"]=30.0
                        save_data["total_candy"]+=points
                        game["message"]=f"P{player_id} CANDY +{points}!" if game["mode"]!="solo" else f"CANDY +{points}!"
                        game["message_time"]=0.65
                        play_sound("collect")
                        check_achievements(game)
                        if game[score_key] % 10 < points:
                            save_progress()
                    else:
                        invuln=game["invulnerability"] if player_id==1 else game["p2_invulnerability"]
                        if invuln<=0:
                            damage_player(game,player_id,"TRICK! -1 LIFE")
                elif item["y"]<LH+10:
                    remaining.append(item)
            game["items"]=remaining

        # Skeleton fire walls block the lane until their timer expires.
        if game["boss"] and game["boss"]["name"]=="SKELETON":
            for fire in game["fires"]:
                if game["player_y"]>=LH-84 and abs((game["player_x"]+17)-fire["x"])<23:
                    if old_x+17 < fire["x"]:
                        game["player_x"]=max(2,fire["x"]-36)
                    else:
                        game["player_x"]=min(LW-36,fire["x"]+20)
                if game["mode"]!="solo" and game["p2_lives"]>0 and game["p2_y"]>=LH-84 and abs((game["p2_x"]+17)-fire["x"])<23:
                    if p2_old_x+17 < fire["x"]:
                        game["p2_x"]=max(2,fire["x"]-36)
                    else:
                        game["p2_x"]=min(LW-36,fire["x"]+20)

        if game["boss"] is None and state=="playing" and game["mode"] in ("solo","coop"):
            game["candy_timer"]-=dt
            if game["candy_timer"]<=0:
                if game["mode"]=="coop":
                    for player_id in (1,2):
                        if (player_id==1 and game["lives"]>0) or (player_id==2 and game["p2_lives"]>0):
                            damage_player(game,player_id,"NO CANDY! -1 LIFE")
                else:
                    lose_life(game,"NO CANDY! -1 LIFE")
                game["candy_timer"]=30.0
        update_hearts(game,dt)
        game["message_time"]=max(0,game["message_time"]-dt)
        if game["mode"]=="versus" and (game["lives"]<=0 or game["p2_lives"]<=0):
            if game["lives"]<=0 and game["p2_lives"]<=0:
                game["winner"]=None
            else:
                game["winner"]=2 if game["lives"]<=0 else 1
            state="gameover"
        elif game["mode"]=="coop" and ((not game["coop_endless"] and (game["lives"]<=0 or game["p2_lives"]<=0)) or (game["coop_endless"] and game["lives"]<=0 and game["p2_lives"]<=0)):
            state="gameover"
        elif state=="playing" and game["mode"]=="coop" and not game["coop_endless"] and game["level"]>=MAX_STAGE and game["boss"] is None:
            state="victory"
            game["victory"]=True
            check_achievements(game)
            save_progress()
            play_sound("victory")
        elif game["mode"]=="solo" and game["lives"]<=0:
            state="gameover"
            if not game["death_recorded"]:
                save_data["deaths"]+=1
                game["death_recorded"]=True
                save_progress()
                check_achievements(game)
            set_stage_music(game["level"],game["mode"],game["coop_endless"])
            play_sound("defeat")
        if state=="gameover" and game["mode"]!="solo" and not game["death_recorded"]:
            save_data["deaths"]+=1
            game["death_recorded"]=True
            save_progress()
            check_achievements(game)

    if state=="victory_cutscene":
        update_final_cutscene(game,dt)
        if game["final_boss_death"]["timer"]>=7.5:
            state="victory"

    if state=="menu":
        menu()
    elif state=="achievements":
        draw_achievements()
    elif state=="playing":
        if game["mode"]=="solo":
            game_screen(game)
        else:
            multiplayer_game_screen(game)
        if game["boss"] and game["boss"]["intro_timer"]>0:
            # Cinema-style letterbox and title overlay.
            rect(BLACK,0,0,LW,35); rect(BLACK,0,LH-34,LW,34)
            text("BOSS APPROACHING",LW//2,13,MENU_FONT,GOLD,True)
            text(f"STAGE {game['boss']['phase']}  -  {game['boss']['name']}",LW//2,LH-20,MENU_FONT,WHITE,True)
    elif state=="victory_cutscene":
        final_boss_cutscene(game)
    elif state=="paused":
        if game["mode"]=="solo":
            game_screen(game)
        else:
            multiplayer_game_screen(game)
        pause_screen()
    elif state=="gameover":
        multiplayer_game_over(game) if game["mode"]!="solo" else game_over(game)
    else:
        multiplayer_victory_screen(game) if game["mode"]=="coop" else victory_screen(game)

    pygame.transform.scale(canvas,screen.get_size(),screen)
    pygame.display.flip()
    if not AUDIO_READY:
        setup_audio()
        set_stage_music(game["level"],game["mode"],game["coop_endless"])
        AUDIO_READY=True

save_progress()
pygame.quit()
sys.exit()
