# PIXEL APOCALYPSE × PixelLab — что генерировать для серии 1 «72 ЧАСА»

Итог: **2 персонажа + 5 анимаций + 10 фонов (+1 вариант)**. Из них собирается всё видео:
камеру, частицы, свет телефона, субтитры, звук и проверку стиля делает `video.py`.

---

## 0. Перед началом

- **Тариф 1 или выше.** Фон нужен 270×320 пикселей (камера ездит по нему вбок). Бесплатно PixelLab
  даёт максимум 200×200 — фон в кадр не влезет. Если 270×320 не принимается, делайте **180×320** (камера будет стоять).
- **Палитра.** Загрузите `refs/palette_1px.png` (или `refs/palette.gpl` в Aseprite) и включите **Force colors** —
  тогда картинка сразу в нашей палитре. Без этого скрипт приёмки всё равно переведёт цвета, но тени могут «сползти».
- **Образцы** (в `refs/`, родное разрешение, ничего не увеличивать):
  `hero_ref_128.png`, `hero_pipe_ref_128.png`, `zombie_ref_128.png` — как выглядят герои;
  `style_bunker_200.png`, `style_street_200.png` — образец стиля (инструменты со style image принимают до 200×200).

## 1. Общие настройки

| Параметр | Персонажи | Фоны |
|---|---|---|
| Холст | **128×128** | **270×320** |
| View | side | side |
| Outline | single color black outline | lineless / selective outline |
| Shading | detailed shading | medium / detailed shading |
| Detail | highly detailed | highly detailed |
| Background | transparent (no background) | — |
| Force colors | вкл, `palette_1px.png` | вкл, `palette_1px.png` |
| Seed | один и тот же для всех вариантов одного ассета | |

**Начало каждого запроса (стиль):**
```
16-bit pixel art, dark post-apocalyptic side-scrolling survival game, side view, limited muted palette: dark olive green, muted grey, dirty brown, charcoal black, rust red, faded orange, gloomy lighting,
```
**Negative description:**
```
text, letters, numbers, logo, watermark, UI, HUD, bright saturated colors, blur, anti-aliasing, gradient, photorealistic, 3d render, anime, chibi
```

## 2. Персонажи (холст 128×128, смотрят ВПРАВО, ступни на нижнем крае)

Герой ростом ~106 px — как в `hero_ref_128.png`. Загрузите этот файл как образец / init image.

**HERO** → файл `hero_idle.png`
```
young male survivor, short messy dark brown hair, stubble, rust-red high-collar jacket with zipper, olive green backpack with rolled sleeping mat on top, dark leather belt with pouch, grey cargo pants with brown knee pad, brown boots, standing, side view facing right, full body
```
Позы (тот же seed, отредактировать / сгенерировать от `hero_idle.png`):
- `hero_pipe.png` — `... holding a metal pipe raised in front of him, tense`
- `hero_crouch.png` — `... crouching on one knee, hiding, looking right`
- `hero_sit.png` — `... sitting on the floor with back against the wall, knees up, arm resting on knee, no backpack`

**ZOMBIE** → `zombie_idle.png` (образец `zombie_ref_128.png`)
```
infected zombie, hunched forward, head low and pushed forward, pale grey-green skin, torn dirty beige shirt with dark blood stains, ragged grey pants with a hole at the knee, barefoot, one arm reaching forward, open mouth, single dull red glowing eye, side view facing right, full body
```

**Анимации** (Skeleton animation на холсте 128×128 из готовых спрайтов; экспорт — GIF или лист кадров в ряд):
| Файл | Что | Кадров |
|---|---|---|
| `hero_walk.gif` | шаг вправо, цикл | 6–8 |
| `hero_idle_anim.gif` | дыхание, лёгкое покачивание | 4 |
| `hero_sit_anim.gif` | сидит, голова чуть поворачивается к радио | 4 |
| `zombie_walk.gif` | шаркающая походка, рука тянется | 6–8 |
| `zombie_idle_anim.gif` | покачивание, голова дёргается | 4 |

## 3. Фоны (270×320, БЕЗ людей — персонажей добавляю я)

Пол — горизонтально в нижней части кадра (примерно последние 40 px). В каждый запрос после стиля добавьте `no people, no characters`.

| Файл | Запрос (после стиля) | Где в видео |
|---|---|---|
| `bg01_wake.png` | `interior of an abandoned apartment bedroom at dawn, large broken window on the right showing a burning ruined city skyline with orange fire glow, torn green curtains, peeling wallpaper, unmade bed on the left, wooden floor with debris, rusty pipe along the ceiling` | 0:00 «Представь… проснулся» |
| `bg02_street.png` | `ruined city street at dawn, collapsed high-rise buildings with broken windows, open manhole hatch on cracked asphalt road, abandoned rusty red car on the right, rubble, distant smoke` | «Связи нет» |
| `bg03_shop.png` | `inside an abandoned grocery store, empty metal shelves with a few cans, one fallen shelf, shattered storefront window on the left with pale daylight, shopping cart, trash on a tiled floor, broken hanging ceiling panels` | «Магазины закрыты» |
| `bg04_checkpoint.png` | `abandoned military checkpoint on a city road, sandbag wall with barbed wire, concrete road barriers with faded red stripes, broken boom barrier, watchtower with a searchlight, abandoned army truck, ruined high-rises behind, overcast sky` | «паника», Правило №3 «слухи» |
| `bg05_forest.png` | `city street reclaimed by forest, a tree growing through cracked asphalt, vines covering ruined building facades, moss on the road, overgrown abandoned car in tall grass, light rays through haze, small birds` | «…что будет дальше» |
| `bg06_night_road.png` | `night, collapsed highway overpass with a broken concrete span and exposed rebar, burning wrecked car in the middle of the road, embers and smoke, dark ruined skyscrapers, full moon` | «ошибка может стать последней», финал |
| `bg07_storeroom.png` | `underground bunker storeroom, damp green stone brick wall, metal shelves with canned food and jars, wooden table with two water jugs, canned food, first aid kit, batteries and a flashlight, caged wall lamp with warm glow, pipes and hanging cables under the ceiling` | Правило №1, припасы, «вода» |
| `bg08_corridor.png` | `underground bunker corridor, mossy green stone brick wall with a patch of red bricks, heavy metal door with a small barred window in the center, thin warm light strip under the door broken by two shadows of feet, chair, caged wall lamp, rusty pipes, hanging cables, cobwebs, metal grate floor` | стук в дверь, Правило №2 |
| `bg09_radio.png` | `basement room at night, stone wall, boarded-up window with moonlight through the gaps, old radio with a glowing orange dial on a wooden crate, candle stub, sleeping bag on the floor, rifle leaning on the wall` | вторая ночь, радио |
| `bg09b_radio_off.png` | тот же фон, Inpaint только шкалы радио: `old radio with a dark switched-off dial` | «Ты выключаешь радио», телефон |
| `bg10_window.png` | `dark apartment room at night, window on the right showing an empty night street with a single street lamp and an abandoned car, dark open doorway on the left, peeling wallpaper, wooden floor with a loose plank` | «НЕ СМОТРИ В ОКНО», скрип, заражённый в проёме |

## 4. Как передать мне

Прикрепите файлы в чат **с именами из таблиц** (PNG, GIF; можно увеличенные — масштаб определю сам).
Я прогоню их через `ingest.py` (родные пиксели + палитра + проверка стиля), расставлю персонажей
на фонах, подключу к монтажу и пересоберу видео. Можно присылать частями — недостающее пока останется из текущей версии.

**Порядок, который даст результат быстрее всего:** `hero_idle` → `hero_walk` → `bg08_corridor` → `bg07_storeroom` → остальное.
