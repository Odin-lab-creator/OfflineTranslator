"""«28 дней спустя» · промты для Google Flow (Nano Banana), формат 9:16.
Внешность героев прописана прямо в каждой сцене, чтобы не «плыла» между кадрами.
python3 prompts.py → PROMPTS.md
"""
import os

from script import SCENES as TEXT

STYLE = ("Detailed pixel art illustration in the style of a modern 16-bit retro game, crisp visible pixels, "
         "rich detail, cinematic lighting, muted desaturated colors, vertical 9:16 composition, "
         "no text, no letters, no logos, no watermark.")

JIM = ("Jim (a thin young man in his late 20s with short buzzed dark hair and light stubble, dark grey jacket over a "
       "white t-shirt, jeans)")
JIM_H = ("Jim (a thin young man in his late 20s with short buzzed dark hair and light stubble, wearing pale blue "
         "hospital scrubs, barefoot)")
SEL = ("Selena (a fierce young woman with dark skin and short braided hair tied back, olive green jacket, cargo pants, "
       "a machete on her belt)")
MARK = "Mark (a young man with short messy brown hair in a dark navy parka)"
FRANK = "Frank (a big friendly man in his 50s with short grey hair and a grey beard, brown leather jacket)"
HANNAH = "Hannah (a 15-year-old girl with long auburn hair in a ponytail, dark green parka)"
WEST = "Major West (a cold army officer in his 40s with short brown hair, British camouflage uniform)"
INF = ("infected people with glowing blood-red eyes, pale skin, blood around their mouths and torn clothes, "
       "running wildly and fast")
INF1 = "an infected person with glowing blood-red eyes, pale skin, blood around the mouth and torn clothes"

REFS = [
    ("R1", "Джим", "Character reference sheet. An original character: a thin young man in his late 20s with short "
     "buzzed dark hair and light stubble, dark grey jacket over a white t-shirt, jeans, worn sneakers. Full body, front "
     "view and three-quarter view side by side, plain neutral grey background. Original design, not resembling any real actor."),
    ("R2", "Селена и Марк", "Character reference sheet. Two original characters side by side: a fierce young woman "
     "with dark skin and short braided hair tied back, olive green jacket, cargo pants, a machete on her belt; a young "
     "man with short messy brown hair in a dark navy parka. Full body, front view, plain neutral grey background. "
     "Original designs, not resembling any real actors."),
    ("R3", "Фрэнк и Ханна", "Character reference sheet. Two original characters side by side: a big friendly man in "
     "his 50s with short grey hair and a grey beard, brown leather jacket; a 15-year-old girl with long auburn hair in "
     "a ponytail, dark green parka. Full body, front view, plain neutral grey background. Original designs, not "
     "resembling any real actors."),
    ("R4", "Заражённый", "Character reference sheet. A person infected with a rage virus: glowing blood-red eyes, "
     "pale grey skin, blood around the mouth, torn dirty everyday clothes, hunched aggressive running pose. Full body, "
     "front view, plain neutral grey background. Scary but not gory."),
    ("R5", "Майор Уэст", "Character reference sheet. An original character: a cold army officer in his 40s with short "
     "brown hair and a stern face, British camouflage uniform, pistol holster. Full body, front view, plain neutral "
     "grey background. Original design, not resembling any real actor."),
]

# (№, образцы, промт сцены)
SCENES = [
    (1, "R1", f"{JIM_H} stands alone in the middle of an empty Westminster Bridge in London at dawn, an overturned red "
     "double-decker bus, scattered papers on the road, Big Ben in grey morning mist behind him. Keep the top third of "
     "the image as open sky for a title."),
    (2, "", "Night, a secret primate research laboratory: animal rights activists in dark hoodies and balaclavas break "
     "into the lab, rows of cages with chimpanzees, monitors on the wall, cold blue light."),
    (3, "", "Close shot: a frightened scientist in a white lab coat raises his hands and shouts a warning, behind him a "
     "chimpanzee with glowing blood-red eyes rattles its cage, red alarm light."),
    (4, "R4", f"A young female activist in a hoodie convulses and turns into {INF1}, her eyes glowing blood red, other "
     "activists back away in horror, dark lab, red alarm light, not gory."),
    (5, "R1", f"{JIM_H} wakes up in an abandoned hospital room, pulling an IV drip from his arm, empty beds, scattered "
     "medical papers, cold daylight through dirty blinds."),
    (6, "R1", f"Wide shot: {JIM_H} walks alone through empty central London, Piccadilly Circus with dark dead "
     "billboards, abandoned cars, rubbish blowing in the wind, total silence."),
    (7, "R1", f"{JIM_H} stares at a huge wall covered with hundreds of handwritten missing person notes and photos, "
     "grey morning light, sad and lonely."),
    (8, "R1 R4", f"Inside a dark old church with candles, a priest who is {INF1} lunges toward {JIM_H}, who stumbles "
     "back toward the door in terror."),
    (9, "R1 R2", f"Night street: {SEL} and {MARK} throw burning petrol bombs at a group of {INF}, fire lights up the "
     f"street, {JIM_H} on the ground looks up at them."),
    (10, "R1 R2", f"Inside a dark small corner shop lit by a camping lamp, {SEL} seriously explains something, holding "
     f"up one finger, to {JIM}, who listens in shock, {MARK} keeps watch at the window."),
    (11, "R1", f"{JIM} sits on the floor of his parents' quiet suburban bedroom holding a handwritten farewell note, "
     "an old family photo on the nightstand, soft grey light, grief. No bodies."),
    (12, "R2 R4", f"Night, a dark suburban kitchen: {INF} burst through the window, {MARK} struggles with one of "
     "them, his arm bleeding, broken glass, chaos, not gory."),
    (13, "R2 R1", f"{SEL} stands with a raised machete and a hard cold face, {JIM} behind her frozen in shock, the "
     "moment before the strike, dark kitchen, red light, not gory."),
    (14, "R3", f"Night: a tall grey London tower block, on one high balcony colourful Christmas lights blink, {FRANK} "
     f"and {HANNAH} wave a torch from the balcony."),
    (15, "R1 R2 R3", f"Inside a cozy tower block flat at night: {FRANK}, {HANNAH}, {SEL} and {JIM} gather around an "
     "old radio, a map of England on the table, candle light, hope."),
    (16, "", "A black London taxi cab with luggage tied to the roof drives along an empty motorway through green "
     "English countryside, morning sun, wide shot."),
    (17, "R1 R4", f"A dark road tunnel full of abandoned cars, the black taxi with a flat tyre, {JIM} desperately "
     f"changes the wheel, hundreds of rats run out of the darkness, behind them {INF} sprint toward the car."),
    (18, "R1 R2 R3", f"A rare happy moment: {JIM}, {SEL}, {HANNAH} and {FRANK} laugh while filling shopping trolleys "
     "in an empty, perfectly clean supermarket, bright light."),
    (19, "R3", f"{FRANK} stands near a military roadblock among empty fields, a crow on a pole above him, a single drop "
     "of blood falls toward his eye, slow-motion moment, grey sky."),
    (20, "R3 R1", f"{FRANK} with glowing blood-red eyes kneels on the road, soldiers in gas masks aim rifles at him, "
     f"{HANNAH} screams while {JIM} holds her back, grey sky, not gory."),
    (21, "R5", f"{WEST} stands in front of a grand old English mansion surrounded by barbed wire, soldiers and a "
     "military truck, evening."),
    (22, "R2 R3 R5", f"Grand mansion dining hall at night: soldiers drink and laugh around a long table, {SEL} and "
     f"{HANNAH} sit tense by the fireplace, Selena protectively holds Hannah's hand, {WEST} watches them coldly."),
    (23, "R4 R5", f"In the mansion courtyard {INF1} in a torn army uniform is chained by the neck to a wall, lunging "
     f"and screaming, {WEST} calmly watches with a notebook."),
    (24, "R1", f"{JIM} runs through a dark forest at dusk away from two soldiers with rifles, jumping over a fallen "
     "tree, tense escape."),
    (25, "R1", f"{JIM} stands on a country road looking up at the sky, a white jet contrail crosses the sunset sky, "
     "hope on his face."),
    (26, "R1 R4", f"Night thunderstorm: soaked, wild-eyed {JIM} unlocks the chain of {INF1} in a torn army uniform in "
     "the mansion courtyard, the infected soldier rushes toward the house, lightning."),
    (27, "R1 R2 R3 R5", f"Night rain: the black taxi breaks through the mansion gates, {SEL} and {HANNAH} inside, "
     f"{JIM} wounded in the back seat holding his stomach, {WEST} aims a pistol at the car."),
    (28, "R1", f"{JIM} sleeps peacefully in a cozy countryside cottage bedroom, sunlight through the window, a bandage "
     "on his stomach; through the window, far away in a green field, an exhausted infected person lies collapsed in "
     "the grass."),
    (29, "R1 R2 R3", f"Bird's-eye view of a green meadow by a stone cottage: {JIM}, {SEL} and {HANNAH} lay out huge "
     "pieces of white fabric spelling the giant word HELLO on the grass, a jet fighter flies low overhead."),
    (30, "R1", f"{JIM} stands in a green summer field looking at the viewer with a quiet smile, a stone cottage behind "
     "him, warm hopeful light, a jet contrail in the sky."),
]

REF_NAMES = {r: n for r, n, _ in REFS}


def full(prompt, n=0):
    if prompt.startswith("Character reference"):
        return f"{prompt} {STYLE}"
    head = "Use the attached reference images for the characters. "
    if n != 1:
        head = ("Match the art style, color palette and level of detail of the attached scene image exactly. " + head)
    style = STYLE
    if "HELLO" in prompt:
        style = style.replace("no text, no letters,", "no other text except the word HELLO on the grass,")
    return f"{head}{prompt} {style}"


if __name__ == "__main__":
    assert [n for n, *_ in SCENES] == [n for n, *_ in TEXT]
    text = {n: t.replace("**", "") for n, _, t in TEXT}
    out = ["# «28 дней спустя» · промты для Google Flow (Nano Banana)", "",
           "Формат 9:16. Сначала образцы R1–R5. Сцену 01 делай только с образцами героев,",
           "дальше прикрепляй готовую сцену 01 как образец стиля.", "", "## Образцы героев", ""]
    for r, nm, p in REFS:
        out += [f"### {r} · {nm}", "", full(p), ""]
    out += ["## Сцены", ""]
    for n, refs, p in SCENES:
        rr = ", ".join(f"{r} ({REF_NAMES[r]})" for r in refs.split()) or "без образцов"
        out += [f"### {n:02d} · образцы: {rr}", "", f"Голос: {text[n]}", "", full(p, n), ""]
    open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "PROMPTS.md"), "w").write("\n".join(out))
    print("PROMPTS.md:", len(REFS), "образцов,", len(SCENES), "сцен")
