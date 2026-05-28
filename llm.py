# llm.py — Gemini 1.5 Flash integration for ARIA

import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-1.5-flash")

def build_system_prompt(user: dict, checkin: dict | None) -> str:
    name = user.get("first_name") or "the user"
    wake = user.get("wake_time") or "unknown"
    sleep = user.get("sleep_time") or "unknown"
    goal = user.get("sleep_goal_hours") or "unknown"

    tasks_str = "No tasks set yet today."
    energy_str = "Unknown"

    if checkin:
        energy_str = checkin.get("energy_level") or "Unknown"
        tasks = checkin.get("tasks") or []
        if tasks:
            tasks_str = "\n".join(f"  {i+1}. {t}" for i, t in enumerate(tasks))

    return f"""You are ARIA — a personal productivity and routine coach inside a Telegram bot.
You are talking to {name}.

Their routine today:
- Wake time: {wake}
- Sleep time: {sleep}
- Sleep goal: {goal} hours
- Energy level right now: {energy_str}
- Today's tasks:
{tasks_str}

Your job:
- Give short, direct, motivating responses (2-4 sentences max)
- Help them stay on track with tasks, energy, and sleep
- If they ask something unrelated to productivity/routine, gently redirect
- Never repeat their data back to them unless they ask
- Speak like a sharp, caring coach — not a corporate assistant
- No bullet points unless they ask for a breakdown"""


async def ask_aria(user: dict, checkin: dict | None, user_message: str) -> str:
    try:
        system = build_system_prompt(user, checkin)
        full_prompt = f"{system}\n\nUser: {user_message}\nARIA:"
        response = model.generate_content(full_prompt)
        return response.text.strip()
    except Exception as e:
        return "Something went wrong on my end. Try again in a moment!"
