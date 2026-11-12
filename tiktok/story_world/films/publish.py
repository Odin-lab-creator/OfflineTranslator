"""Тексты для публикации роликов «Сюжет фильма за минуту»: TikTok и YouTube.
python3 publish.py → <фильм>/PUBLISH.md и publish_page.html (страница с кнопками «Копировать»)
Новый фильм — добавить запись в FILMS.
"""
import html
import os

HERE = os.path.dirname(os.path.abspath(__file__))
TAIL_YT = "Подпишись, чтобы не пропустить следующий фильм. Какой фильм разобрать дальше? Пиши в комментариях 👇"

FILMS = [
    {
        "dir": "../dela/alkatras", "name": "Побег из Алькатраса", "year": 1962, "dur": "~1:45",
        "tail": "Подпишись, чтобы не пропустить следующее дело. Какое реальное дело разобрать дальше? Пиши в комментариях 👇",
        "tt_title": "Побег из Алькатраса | Реальное дело",
        "tt_desc": "Трое сбежали из самой надёжной тюрьмы Америки — и исчезли навсегда 🌊 Реальное дело за минуту. Как думаешь, они доплыли? 👇",
        "tt_tags": "#алькатрас #реальноедело #трукрайм #побег #загадка #нераскрытоедело #историязаминуту #pixelart #alcatraz",
        "yt_title": "Побег из Алькатраса за 1 минуту | Реальное дело в пиксель-арте",
        "yt_desc": ("Июнь 1962 года. Фрэнк Моррис и братья Джон и Кларенс Энглин месяцами ковыряли ложками бетон, "
                    "слепили головы-куклы из мыла и бумаги, склеили плот из плащей и ночью ушли в ледяной залив "
                    "Сан-Франциско. Их так и не нашли — ни живыми, ни мёртвыми.\n\nКак думаешь, они доплыли?"),
        "yt_tags_top": "#алькатрас #реальноедело #shorts",
        "yt_tags": ["побег из алькатраса", "алькатрас", "алькатрас побег 1962", "фрэнк моррис", "братья энглин",
                    "реальное дело", "тру крайм", "true crime", "true crime на русском", "нераскрытые дела",
                    "загадочные истории", "реальные истории", "побег из тюрьмы", "самый известный побег",
                    "история за минуту", "escape from alcatraz", "alcatraz", "pixel art", "пиксель арт", "shorts"],
    },
    {
        "dir": "ptichiy_korob", "name": "Птичий короб", "year": 2018, "dur": "1:43",
        "tt_title": "«Птичий короб» за 1 минуту",
        "tt_desc": "Сними повязку — и ты умрёшь 🙈 «Птичий короб» за минуту. А ты смог бы прожить 5 лет с завязанными глазами? 👇",
        "tt_tags": "#птичийкороб #сюжетзаминуту #фильмзаминуту #кино #чтопосмотреть #ужасы #постапокалипсис #pixelart #birdbox",
        "yt_title": "«Птичий короб» за 1 минуту | Сюжет фильма в пиксель-арте",
        "yt_desc": ("«Птичий короб» (2018) за одну минуту. Мир захватили невидимые существа: кто их увидит, сходит с ума. "
                    "Малори с двумя детьми плывёт вслепую по реке к убежищу, а единственная защита — повязки на глазах "
                    "и птицы, которые чуют опасность.\n\nА ты смог бы прожить 5 лет с завязанными глазами?"),
        "yt_tags_top": "#птичийкороб #сюжетзаминуту #shorts",
        "yt_tags": ["птичий короб", "птичий короб сюжет", "птичий короб за минуту", "птичий короб пересказ",
                    "птичий короб концовка", "птичий короб 2018", "bird box", "bird box summary", "сюжет за минуту",
                    "фильм за минуту", "краткий пересказ фильма", "пересказ фильма", "фильм с завязанными глазами",
                    "фильмы ужасов", "триллер", "постапокалипсис", "фильмы про апокалипсис", "что посмотреть",
                    "пиксель арт", "pixel art", "shorts"],
    },
    {
        "dir": "tikhoe_mesto", "name": "Тихое место", "year": 2018, "dur": "1:49",
        "tt_title": "«Тихое место» за 1 минуту",
        "tt_desc": "Если они тебя услышат — ты не жилец 🤫 «Тихое место» за минуту. А ты смог бы прожить без единого звука? 👇",
        "tt_tags": "#тихоеместо #сюжетзаминуту #фильмзаминуту #кино #чтопосмотреть #ужасы #постапокалипсис #pixelart #aquietplace",
        "yt_title": "«Тихое место» за 1 минуту | Сюжет фильма в пиксель-арте",
        "yt_desc": ("«Тихое место» (2018) за одну минуту. Землю захватили слепые твари, которые охотятся на любой звук. "
                    "Семья Эбботт выживает в полной тишине, но ребёнок вот-вот родится, а оружие против тварей всё это "
                    "время было у глухой Риган за ухом.\n\nА ты смог бы прожить без единого звука?"),
        "yt_tags_top": "#тихоеместо #сюжетзаминуту #shorts",
        "yt_tags": ["тихое место", "тихое место сюжет", "тихое место за минуту", "тихое место пересказ",
                    "тихое место концовка", "тихое место 2018", "a quiet place", "a quiet place summary",
                    "сюжет за минуту", "фильм за минуту", "краткий пересказ фильма", "пересказ фильма",
                    "фильм про монстров", "фильмы ужасов", "фильм про пришельцев", "постапокалипсис", "что посмотреть",
                    "пиксель арт", "pixel art", "shorts"],
    },
    {
        "dir": "ya_legenda", "name": "Я — легенда", "year": 2007, "dur": "1:47",
        "tt_title": "«Я — легенда» за 1 минуту",
        "tt_desc": "Последний человек в Нью-Йорке… или нет? 🧟‍♂️ «Я — легенда» за минуту. А какая концовка лучше? 👇",
        "tt_tags": "#ялегенда #сюжетзаминуту #фильмзаминуту #кино #чтопосмотреть #постапокалипсис #pixelart #iamlegend",
        "yt_title": "«Я — легенда» за 1 минуту | Сюжет фильма в пиксель-арте",
        "yt_desc": ("«Я — легенда» (2007) за одну минуту. Вирусолог Роберт Невилл три года живёт один в пустом Нью-Йорке "
                    "с овчаркой Сэм и ищет лекарство от вируса, который превратил людей в тварей.\n\n"
                    "А ты знал, что у фильма есть альтернативная концовка? Какая лучше?"),
        "yt_tags_top": "#ялегенда #сюжетзаминуту #shorts",
        "yt_tags": ["я легенда", "я легенда сюжет", "я легенда за минуту", "я легенда пересказ", "я легенда концовка",
                    "я легенда альтернативная концовка", "я легенда 2007", "сюжет за минуту", "фильм за минуту",
                    "краткий пересказ фильма", "пересказ фильма", "роберт невилл", "последний человек на земле",
                    "фильм про вирус", "фильм про зомби", "постапокалипсис", "что посмотреть", "i am legend",
                    "i am legend summary", "pixel art", "shorts"],
    },
]


def texts(f):
    tt_desc = f"{f['tt_desc']}\n\n{f['tt_tags']}"
    yt_desc = f"{f['yt_desc']}\n\n{f.get('tail', TAIL_YT)}\n\n{f['yt_tags_top']}"
    tags = ", ".join(f["yt_tags"])
    assert len(tags) <= 500, (f["name"], len(tags))
    assert len(f["yt_title"]) <= 100 and len(tt_desc) <= 2200
    return [("TikTok · название", f["tt_title"]), ("TikTok · описание с хештегами", tt_desc),
            ("YouTube · название", f["yt_title"]), ("YouTube · описание с хештегами", yt_desc),
            ("YouTube · теги (через запятую)", tags)]


def md(f):
    out = [f"# «{f['name']}» · тексты для публикации", ""]
    for head, body in texts(f):
        out += [f"## {head}", "", body, ""]
    return "\n".join(out)


def page():
    esc = html.escape
    secs = []
    for i, f in enumerate(FILMS):
        cards = []
        for j, (head, body) in enumerate(texts(f)):
            pid = f"t{i}_{j}"
            cards.append(f'''<article class="card"><h3>{esc(head)}</h3>
<pre class="txt" id="{pid}">{esc(body)}</pre>
<button class="copy" type="button" data-target="{pid}">Копировать</button></article>''')
        secs.append(f'''<section><h2>«{esc(f["name"])}» <span class="meta">{f["year"]} · {f["dur"]}</span></h2>
{"".join(cards)}</section>''')
    return f'''<title>Сюжет за минуту: публикация</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Russo+One&family=PT+Sans:wght@400;700&family=JetBrains+Mono:wght@400&display=swap">
<style>
/* Тот же «кинозал», что у страниц с промтами: тёмный фон, фиолетовый акцент, жёлтые подписи. Тема одна, тёмная. */
:root {{ --bg:#0f0d14; --panel:#1a1622; --line:#2e2739; --fg:#ece8f2; --muted:#a39cb3; --violet:#9b63ff; --gold:#ffcf3f; --ok:#5fd38a;
  --display:"Russo One","Arial Black",system-ui,sans-serif; --body:"PT Sans","Segoe UI",system-ui,sans-serif;
  --mono:"JetBrains Mono",ui-monospace,Menlo,monospace; color-scheme:dark; }}
body {{ background:var(--bg); color:var(--fg); font:16px/1.5 var(--body); }}
.wrap {{ max-width:760px; margin:0 auto; padding-block:28px 64px; padding-left:max(16px, env(safe-area-inset-left, 0px));
  padding-right:max(16px, env(safe-area-inset-right, 0px)); display:grid; gap:32px; }}
.eyebrow {{ font:700 13px/1 var(--body); letter-spacing:.14em; text-transform:uppercase; color:var(--gold); }}
h1 {{ font:400 clamp(30px,8vw,46px)/1.05 var(--display); margin:6px 0 4px; text-wrap:balance; }}
h1 span {{ color:var(--violet); }}
.sub {{ color:var(--muted); margin:0; }}
section {{ display:grid; gap:12px; }}
h2 {{ font:400 24px/1.2 var(--display); margin:0; }}
.meta {{ font:400 14px var(--body); color:var(--muted); }}
.card {{ background:var(--panel); border:1px solid var(--line); border-radius:10px; padding:14px; display:grid; gap:10px; min-width:0; }}
h3 {{ margin:0; font:700 13px/1 var(--body); letter-spacing:.06em; text-transform:uppercase; color:var(--gold); }}
.txt {{ margin:0; font:13px/1.55 var(--mono); white-space:pre-wrap; word-break:break-word; background:var(--bg);
  border:1px solid var(--line); border-radius:6px; padding:10px 12px; user-select:all; }}
.copy {{ justify-self:start; font:700 15px/1 var(--body); color:#fff; background:var(--violet); border:0; border-radius:6px; padding:12px 16px; cursor:pointer; }}
.copy:focus-visible {{ outline:2px solid var(--gold); outline-offset:2px; }}
.copy.ok {{ background:var(--ok); color:var(--bg); }}
</style>
<div class="wrap">
  <div><span class="eyebrow">Сюжет фильма за минуту</span>
  <h1>Тексты для <span>публикации</span></h1>
  <p class="sub">Название, описание с хештегами и теги для TikTok и YouTube. Новый ролик — новый блок сверху.</p></div>
  {"".join(secs)}
</div>
<script>
document.querySelectorAll('.copy').forEach(function (btn) {{
  btn.addEventListener('click', function () {{
    var pre = document.getElementById(btn.dataset.target);
    function done() {{ btn.textContent = 'Скопировано'; btn.classList.add('ok');
      setTimeout(function () {{ btn.textContent = 'Копировать'; btn.classList.remove('ok'); }}, 1600); }}
    function fallback() {{ var r = document.createRange(); r.selectNodeContents(pre); var s = getSelection(); s.removeAllRanges(); s.addRange(r);
      btn.textContent = 'Текст выделен, скопируй вручную'; }}
    try {{ navigator.clipboard.writeText(pre.textContent).then(done, fallback); }} catch (e) {{ fallback(); }}
  }});
}});
</script>
'''


if __name__ == "__main__":
    for f in FILMS:
        open(os.path.join(HERE, f["dir"], "PUBLISH.md"), "w").write(md(f))
        print(f["name"], "теги:", len(", ".join(f["yt_tags"])), "симв.")
    open(os.path.join(HERE, "publish_page.html"), "w").write(page())
    print("publish_page.html")
