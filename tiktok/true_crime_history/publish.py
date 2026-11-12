"""Тексты для публикации канала True Crime History (рубрика «Реальное дело»): TikTok и YouTube.
python3 publish.py → cases/<дело>/PUBLISH.md и publish_page.html (страница с кнопками «Копировать»)
Новое дело — добавить запись в FILMS сверху.
"""
import html
import os

HERE = os.path.dirname(os.path.abspath(__file__))
TAIL_YT = "Подпишись, чтобы не пропустить следующее дело. Какую историю разобрать дальше? Пиши в комментариях 👇"

FILMS = [
    {
        "dir": "cases/nablyudatel", "name": "Наблюдатель", "year": 2014, "dur": "~1:45",
        "tt_title": "«Наблюдатель»: письма из ниоткуда | Реальное дело",
        "tt_desc": "Семья купила дом мечты, а через три дня пришло письмо: «Мой дед следил за этим домом… теперь моя очередь» ✉️ Реальное дело за минуту. А ты бы остался? 👇",
        "tt_tags": "#трукрайм #truecrime #реальноедело #сталкер #наблюдатель #нераскрытоедело #жуткиеистории #pixelart #thewatcher",
        "yt_title": "«Наблюдатель» за 1 минуту | Реальная история сталкера в пиксель-арте",
        "yt_desc": ("2014 год, Нью-Джерси. Семья Бродус купила дом мечты за $1,3 млн, и через три дня пришло письмо "
                    "от неизвестного «Наблюдателя»: его дед и отец следили за этим домом, теперь его очередь. "
                    "Семья так и не въехала, полиция никого не нашла, а дом продали с убытком почти $400 тысяч.\n\n"
                    "А ты бы остался жить в таком доме?"),
        "yt_tags_top": "#трукрайм #реальноедело #shorts",
        "yt_tags": ["наблюдатель", "наблюдатель реальная история", "the watcher", "the watcher true story",
                    "657 boulevard", "дом наблюдателя", "сталкер", "преследование", "тру крайм", "true crime",
                    "true crime на русском", "реальное дело", "нераскрытые дела", "жуткие истории",
                    "реальные истории", "загадочные письма", "true crime history", "pixel art", "пиксель арт", "shorts"],
    },
    {
        "dir": "cases/alkatras", "name": "Побег из Алькатраса", "year": 1962, "dur": "~1:45",
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

]


def texts(f):
    tt_desc = f"{f['tt_desc']}\n\n{f['tt_tags']}"
    yt_desc = f"{f['yt_desc']}\n\n{TAIL_YT}\n\n{f['yt_tags_top']}"
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
    return f'''<title>True Crime History: публикация</title>
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
  <div><span class="eyebrow">True Crime History · Реальное дело</span>
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
