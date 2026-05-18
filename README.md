# ARIA — Adaptive Routine Intelligence Agent

> An AI agent that doesn't give you a schedule — it negotiates your day with you in real time and rebuilds itself when you fall off.

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square)
![Telegram](https://img.shields.io/badge/Telegram-Bot%20API-26A5E4?style=flat-square)
![LLM](https://img.shields.io/badge/LLM-Mistral%20%2F%20GPT--4o-purple?style=flat-square)
![Status](https://img.shields.io/badge/Status-In%20Development-orange?style=flat-square)

---

## The Problem

Most people don't fail at productivity because they lack motivation.  
They fail because their tools don't adapt to them.

You sleep late → your schedule is now wrong → your app doesn't care → you abandon the day.

Static habit trackers, calendar apps, and to-do lists all share the same flaw: **they expect you to adapt to them.** ARIA flips this. It adapts to you.

---

## What ARIA Does

ARIA is a conversational AI agent that lives in your Telegram. Every day it:

- **Checks in with you** each morning — understands your energy, what carried over from yesterday, and what your day actually looks like
- **Builds your schedule dynamically** — not a fixed template, but a real plan based on your current state
- **Rebuilds in real time** — mark something skipped or done early and ARIA restructures the rest of your day automatically using constraint-based optimization
- **Learns your patterns** — after 2 weeks it knows your peak hours, your low-energy windows, what you consistently skip. It stops scheduling hard tasks at the wrong times.
- **Detects drift before you spiral** — 3 days of low energy check-ins triggers a flag: *"You've been running low since Tuesday. Want me to reduce today's load?"*
- **Gives you an honest weekly report** — not a streak counter. A real breakdown: completion rate, your worst day and why, patterns in what you do vs avoid.

---

## Why This Is Different

| Tool | What it does | What it can't do |
|---|---|---|
| Google Calendar | Stores your schedule | Doesn't adapt when life happens |
| Notion / Todoist | Tracks your tasks | Doesn't rebuild when you fall off |
| Habitica / Streaks | Gamifies habits | Doesn't understand your energy or context |
| **ARIA** | **Negotiates your day with you** | **— this is the gap** |

---

## System Architecture

```
User (Telegram)
      │
      ▼
┌─────────────────────┐
│   Telegram Bot API   │  ← Conversational interface
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│    LLM Layer         │  ← Natural language parsing + response generation
│  (Mistral / GPT-4o) │     "remind me to call mom after 6" → structured task
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Scheduling Engine   │  ← OR-Tools constraint optimization
│                      │     Handles priority, energy, time blocks, dependencies
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│   Behavioral ML      │  ← Time-series analysis on your real check-in data
│                      │     Learns peak hours, drift patterns, energy cycles
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│   Database Layer     │  ← Stores tasks, check-ins, completions, patterns
│  (SQLite → MongoDB)  │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Weekly Report Gen   │  ← LLM summarization + Matplotlib visualizations
└─────────────────────┘
```

---

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Interface | Telegram Bot API + `python-telegram-bot` | Conversational check-ins and task input |
| LLM | Mistral 7B via Groq API (free) or GPT-4o mini | Natural language understanding + report generation |
| Scheduling | Google OR-Tools | Constraint-based daily schedule optimization |
| ML | scikit-learn + pandas | Behavioral pattern learning from real user data |
| Automation | APScheduler (Python) | Morning check-ins, reminders, daily triggers |
| Storage | SQLite (dev) → MongoDB (prod) | User data, task history, check-in logs |
| Visualization | Matplotlib + Streamlit | Weekly report dashboard |
| Deployment | Railway / Render (free tier) | Always-on bot hosting |

---

## Project Structure

```
aria/
│
├── bot/
│   ├── main.py              # Telegram bot entry point
│   ├── handlers.py          # Message handlers and conversation flows
│   └── keyboards.py         # Inline keyboards and quick replies
│
├── core/
│   ├── scheduler.py         # OR-Tools constraint optimization engine
│   ├── llm.py               # LLM integration (parsing + generation)
│   ├── ml_engine.py         # Behavioral pattern learning
│   └── drift_detector.py    # Low energy / disengagement detection
│
├── data/
│   ├── models.py            # Database models
│   ├── db.py                # Database connection and queries
│   └── migrations/          # Schema migrations
│
├── reports/
│   ├── generator.py         # Weekly report generation
│   └── visualizer.py        # Matplotlib chart generation
│
├── automation/
│   └── scheduler_jobs.py    # APScheduler jobs (morning check-in, reminders)
│
├── config.py                # Environment variables and configuration
├── requirements.txt
└── README.md
```

---

## Getting Started

### Prerequisites
- Python 3.10+
- A Telegram account
- Groq API key (free) or OpenAI API key

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/aria-agent.git
cd aria-agent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys
```

### Environment Variables

```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
GROQ_API_KEY=your_groq_api_key
DATABASE_URL=sqlite:///aria.db
```

### Running ARIA

```bash
# Start the bot
python bot/main.py
```
### First Run Output

\```
ARIA is running...
\```

Open Telegram, search **@aria_routine_bot**, send `/start` and ARIA will respond.
---

## Roadmap

- [x] Project architecture and planning
- [ ] Telegram bot setup and basic message handling
- [ ] Morning check-in conversation flow
- [ ] Natural language task input via LLM
- [ ] OR-Tools scheduling engine
- [ ] Real-time schedule rebuild on task completion/skip
- [ ] SQLite data layer for check-ins and tasks
- [ ] Behavioral ML model on real user data
- [ ] Drift detection and proactive alerts
- [ ] Weekly report generation
- [ ] Deploy to Railway (always-on)
- [ ] WhatsApp integration via Twilio (planned)

---

## Evaluation Metrics

This project tracks real, measurable outcomes — not demo screenshots:

- **Active users** — people using it daily for 7+ days
- **Task completion rate** — before vs after using ARIA
- **Schedule rebuild frequency** — how often real-time adaptation is triggered
- **Drift detection accuracy** — precision/recall of low-energy flagging
- **Weekly report engagement** — do users read and act on it?

---

## ML Details

ARIA's behavioral model is trained entirely on **real user data** — your actual check-in responses, completion patterns, and energy levels logged over time. No synthetic data.

Features learned:
- Peak productivity windows per user
- Task categories most likely to be skipped
- Energy cycle patterns across days of the week
- Early signals of multi-day disengagement

Model: Time-series classification + behavioral clustering (scikit-learn)  
Training: Starts after 14 days of real usage data per user

---

## Author

**Dhara Prajapati**  
B.Tech CSE (AI & Data Science)  
---

## License

MIT License — feel free to use, modify, and build on this.

---

> *"Built because I kept making schedules I never followed. ARIA is the system I wished existed."*
