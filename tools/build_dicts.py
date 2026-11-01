#!/usr/bin/env python3
"""Сжимает словарь WikDict (wdweb/<пара>.sqlite3) в компактную базу для приложения.

Использование: build_dicts.py source.sqlite3 out.db
Схема результата:
  entry(id, word, pos, gender, pronun, senses, importance)  senses = JSON [{"s": [...], "t": [...]}]
  form(form, entry_id, w)  form — нормализованная словоформа (строчные, без ударений, ё→е)
"""
import json
import sqlite3
import sys
import unicodedata


def norm(text):
    if text is None:
        return ""
    t = unicodedata.normalize("NFD", str(text).strip().lower())
    t = "".join(ch for ch in t if ch not in ("́", "̀"))
    t = unicodedata.normalize("NFC", t).replace("ё", "е")
    return t


def main(src, dst):
    s = sqlite3.connect(src)
    d = sqlite3.connect(dst)
    d.execute("PRAGMA page_size=4096")
    d.execute("PRAGMA journal_mode=DELETE")
    d.execute(
        "CREATE TABLE entry(id INTEGER PRIMARY KEY, word TEXT, pos TEXT, gender TEXT, "
        "pronun TEXT, senses TEXT, importance REAL)"
    )
    d.execute("CREATE TABLE form(form TEXT, entry_id INTEGER, w REAL)")
    d.execute("CREATE TABLE meta(key TEXT, value TEXT)")
    count = 0
    for rowid, word, pos, gender, pronuns, groups, importance in s.execute(
        "SELECT rowid, written_rep, part_of_speech, gender, pronuns, sense_groups, importance FROM translation_block"
    ):
        try:
            parsed = json.loads(groups) if groups else []
        except Exception:
            parsed = []
        senses = []
        for g in parsed or []:
            tr = [t for t in (g.get("translations") or []) if t]
            if not tr:
                continue
            senses.append({"s": [x for x in (g.get("senses") or []) if x][:3], "t": tr[:12]})
        if not senses or not word:
            continue
        pron = ""
        if pronuns:
            try:
                items = [p for p in json.loads(pronuns) if p and p != ";"]
                pron = ", ".join(items[:2])
            except Exception:
                pron = ""
        d.execute(
            "INSERT INTO entry VALUES (?,?,?,?,?,?,?)",
            (rowid, word, pos or "", gender or "", pron, json.dumps(senses[:10], ensure_ascii=False, separators=(",", ":")), importance or 0),
        )
        d.execute("INSERT INTO form VALUES (?,?,?)", (norm(word), rowid, 2.0))
        count += 1
    # Словоформы (dogs → dog, домами → дом), если они есть в исходнике.
    try:
        rows = s.execute("SELECT c0form, c1translation_block_rowid, c2form_importance FROM search_by_form_content")
        seen = set()
        for form, block, w in rows:
            key = norm(form)
            if not key:
                continue
            try:
                block = int(block)
            except Exception:
                continue
            if (key, block) in seen:
                continue
            seen.add((key, block))
            d.execute("INSERT INTO form SELECT ?, ?, ? WHERE EXISTS (SELECT 1 FROM entry WHERE id = ?)", (key, block, float(w or 1), block))
    except sqlite3.Error as e:
        print("forms skipped:", e, file=sys.stderr)
    # Убираем дубли «слово → та же статья» (заголовок уже добавлен с весом 2).
    d.execute("DELETE FROM form WHERE rowid NOT IN (SELECT min(rowid) FROM form GROUP BY form, entry_id)")
    d.execute("CREATE INDEX form_idx ON form(form)")
    d.execute("INSERT INTO meta VALUES ('entries', ?)", (str(count),))
    d.commit()
    d.execute("VACUUM")
    d.close()
    print(dst, "entries:", count)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
