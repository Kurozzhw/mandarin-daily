"""One-off: draft entries for HSK 5/6 words the source dataset omitted.

These are words whose base form is taught at a lower HSK level and which levels 5/6
re-introduce with a NEW sense — the official list marks that sense in parentheses,
e.g. 打（介） is 打 used as a preposition. The sense annotation is passed to the model
so the entry describes the level-5/6 meaning rather than the beginner one.

    python tools/gen_missing.py <missing_meta.json> data/details-08.js
"""
import json, os, re, sys, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from gen_details import load_key, valid, js, API, MODEL          # reuse the plumbing

POS_CN = {"名":"noun", "动":"verb", "形":"adjective", "副":"adverb", "量":"measure word",
          "代":"pronoun", "助":"particle", "介":"preposition", "连":"conjunction",
          "数":"numeral", "拟":"onomatopoeia", "叹":"interjection"}

PROMPT = """You write vocabulary entries for a Mandarin study app aimed at HSK 5-6 learners.

Each word below is listed in the official HSK 3.0 level 5/6 vocabulary WITH A SPECIFIC
SENSE in parentheses — often a different sense from the beginner meaning of the same
character. Write the entry for THAT sense only.

Return one JSON object per word with exactly these keys:
  "w"  the word, copied unchanged
  "p"  Hanyu Pinyin with tone marks for the sense in question (readings differ by sense:
       应 is yīng for "ought to" but yìng for "to respond")
  "m"  concise English meaning of that sense, 2-6 words
  "d"  {"c","p","e"} example sentence from ordinary daily life using that sense
  "k"  {"c","p","e"} example sentence from a work setting using that sense
  "x"  2-3 real collocations for that sense, each ["hanzi","pinyin","english"]
"c" is simplified Chinese, "p" its pinyin with tone marks, "e" the English translation.

Rules:
- Both sentences must contain the target word used in the specified sense.
- Natural modern Mandarin, 8-16 characters.
- Collocations must be real fixed pairings for that sense.
- Output a JSON array in the same order as the input, nothing else.

Words:
"""


def describe(r):
    ann = re.search(r"（(.+?)）", r["ann"])
    note = ""
    if ann:
        a = ann.group(1)
        if all(ch in POS_CN or ch == "、" for ch in a):
            note = "used as " + " / ".join(POS_CN[ch] for ch in a if ch in POS_CN)
        else:
            note = "as in " + a
    return (f'{r["w"]}  (HSK {r["l"]}; sense: {note or "general"}; '
            f'readings seen: {", ".join(r["pinyins"][:3])}; '
            f'dictionary senses: {"; ".join(r["cedict"][:4])})')


def main():
    meta, out_path = sys.argv[1], sys.argv[2]
    rows = json.load(open(meta, encoding="utf-8"))
    key = load_key()
    body = json.dumps({
        "model": MODEL, "temperature": 0.3,
        "messages": [{"role": "user",
                      "content": PROMPT + "\n".join(describe(r) for r in rows)}],
        "response_format": {"type": "json_object"},
    }).encode()
    req = urllib.request.Request(API, body, {
        "Authorization": "Bearer " + key, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        txt = json.loads(r.read())["choices"][0]["message"]["content"].strip()
    if txt.startswith("```"):
        txt = re.sub(r"^```\w*\n|\n```$", "", txt)
    data = json.loads(txt)
    if isinstance(data, dict):
        data = next(v for v in data.values() if isinstance(v, list))

    by = {e.get("w"): e for e in data if isinstance(e, dict)}
    kept, bad = [], []
    for r in rows:
        e = by.get(r["w"])
        (kept if e and valid(e, r["w"]) else bad).append(e if e and valid(e, r["w"]) else r["w"])

    with open(os.path.join(ROOT, out_path), "w", encoding="utf-8") as f:
        f.write(f"// {os.path.basename(out_path)} — HSK 5/6 entries missing from the source\n")
        f.write("// dataset, drafted by " + MODEL + " for the officially listed sense.\n")
        f.write("window.HSK_DETAILS = (window.HSK_DETAILS || []).concat([\n")
        f.write(",\n".join(js(e) for e in kept))
        f.write("\n]);\n")
    print(f"kept {len(kept)} / {len(rows)}")
    if bad:
        sys.stdout.buffer.write(("rejected: " + " ".join(map(str, bad))).encode("utf-8") + b"\n")


if __name__ == "__main__":
    main()
