# ARIA — Adaptive Routine Intelligence Agent

ARIA is a personal productivity and routine coach that lives inside Telegram. It onboards you with your sleep/wake schedule, runs a daily morning check-in, builds an energy-aware time-blocked schedule for your tasks, sends smart reminders, and acts as an AI coach for free-form questions — all running 24/7 on AWS.

**Live bot:** [@aria_routine_bot](https://t.me/aria_routine_bot)

---

## Features

- **Personalized onboarding** — captures wake time, sleep time, sleep goal, daily task limit, and reminder frequency
- **Daily morning check-in** — logs sleep, energy level, and the day's tasks
- **Natural language task input** — type tasks however you like ("finish my assignment, go for a run and call mom") and Gemini parses them into a clean list
- **Energy-aware scheduling** — builds time blocks sized to your current energy (High/Medium/Low) with breaks in between
- **Smart reminders** — periodic nudges that only show incomplete tasks
- **Real-time schedule rebuild** — marking a task done with `/done` instantly regenerates the schedule for what's left
- **AI coach fallback** — any free-text message is answered by Gemini with full context of your routine
- **Weekly analytics** — an automatic Sunday-morning summary of your energy and task completion patterns
- **Alarms** — wake-up and wind-down reminders via APScheduler, restored automatically on restart

---

## Commands

| Command | Description |
|---|---|
| `/start` | Begin onboarding (or greet returning users) |
| `/checkin` | Run the daily morning check-in |
| `/schedule` | View today's time-blocked schedule |
| `/done <n>` | Mark task number `n` complete |
| `/done` | List today's tasks and completion status |
| `/alarms` | View your current settings |
| `/setalarm` | Change wake/sleep time, task limit, or reminder gap |
| `/history` | Show your last 5 check-ins |
| `/cancel` | Cancel the current conversation flow |

Any message that isn't a command is answered by the AI coach.

---

## Tech Stack

- **Language:** Python 3
- **Bot framework:** python-telegram-bot
- **LLM:** Google Gemini (via `google-genai` SDK)
- **Scheduling:** APScheduler (alarms, reminders, weekly report) + a custom energy-based time-block scheduler
- **Database:** MySQL (connection-pooled)
- **Hosting:** AWS EC2 (Ubuntu, Mumbai region), managed by systemd for 24/7 uptime and auto-restart on reboot

---

## Project Structure

```
aria-agent/
├── main.py         # Bot entry point, command + conversation handlers, schedulers
├── llm.py          # Gemini integration (AI coach + task parsing)
├── scheduler.py    # Energy-based time-block schedule builder + formatter
├── database.py     # MySQL layer (users, check-ins, task completions, analytics)
├── requirements.txt
├── .env            # Secrets (not committed)
└── .env.example    # Template for required environment variables
```

---

## Setup

### 1. Clone and install

```bash
git clone https://github.com/dharaprajapati127-blip/ARIA-Adaptive-Routine-Intelligence-Agent.git
cd ARIA-Adaptive-Routine-Intelligence-Agent
pip install -r requirements.txt
```

### 2. Configure environment

Copy the template and fill in your values:

```bash
cp .env.example .env
```

```
BOT_TOKEN=your_telegram_bot_token
GEMINI_API_KEY=your_gemini_api_key
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=aria
```

- Get a Telegram bot token from [@BotFather](https://t.me/BotFather)
- Get a free Gemini API key from [Google AI Studio](https://aistudio.google.com)

### 3. Set up MySQL

Create the database (tables are created automatically on first run):

```sql
CREATE DATABASE aria;
```

### 4. Run

```bash
python3 main.py
```

---

## Deployment (AWS EC2)

ARIA runs as a systemd service for 24/7 uptime:

```bash
sudo systemctl status aria     # check status
sudo systemctl restart aria    # restart after code changes
sudo journalctl -u aria -n 50  # view recent logs
```

The service is enabled to auto-start on reboot. A 1GB swap file is configured to keep the instance stable under low memory.

---

## Roadmap

- [x] Project architecture and planning
- [x] Telegram bot setup and basic message handling
- [x] Morning check-in conversation flow
- [x] Personalized onboarding flow (wake time, sleep time, sleep goal, reminder gap)
- [x] MySQL database layer for persistent storage
- [x] Wake-up alarm, task reminders, sleep alarm via APScheduler
- [x] `/setalarm`, `/done`, `/history`, `/alarms` commands
- [x] Deployed on AWS EC2 (Mumbai) — running 24/7
- [x] Natural language task input via LLM
- [x] Energy-based scheduling engine
- [x] Real-time schedule rebuild on task completion
- [x] Weekly report generation
- [ ] Behavioral ML model on real user data *(future)*
- [ ] Drift detection and proactive alerts *(future)*
- [ ] WhatsApp integration via Twilio *(planned)*

---

## License

Personal project by Dhara Prajapati.
