"""«Птичий короб» · промты для Google Flow (Nano Banana), формат 9:16. Метод как в «Тихом месте»:
образцы героев + удачная сцена как образец стиля + полное описание героев в каждом промте.
Твари в фильме невидимы — их не рисуем: только ветер, кружащиеся листья, тени.
python3 prompts.py → PROMPTS.md
"""
import os

from script import SCENES as TEXT

STYLE = ("Detailed pixel art illustration in the style of a modern 16-bit retro game, crisp visible pixels, "
         "rich detail, cinematic lighting, muted desaturated colors, vertical 9:16 composition, "
         "no text, no letters, no logos, no watermark.")

MAL = ("Malorie (a tough woman in her late 30s with shoulder-length dark brown hair tied back, olive green jacket, "
       "dark jeans)")
MAL_P = ("Malorie (a pregnant woman in her late 30s with shoulder-length dark brown hair, grey cardigan over a dark "
         "blue dress)")
BOY = "the Boy (a 5-year-old boy with short brown hair in a dark blue jacket)"
GIRL = "the Girl (a 5-year-old girl with long light brown hair in a faded pink jacket)"
TOM = "Tom (a kind man in his late 30s with dark skin, short black hair and a short beard, brown canvas jacket)"
OLY = "Olympia (a shy pregnant young woman with curly blonde hair in a light floral dress)"
GARY = ("Gary (an unsettling man in his 50s with a receding grey hairline, wire glasses and a beige knitted "
        "sweater)")
BLIND = "grey cloth blindfold over the eyes"
BIRDS = "three small green and yellow budgerigar birds in a cardboard box with air holes"
UNSEEN = "something invisible is near: leaves swirl in an unnatural wind and shadows move, no creature is shown"

REFS = [
    ("R1", "Малори", "Character reference sheet. An original character: a tough woman in her late 30s with "
     "shoulder-length dark brown hair tied back, olive green jacket, dark jeans, boots, a grey cloth blindfold hanging "
     "around her neck. Full body, front view and three-quarter view side by side, plain neutral grey background. "
     "Original design, not resembling any real actress."),
    ("R2", "Мальчик и Девочка", "Character reference sheet. Two original characters side by side: a 5-year-old boy "
     "with short brown hair in a dark blue jacket; a 5-year-old girl with long light brown hair in a faded pink "
     "jacket; both have grey cloth blindfolds pushed up on their foreheads. Full body, front view, plain neutral grey "
     "background."),
    ("R3", "Том", "Character reference sheet. An original character: a kind man in his late 30s with dark skin, "
     "short black hair and a short beard, brown canvas jacket, jeans, boots. Full body, front view and three-quarter "
     "view side by side, plain neutral grey background. Original design, not resembling any real actor."),
    ("R4", "Олимпия и Гэри", "Character reference sheet. Two original characters side by side: a shy pregnant young "
     "woman with curly blonde hair in a light floral dress; an unsettling man in his 50s with a receding grey "
     "hairline, wire glasses and a beige knitted sweater. Full body, front view, plain neutral grey background. "
     "Original designs, not resembling any real actors."),
    ("R5", "Птицы", "Reference sheet: three small green and yellow budgerigar birds sitting in an open cardboard box "
     "with air holes, front view and top view side by side, plain neutral grey background."),
]

# (№, образцы, промт сцены)
SCENES = [
    (1, "R1 R2 R5", f"{MAL}, {BOY} and {GIRL}, all wearing a {BLIND}, sit in a small wooden rowboat drifting on a "
     f"wide misty river through a dark forest at dawn, Malorie rows, {BIRDS} at her feet. Keep the top third of the "
     "image as open sky for a title."),
    (2, "R1 R2", f"Inside a dim wooden riverside shed, {MAL} kneels and firmly ties a {BLIND} on {GIRL}, {BOY} "
     "already blindfolded stands beside her, serious and scared, thin grey light through cracks in the walls."),
    (3, "R1 R2 R5", "Wide shot: a small wooden rowboat with a blindfolded woman and two blindfolded children pushes "
     "off from a rocky shore into thick white fog on a river, a cardboard box with birds in the boat."),
    (4, "R1", f"{MAL_P} stands in a cozy art studio full of canvases, watching a TV news report about mass panic in "
     "Europe, a paintbrush frozen in her hand, worried, warm lamp light."),
    (5, "", f"A city street in chaos: people stop and stare at the sky with frozen terrified faces, crashed cars, "
     f"smoke, people running in panic, {UNSEEN}, no violence."),
    (6, "R1 R3", f"{MAL_P} runs toward the front door of a big suburban house through a chaotic street, {TOM} holds "
     "the door open and reaches out his hand to her, urgent."),
    (7, "R1 R3", f"Inside a dim living room of a big house, a group of tense strangers (a grumpy older man with grey "
     f"hair, a young woman, a middle-aged man in a suit) sit apart from each other, {MAL_P} and {TOM} among them, "
     "candles, windows covered."),
    (8, "R3", f"{TOM} and other survivors tape thick blankets and newspapers over all the windows of a big house, "
     "thin lines of daylight through the gaps, tense."),
    (9, "", "A dark room lit only by security camera monitors, a man in a sweater leans close to the screens showing "
     "an empty garden where leaves swirl strangely, his face frozen in fear."),
    (10, "R1 R3", f"A car with all windows painted black drives slowly down an empty road full of abandoned cars; "
     f"inside, {TOM} drives using only the GPS screen and car sensors, {MAL_P} sits beside him holding her breath."),
    (11, "R1 R5", f"Inside an empty dusty supermarket, {MAL_P} carefully holds {BIRDS} in her hands, the birds "
     "chirping loudly, dim light through dirty windows."),
    (12, "R4 R1", f"{OLY} stands at the front door of the house, scared and shivering, {MAL_P} opens the door for "
     "her."),
    (13, "R4", f"{GARY} stands on the doorstep of the house at dusk, smiling politely, survivors look at him "
     "suspiciously from the doorway."),
    (14, "R4", f"Close shot: a sketchbook full of eerie pencil drawings of twisted shapes on {GARY}'s lap, he smiles "
     "strangely, dim candle light."),
    (15, "R4", f"{GARY} rips the blankets off the living room windows, bright daylight floods in, survivors cover their "
     f"eyes and scream, outside {UNSEEN}, no violence."),
    (16, "R1 R4", f"{MAL_P} and {OLY} are both in labor in a dim upstairs bedroom, holding each other's hands, "
     "scared, blankets over the windows, candle light."),
    (17, "R1 R3", f"{MAL} and {TOM} each hold a newborn baby wrapped in blankets in a dark quiet house, exhausted and "
     "grieving, candle light."),
    (18, "R1 R2 R3", f"Five years later: {TOM}, {MAL}, {BOY} and {GIRL} sit around an old radio in a boarded-up "
     "house, listening to a man's voice, hope on their faces, candle light."),
    (19, "R3", f"{TOM}, wearing a {BLIND}, bravely fights two wild-eyed men in the overgrown backyard of the house, "
     "protecting the family, dramatic, not gory."),
    (20, "R1 R2 R5", f"At a misty riverbank, {MAL} lifts blindfolded {BOY} into a small wooden rowboat, blindfolded "
     f"{GIRL} holds {BIRDS}."),
    (21, "R1 R2", f"A wild-eyed man stands on the foggy riverbank shouting to the boat, blindfolded {MAL} rows hard, "
     "the blindfolded children hug each other."),
    (22, "R1 R2", f"Blindfolded {MAL} in the rowboat listens to roaring rapids ahead, white water and rocks in front of "
     "them, she holds the blindfolded children close, a tense decision."),
    (23, "R1 R2", f"The small rowboat with blindfolded {MAL}, {BOY} and {GIRL} plunges into wild white-water rapids, "
     "spray everywhere, dramatic."),
    (24, "R1 R2", f"{MAL} drags the soaked blindfolded children onto a rocky riverbank, the capsized boat behind them, "
     "exhausted but alive."),
    (25, "R1 R2", f"A dark forest: blindfolded {MAL} holds the hands of the blindfolded children, {UNSEEN}, eerie."),
    (26, "R1", f"Blindfolded {MAL} crawls on the forest floor among roots and ferns, calling out desperately, one "
     "hand reaching forward, misty forest."),
    (27, "R1 R2 R5", f"Blindfolded {MAL} and the blindfolded children walk through the forest following the chirping "
     f"of {BIRDS} that she carries, soft light rays through the trees."),
    (28, "", "The gates of an old school with a stone wall among trees, blind people with white canes in the yard, "
     "hundreds of birds flying over the courtyard, safe and peaceful, sunlight."),
    (29, "R1 R2", f"In a bright school courtyard full of free-flying birds, {MAL} without a blindfold hugs {BOY} and "
     f"{GIRL}, both without blindfolds, tears of joy, warm sunlight."),
    (30, "R1", f"{MAL} with the blindfold lowered around her neck looks straight at the viewer, a misty river behind "
     "her, birds flying, mysterious hopeful mood."),
]

REF_NAMES = {r: n for r, n, _ in REFS}


def full(prompt):
    """Как в «Тихом месте»: просьба повторить стиль прикреплённой сцены и использовать образцы героев."""
    if prompt.startswith(("Character reference", "Reference sheet")):
        return f"{prompt} {STYLE}"
    return ("Match the art style, color palette and level of detail of the attached scene image exactly. "
            f"Use the attached reference images for the characters. {prompt} {STYLE}")


if __name__ == "__main__":
    assert [n for n, *_ in SCENES] == [n for n, *_ in TEXT]
    text = {n: t.replace("**", "") for n, _, t in TEXT}
    out = ["# «Птичий короб» · промты для Google Flow (Nano Banana)", "",
           "Формат 9:16. Сначала образцы R1–R5, сцену 01 — только с образцами,",
           "дальше прикрепляй образцы с плашек и удачную сцену как образец стиля.", "", "## Образцы", ""]
    for r, nm, p in REFS:
        out += [f"### {r} · {nm}", "", full(p), ""]
    out += ["## Сцены", ""]
    for n, refs, p in SCENES:
        rr = ", ".join(f"{r} ({REF_NAMES[r]})" for r in refs.split()) or "без образцов"
        out += [f"### {n:02d} · образцы: {rr}", "", f"Голос: {text[n]}", "", full(p), ""]
    open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "PROMPTS.md"), "w").write("\n".join(out))
    print("PROMPTS.md:", len(REFS), "образцов,", len(SCENES), "сцен")
