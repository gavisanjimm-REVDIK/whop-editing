#!/usr/bin/env python3
"""YoungLA Black Friday (Bodybuilders vs Models) - three clips. Each one has its own editing style.

  01_rage_quit   meme storytime: cold-open hook, B&W freeze + record scratch, 2.5x speed ramp,
                 punch-in zooms with bass booms, white backflash transitions, bleeped swears.
  02_fit_judges  game-show scoring: green ding + green flash for a W, red buzzer + red flash
                 for an L, scorecard pop-ups, word-by-word karaoke captions.
  03_aura_battle hype runway edit: camera-flash backflashes with shutter clicks, B&W plot-twist freeze,
                 aura-meter pop-ups, versus card, airhorn at the end.

python3 youngla_bf.py [name ...] [--preview]
"""
import os
import sys

from editor import Fx, Shot, Sound, Source, Text, Video, render

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "footage", "bvm.mp4")
WORDS = os.path.join(ROOT, "transcripts", "youngla_bvm_words.json")
MUSIC = os.path.join(ROOT, "assets", "music")

YELLOW = (255, 230, 0)
GREEN = (40, 230, 100)
RED = (255, 60, 60)
PINK = (255, 120, 200)


def at(v, i, dt=0.0):
    """output time of the start of shot i (+dt). call after the shot list is final."""
    t = 0.0
    for s in v.shots[:i]:
        t += s.dur
    return t + dt


def src_t(v, i, src_time):
    """output time of a source timestamp inside shot i."""
    s = v.shots[i]
    return at(v, i) + (src_time - s.src_in) / s.speed


# --------------------------------------------------------------------------- 1: rage quit

def rage_quit():
    v = Video(shots=[
        # 0 cold open: the punchline first
        Shot(329.45, 331.00, cx=1230, cy=420, zoom=1.45, zoom_end=1.55, freeze=1.3, bw=True),
        # 1 rewind: "be right back"
        Shot(307.10, 308.60, cx=1300, cy=470, zoom=1.0, zoom_end=1.08),
        # 2 host: "you're coming back?"
        Shot(309.45, 310.45, cx=600, cy=480, zoom=1.05),
        # 3 guest: "yeah one second... give me 30 seconds"
        Shot(311.40, 314.25, cx=1300, cy=470, zoom=1.0, zoom_end=1.12),
        # 4 the walk out, sped up
        Shot(314.25, 327.40, cx=1200, cy=540, zoom=1.0, speed=2.6, layout="fit", audio="mute", captions=False),
        # 5 in the car
        Shot(327.50, 338.10, cx=1250, cy=400, zoom=1.4, cx_end=1420),
        # 6 drives off
        Shot(338.10, 342.60, cx=1000, cy=420, zoom=1.15, speed=1.5, captions=False),
        # 7 host: "___ went, but I got Lukey"
        Shot(343.60, 346.30, cx=600, cy=420, zoom=1.1, zoom_end=1.25, captions=False),
    ], caption_style=dict(font="montserrat", size=90, hl=YELLOW, y=0.73, words=3))

    s = v.shots
    t_freeze = at(v, 0, s[0].run)
    v.texts += [
        Text(0.0, at(v, 1), "HE SAID HE WAS GOING TO THE BATHROOM", y=0.17, size=72, box=(255, 255, 255, 255),
             fill=(0, 0, 0), stroke_w=0, width=17, anim="pop"),
        Text(t_freeze + 0.05, at(v, 1), "HOW DID WE GET HERE?", y=0.45, size=100, fill=YELLOW, anim="shake"),
        Text(at(v, 3, 1.4), at(v, 4), "30 SECONDS", y=0.35, size=130, fill=YELLOW, anim="shake", rot=-4),
        Text(at(v, 4, 0.1), at(v, 4, s[4].dur * 0.55), "THE BATHROOM:", y=0.22, size=100, anim="pop"),
        Text(at(v, 4, s[4].dur * 0.55), at(v, 5), "BRO THE BATHROOM IS INSIDE", y=0.22, size=96, fill=YELLOW,
             anim="shake", width=14),
        Text(at(v, 6, 0.2), at(v, 7), "HE REALLY LEFT", y=0.30, size=120, fill=RED, anim="shake", rot=3),
        Text(at(v, 7, 0.6), at(v, 8), "THE SHOW MUST GO ON", y=0.72, size=92, fill=YELLOW, anim="pop", width=12),
    ]
    v.fx += [
        Fx(0.0, "punch", 0.35, 1.12), Fx(0.0, "shake", 0.3, 0.8),
        Fx(t_freeze, "flash", 0.25, 0.9), Fx(t_freeze, "rgb", 0.4, 1.0), Fx(t_freeze, "shake", 0.5, 1.0),
        Fx(at(v, 1), "flash", 0.35, 1.0),                     # backflash into the rewind
        Fx(at(v, 3, 1.4), "punch", 0.6, 1.25), Fx(at(v, 3, 1.4), "shake", 0.4, 0.7),
        Fx(at(v, 4), "flash", 0.25, 0.8),
        Fx(at(v, 4, s[4].dur * 0.55), "punch", 0.4, 1.12),
        Fx(at(v, 5), "flash", 0.3, 1.0),                      # backflash into the car reveal
        Fx(src_t(v, 5, 329.5), "punch", 0.7, 1.2), Fx(src_t(v, 5, 329.5), "shake", 0.4, 1.0),
        Fx(src_t(v, 5, 333.9), "punch", 0.5, 1.12),
        Fx(src_t(v, 5, 336.4), "punch", 0.5, 1.15), Fx(src_t(v, 5, 336.4), "shake", 0.3, 0.6),
        Fx(at(v, 6, 0.2), "shake", 0.5, 0.8),
        Fx(at(v, 7), "flash", 0.3, 0.8),
        Fx(at(v, 7, 0.9), "punch", 0.5, 1.15),
    ]
    v.sounds += [
        Sound(0.0, "boom", 1.0),
        Sound(t_freeze, "record_scratch", 1.2),
        Sound(at(v, 1) - 0.25, "whoosh", 0.9),
        Sound(at(v, 3, 1.4), "boom", 0.9),
        Sound(at(v, 4) - 0.2, "whoosh", 0.8),
        Sound(at(v, 4, s[4].dur * 0.55), "pop", 1.0),
        Sound(at(v, 5) - 0.25, "flash", 0.9),
        Sound(src_t(v, 5, 329.5), "boom", 1.0),
        Sound(src_t(v, 5, 336.4), "record_scratch", 0.8),
        Sound(at(v, 6, 0.2), "bruh_drop", 1.0),
        Sound(at(v, 7) - 0.2, "whoosh", 0.7),
        Sound(at(v, 7, 0.9), "ding_green", 0.8),
    ]
    v.music = dict(file=os.path.join(MUSIC, "Sneaky_Snitch.mp3"), offset=0.0, gain_db=-17, open_db=-9,
                   stops=[(0, at(v, 1) - 0.05), (at(v, 6, 0.2), at(v, 7))])  # cold open + "he really left"
    return v


# --------------------------------------------------------------------------- 2: fit judges

def stamp(v, t, good, label):
    """big check / cross stamp + label + ding/buzzer + screen tint."""
    col = GREEN if good else RED
    v.texts += [
        Text(t, t + 0.9, "✔" if good else "✘", y=0.47, size=330, font="dejavu", fill=col,
             stroke=(255, 255, 255), stroke_w=12, anim="pop", rot=-8 if good else 8),
        Text(t + 0.05, t + 1.3, label, y=0.62, size=96, font="luckiest", fill=col, stroke_w=10,
             anim="shake", width=14),
    ]
    v.fx += [Fx(t, "green" if good else "red", 0.9, 1.0), Fx(t, "punch", 0.4, 1.08)]
    if not good:
        v.fx.append(Fx(t, "shake", 0.45, 0.9))
    v.sounds.append(Sound(t, "ding_green" if good else "ding_red", 1.0))


def fit_judges():
    v = Video(shots=[
        # 0 skully debate (Marlin close-up then the commentators)
        Shot(178.55, 192.15, layout="fit", zoom=1.3),
        # 1 Quav hits the runway
        Shot(361.10, 364.32, cx=1040, cy=520, zoom=1.0, zoom_end=1.1),
        # 2 "what do you think he's listening to?"
        Shot(364.32, 366.50, layout="fit", zoom=1.3),
        # 3 "oh he's definitely..."
        Shot(367.15, 368.12, layout="fit", zoom=1.3),
        # 4 "...Justin Bieber-esque 2008 song" / "good call"
        Shot(368.12, 372.91, cx=1000, cy=520, zoom=1.0, zoom_end=1.12),
        # 5 "that pink looks really good on him... level of man to rock some pink"
        Shot(372.91, 377.50, cx=950, cy=500, zoom=1.05, zoom_end=1.2),
        # 6 the intel drop
        Shot(456.25, 462.00, layout="fit", zoom=1.3, freeze=0.9),
    ], caption_style=dict(font="luckiest", size=86, hl=GREEN, y=0.79, words=3, stroke_w=10))

    t_love = src_t(v, 0, 184.0)
    t_no = src_t(v, 0, 186.85)
    t_cooked = src_t(v, 0, 191.4)
    t_guess = src_t(v, 4, 371.2)
    t_pink = src_t(v, 5, 373.3)
    t_man = src_t(v, 5, 376.6)
    t_wrong = src_t(v, 6, 460.65)
    end = at(v, len(v.shots))

    v.texts.append(Text(0, end, "RATING FITS AT THE FASHION SHOW", y=0.105, size=62, font="luckiest",
                        fill=(0, 0, 0), stroke_w=0, box=(255, 230, 0, 255), width=20, anim="none"))
    # live W / L scoreboard
    score = [(0, 0, 0), (t_love, 1, 0), (t_no, 1, 1), (t_cooked, 1, 2), (t_pink, 2, 2), (t_man, 3, 2),
             (t_wrong, 3, 3)]
    for i, (t, w, l) in enumerate(score):
        t1 = score[i + 1][0] if i + 1 < len(score) else end
        anim = "none" if i == 0 else "pop"
        v.texts.append(Text(t, t1, f"W {w}", x=0.36, y=0.19, size=84, font="luckiest", fill=GREEN, anim=anim))
        v.texts.append(Text(t, t1, f"L {l}", x=0.64, y=0.19, size=84, font="luckiest", fill=RED, anim=anim))

    stamp(v, t_love, True, "SKULLY W")
    stamp(v, t_no, False, "DENIED")
    stamp(v, t_cooked, False, "HE GOT COOKED")
    v.texts.append(Text(t_guess, at(v, 5), "FINAL ANSWER: JUSTIN BIEBER", y=0.3, size=80, font="luckiest",
                        fill=(255, 255, 255), stroke_w=0, box=(30, 30, 30, 230), width=16, anim="slide"))
    v.sounds += [Sound(t_guess, "tick", 1.0), Sound(t_guess + 0.12, "tick", 1.0), Sound(t_guess + 0.24, "pop", 1.0)]
    stamp(v, t_pink, True, "PINK = W")
    stamp(v, t_man, True, "CERTIFIED")
    v.texts.append(Text(src_t(v, 6, 456.3), t_wrong, "THE ANSWER WAS...", y=0.3, size=88, font="luckiest",
                        fill=YELLOW, anim="pop"))
    v.sounds.append(Sound(src_t(v, 6, 456.3), "riser", 0.8))
    stamp(v, t_wrong, False, "WRONG")
    v.sounds.append(Sound(src_t(v, 6, 461.4), "bruh_drop", 0.9))
    v.fx.append(Fx(at(v, 6, v.shots[6].run), "bw", v.shots[6].freeze + 0.1))
    for i in range(1, len(v.shots)):         # whoosh + quick flash on every cut
        v.fx.append(Fx(at(v, i), "flash", 0.18, 0.5))
        v.sounds.append(Sound(at(v, i) - 0.15, "whoosh", 0.5))
    v.music = dict(file=os.path.join(MUSIC, "Fluffing_a_Duck.mp3"), offset=0.0, gain_db=-17, open_db=-9,
                   stops=[(t_wrong - 0.05, end + 1)])                      # cuts out on WRONG
    return v


# --------------------------------------------------------------------------- 3: aura battle

def aura_battle():
    v = Video(shots=[
        # 0 "the biggest question to me is who's gonna win the mog off?"
        Shot(130.15, 133.22, cx=1380, cy=430, zoom=1.0, zoom_end=1.12),
        # 1 "the aura battle between Jay Cutler..."
        Shot(133.22, 135.84, cx=1000, cy=470, zoom=1.0, zoom_end=1.1),
        # 2 "...and Marlin"
        Shot(135.84, 136.95, cx=1000, cy=470, zoom=1.05, freeze=0.25),
        # 3 "Marlin's got the face card" (picture: Marlin close-up)
        Shot(142.15, 143.25, v_in=179.40, cx=950, cy=470, zoom=1.0, zoom_end=1.1),
        # 4 Marlin walks
        Shot(164.00, 169.09, cx=960, cy=560, zoom=1.0, zoom_end=1.08),
        Shot(169.09, 171.38, cx=1120, cy=540, zoom=1.05, zoom_end=1.15),
        # 6 "but Jay Cutler got the aura points"
        Shot(143.25, 146.05, cx=1380, cy=430, zoom=1.05, zoom_end=1.2),
        # 7 Jay walks: "oh sh*t, this is a big moment here, this is the people's favourite"
        Shot(233.19, 238.20, cx=860, cy=540, zoom=1.0, zoom_end=1.1),
        # 8 "I'm gonna vote Jay Cutler wins the aura battle"
        Shot(249.92, 252.65, cx=830, cy=500, zoom=1.05, zoom_end=1.15),
        # 9 the twist: "honestly who the f*** had the most aura?"
        Shot(836.75, 838.35, cx=960, cy=520, zoom=1.0, freeze=0.9, bw=True),
        # 10 "this guy right here. the sound guy."
        Shot(841.80, 843.75, cx=1380, cy=430, zoom=1.0, zoom_end=1.1),
        # 11 "Griffin, you have been awarded the most aura"
        Shot(847.30, 850.70, cx=1080, cy=470, zoom=1.1, zoom_end=1.35),
        # 12 "a man who can handle all the noise but doesn't produce any himself"
        Shot(861.00, 863.75, cx=1380, cy=430, zoom=1.0, zoom_end=1.18),
        # 13 "wow. deep sh*t."
        Shot(865.40, 867.40, cx=560, cy=430, zoom=1.0, zoom_end=1.1),
    ], caption_style=dict(font="anton", size=104, hl=PINK, y=0.77, words=2, stroke_w=9))
    s = v.shots

    # camera-flash backflash + shutter on every cut (runway paparazzi feel)
    for i in range(1, len(s)):
        v.fx.append(Fx(at(v, i), "flash", 0.3, 1.0))
        v.sounds.append(Sound(at(v, i) - 0.03, "shutter", 0.9))
    for t in (src_t(v, 4, 165.0), src_t(v, 4, 167.3), src_t(v, 7, 235.0), src_t(v, 7, 236.8)):
        v.fx += [Fx(t, "flash", 0.22, 0.85)]       # extra paparazzi flashes mid-walk
        v.sounds.append(Sound(t, "flash", 0.7))

    t_mog = src_t(v, 0, 133.0)
    v.texts += [
        Text(0.0, at(v, 1), "BODYBUILDER VS MODEL", y=0.16, size=96, font="anton", fill=(255, 255, 255),
             anim="pop", width=12),
        Text(at(v, 1), at(v, 3), "WHO HAS MORE AURA?", y=0.16, size=96, font="anton", fill=PINK, anim="pop", width=12),
        Text(src_t(v, 1, 135.35), at(v, 3), "JAY CUTLER", y=0.30, size=120, font="anton", fill=YELLOW,
             anim="shake", rot=-4),
        Text(at(v, 2), at(v, 3), "VS", y=0.40, size=150, font="anton", fill=RED, anim="pop"),
        Text(src_t(v, 2, 136.1), at(v, 3), "MARLIN", y=0.50, size=120, font="anton", fill=PINK, anim="shake", rot=4),
        Text(at(v, 4, 0.3), at(v, 6), "FACE CARD", y=0.14, size=80, font="anton", fill=(255, 255, 255), anim="slide"),
        Text(at(v, 5), at(v, 6), "10 / 10", y=0.22, size=140, font="anton", fill=PINK, anim="shake"),
        Text(at(v, 7, 0.3), at(v, 9), "AURA POINTS", y=0.14, size=80, font="anton", fill=(255, 255, 255), anim="slide"),
        Text(at(v, 8), at(v, 9), "+ 1,000,000", y=0.22, size=130, font="anton", fill=YELLOW, anim="shake"),
        Text(at(v, 9, s[9].run), at(v, 10), "PLOT TWIST", y=0.42, size=150, font="anton", fill=RED, anim="shake", rot=-5),
        Text(src_t(v, 10, 843.2), at(v, 11), "THE SOUND GUY?!", y=0.20, size=110, font="anton", fill=YELLOW,
             anim="shake", width=10),
        Text(at(v, 11, 0.2), at(v, 12), "AURA: INFINITE", y=0.20, size=120, font="anton", fill=PINK, anim="pop",
             width=10),
        Text(at(v, 13, 0.4), at(v, 14), "AURA WINNER: GRIFFIN", y=0.20, size=100, font="anton", fill=YELLOW,
             anim="pop", width=12),
    ]
    v.fx += [
        Fx(t_mog, "punch", 0.5, 1.15),
        Fx(src_t(v, 1, 135.35), "punch", 0.5, 1.12), Fx(src_t(v, 1, 135.35), "rgb", 0.3, 0.8),
        Fx(at(v, 2), "rgb", 0.3, 0.8), Fx(at(v, 2), "shake", 0.3, 0.6),
        Fx(src_t(v, 6, 145.5), "punch", 0.6, 1.2), Fx(src_t(v, 6, 145.5), "shake", 0.4, 0.6),
        Fx(at(v, 9, s[9].run), "rgb", 0.5, 1.2), Fx(at(v, 9, s[9].run), "shake", 0.5, 1.0),
        Fx(src_t(v, 10, 843.3), "punch", 0.6, 1.22), Fx(src_t(v, 10, 843.3), "shake", 0.4, 0.8),
        Fx(src_t(v, 12, 862.2), "punch", 0.6, 1.1),
        Fx(at(v, 13, 0.4), "shake", 0.5, 0.7),
    ]
    v.sounds += [
        Sound(t_mog, "boom", 0.9),
        Sound(src_t(v, 1, 135.35), "boom", 0.7),
        Sound(src_t(v, 2, 136.1), "boom", 0.7),
        Sound(at(v, 5), "ka_ching", 0.8),
        Sound(src_t(v, 6, 145.5), "boom", 0.9),
        Sound(at(v, 8), "ka_ching", 0.8),
        Sound(at(v, 9) + 0.2, "riser", 0.8),
        Sound(at(v, 9, s[9].run), "record_scratch", 1.1),
        Sound(src_t(v, 10, 843.3), "boom", 1.0),
        Sound(at(v, 11, 0.2), "ding_green", 0.9),
        Sound(at(v, 13, 0.4), "airhorn", 0.75),
    ]
    v.music = dict(file=os.path.join(MUSIC, "Investigations.mp3"), offset=0.0, gain_db=-17, open_db=-9,
                   stops=[(at(v, 9, s[9].run) - 0.05, at(v, 10) + 0.1)])   # silence on the plot twist
    return v


VIDEOS = {"01_rage_quit": rage_quit, "02_fit_judges": fit_judges, "03_aura_battle": aura_battle}


def fix_transcript(src):
    """lines whisper got wrong, re-checked by a second pass / the source video's own captions."""
    src.override(186.5, 192.3, [
        (186.85, 187.0, "You"), (187.0, 187.06, "don't"), (187.06, 187.16, "wear"), (187.16, 187.34, "no"),
        (187.34, 187.8, "skully,"), (187.8, 188.0, "dude."), (188.0, 188.18, "When's"), (188.18, 188.22, "the"),
        (188.22, 188.3, "last"), (188.3, 188.4, "time"), (188.4, 188.52, "you"), (188.52, 188.62, "wore"),
        (188.62, 188.95, "one?"), (189.0, 189.16, "Two"), (189.16, 189.3, "days"), (189.3, 189.6, "ago."),
        (189.84, 190.3, "What?"), (190.54, 190.7, "That"), (190.7, 191.0, "ass?"), (191.54, 191.78, "That's"),
        (191.78, 191.86, "what"), (191.86, 191.94, "I"), (191.94, 192.2, "thought."),
    ])
    src.override(335.9, 336.0, [(335.92, 336.2, "runway.")])


def main():
    names = [a for a in sys.argv[1:] if not a.startswith("--")] or list(VIDEOS)
    preview = "--preview" in sys.argv
    src = Source(SRC, WORDS)
    fix_transcript(src)
    os.makedirs(os.path.join(ROOT, "out"), exist_ok=True)
    for n in names:
        out = os.path.join(ROOT, "out", n + ".mp4")
        d = render(VIDEOS[n](), src, out, preview=preview)
        print(f"wrote {out} ({d:.1f}s)")


if __name__ == "__main__":
    main()
