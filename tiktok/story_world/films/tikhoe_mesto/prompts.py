"""«Тихое место» · промты для Google Flow (Nano Banana), формат 9:16.
Сначала образцы героев (REFS), потом сцены (SCENES) с этими образцами. python3 prompts.py → PROMPTS.md
"""
import os

from script import SCENES as TEXT

STYLE = ("Detailed pixel art illustration in the style of a modern 16-bit retro game, crisp visible pixels, "
         "rich detail, cinematic lighting, muted desaturated colors, vertical 9:16 composition, "
         "no text, no letters, no logos, no watermark.")

REFS = [
    ("R1", "Ли", "Character reference sheet. An original character: a rugged bearded father in his late 30s with "
     "short brown hair, tired gentle eyes, faded plaid flannel shirt, worn jeans, barefoot. Full body, front view and "
     "three-quarter view side by side, plain neutral grey background. Original design, not resembling any real actor."),
    ("R2", "Эвелин", "Character reference sheet. An original character: a pregnant woman in her 30s with long dark "
     "brown hair in a loose braid, simple grey cardigan over a light dress, barefoot, calm but strong. Full body, front "
     "view, plain neutral grey background. Original design, not resembling any real actress."),
    ("R3", "Риган и Маркус", "Character reference sheet. Two original characters side by side: a 12-year-old deaf "
     "girl with short blonde hair, a small hearing implant behind her ear, denim jacket, barefoot; a 10-year-old boy "
     "with messy dark hair in a green t-shirt, barefoot. Full body, front view, plain neutral grey background. "
     "Original designs, not resembling any real actors."),
    ("R4", "Бо", "Character reference sheet. A 4-year-old boy with short light brown hair in a plain blue t-shirt "
     "with a simple rocket drawing, holding a small toy space shuttle, barefoot. Full body, front view, plain neutral "
     "grey background."),
    ("R5", "Тварь", "Character reference sheet. A tall thin blind alien creature, dark armored skin, long spidery "
     "limbs, no eyes, a head made of layered armor plates that can open to reveal a soft inner ear, sharp claws. "
     "Full body, front view, plain neutral grey background. Scary but not gory."),
]

# (№, образцы, промт сцены)
SCENES = [
    (1, "R1 R2 R3", "A family walks barefoot single file along a sand path through a golden cornfield at sunset, "
     "the father leads with a finger to his lips, an old farmhouse in the distance. Keep the top third of the image "
     "as open sky for a title."),
    (2, "R5", "Night, an empty small-town street with abandoned cars, a tall blind armored creature stands among them "
     "tilting its head, listening, a fallen bicycle nearby, eerie moonlight."),
    (3, "R1 R2", "Inside an abandoned pharmacy, the father and the pregnant mother talk silently in sign language, "
     "barefoot on the dusty floor, scattered pills and empty shelves, soft daylight through dusty windows."),
    (4, "R4 R3", "The little boy in the abandoned store reaches up for a toy space shuttle on a high shelf, his older "
     "sister watches him, dusty toy aisle, soft daylight."),
    (5, "R1 R3 R4", "The father kneels and gently takes the batteries out of the toy shuttle, shaking his head, the "
     "little boy looks sad, the older sister stands behind them."),
    (6, "R4", "A long old wooden bridge over a river in a forest, the little boy stands alone in the middle holding the "
     "toy shuttle that lights up and makes noise, the rest of the family far ahead, tense moment."),
    (7, "R1", "The father runs desperately toward the camera along the bridge, arm reaching forward, face full of "
     "horror, a dark blur of movement at the edge of the frame."),
    (8, "", "Wide shot of an isolated farmhouse and a red barn among cornfields under a grey sky, a year later, quiet "
     "and lonely, a lantern on the porch."),
    (9, "R1", "A farm at dusk: paths of white sand lead between the house and the barn, strings of lightbulbs on poles, "
     "a red warning bulb glows, the father walks barefoot on the sand path."),
    (10, "R2", "The pregnant mother sits on the edge of a bed in a dim farmhouse bedroom, one hand on her belly, "
     "looking at a baby crib, worried and tender, warm candle light."),
    (11, "R3", "The deaf girl sits alone on a basement workbench full of radio parts and hearing devices, holding her "
     "hearing implant, sad and angry, cold lamp light."),
    (12, "R1 R3", "The father and his son stand by a loud waterfall in a forest, talking out loud, mist and spray "
     "around them, the son looks surprised that they can speak."),
    (13, "R2", "Close shot on the wooden basement stairs: a big rusty nail sticks up from a step, the pregnant mother's "
     "bare foot is about to step on it, dim light, suspense."),
    (14, "R2 R5", "The mother drops a picture frame that shatters on the floor, through the window behind her the "
     "silhouette of a blind creature turns its head toward the house."),
    (15, "R2", "The pregnant mother in labor flips a switch, red bulbs light up the whole farm around the house at "
     "night, she holds her belly in pain, biting her lip."),
    (16, "R3", "Night: the son lights fireworks in a field, bright colorful fireworks burst over the cornfield, he "
     "runs away from them, dramatic."),
    (17, "R2", "The mother lies in a bathtub in a dim bathroom with red light, giving birth silently, hand pressed over "
     "her own mouth, sweat and tears, a dark shape of a creature in the doorway behind the curtain."),
    (18, "R3", "The girl and the boy climb onto the top of a tall grain silo at night, holding hands, the farm with red "
     "lights below them."),
    (19, "R3", "Inside a grain silo, the boy sinks into the corn grain up to his chest, the girl pulls him out by the "
     "arms with all her strength, grain pouring down."),
    (20, "R3 R5", "Inside a dark grain silo, the blind creature recoils and twists in pain, the deaf girl in front of "
     "it holds her hand to her ear, sparks of sound in the air."),
    (21, "R1 R5", "Night, the father stands in front of an old pickup truck where the children hide, the creature "
     "attacks the truck, the father holds an axe, injured."),
    (22, "R1 R3", "Close shot: the injured father looks at his daughter through the truck window and signs I love you "
     "with his hand, tears in his eyes, red light on his face."),
    (23, "R3", "The deaf girl looks at her hearing implant in her palm with sudden realization, a light of hope in her "
     "eyes, dim basement."),
    (24, "R3 R2", "In the basement the girl holds her hearing implant to a microphone and turns the volume knob of a "
     "radio amplifier to the maximum, the mother holds the baby and a shotgun behind her."),
    (25, "R5", "Close shot: the blind creature in the basement doorway opens the armored plates on its head in pain, "
     "revealing the soft vulnerable inner part, sound waves in the air."),
    (26, "R2", "The mother fires a shotgun, a bright muzzle flash in the dark basement, determined face."),
    (27, "R5", "Wide night shot of the farm, several blind creatures run through the cornfield toward the house, "
     "lit by red lights."),
    (28, "R2 R3", "The mother cocks the shotgun with one sharp motion, the daughter stands beside her holding the "
     "hearing implant to the microphone, both look forward fearless, the baby sleeps in a box behind them."),
    (29, "R3", "The deaf girl stands in a golden cornfield at dawn, finger to her lips, looking at the viewer, "
     "mysterious mood."),
]

REF_NAMES = {r: n for r, n, _ in REFS}


def full(prompt):
    return f"{prompt} {STYLE}"


if __name__ == "__main__":
    assert [n for n, *_ in SCENES] == [n for n, *_ in TEXT]
    text = {n: t.replace("**", "") for n, _, t in TEXT}
    out = ["# «Тихое место» · промты для Google Flow (Nano Banana)", "",
           "Формат 9:16. Сначала образцы героев R1–R5, потом сцены: к сцене прикрепляй указанные образцы",
           "и одну удачную сцену как образец стиля.", "", "## Образцы героев", ""]
    for r, n, p in REFS:
        out += [f"### {r} · {n}", "", full(p), ""]
    out += ["## Сцены", ""]
    for n, refs, p in SCENES:
        rr = ", ".join(f"{r} ({REF_NAMES[r]})" for r in refs.split()) or "без образцов"
        out += [f"### {n:02d} · образцы: {rr}", "", f"Голос: {text[n]}", "", full(p), ""]
    open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "PROMPTS.md"), "w").write("\n".join(out))
    print("PROMPTS.md:", len(REFS), "образцов,", len(SCENES), "сцен")
