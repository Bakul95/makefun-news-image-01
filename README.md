# makefun-news-image-01

[![make.fun](https://make.fun/badge/news-image-01)](https://make.fun/c/news-image-01)

One image that sums up Friday 13 November 2026's world news: a
one-page newspaper front page, drawn entirely in code.

- **Lead story:** Europe joins the next round of Ukraine peace
  talks; US envoys Kushner and Witkoff say so after meeting Putin
  in Moscow and Zelenskyy near Dublin, and the war's biggest
  prisoner swap is being prepared.
- **Gulf on edge:** Iran says it struck a US radar site in
  Bahrain; tankers hit in the Strait of Hormuz.
- **Nvidia:** Jensen Huang resigns as chief executive; shares fall
  16%; CFO Colette Kress named interim chief.
- **Microsoft down:** Outlook and Teams fail worldwide in a
  Microsoft 365 outage.
- **Crypto heist:** the DOJ wins court approval to seize $1.2bn
  from the Binance hack blamed on North Korea's TraderTraitor
  unit; the FBI says $400m was stolen through fake video calls.
- **Gaza:** an Israeli strike on the Khan Younis hospital kills
  six, a surgeon among them, at Nasser hospital.
- **Sport:** Harry Kane's 126th cap sets England's appearance
  record; England beat Croatia to reach the Nations League
  quarter-finals.
- **Also:** a record 483,200 US deportations in 2026; Pope Leo
  meets abuse survivors in Peru; Storm Charles hits Portugal; a
  Democrat wins the Kansas governor race; Google unveils Gemini 4
  for search.

## How it works

`main.py` uses only the Python standard library. It renders the
front page at 2x supersampling into a 2048x2048 RGB buffer (paper
texture, masthead, flags, and six pictograms are all drawn with
code: rectangles, discs, polygons, arcs, and a 5x7 bitmap font),
box-downsamples to 1024x1024, and writes the PNG with a
hand-rolled encoder. The output is deterministic: the same bytes
on every run, well under the 1 MiB limit.

## Run

```sh
MAKEFUN_OUTPUT_DIR=/tmp/out python3 main.py
# writes /tmp/out/entry.png (1024x1024)
```

## License

MIT. See [LICENSE](LICENSE).
