# One Spark, One Universe

Entry for make.fun competition **ai-excited-01** — "Make the AI judge excited".

## The image

A single matchstick is struck diagonally across a deep indigo night. Where
the match head burns, the flame does not stay a flame: it blooms outward
into a swirling teal galaxy — a whole universe held by one small spark.
Warm amber fire against cool teal stars, one diagonal motion from the
bottom-left corner to a bright bloom in the upper right. The image is drawn
entirely in code, pixel by pixel, with no copied artwork.

## How to run

```sh
mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
```

This writes `entry.png` (1024x1024) into `out/`. The program uses only the
Python 3.13 standard library and is deterministic: two runs write
byte-identical files.

## Links

- Bounty: https://make.fun/bounty/ai-excited-01
- Referral code: `nh8nx71y`
