# PIXEL APOCALYPSE × PixelLab — серия 1 «72 ЧАСА» (вариант А, бесплатный тариф)

Сетка: кадр **108×192**, пиксель на экране 10×10. Персонажи **64px**, фоны **162×192** — всё в бесплатных лимитах.
Итог: **2 персонажа + анимации + 10 фонов (+1 вариант)**. Камеру, частицы, свет, субтитры, звук и проверку стиля
делаю я (`ingest.py` → монтаж).

---

## 1. Персонажи — Character Creator

Меню PixelLab → **Character Creator** → **Create from Text** → **Humanoid**.

| Настройка | Значение |
|---|---|
| Generation Mode | **v3** |
| Camera View | **Sidescroller** |
| Sprite Size | **64px** (ползунки 64×64) |
| Detail | **Highly detailed** |
| Outline | чёрный контур, если есть в списке; иначе Default |

Нужен вид **сбоку лицом вправо** (3-й кадр в GIF поворотов).

**HERO** — ✅ готов (`assets/hero_rot/`).

**ZOMBIE** → `zombie`
```
16-bit pixel art, dark post-apocalyptic survival game, muted gloomy colors: dark olive green, grey, dirty brown, rust red. Infected zombie, hunched forward, head low and pushed forward, pale grey-green skin, torn dirty beige shirt with dark blood stains, ragged grey pants with a hole at the knee, barefoot, one arm reaching forward, open mouth, dull red glowing eyes. Full body.
```

**Анимации** (в карточке персонажа — Animate / Animations; экспорт GIF или лист кадров):
| Файл | Что | Кадров |
|---|---|---|
| `hero_walk` | шаг вправо, цикл | 6–8 |
| `hero_idle` | дыхание, лёгкое покачивание | 4 |
| `hero_crouch` | присел на одно колено (поза или анимация) | 1–4 |
| `hero_sit` | сидит у стены, колени подняты | 1–4 |
| `zombie_walk` | шаркающая походка, рука тянется | 6–8 |
| `zombie_idle` | покачивание, голова дёргается | 4 |

## 2. Фоны — 162×192, без людей

Инструмент для картинок (Simple Creator / Pixelorama — уточним по интерфейсу). Размер **162×192**.
Вид сбоку, пол — горизонтально в нижней части (последние ~25 px). Палитру, если есть такая опция, —
`refs/palette_1px.png` + Force colors (не обязательно: цвета подгоню при приёмке).

**Начало каждого запроса:**
```
16-bit pixel art, side view screenshot of a dark post-apocalyptic side-scrolling survival game, muted gloomy palette: dark olive green, muted grey, dirty brown, charcoal black, rust red, faded orange, no people, no characters,
```
**Negative:** `text, letters, logo, watermark, UI, bright saturated colors, blur, anti-aliasing, photorealistic, 3d render`

| Файл | Сцена (после начала запроса) | Где в видео |
|---|---|---|
| `bg01_wake` | `abandoned apartment bedroom at dawn, large broken window on the right showing a burning ruined city with orange fire glow, torn green curtains, peeling wallpaper, unmade bed on the left, wooden floor with debris` | «Представь… проснулся» |
| `bg02_street` | `ruined city street at dawn, collapsed high-rise buildings with broken windows, open manhole hatch on cracked asphalt, abandoned rusty red car on the right, rubble, distant smoke` | «Связи нет» |
| `bg03_shop` | `inside an abandoned grocery store, empty metal shelves with a few cans, fallen shelf, shattered storefront window on the left with pale daylight, shopping cart, trash on tiled floor` | «Магазины закрыты» |
| `bg04_checkpoint` | `abandoned military checkpoint on a city road, sandbag wall with barbed wire, concrete barriers with faded red stripes, broken boom barrier, watchtower, abandoned army truck, ruined high-rises, overcast sky` | «паника», Правило №3 |
| `bg05_forest` | `city street reclaimed by forest, tree growing through cracked asphalt, vines on ruined facades, moss on the road, overgrown abandoned car in tall grass, light rays through haze` | «…что будет дальше» |
| `bg06_night_road` | `night, collapsed highway overpass with broken concrete span, burning wrecked car in the middle of the road, embers and smoke, dark ruined skyscrapers, full moon` | «ошибка…», финал |
| `bg07_storeroom` | `underground bunker storeroom, damp green stone brick wall, metal shelves with canned food, wooden table with two water jugs, canned food, first aid kit, batteries and a flashlight, caged wall lamp with warm glow, pipes and cables under the ceiling` | Правило №1, припасы |
| `bg08_corridor` | `underground bunker corridor, mossy green stone brick wall, heavy metal door with a small barred window, thin warm light strip under the door with two shadows of feet, caged wall lamp, rusty pipes, hanging cables, cobwebs, metal grate floor` | стук в дверь, Правило №2 |
| `bg09_radio` | `basement room at night, stone wall, boarded-up window with moonlight through the gaps, old radio with glowing orange dial on a wooden crate, candle stub, sleeping bag on the floor` | вторая ночь, радио |
| `bg09b_radio_off` | тот же фон, радио выключено (Inpaint / перегенерация с `switched-off radio, dark dial`) | «выключаешь радио», телефон |
| `bg10_window` | `dark apartment room at night, window on the right with an empty night street, a single street lamp and an abandoned car, dark open doorway on the left, peeling wallpaper, wooden floor` | «НЕ СМОТРИ В ОКНО» |

## 3. Как передать мне
Скачанные PNG / GIF — прямо в чат, с подписью-именем из таблиц. Можно частями.
Порядок: `hero_walk` → `zombie` → `bg08_corridor` → `bg07_storeroom` → остальное.
