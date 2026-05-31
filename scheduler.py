from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
ENERGY_BLOCK = {
    "High 🔥": 90,
    "Medium ⚡": 60,
    "Low 🌙": 45,
}
BREAK_MINUTES = 15
def build_schedule(tasks: list[str], energy: str, wake_time: str, timezone: str = "Asia/Kolkata") -> list[dict]:
    block_mins = ENERGY_BLOCK.get(energy, 60)
    tz = ZoneInfo(timezone)
    now = datetime.now(tz)
    wh, wm = map(int, wake_time.split(":"))
    start = now.replace(hour=wh, minute=wm, second=0, microsecond=0)
    if start < now:
        start = now + timedelta(minutes=5)
    schedule = []
    current = start
    for task in tasks:
        end = current + timedelta(minutes=block_mins)
        schedule.append({
            "task": task,
            "start": current.strftime("%H:%M"),
            "end": end.strftime("%H:%M"),
            "duration": block_mins,
        })
        current = end + timedelta(minutes=BREAK_MINUTES)
    return schedule
def format_schedule(schedule: list[dict], energy: str) -> str:
    emoji = {"High 🔥": "🔥", "Medium ⚡": "⚡", "Low 🌙": "🌙"}.get(energy, "📌")
    lines = ["📅 *Your schedule for today:*\n"]
    for i, block in enumerate(schedule):
        lines.append(f"{block['start']} - {block['end']}  {emoji} {block['task']}")
        if i < len(schedule) - 1:
            break_end = datetime.strptime(block['end'], "%H:%M") + timedelta(minutes=15)
            lines.append(f"{block['end']} - {break_end.strftime('%H:%M')}  ☕ Break")
    return "\n".join(lines)
