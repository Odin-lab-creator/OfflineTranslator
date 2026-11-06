"""«Я — легенда» · промты для Google Flow (Nano Banana), формат 9:16.

Сначала генерируются образцы героев (REFS), потом сцены (SCENES) с этими образцами.
python3 prompts.py → PROMPTS.md
"""
import os

from script import SCENES as TEXT

STYLE = ("Detailed pixel art illustration in the style of a modern 16-bit retro game, crisp visible pixels, "
         "rich detail, cinematic lighting, muted desaturated colors, vertical 9:16 composition, "
         "no text, no letters, no logos, no watermark.")

REFS = [
    ("R1", "Невилл", "Character reference sheet. An original character: a fit Black man in his late 30s with short "
     "cropped hair and a short dark beard, tired determined eyes, grey hoodie over a dark t-shirt, olive cargo pants, "
     "brown boots, a scoped hunting rifle on a shoulder strap. Full body, front view and three-quarter view side by "
     "side, plain neutral grey background. Original design, not resembling any real actor."),
    ("R2", "Сэм", "Character reference sheet. A German Shepherd dog with a tan and black coat and a red collar. Full "
     "body side view and front view side by side, plain neutral grey background."),
    ("R3", "Анна и Итан", "Character reference sheet. Two original characters standing side by side: a woman in her "
     "early 30s with long dark wavy hair, olive field jacket and jeans; a quiet 10-year-old boy with short brown hair "
     "in an oversized blue hoodie. Full body, front view, plain neutral grey background. Original designs, not "
     "resembling any real actors."),
    ("R4", "Вожак", "Character reference sheet. The leader of infected creatures: bald head, pale grey skin, gaunt but "
     "muscular body, bloodshot eyes, wide screaming mouth, torn dark trousers, bare chest. Full body, front view, "
     "plain neutral grey background. Creepy but not gory."),
    ("R5", "Зои и Марли", "Character reference sheet. A Black woman in her early 30s with curly shoulder-length hair "
     "in a beige coat, holding the hand of a 6-year-old girl with braids in a pink jacket. Full body, front view, "
     "plain neutral grey background. Original designs, not resembling any real actors."),
]

# (№, образцы, промт сцены)
SCENES = [
    (1, "R1 R2", "Robert and his German Shepherd stand in the middle of an empty overgrown Times Square at golden "
     "hour, abandoned cars, tall grass growing through cracked asphalt, giant dark blank billboards, deer in the "
     "distance. Keep the top third of the image as open sky for a title."),
    (2, "", "A TV in a cozy living room shows a smiling female scientist in a lab coat at a press conference, a "
     "family watches hopefully from the sofa, warm evening light."),
    (3, "", "Panic on a New York street: people in face masks running, a military quarantine checkpoint, soldiers in "
     "hazmat suits, ambulances with flashing lights, smoke, overcast sky."),
    (4, "R4", "Inside a pitch-dark abandoned building, a crowd of pale bald infected creatures huddle together in the "
     "shadows, avoiding a single beam of sunlight from a broken window, eerie mood."),
    (5, "R1", "Wide shot of an empty overgrown Manhattan avenue, weeds and vines on the skyscrapers, abandoned cars. "
     "Robert with a scoped hunting rifle walks alone down the middle of the street, small figure, morning light."),
    (6, "R1 R2", "Robert drives a red classic 1960s muscle car with white racing stripes through empty city streets, "
     "his German Shepherd in the passenger seat with its head out of the window, sunny day, a rare happy moment."),
    (7, "R1", "Robert aims a scoped rifle from the hood of his car at a herd of deer running through an empty "
     "overgrown Times Square, giant blank billboards, tall grass."),
    (8, "R1 R2", "Noon at an empty river harbor with old sailing ships, Robert sits alone on the pier with a portable "
     "radio transmitter and a microphone, his German Shepherd lying beside him, sunny but melancholic."),
    (9, "R1 R2", "Night inside an old brownstone house: steel shutters over the windows, Robert lies in a bathtub "
     "hugging his German Shepherd and holding a rifle, dim candle light, terrifying shadows of creatures behind a "
     "frosted window."),
    (10, "R1", "Basement laboratory: Robert in a lab coat examines a test tube, cages with lab rats, rows of vials, a "
     "microscope, a wall covered with photos, cold fluorescent light."),
    (11, "R5", "Flashback with a faded warm tint: night evacuation of Manhattan, crowds at a military checkpoint on a "
     "bridge, helicopters with searchlights; the woman holds the little girl's hand, both look back worried."),
    (12, "R1", "Dark warehouse, a net trap has caught a pale infected woman lying unconscious in a beam of sunlight, "
     "Robert stands over her with a rifle."),
    (13, "R4", "The infected leader stands at the exact edge between deep shadow and bright sunlight in a doorway, "
     "screaming furiously, dust glowing in the sunbeam."),
    (14, "R1", "Robert caught in a rope snare, hanging upside down by one leg near a grand old train station, a store "
     "mannequin standing nearby, his rifle on the ground out of reach, shocked face."),
    (15, "R1 R2", "Robert still hanging upside down and wounded while the sun sets red behind the skyscrapers, long "
     "shadows creep toward him, his German Shepherd barks at the shadows."),
    (16, "R2", "Dusk: the German Shepherd fiercely fights off three pale hairless infected dogs to protect its owner, "
     "dramatic action, dust. Not gory."),
    (17, "R1 R2", "Dark laboratory: Robert sits on the floor holding his German Shepherd in his arms, tears in his "
     "eyes, the dog weak, cold blue light, tragic emotional moment."),
    (18, "R1", "Night: Robert's pickup truck with blinding headlights drives straight at a horde of pale infected "
     "creatures on a pier, sparks and dust, rage."),
    (19, "R3 R1", "Night, a bright flashlight beam: the woman with long dark hair and the boy in the blue hoodie lean "
     "over Robert lying unconscious, an old SUV with open doors behind them."),
    (20, "R3 R1", "Morning in a kitchen: the woman and Robert argue across a breakfast table, the boy quietly eats, "
     "thin warm light through closed shutters."),
    (21, "R4", "Night attack: dozens of pale infected creatures swarm over an old brownstone house, smashing windows "
     "and climbing the walls, led by the bald screaming leader, chaos."),
    (22, "R1", "Laboratory behind thick glass: the captured woman lies on a medical bed, her skin turning healthy "
     "again, Robert stares at her in amazement, glowing monitors."),
    (23, "R1 R3", "Close shot: Robert hands a small glass vial of blood to the woman, both faces lit by red emergency "
     "light, desperate and determined."),
    (24, "R3 R1", "The woman and the boy squeeze into a narrow old coal chute in a brick basement wall, looking out "
     "in fear, Robert closes the hatch."),
    (25, "R1 R4", "Robert stands with his back to the wall holding a grenade, the infected leader smashes his head "
     "against a cracking glass wall, spiderweb cracks, red emergency light."),
    (26, "", "A huge bright orange explosion bursts out of the windows of an old brownstone house at night, debris "
     "and smoke flying."),
    (27, "R3", "Autumn morning: the woman and the boy arrive at the gate of a fortified village with a wooden wall, "
     "soldiers open the gate, a white church steeple and golden trees behind, hope."),
    (28, "", "Sunrise over the empty Manhattan skyline seen from a bridge, warm golden light, birds flying, peaceful "
     "and hopeful."),
    (29, "R1", "Robert stands on the empty overgrown Times Square at dusk, looking over his shoulder at the viewer, a "
     "light of hope in the distance, mysterious mood."),
]

REF_NAMES = {r: n for r, n, _ in REFS}


def full(prompt):
    return f"{prompt} {STYLE}"


if __name__ == "__main__":
    assert [n for n, *_ in SCENES] == [n for n, *_ in TEXT]
    text = {n: t.replace("**", "") for n, _, t in TEXT}
    out = ["# «Я — легенда» · промты для Google Flow (Nano Banana)", "",
           "Формат 9:16. Сначала образцы героев R1–R5, потом сцены: к сцене прикрепляй указанные образцы.", "",
           "## Образцы героев", ""]
    for r, n, p in REFS:
        out += [f"### {r} · {n}", "", full(p), ""]
    out += ["## Сцены", ""]
    for n, refs, p in SCENES:
        rr = ", ".join(f"{r} ({REF_NAMES[r]})" for r in refs.split()) or "без образцов"
        out += [f"### {n:02d} · образцы: {rr}", "", f"Голос: {text[n]}", "", full(p), ""]
    open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "PROMPTS.md"), "w").write("\n".join(out))
    print("PROMPTS.md:", len(REFS), "образцов,", len(SCENES), "сцен")
