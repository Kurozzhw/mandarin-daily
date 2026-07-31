# 每日中文 · Daily Mandarin (HSK 5–6)

A daily vocabulary reader for HSK 3.0 levels 5 and 6. Twenty words a day, laid out to read
top to bottom — no flashcards, no quizzing.

Each word shows pinyin, English meaning, an example sentence from daily life, one from a work
setting, and its common collocations. Every sentence carries pinyin and a translation.

**2182 words · 110 days.**

## Running it

Static files, no build step and no dependencies. Open `index.html`, or serve the folder:

```bash
python -m http.server 5599
```

Your position — which day you're on and where you'd scrolled to — is stored in the browser's
localStorage, so it is per-device and does not sync.

## Layout

```
index.html              the whole app
data/words.js           2182 words: hanzi, traditional, pinyin, gloss, POS, HSK level, frequency
data/details-01..04.js  200 entries written by hand
data/details-05..07.js  1982 entries drafted by DeepSeek, validated on write
tools/gen_details.py    regenerates detail for any uncovered words
```

`tools/gen_details.py` skips words that already have entries, so it is safe to rerun. It reads
`DEEPSEEK_API_KEY` from a local `.env` outside this repo — no key is stored here.

## Credits

Word list and dictionary glosses come from
[complete-hsk-vocabulary](https://github.com/drkameleon/complete-hsk-vocabulary) (MIT), filtered
to its `new-5` and `new-6` levels. Its English definitions originate from
[CC-CEDICT](https://www.mdbg.net/chinese/dictionary?page=cc-cedict), licensed
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) — this project's word data
carries that license onward. Example sentences and collocations are original to this project.
