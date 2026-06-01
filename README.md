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
