# Fenrir weekly automation

Every Saturday 08:00 CET this repo pulls the week's closes (OMXS30, S&P 500, MSCI World via Yahoo),
appends the completed Friday to `data.json`, recomputes the Fenrir regime, bakes a fresh
`index.html` console with a Weekly Dispatch block, commits, and (optionally) emails you.

## One-time setup (~15 min)
1. Create a GitHub account if needed, then a new **private** repo, e.g. `fenrir`.
2. Upload the contents of this folder (keep the `.github/workflows/` path intact).
3. Repo Settings -> Pages -> Source: "Deploy from a branch" -> branch `main`, folder `/ (root)`.
   Your console will live at `https://<user>.github.io/fenrir/` (private repos need GitHub Pro for Pages —
   alternative: keep repo public but it only contains index prices, no personal data; or skip Pages and
   use the email attachment).
4. Optional email: repo Settings -> Secrets and variables -> Actions -> add
   `MAIL_SERVER` (e.g. smtp.gmail.com), `MAIL_USERNAME`, `MAIL_PASSWORD` (Gmail app password), `MAIL_TO`.
5. Actions tab -> `fenrir-weekly` -> "Run workflow" once to test.

## Rules of the pipeline
- History in `data.json` is immutable: the job only appends completed weeks, never revises.
- Each new week passes a +/-25% sanity check vs the prior week; rejects are logged in the dispatch.
- A missing MSCI World print carries the prior value forward (the OMX deployment never blocks on it).
- The dispatch flags approaching thresholds (RSI near 69/35, price within 3% of MA52, MACD% nearing -2)
  so next week's possible regime change announces itself.

## Weekly experience
Saturday morning: email (or visit the Pages URL) -> current regime, any SWITCH order for Monday,
the week's Fenrir return, machine readings, and watch-flags. The console itself carries the full
40-year record, gauges, codex and saga as before.
