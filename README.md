# XENTED x ToshiBet Leaderboard (GitHub Pages)

`index.html` is the page. It reloads `leaderboard.json` every minute by itself.
`update_leaderboard.py` runs on your PC, writes that file and pushes it to GitHub.

## 1. Put it on GitHub Pages (once)
1. Create a new **public** GitHub repo (Pages needs public on free plans), e.g. `toshibet-leaderboard`.
2. Upload everything in this folder (or `git init`, `git add .`, `git commit`, `git remote add origin ...`, `git push -u origin main`).
3. Repo > Settings > Pages > Source: **Deploy from a branch** > `main` / root > Save.
4. After a minute your site is at `https://YOURNAME.github.io/toshibet-leaderboard/`.
5. Own domain later: Settings > Pages > Custom domain, then add the DNS record GitHub shows you.

## 2. Set up the updater on your PC
1. Install Python 3.8+ and Git. Make sure `git push` works from this folder without a password prompt (GitHub Desktop login, or a credential helper).
2. Copy `config.example.json` to `config.json` and edit:
   - `prizes`: what YOU will actually pay, 1st place first
   - `ends_at`: race end in UTC, `period`: label shown on the page
   - `source`: where the wagers come from (below)
3. Test without pushing: `python update_leaderboard.py --no-git`
4. Run for real, every 10 minutes: `python update_leaderboard.py --loop 600`

## 3. Wager data sources
Set `source` in `config.json` to one of:
- **csv** (manual): `{"type":"csv","path":"players.csv"}` with columns `name,wagered`. Edit the CSV, the script does the rest.
- **json_url** (API): `{"type":"json_url","url":"https://...","list_key":"data.users","name_key":"username","wager_key":"wagered","token_env":"TOSHI_TOKEN"}`. Put the token in an environment variable, never in a file.
- **command** (your own scraper): `{"type":"command","command":"python my_scraper.py"}`. It prints CSV (`name,wagered`) or a JSON list to stdout.

ToshiBet has not given us an official export yet. Ask your partner manager or support for a per-player wager export or API for your referrals.

## Good to know
- Names are masked and hashed in `leaderboard.json`; real names never leave your PC. Never commit `config.json`, CSVs or tokens (`.gitignore` already blocks them).
- Minimum loop is 5 minutes. GitHub limits how often Pages can rebuild, so 10 minutes is a good rhythm.
- Safety: an empty source, or a top wager that suddenly halves, is rejected and the old board stays up. `--force` overrides once.
- If the data is more than 90 minutes old the page shows an amber "may be delayed" notice.
- The file is rewritten at least every 30 minutes even with no changes, so the "Updated" time stays honest.
- Windows: Task Scheduler > run `python update_leaderboard.py --loop 600` at log on. Mac/Linux: run it in a terminal or `tmux`.
- Sample data is flagged `"demo": true`. Set it to `false` for the real race.
