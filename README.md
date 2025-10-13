# Random Cappuccino Bot

A Telegram bot that helps international students meet on campus.  
Each week it:
1) invites students to join the round,
2) pairs verified students by overlapping interests,
3) sends an intro to both,
4) collects feedback to improve future rounds.

Students must verify a university email from a whitelist of Italian universities before joining.

---

## How it works

- **Stack:** Python, `pyTelegramBotAPI` (`telebot`), APScheduler, SQLite.
- **DB:** `data/random_cappuccino.db`.
- **Polling:** `main.py` runs long polling and registers all handlers.
- **Scheduler:** `bot_scheduler.py` runs two weekly cron jobs (Europe/Rome):
  - Monday 10:00 — check bot status and run pairing.
  - Sunday 10:00 — request and collect feedback.
- **Matching:** pairs are formed by common interests; pairs and feedback are stored in `pair_registry`. If an odd user remains, the admin is notified.
- **Verification:** an email with a one-time code is sent via SMTP; the domain must be in the Italian universities allowlist.

Main user commands (set in `main.py`):  
`/start, /help, /profile, /about, /rules, /faq, /pause, /resume, /edit_profile, /delete_profile, /feedback`

---

## Repository structure

├─ data/
│ ├─ Logo/ # assets
│ ├─ images/ # assets
│ └─ random_cappuccino.db
├─ handlers/
│ ├─ admin_handlers.py
│ └─ user_handlers.py
├─ utils/
│ └─ init.py # DB helpers, pairing, email, etc.
├─ bot_scheduler.py
├─ config.env # example env file
├─ config.py # loads env/config
├─ main.py # entrypoint (polling + scheduler)
└─ requirements.txt

