"""Страница с промтами для телефона: кнопка «Копировать» у каждого промта.  python3 page.py → flow_page.html"""
import html
import os
import re

from prompts import REFS, SCENES, REF_NAMES, full
MISSING = []  # всё генерируется заново
from script import SCENES as TEXT

esc = html.escape
text = {n: t for n, _, t in TEXT}


def voice(t):
    t = esc(t)
    return re.sub(r"\*\*(.+?)\*\*", r'<b class="key">\1</b>', t)


def card(pid, head, chips, line, prompt):
    chips_html = "".join(f'<span class="chip">{esc(c)}</span>' for c in chips)
    line_html = f'<p class="voice">{line}</p>' if line else ""
    return f'''
<article class="card" id="c-{pid}">
  <header class="card-head">
    <label class="done"><input type="checkbox" id="done-{pid}" data-id="{pid}"><span>{esc(head)}</span></label>
    <div class="chips">{chips_html}</div>
  </header>
  {line_html}
  <pre class="prompt" id="p-{pid}">{esc(prompt)}</pre>
  <button class="copy" type="button" data-target="p-{pid}">Копировать промт</button>
</article>'''


refs_html = "".join(card(r, f"{r} · {n}", [], "", full(p)) for r, n, p in REFS)
todo_html = "".join(
    card(f"s{n:02d}", f"Сцена {n:02d}", [f"{r} · {REF_NAMES[r]}" for r in refs.split()] or ["без образцов"],
         voice(text[n]), full(p, n))
    for n, refs, p in SCENES if n in MISSING)
scenes_html = "".join(
    card(f"s{n:02d}", f"Сцена {n:02d}", [f"{r} · {REF_NAMES[r]}" for r in refs.split()] or ["без образцов"],
         voice(text[n]), full(p, n))
    for n, refs, p in SCENES if n not in MISSING)

page = f'''<title>28 дней спустя: промты</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Russo+One&family=PT+Sans:ital,wght@0,400;0,700;1,400&family=JetBrains+Mono:wght@400;500&display=swap">
<style>
/* Плёночная лента: тёмный зал кинотеатра, фиолетовые ключевые фразы и жёлтые имена, как в формате «Сюжет за минуту». Тема одна, тёмная, намеренно. */
:root {{
  --bg: #0f0d14; --panel: #1a1622; --line: #2e2739; --fg: #ece8f2; --muted: #a39cb3;
  --violet: #9b63ff; --gold: #ffcf3f; --ok: #5fd38a;
  --display: "Russo One", "Arial Black", system-ui, sans-serif;
  --body: "PT Sans", "Segoe UI", system-ui, sans-serif;
  --mono: "JetBrains Mono", ui-monospace, "SFMono-Regular", Menlo, monospace;
  color-scheme: dark;
}}
body {{ background: var(--bg); color: var(--fg); font: 16px/1.5 var(--body); }}
.wrap {{ max-width: 760px; margin: 0 auto; padding-block: 28px 64px;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px));
  display: grid; gap: 28px; }}
.top {{ display: grid; gap: 6px; }}
.eyebrow {{ font: 700 13px/1 var(--body); letter-spacing: .14em; text-transform: uppercase; color: var(--gold); }}
h1 {{ font: 400 clamp(34px, 9vw, 54px)/1 var(--display); margin: 0; letter-spacing: .01em; text-wrap: balance; }}
h1 span {{ color: var(--violet); }}
.sub {{ color: var(--muted); margin: 0; }}
h2 {{ font: 400 22px/1.2 var(--display); margin: 0; text-wrap: balance; }}
.steps {{ margin: 0; padding-left: 1.3em; display: grid; gap: 6px; color: var(--fg); }}
.steps b {{ color: var(--gold); font-weight: 700; }}
.note {{ color: var(--muted); font-size: 14px; margin: 0; }}
section {{ display: grid; gap: 14px; }}
.progress {{ font: 500 13px/1 var(--mono); color: var(--muted); }}
.card {{ background: var(--panel); border: 1px solid var(--line); border-radius: 10px; padding: 14px; display: grid; gap: 10px; min-width: 0; }}
.card.is-done {{ border-color: color-mix(in srgb, var(--ok) 55%, var(--line)); }}
.card-head {{ display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 8px; }}
.done {{ display: flex; align-items: center; gap: 10px; font: 400 18px/1 var(--display); cursor: pointer; }}
.done input {{ width: 20px; height: 20px; accent-color: var(--ok); }}
.chips {{ display: flex; flex-wrap: wrap; gap: 6px; }}
.chip {{ font: 700 12px/1 var(--body); letter-spacing: .04em; text-transform: uppercase; color: var(--bg); background: var(--gold); padding: 5px 8px; border-radius: 4px; }}
.voice {{ margin: 0; font-style: italic; color: var(--muted); }}
.voice .key {{ color: var(--violet); font-style: normal; font-weight: 700; }}
.prompt {{ margin: 0; font: 13px/1.55 var(--mono); white-space: pre-wrap; word-break: break-word; background: var(--bg); border: 1px solid var(--line); border-radius: 6px; padding: 10px 12px; color: var(--fg); user-select: all; }}
.copy {{ justify-self: start; font: 700 15px/1 var(--body); color: #fff; background: var(--violet); border: 0; border-radius: 6px; padding: 12px 16px; cursor: pointer; }}
.copy:focus-visible, .done input:focus-visible {{ outline: 2px solid var(--gold); outline-offset: 2px; }}
.copy.ok {{ background: var(--ok); color: var(--bg); }}
@media (prefers-reduced-motion: no-preference) {{ .copy {{ transition: background .15s; }} }}
</style>

<div class="wrap">
  <div class="top">
    <span class="eyebrow">Сюжет фильма за минуту · выпуск 3</span>
    <h1>28 дней <span>спустя</span></h1>
    <p class="sub">Промты для Google Flow: внешность героев и заражённых прописана в каждой сцене. 5 образцов и 30 сцен, формат 9:16.</p>
  </div>

  <section aria-labelledby="how">
    <h2 id="how">Как генерировать</h2>
    <ol class="steps">
      <li>Во Flow выбери генерацию картинок (Nano Banana) и формат <b>9:16</b>.</li>
      <li>Сначала сделай образцы <b>R1–R5</b>. Выбери лучший вариант каждого и сохрани.</li>
      <li>Модель выбери <b>одну на все сцены</b> (лучше Nano Banana Pro) и не меняй до конца.</li>
      <li><b>Сцену 01</b> делай только с образцами героев. Дальше ко всем сценам прикрепляй <b>одну удачную сцену как образец стиля</b> (например, лабораторию 02) — фраза про стиль уже есть в начале каждого промта.</li>
      <li>Для сцен с заражёнными (жёлтая плашка R4) обязательно прикрепляй образец заражённого R4.</li>
      <li>Для каждой сцены прикрепи образцы с жёлтых плашек и вставь промт.</li>
      <li>Сохраняй картинки с номером сцены (01, 02 … 29) и присылай мне. Голос, субтитры и сборку сделаю я.</li>
    </ol>
    <p class="note">Галочки у сцен запоминаются на этом телефоне, так видно, что уже готово. Под сценой серым — что в этот момент говорит рассказчик.</p>
  </section>

  <section aria-labelledby="refs">
    <h2 id="refs">Образцы героев</h2>
    {refs_html}
  </section>

  <section aria-labelledby="scenes">
    <h2 id="scenes">Сцены</h2>
    <span class="progress" id="progress"></span>
    {scenes_html}
  </section>
</div>

<script>
(function () {{
  function store(k, v) {{ try {{ if (v === undefined) return localStorage.getItem(k); localStorage.setItem(k, v); }} catch (e) {{ return null; }} }}
  var boxes = Array.prototype.slice.call(document.querySelectorAll('.done input'));
  function paint() {{
    var scenes = boxes.filter(function (b) {{ return b.dataset.id.charAt(0) === 's'; }});
    var n = scenes.filter(function (b) {{ return b.checked; }}).length;
    document.getElementById('progress').textContent = 'Готово сцен: ' + n + ' из ' + scenes.length;
    boxes.forEach(function (b) {{ document.getElementById('c-' + b.dataset.id).classList.toggle('is-done', b.checked); }});
  }}
  boxes.forEach(function (b) {{
    b.checked = store('days28b-' + b.dataset.id) === '1';
    b.addEventListener('change', function () {{ store('days28b-' + b.dataset.id, b.checked ? '1' : '0'); paint(); }});
  }});
  paint();
  document.querySelectorAll('.copy').forEach(function (btn) {{
    btn.addEventListener('click', function () {{
      var pre = document.getElementById(btn.dataset.target);
      function done() {{ btn.textContent = 'Скопировано'; btn.classList.add('ok');
        setTimeout(function () {{ btn.textContent = 'Копировать промт'; btn.classList.remove('ok'); }}, 1600); }}
      function fallback() {{ var r = document.createRange(); r.selectNodeContents(pre); var s = getSelection(); s.removeAllRanges(); s.addRange(r);
        btn.textContent = 'Текст выделен, скопируй вручную'; }}
      try {{ navigator.clipboard.writeText(pre.textContent).then(done, fallback); }} catch (e) {{ fallback(); }}
    }});
  }});
}})();
</script>
'''
open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "flow_page.html"), "w").write(page)
print("flow_page.html", len(page), "байт")
