"""Generate word detail (examples + collocations) for the HSK 5-6 list via DeepSeek.

Usage:
    python tools/gen_details.py --count 40 --out data/details-05.js
    python tools/gen_details.py --count 200 --out data/details-06.js --batch 10

Reads DEEPSEEK_API_KEY from E:/Programming/llm-council/.env.
Skips any word that already has detail in data/details-*.js.
"""
import argparse, concurrent.futures as cf, glob, json, os, re, sys, time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV = r"E:/Programming/llm-council/.env"
API = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-v4-pro"

PROMPT = """You write vocabulary entries for a Mandarin study app aimed at HSK 5-6 learners.

For each word given, return one JSON object with exactly these keys:
  "w"  the word, copied unchanged
  "p"  Hanyu Pinyin of the word with tone marks, syllables separated by spaces
  "m"  concise English meaning, 2-6 words, semicolon-separated if several senses
  "d"  {"c","p","e"} one natural example sentence about ordinary daily life
  "k"  {"c","p","e"} one natural example sentence from a work/professional setting
  "x"  2-3 common collocations, each ["hanzi","pinyin","english"]
In "d" and "k": "c" is the Chinese sentence in simplified characters, "p" is its
pinyin with tone marks (syllables of a word joined, words separated by spaces,
sentence-initial capital), "e" is the English translation.

Rules:
- Sentences must be natural modern Mandarin a native speaker would actually say,
  8-16 characters, and must contain the target word.
- Use the word's most common everyday sense, not a rare or literary one.
- Collocations must be real fixed pairings, not invented phrases.
- Output a JSON array of these objects, in the same order as the input, nothing else.

Words:
"""


def load_key():
    for line in open(ENV, encoding="utf-8"):
        if line.startswith("DEEPSEEK_API_KEY"):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    sys.exit("DEEPSEEK_API_KEY not found in " + ENV)


def load_words():
    s = open(os.path.join(ROOT, "data/words.js"), encoding="utf-8").read()
    return json.loads(s[s.index("["):s.rindex("]") + 1])


def already_done():
    done = set()
    for f in glob.glob(os.path.join(ROOT, "data/details-*.js")):
        done |= set(re.findall(r'^\{w:"(.+?)"', open(f, encoding="utf-8").read(), re.M))
    return done


def ask(key, words):
    lines = "\n".join(
        f'{w["w"]}  (dictionary hint: {"; ".join(w["m"][:2])})' for w in words)
    body = json.dumps({
        "model": MODEL,
        "temperature": 0.4,
        "messages": [{"role": "user", "content": PROMPT + lines}],
        "response_format": {"type": "json_object"},
    }).encode()
    req = urllib.request.Request(API, body, {
        "Authorization": "Bearer " + key, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        txt = json.loads(r.read())["choices"][0]["message"]["content"]
    txt = txt.strip()
    if txt.startswith("```"):
        txt = re.sub(r"^```\w*\n|\n```$", "", txt)
    data = json.loads(txt)
    if isinstance(data, dict):                       # model wrapped the array
        for v in data.values():
            if isinstance(v, list):
                return v
        return [data]
    return data


def valid(e, want):
    try:
        return (e["w"] == want and e["p"] and e["m"]
                and all(k in e["d"] and e["d"][k] for k in "cpe")
                and all(k in e["k"] and e["k"][k] for k in "cpe")
                and len(e["x"]) >= 2 and all(len(p) == 3 for p in e["x"])
                and want in e["d"]["c"] and want in e["k"]["c"])
    except Exception:
        return False


def js(e):
    q = lambda s: json.dumps(s, ensure_ascii=False)
    return (f'{{w:{q(e["w"])},p:{q(e["p"])},m:{q(e["m"])},\n'
            f' d:{{c:{q(e["d"]["c"])},p:{q(e["d"]["p"])},e:{q(e["d"]["e"])}}},\n'
            f' k:{{c:{q(e["k"]["c"])},p:{q(e["k"]["p"])},e:{q(e["k"]["e"])}}},\n'
            f' x:[{",".join("[" + ",".join(q(t) for t in p) + "]" for p in e["x"][:3])}]}}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=40)
    ap.add_argument("--batch", type=int, default=10)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", required=True)
    ap.add_argument("--multi-char-only", action="store_true",
                    help="skip single characters (CC-CEDICT glosses for them are unreliable)")
    a = ap.parse_args()

    key = load_key()
    done = already_done()
    pool = [w for w in load_words() if w["w"] not in done]
    if a.multi_char_only:
        pool = [w for w in pool if len(w["w"]) >= 2]
    pool = pool[:a.count]
    print(f"{len(pool)} words to generate, {len(done)} already done")

    chunks = [pool[i:i + a.batch] for i in range(0, len(pool), a.batch)]

    def run(chunk):
        kept, bad = [], []
        for attempt in (1, 2, 3):
            try:
                res = ask(key, chunk)
                break
            except Exception as ex:
                print(f"  error ({ex}), retry {attempt}")
                res = []
                time.sleep(3 * attempt)
        by = {e.get("w"): e for e in res if isinstance(e, dict)}
        for w in chunk:
            e = by.get(w["w"])
            (kept if e and valid(e, w["w"]) else bad).append(e if e and valid(e, w["w"]) else w["w"])
        return kept, bad

    out, rejected = [], []
    with cf.ThreadPoolExecutor(max_workers=a.workers) as pool_ex:
        for n, (kept, bad) in enumerate(pool_ex.map(run, chunks), 1):
            out += kept
            rejected += bad
            print(f"  batch {n}/{len(chunks)}: {len(out)} kept, {len(rejected)} rejected", flush=True)

    path = os.path.join(ROOT, a.out)
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"// {os.path.basename(a.out)} — drafted by {MODEL}, review before trusting\n")
        f.write("window.HSK_DETAILS = (window.HSK_DETAILS || []).concat([\n")
        f.write(",\n".join(js(e) for e in out))
        f.write("\n]);\n")
    print(f"wrote {len(out)} entries to {a.out}")
    if rejected:
        msg = "rejected (need a rerun or hand-writing): " + " ".join(rejected)
        sys.stdout.buffer.write(msg.encode("utf-8") + b"\n")


if __name__ == "__main__":
    main()
