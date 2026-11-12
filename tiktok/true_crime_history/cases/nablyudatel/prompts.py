"""«Наблюдатель» · промты для Google Flow (Nano Banana Pro), 9:16. Метод «Тихого места»:
образцы R1–R5 + удачная сцена как образец стиля + полное описание героев в каждом промте.
Наблюдателя НИКОГДА не показываем: только тень, силуэт без лица, рука в перчатке, фары машины.
Герои — реальные люди, рисуем оригинальных персонажей без портретного сходства.
python3 prompts.py → PROMPTS.md
"""
import os

from script import SCENES as TEXT

STYLE = ("Detailed pixel art illustration in the style of a modern 16-bit retro game, crisp visible pixels, "
         "rich detail, cinematic lighting, slightly muted colors, subtle suspense mood, all people have natural "
         "warm human skin tones (never blue or grey skin), colors and light match the time of day of the scene, vertical 9:16 composition, no readable text, no letters, no logos, no watermark.")

DEREK = ("Derek (a man around 40 with short dark brown hair, clean-shaven, navy blue quarter-zip sweater, "
         "khaki trousers)")
MARIA = ("Maria (a woman around 40 with shoulder-length wavy dark brown hair, cream knitted cardigan, dark jeans)")
KIDS = ("their three children (a 10-year-old girl with long brown hair in a red hoodie, an 8-year-old boy with short "
        "brown hair in a green striped t-shirt, a 5-year-old boy with blond hair in a light blue t-shirt)")
GIRL = "the 10-year-old girl with long brown hair in a red hoodie"
HOUSE = ("the house (a large white three-story Dutch colonial house from 1905 with a grey gambrel roof, black "
         "shutters, a wide front porch with white columns, tall old trees and a big green lawn)")
LETTER = ("a typewritten letter on white paper with tiny illegible typed lines and a plain white envelope without "
          "a return address")
WATCHER = "a dark faceless silhouette of a person standing in deep shadow, no face or features visible"

REFS = [
    ("R1", "Дерек", "Character reference sheet. An original character: a man around 40 with short dark brown hair, "
     "clean-shaven, navy blue quarter-zip sweater, khaki trousers, brown shoes. Full body, front view and "
     "three-quarter view side by side, plain neutral grey background. Original design, not resembling any real person."),
    ("R2", "Мария", "Character reference sheet. An original character: a woman around 40 with shoulder-length wavy "
     "dark brown hair, cream knitted cardigan over a white top, dark jeans, ankle boots. Full body, front view and "
     "three-quarter view side by side, plain neutral grey background. Original design, not resembling any real person."),
    ("R3", "Дети", "Character reference sheet. Three original children side by side: a 10-year-old girl with long "
     "brown hair in a red hoodie; an 8-year-old boy with short brown hair in a green striped t-shirt; a 5-year-old boy "
     "with blond hair in a light blue t-shirt. Full body, front view, plain neutral grey background."),
    ("R4", "Дом", "Reference sheet: a large white three-story Dutch colonial house from 1905 with a grey gambrel roof, "
     "black shutters, a wide front porch with white columns, tall old trees and a big green lawn, a mailbox at the "
     "curb. Front view and three-quarter view side by side, daylight."),
    ("R5", "Письмо", "Reference sheet: a typewritten letter on white paper with tiny illegible typed lines, folded "
     "in three, next to a plain white envelope without a return address, on a dark wooden table, top view, "
     "plain background."),
]

# (№, образцы, промт сцены)
SCENES = [
    (1, "R4", f"Night: {HOUSE} stands silent under a dark cloudy sky, one upstairs window faintly glowing, "
     f"across the street under a tree {WATCHER} watches the house. Keep the top third of the image as dark sky "
     "for a title."),
    (2, "R4", "A quiet leafy American suburban street in a small New Jersey town in summer, old trees, big "
     "colonial houses with lawns, a church steeple in the distance, peaceful sunny morning."),
    (3, "R1 R2 R4", f"{DEREK} and {MARIA} stand on the lawn in front of {HOUSE}, holding a key with a tag, smiling "
     "happily, a 'sold' sign on the lawn, sunny summer day."),
    (4, "R4", f"Inside {HOUSE}: a grand old wooden staircase, high ceilings, many doors, empty rooms with sunlight "
     "through tall windows, dust in the air."),
    (5, "R1 R2", f"{DEREK} and {MARIA} sit at a small kitchen table in a modest old apartment, looking at house "
     "photos on a laptop, a jar of saved coins on the table, warm lamp light, dreaming."),
    (6, "R2 R3", f"{MARIA} with {KIDS} runs through the empty sunny rooms of a big old house, the kids laughing and "
     "choosing their bedrooms, joyful."),
    (7, "R1 R4", f"Evening: {DEREK} on a ladder painting a wall in an empty room of {HOUSE}, paint cans and drop "
     "cloths on the floor, dark windows behind him, a single work lamp."),
    (8, "R1 R4 R5", f"Dusk: {DEREK} opens the mailbox at the curb in front of {HOUSE} and finds {LETTER} inside, "
     "his face uneasy, long shadows."),
    (9, "R1 R5", f"Close shot: {DEREK}'s hands unfold {LETTER} under a work lamp, the envelope has no return "
     "address, dramatic light, suspense."),
    (10, "R5 R4", f"Close shot: {LETTER} lying on the porch steps of {HOUSE} at dusk, a long dark shadow of a "
     "person falls across it, eerie."),
    (11, "R4", f"Old sepia-toned scene: {HOUSE} decades ago with old-fashioned cars on the street, the same tall "
     "trees, mysterious mood, as if remembered."),
    (12, "R4", f"Three generations: split vertical composition of {HOUSE} in the 1920s with an old car, in the "
     f"1960s with a vintage car, and today at night, in each era {WATCHER} stands across the street."),
    (13, "R3 R4", f"{KIDS} play on the front lawn of {HOUSE} on a sunny day, while far away behind a tree trunk "
     f"across the street {WATCHER} is half-hidden, the kids don't notice."),
    (14, "R5", f"Extreme close-up: the bottom of {LETTER}, a typed signature line, an old black typewriter in "
     "shadow nearby, cold light, ominous."),
    (15, "R1 R5", f"Night: {DEREK} in a dark kitchen speaks on his phone to the police, {LETTER} in his other hand, "
     "worried, blue moonlight through the window."),
    (16, "R1 R2", f"A police officer in a dark uniform talks quietly with {DEREK} and {MARIA} on a porch at night, "
     "the officer glances at the neighboring houses, tense."),
    (17, "R2", f"{MARIA} talks on the phone in a living room, shocked, one hand on her forehead, an old family photo "
     "of the house on the shelf behind her, warm lamp light."),
    (18, "", "An elderly couple stands in a doorway of an old house, the old man holds a single old letter and "
     "shrugs, the woman looks away awkwardly, soft daylight."),
    (19, "R1 R4 R5", f"{DEREK} pulls a second {LETTER} out of the mailbox of {HOUSE} on a grey cloudy day, his face "
     "pale."),
    (20, "R2 R3 R5", f"{MARIA} reads {LETTER} in horror, her hand over her mouth, in the background {KIDS} play "
     "with toys unaware, cold light."),
    (21, "R4", f"Inside {HOUSE}: an old plaster wall with a crack in a dark empty hallway, a flashlight beam on the "
     "wall, as if something is hidden inside, eerie."),
    (22, "R4", f"A dark old stone basement of {HOUSE}, a single bare bulb, a children's ball lies on the floor at "
     "the bottom of the narrow wooden stairs, shadows in the corners, creepy."),
    (23, "R4", f"Cross-section of {HOUSE} at night: warm lit rooms upstairs, a dark far basement below, the "
     "distance between them is huge, unsettling."),
    (24, "R4", f"Night street in front of {HOUSE}: many cars drive by with glowing headlights, one dark car slows "
     "down in front of the house, its driver only a shadow."),
    (25, "R4 R5", f"A short {LETTER} lies on the doormat of the dark empty porch of {HOUSE}, fallen leaves, lonely, "
     "melancholic and eerie."),
    (26, "R1 R2", f"{DEREK} and {MARIA} sit at a cramped kitchen table in their old small house among moving boxes "
     "they never unpacked, exhausted and worried, night."),
    (27, "R2 R3", f"{MARIA} holds the hands of {KIDS} tightly as they walk along a suburban sidewalk, looking around "
     "nervously, overcast day."),
    (28, "", "A police detective in a coat knocks on the door of a neighbor's old house at dusk, notebook in hand, "
     "curtains in the windows are drawn."),
    (29, "R5", f"A forensic lab: a scientist in gloves holds the envelope from {LETTER} under a blue light, DNA test "
     "tubes and a computer screen nearby, cold blue light."),
    (30, "R1", f"{DEREK} meets a serious older man in a dark suit, a former FBI agent, in a dim office, files and "
     "photos of the house spread on the desk."),
    (31, "R4", f"A private detective sits in a parked car at night with binoculars, watching {HOUSE} across the "
     "street, cold coffee on the dashboard."),
    (32, "R1 R2", f"{DEREK} and {MARIA} sit in a wooden courtroom with a lawyer, a judge in a black robe at the "
     "bench, serious mood."),
    (33, "R4", f"Daytime: a crowd of curious people and TV news vans with cameras gather on the street in front of "
     f"{HOUSE}, people take photos with phones."),
    (34, "", "A dark room lit only by several computer screens with maps and photos of a suburban street, a person "
     "in a hoodie seen from behind, red strings on a corkboard."),
    (35, "R1 R2", f"{DEREK} and {MARIA} sit on a couch watching TV news about themselves, sad, while phone screens "
     "next to them show angry comments as abstract red symbols."),
    (36, "R1 R4", f"{DEREK} unrolls a large architect's plan on a table showing two smaller new houses on the plot "
     f"of {HOUSE}, determined."),
    (37, "R1 R2", f"A town council meeting in a crowded hall, many neighbors raise their hands against, {DEREK} and "
     f"{MARIA} sit in the front row, disappointed."),
    (38, "R4", f"A new family with two kids carries boxes into {HOUSE} on a sunny day, a moving truck at the curb, "
     "the father glances at the mailbox uneasily."),
    (39, "R1 R5", f"Night: {DEREK} holds a new {LETTER}, his face lit by the cold light of a hallway lamp, anger "
     "and fear."),
    (40, "R5", f"Dark montage: {LETTER} on a table, its shadow forms the shapes of a car crash, flames and a "
     "hospital bed, symbolic, no violence."),
    (41, "R4", f"Day: a 'sold' sign on the lawn of {HOUSE} again, the grass a bit overgrown, cloudy sky, a sense of "
     "loss."),
    (42, "R4", f"A new owner checks the mailbox in front of {HOUSE} on a calm sunny day, it is empty, birds on the "
     "wires."),
    (43, "", f"A film set: cameras, lights and a director's chair in front of a big white colonial house, and far "
     f"away at the end of the street {WATCHER} watches."),
    (44, "R4", f"Triple composition: a curtain moving in a neighbor's window, a hand in a black glove typing on an "
     f"old typewriter, and {WATCHER} under a streetlight, mysterious."),
    (45, "R4", f"Present day night: {HOUSE} on the quiet street under a streetlight, fog, all windows dark."),
    (46, "R4", f"Night: view from across the street of {HOUSE}, in the foreground the dark shoulder of {WATCHER} "
     "in the corner of the frame, as if the viewer is the watcher, eerie."),
]

REF_NAMES = {r: n for r, n, _ in REFS}


def full(prompt):
    """Как в «Тихом месте»: просьба повторить стиль прикреплённой сцены и использовать образцы героев."""
    if prompt.startswith(("Character reference", "Reference sheet")):
        return f"{prompt} {STYLE}"
    return ("Match the art style, color palette and level of detail of the attached scene image exactly. "
            f"Use the attached reference images for the characters and the house. {prompt} {STYLE}")


if __name__ == "__main__":
    assert [n for n, *_ in SCENES] == [n for n, *_ in TEXT]
    text = {n: t.replace("**", "") for n, _, t in TEXT}
    out = ["# «Наблюдатель» · промты для Google Flow (Nano Banana Pro)", "",
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
