"""Серия 4 «Осада» (дни 60–83). Ответ на загадку 3-й серии в начале, «проблема → решение», загадка в конце.
Новые признаки: "decoy" — будильник в дальнем конце огорода и зомби, роющие там; "tunneldig" — тоннель к оврагу
растёт по ходу сцены (герой копает на его конце); "tunnel" убран из OFF, когда тоннель готов; "radio" — радио;
"ceilinghole" — мёртвые пробили потолок; "mityalead" — Митя уводит толпу по поверхности."""
B = ("dooropen", "grate", "garden", "clay")
SCENES = [
    (1, "ДЕНЬ 60", "Мёртвые роют яму прямо над вашей комнатой. С потолка **сыплется земля.**",
     [(16, None, None, B + ("zdig", "dirtfall", "hero=300,462,up,1", "anya=330,462,stand,-1", "mitya=530,588,stand,-1"))]),
    (2, "ДЕНЬ 60", "Митя шепчет: они идут на гул генератора. Вы глушите его, а в дальний угол огорода ставите старый будильник. **Толпа уходит рыть туда.**",
     [(16, None, None, B + ("zdig", "dirtfall", "hero=238,586,stand,1", "anya=270,586,stand,-1", "mitya=530,588,stand,-1")),
      (16, None, "ГЛУШИТЕ", B + ("lamp", "zdig", "hero=238,586,stand,1", "anya=270,586,stand,-1", "mitya=530,588,stand,-1")),
      (16, None, "ТОЛПА", B + ("lamp", "decoy", "hero=238,586,stand,1", "anya=270,586,stand,-1", "mitya=530,588,stand,-1"))]),
    (3, "ДЕНЬ 66", "Но люк теперь знают все мёртвые в округе. Нужен второй выход. Неделю ты роешь тоннель к оврагу, **подальше от дома.**",
     [(16, None, None, B + ("lamp", "hero=232,364,stand,1", "anya=200,462,stand,1")),
      (16, None, "РОЕШЬ", B + ("lamp", "-tunnel", "tunneldig", "anya=200,462,stand,1"))]),
    (4, "НОЧЬ 75", "Ночью Аня ловит на старом радио голос: выжившие, идите к реке, здесь безопасно. **Голос живой.**",
     [(16, None, None, B + ("lamp", "-tunnel", "night", "radio", "hero=250,462,sit,1", "anya=284,462,sit,-1"))]),
    (5, "НОЧЬ 75", "А Митя за решёткой мотает головой: не ходите, там их тысячи.",
     [(16, None, None, B + ("lamp", "-tunnel", "night", "radio", "hero=470,588,stand,1", "anya=500,588,stand,1", "mitya=530,588,stand,-1"))]),
    (6, "ДЕНЬ 80", "Без света огород засох, еды почти не осталось. Вы решаете уходить к реке через новый тоннель.",
     [(16, None, None, ("dooropen", "grate", "clay", "lamp", "-tunnel", "radio", "hero=330,586,stand,1", "anya=360,586,stand,-1"))]),
    (7, "НОЧЬ 82", "Но в ночь перед уходом мёртвые **пробивают потолок.** В дыру лезут руки. Ты отбиваешься лопатой, Аня заваливает дыру мешками. **Их слишком много.**",
     [(16, None, None, ("dooropen", "grate", "clay", "lamp", "-tunnel", "night", "radio", "ceilinghole", "dirtfall", "hero=296,462,dig,1", "anya=250,462,stand,1", "mitya=530,588,stand,-1")),
      (16, None, "МЕШКАМИ", ("dooropen", "grate", "clay", "lamp", "-tunnel", "night", "radio", "ceilinghole", "dirtfall", "sacks", "hero=330,462,dig,-1", "anya=286,462,give,1", "mitya=530,588,stand,-1"))]),
    (8, "НОЧЬ 82", "Тогда Митя срывает решётку, выходит наверх и уводит толпу за собой. **Его они не трогают.**",
     [(16, None, None, ("dooropen", "clay", "lamp", "-tunnel", "night", "radio", "ceilinghole", "sacks", "hero=296,462,stand,1", "anya=250,462,stand,1", "mitya=530,588,stand,-1")),
      (16, None, "УВОДИТ", ("dooropen", "clay", "lamp", "-tunnel", "night", "radio", "ceilinghole", "sacks", "mityalead"))]),
    (9, "ДЕНЬ 83", "Утром Мити нет. Вы с Аней собираете рюкзаки. И тут снова оживает радио.",
     [(16, None, None, ("dooropen", "clay", "lamp", "-tunnel", "radio", "ceilinghole", "sacks", "hero=250,462,stand,1", "anya=284,462,stand,-1"))]),
    (10, "ДЕНЬ 83", "Тот же голос говорит: мы ждём тебя у реки. **И называет тебя по имени.**",
     [(16, None, None, ("dooropen", "clay", "lamp", "-tunnel", "radio", "ceilinghole", "sacks", "hero=250,462,stand,1", "anya=284,462,stand,-1"))]),
]
OFF = ("tunnel", "shelf", "tools", "room2wood", "lantern", "snow")
TITLE = [("100 ДНЕЙ", "white", 315, "glitch140"), ("В БУНКЕРЕ", "red", 450, "glitch140"), ("СЕРИЯ 4", "purple", 570, "glitch66")]
END = [("ОТКУДА ОН", "white", 330, "glitch130"), ("ЗНАЕТ?", "red", 470, "glitch150")]
NEXT_FONT = "glitch60"
NEXT = "СЕРИЯ 5 — ФИНАЛ"
NAMES = {}
VOICE = "ep4_voice"
FINAL = "static"         # в конце — треск радио

if __name__ == "__main__":
    n = sum(len(t.replace("**", "")) for _, _, t, _ in SCENES)
    print(n, "символов")
