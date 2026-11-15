# Handoff: XENTED x ToshiBet wager leaderboard

Owner: Olly (Xented), UK. Promotes ToshiBet (toshi.bet/r/toshibetx) as an affiliate in his Discord. Repo: https://github.com/xentd/toshibet-leaderboard (public). Target: GitHub Pages at https://xentd.github.io/toshibet-leaderboard/ (own domain later).

## Decisions made
- Olly pays prizes himself (ToshiBet's Create Race tool failed: account credits were $0). Keep the pool small; commission is only ~0.07-0.15% of wagers.
- Wagers are tracked manually (CSV) or by a script on his PC. Page updates live from a JSON file on GitHub Pages.
- Repo is public, so only masked names + a hash go in leaderboard.json. Never commit real usernames, raw CSVs, config.json, tokens.

## Files (all in the package)
- index.html: self-contained page (dark Japanese-arena theme, gold/lacquer red, podium, find-your-rank, countdown). Fetches `leaderboard.json?v=<minute>` every 60s, re-renders only on change, keeps the searched rank highlighted, shows amber "may be delayed" if older than 90 min.
- leaderboard.json: `{demo, name, period, endsAt, updated, joinUrl, prizes[], players:[{m, h, w}]}` (m = masked name, h = FNV-1a 32-bit hex of lowercased trimmed name, w = wagered USD). Currently SAMPLE data with demo:true (shows a "Preview" ribbon).
- update_leaderboard.py: stdlib only. Reads config.json (copy of config.example.json). Sources: csv (name,wagered) | json_url (token from env var) | command (prints CSV/JSON). Sums duplicates case-insensitively, keeps top_n (50), masks + hashes, safety guard (rejects empty source or top wager dropping >50% unless --force), writes atomically, rewrites at least every heartbeat_minutes (30), git add/commit/push, `--loop N` (minimum 300s), `--no-git`.
- The Python mask()/fnv() MUST stay identical to the JS fnv() in index.html (verified equal for "kitsune_x" = 28ebfc71).
- README.md has setup steps. .gitignore should contain: config.json, players*.csv (except players.sample.csv), *.tmp, __pycache__/. Add .nojekyll too (optional).

## To do
1. Upload files to the repo, enable Pages (Settings > Pages > main / root).
2. Get a real per-player wager data source. ToshiBet has no known export yet; ask the partner manager/support for an export or API. Until then use a CSV.
3. Set real prizes, period, ends_at in config.json, set demo to false, run `python update_leaderboard.py --loop 600`.
4. Optionally add a line on the page saying prizes are paid by XENTED, and replace the expiring Discord CDN logo link in the Discohook embeds with a permanent host (Imgur).

## Instruction for Claude Code
The site is live on GitHub Pages (main / root). index.html was redesigned at Olly's request (Nov 2026): sticky nav with live status and timer, prize card, stats strip, podium with open-spot placeholders, board with prize cut-off and open prize rows, Discord preview (og.png) and favicon.png. Treat the current index.html as the approved design: make only the changes Olly asks for, and keep the leaderboard.json contract and fnv() unchanged. Copy edits Olly made: say "OFFICIAL link", not "XENTED link"; no affiliate-disclaimer paragraph, no preview ribbon. The board shipped empty (players: []) with prizes 2000,1000,625,375,300,225,175,125,100,75 ($5,000). Next: help set up config.json and the updater.
