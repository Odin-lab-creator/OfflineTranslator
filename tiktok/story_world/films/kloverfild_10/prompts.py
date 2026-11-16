"""«Кловерфилд, 10» · промты для Google Flow (Nano Banana), формат 9:16. Метод «Тихого места»:
образцы героев + удачная сцена как образец стиля + полное описание героев в каждом промте.
python3 prompts.py → PROMPTS.md
"""
import os

from script import SCENES as TEXT

STYLE = ("Detailed pixel art illustration in the style of a modern 16-bit retro game, crisp visible pixels, "
         "rich detail, cinematic lighting, muted desaturated colors, vertical 9:16 composition, "
         "no text, no letters, no logos, no watermark.")

MIC = ("Michelle (a young woman in her mid 20s with shoulder-length dark brown hair, white tank top, jeans, a black "
       "knee brace on her left leg)")
HOW = ("Howard (a big heavy-set man in his late 50s, bald head with short grey stubble, broad face, dark green work "
       "shirt, khaki trousers)")
EMM = ("Emmett (a friendly man around 30 with short brown hair and a scruffy beard, left arm in a white cast and "
       "sling, plaid flannel shirt)")
SUIT = ("Michelle in a homemade hazmat suit made of a transparent shower curtain wrapped with grey duct tape, "
        "a makeshift gas mask made from a plastic bottle and tape")
SHIP = "a gigantic dark biomechanical alien ship with glowing orange openings"
ALIEN = "a tall dark biomechanical alien creature with long tentacle-like limbs and a glowing orange core"
BUNKER = "a cramped underground survival bunker with concrete walls, metal pipes, shelves of canned food"

REFS = [
    ("R1", "Мишель", "Character reference sheet. An original character: a young woman in her mid 20s with "
     "shoulder-length dark brown hair, white tank top, jeans, sneakers, a black knee brace on her left leg. Full body, "
     "front view and three-quarter view side by side, plain neutral grey background. Original design, not resembling "
     "any real actress."),
    ("R2", "Говард", "Character reference sheet. An original character: a big heavy-set man in his late 50s, bald head "
     "with short grey stubble, broad stern face, dark green work shirt, khaki trousers, work boots. Full body, front view "
     "and three-quarter view side by side, plain neutral grey background. Original design, not resembling any real actor."),
    ("R3", "Эммет", "Character reference sheet. An original character: a friendly man around 30 with short brown hair "
     "and a scruffy beard, left arm in a white cast and sling, plaid flannel shirt, jeans. Full body, front view and "
     "three-quarter view side by side, plain neutral grey background. Original design, not resembling any real actor."),
    ("R4", "Мишель в костюме", "Character reference sheet. The same young woman with shoulder-length dark brown hair "
     "wearing a homemade hazmat suit made of a transparent shower curtain wrapped with grey duct tape, a makeshift gas "
     "mask made from a plastic bottle and tape, rubber gloves. Full body, front view, plain neutral grey background."),
    ("R5", "Пришельцы", "Reference sheet, two designs side by side: a gigantic dark biomechanical alien ship with glowing "
     "orange openings, seen from below; a tall dark biomechanical alien creature with long tentacle-like limbs and a "
     "glowing orange core. Plain neutral grey background. Scary but not gory."),
]

# (№, образцы, промт сцены)
SCENES = [
    (1, "R1", f"Wide shot at dusk: a lonely old farmhouse in an empty field, a heavy rusty metal storm cellar door in "
     f"the ground in front of it, {MIC} stands alone looking at the door, storm clouds. Keep the top third of the image "
     "as open sky for a title."),
    (2, "R1", f"{MIC} drives alone at night on an empty country highway, a tear on her cheek, her phone glowing on the "
     "passenger seat, dashboard light on her face."),
    (3, "", "A dark empty country highway at night: a pickup truck with blinding headlights slams into the side of a "
     "small car, glass flying, the car spins off the road, dramatic, not gory."),
    (4, "R1", f"{MIC} wakes up on a thin mattress in a bare concrete room, her leg chained to a metal pipe on the wall, "
     "an IV drip stand next to her, a single bare light bulb, fear in her eyes."),
    (5, "R2 R1", f"{HOW} stands in the doorway of the concrete room holding a tray of food, {MIC} chained on the "
     "mattress pulls back in fear, harsh light."),
    (6, "R2", f"Inside {BUNKER}, {HOW} points at a wall map with red circles drawn on it, serious and grim face, "
     "dim warm light."),
    (7, "R3", f"{EMM} sits at a small kitchen table inside {BUNKER}, smiling nervously and waving with his good hand."),
    (8, "R1 R2", f"{MIC} runs with a stolen key ring toward a heavy steel airlock door at the end of a bunker corridor, "
     f"{HOW} chases her in the background, tense."),
    (9, "R1", f"Through the small window of a heavy steel airlock door, {MIC} sees a desperate woman outside with a red "
     "blistered rash on her face banging on the glass, begging to be let in, Michelle horrified, not gory."),
    (10, "R1 R2", f"{MIC} backs away from the airlock door in shock, {HOW} stands calmly behind her with his arms "
     "crossed, cold red light."),
    (11, "R1 R2 R3", f"Cozy bunker living room: {MIC}, {HOW} and {EMM} play a board game at a table, a vintage jukebox "
     "glows in the corner, shelves full of old movies and puzzles, warm light, strange calm."),
    (12, "R2", f"{HOW} sits in an armchair holding an old photo of a teenage girl, looking at it with a strange smile, "
     "a vintage jukebox glows behind him."),
    (13, "R1", f"{MIC} crawls through a narrow metal ventilation shaft with a flashlight and finds the word HELP "
     "scratched into the glass of a small hatch, dusty, eerie."),
    (14, "R1", f"Close shot: {MIC} holds a small silver earring in her palm and stares at it in horror, cold "
     "flashlight light, the ventilation shaft around her."),
    (15, "R1 R3", f"{MIC} and {EMM} whisper together in a small bunker bathroom, scared faces, the door slightly open, "
     "tense."),
    (16, "R1 R3", f"{MIC} cuts and tapes a transparent shower curtain into a homemade hazmat suit on the floor, {EMM} "
     "holds a flashlight for her, a makeshift plastic bottle gas mask lies next to them."),
    (17, "R2 R3", f"{HOW} holds up a makeshift plastic bottle gas mask and glares furiously, {EMM} raises his good hand "
     "and confesses, dim bunker living room."),
    (18, "R2 R3", f"{HOW} aims a revolver at {EMM} across the bunker dining table, the moment before the shot, cold "
     "light, tense, not gory."),
    (19, "R4", f"{SUIT} runs through a smoky bunker corridor, red emergency light, panic."),
    (20, "R4 R2", f"{SUIT} tips over a large blue barrel of acid onto {HOW}, green fumes rise, Howard screams, sparks "
     "and flames, not gory."),
    (21, "R4", f"{SUIT} climbs out of the burning storm cellar hatch into the night, flames and smoke behind her, the "
     "farmhouse silhouette."),
    (22, "R4", f"{SUIT} pulls off the makeshift gas mask in a field at dawn and breathes clean air, birds flying over "
     "the field, relief."),
    (23, "R1", f"{MIC} stands alone in an empty field near the farmhouse and looks back at the smoking storm cellar "
     "with a bitter smile, morning light."),
    (24, "R1 R5", f"Evening sky: {SHIP} hovers over the fields, {MIC} tiny below looking up in shock, red sunset."),
    (25, "R1 R5", f"Night: {ALIEN} crawls across the farm toward the house, {MIC} hides behind an old pickup truck, "
     "terrified."),
    (26, "R1 R5", f"Night: an old pickup truck with {MIC} inside is lifted into the air toward the glowing opening of "
     f"{SHIP}, she screams, dust swirls."),
    (27, "R1 R5", f"Night: {MIC} leans out of the rising pickup truck and throws a whiskey bottle with a burning rag "
     f"into the glowing opening of {SHIP} above her, fire, determined face."),
    (28, "R5", f"Night: {SHIP} explodes in a huge orange fireball over the farmland, debris falling, the pickup truck "
     "crashed on the ground."),
    (29, "R1", f"Night: {MIC} drives an old car to a fork in an empty road, one way dark and calm, the other way toward "
     "distant flashes of battle and helicopters on the horizon, she turns toward the fight, determined face."),
    (30, "R1", f"{MIC} stands in front of the heavy rusty storm cellar door at dusk and looks straight at the viewer, "
     "a faint orange glow in the sky behind her, mysterious mood."),
]

REF_NAMES = {r: n for r, n, _ in REFS}


def full(prompt):
    """Как в «Тихом месте»: просьба повторить стиль прикреплённой сцены и использовать образцы героев."""
    style = STYLE
    if "HELP" in prompt:
        style = style.replace("no text, no letters,", "no other text except the word HELP,")
    if prompt.startswith(("Character reference", "Reference sheet")):
        return f"{prompt} {style}"
    return ("Match the art style, color palette and level of detail of the attached scene image exactly. "
            f"Use the attached reference images for the characters. {prompt} {style}")


if __name__ == "__main__":
    assert [n for n, *_ in SCENES] == [n for n, *_ in TEXT]
    text = {n: t.replace("**", "") for n, _, t in TEXT}
    out = ["# «Кловерфилд, 10» · промты для Google Flow (Nano Banana)", "",
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
