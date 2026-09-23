import streamlit as st
from database import get_connection
import calendar as calendar_module
from datetime import date, datetime
from google import genai
from google.genai import types
import json
import os
import re

from streamlit_mic_recorder import speech_to_text

st.set_page_config(page_title="RIVO", page_icon="🤖", layout="wide")

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    try:
        API_KEY = st.secrets["GEMINI_API_KEY"]
    except (KeyError, FileNotFoundError):
        API_KEY = None

client = genai.Client(api_key=API_KEY) if API_KEY else None

if "reschedule_suggestions" not in st.session_state:
    st.session_state.reschedule_suggestions = {}
if "reschedule_dismissed" not in st.session_state:
    st.session_state.reschedule_dismissed = set()
if "reschedule_accepted" not in st.session_state:
    st.session_state.reschedule_accepted = {}
if "stuck_tasks" not in st.session_state:
    st.session_state.stuck_tasks = set()
if "stuck_breakdown_done" not in st.session_state:
    st.session_state.stuck_breakdown_done = set()
if "theme" not in st.session_state:
    st.session_state.theme = "light"
if "tasks_view_open" not in st.session_state:
    st.session_state.tasks_view_open = False

theme_is_dark = st.session_state.theme == "dark"
st.markdown(
    f"""
    <style>
    :root {{
        --app-bg: {"#101827" if theme_is_dark else "#f4f7fb"};
        --panel: {"#172235" if theme_is_dark else "#ffffff"};
        --panel-soft: {"#1d2a40" if theme_is_dark else "#eef3f8"};
        --ink: {"#edf4ff" if theme_is_dark else "#172235"};
        --muted: {"#c7d5e8" if theme_is_dark else "#66758a"};
        --line: {"#48627f" if theme_is_dark else "#dbe4ee"};
        --accent: #36b7a5;
        --accent-soft: {"#173f45" if theme_is_dark else "#e0f5f1"};
        --button-bg: {"#284b57" if theme_is_dark else "#dceeea"};
        --button-text: {"#f4fffd" if theme_is_dark else "#12332f"};
        --button-hover: {"#356273" if theme_is_dark else "#c7e5df"};
    }}
    .stApp {{ background: var(--app-bg); color: var(--ink); }}
    .block-container {{ max-width: 1240px; padding-top: 2rem; padding-bottom: 4rem; }}
    h1, h2, h3, p, label, [data-testid="stMarkdownContainer"] {{ color: var(--ink); }}
    [data-testid="stHeader"] {{ background: transparent; }}
    [data-testid="stVerticalBlockBorderWrapper"] {{
        background: var(--panel); border: 1px solid var(--line); border-radius: 18px;
        box-shadow: 0 12px 30px rgba(16, 24, 39, .08); padding: .35rem .8rem;
    }}
    .dashboard-kicker {{ color: var(--accent); font-size: .78rem; font-weight: 700; letter-spacing: .12em; text-transform: uppercase; }}
    .dashboard-title {{ color: var(--ink); font-size: 2.15rem; font-weight: 800; letter-spacing: -.03em; margin: .15rem 0 .2rem; }}
    .dashboard-subtitle {{ color: var(--muted); font-size: 1rem; margin-bottom: .3rem; }}
    .metric-card {{ background: var(--panel); border: 1px solid var(--line); border-radius: 14px; padding: .8rem 1rem; }}
    .metric-label {{ color: var(--muted); font-size: .78rem; text-transform: uppercase; letter-spacing: .08em; }}
    .metric-value {{ color: var(--ink); font-size: 1.45rem; font-weight: 800; }}
    [data-testid="stDialog"], [data-testid="stDialog"] > div,
    [role="dialog"], [data-baseweb="modal"], [data-baseweb="modal"] > div,
    [data-baseweb="popover"] {{ background: var(--panel); color: var(--ink); }}
    [data-testid="stDialog"] h1, [data-testid="stDialog"] h2,
    [data-testid="stDialog"] h3, [data-testid="stDialog"] p,
    [data-testid="stDialog"] label, [role="dialog"] h1,
    [role="dialog"] h2, [role="dialog"] h3, [role="dialog"] p,
    [role="dialog"] label {{ color: var(--ink); }}
    [data-testid="stDialog"] [data-testid="stMarkdownContainer"],
    [role="dialog"] [data-testid="stMarkdownContainer"] {{ color: var(--ink); }}
    [data-baseweb="input"], [data-baseweb="textarea"],
    [data-baseweb="select"] > div, [data-baseweb="input"] > div,
    [data-baseweb="textarea"] > div {{
        background: var(--panel-soft); color: var(--ink); border-color: var(--line);
    }}
    input, textarea {{ background: var(--panel-soft) !important; color: var(--ink) !important; caret-color: var(--accent); }}
    input::placeholder, textarea::placeholder {{ color: var(--muted) !important; opacity: 1; }}
    [data-baseweb="select"] *, [data-baseweb="input"] *,
    [data-baseweb="textarea"] * {{ color: var(--ink); }}
    [role="listbox"], [role="option"], [data-baseweb="menu"] {{ background: var(--panel); color: var(--ink); }}
    [role="option"]:hover, [role="option"][aria-selected="true"] {{ background: var(--accent-soft); color: var(--ink); }}
    [data-testid="stRadio"] label, [data-testid="stCheckbox"] label,
    [data-testid="stSelectbox"] label, [data-testid="stNumberInput"] label,
    [data-testid="stDateInput"] label, [data-testid="stTextInput"] label,
    [data-testid="stTextArea"] label {{ color: var(--ink) !important; }}
    [data-testid="stRadio"] span, [data-testid="stCheckbox"] span {{ color: var(--ink); }}
    [data-testid="stRadio"] [role="radio"], [data-testid="stCheckbox"] [role="checkbox"] {{ border-color: var(--muted); }}
    [data-testid="stNumberInput"] button, [data-testid="stDateInput"] button {{
        background: var(--button-bg); color: var(--button-text); border-color: var(--line);
    }}
    [data-testid="stMetricLabel"], [data-testid="stMetricValue"],
    [data-testid="stMetricDelta"] {{ color: var(--ink) !important; }}
    [data-testid="stProgress"] > div {{ background: var(--panel-soft); }}
    [data-testid="stProgress"] > div > div {{ background: var(--accent); }}
    [data-testid="stAlert"] {{ background: var(--panel-soft); color: var(--ink); border-color: var(--line); }}
    [data-testid="stAlert"] p, [data-testid="stAlert"] div {{ color: var(--ink); }}
    [data-testid="stDialog"] button[aria-label="Close"],
    [role="dialog"] button[aria-label="Close"] {{ color: var(--ink); background: transparent; }}
    div.stButton > button {{
        background: var(--button-bg); color: var(--button-text); border: 1px solid var(--line);
        border-radius: 10px; min-height: 2.45rem; font-weight: 650;
    }}
    div.stButton > button p, div.stButton > button span {{ color: inherit; }}
    div.stButton > button:hover {{ background: var(--button-hover); color: var(--button-text); border-color: var(--accent); }}
    div.stButton > button:focus, div.stButton > button:focus-visible {{ color: var(--button-text); border-color: var(--accent); box-shadow: 0 0 0 .15rem var(--accent-soft); }}
    div.stButton > button:disabled {{ background: var(--panel-soft); color: var(--muted); border-color: var(--line); opacity: .7; }}
    div.stButton > button[kind="primary"] {{ background: var(--accent); border-color: var(--accent); color: #071b1a; }}
    div.stButton > button[kind="primary"] p, div.stButton > button[kind="primary"] span {{ color: #071b1a; }}
    div.stButton > button[kind="primary"]:hover {{ background: #2a9d90; color: #061917; }}
    [data-testid="stExpander"] {{ border-color: var(--line); background: var(--panel-soft); }}
    [data-testid="stExpander"] * {{ color: var(--ink); }}
    </style>
    """,
    unsafe_allow_html=True,
)

def insert_task(task_name, description, deadline, priority, estimated_time):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT INTO tasks
        (title, description, deadline, priority, estimated_time, status)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (task_name, description, str(deadline) if deadline else None, priority, estimated_time, "Pending")
    )
    connection.commit()
    connection.close()


def _gemini_response_text(response):
    response_text = getattr(response, "text", None)
    if isinstance(response_text, str) and response_text.strip():
        return response_text.strip()

    for candidate in getattr(response, "candidates", None) or []:
        content = getattr(candidate, "content", None)
        for part in getattr(content, "parts", None) or []:
            part_text = getattr(part, "text", None)
            if isinstance(part_text, str) and part_text.strip():
                return part_text.strip()

    return ""


def _parse_gemini_task_response(response):
    response_text = _gemini_response_text(response)
    if not response_text:
        return None

    fenced_match = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", response_text, re.IGNORECASE | re.DOTALL)
    if fenced_match:
        response_text = fenced_match.group(1).strip()

    try:
        result = json.loads(response_text)
    except (json.JSONDecodeError, TypeError):
        return None

    return result if isinstance(result, dict) else None


def interpret_voice_task(transcript):
    if client is None:
        st.error("Gemini is not configured. Switch to manual entry or configure the existing Gemini secret.")
        return None

    prompt = f"""
Extract task fields from the user's spoken task. Return ONLY valid JSON with these keys:
title, description, deadline, priority, estimated_time, deadline_ambiguous.

Rules:
- title is required and must contain only the task name.
- description is a string or null. Do not invent it.
- deadline is an ISO date (YYYY-MM-DD) or null. Resolve relative dates using today's date: {date.today().isoformat()}.
- If a deadline is unclear or has multiple reasonable interpretations, use null and set deadline_ambiguous to a short explanation.
- priority must be exactly Low, Medium, or High, or null when not mentioned.
- estimated_time is a number of hours or null when not mentioned.
- Do not invent missing information.

Spoken task:
{transcript}
"""

    try:
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        result = _parse_gemini_task_response(response)
        if result is None:
            st.warning("I couldn't understand the task details. Please edit the recognized text or try speaking again.")
            return None

        deadline = result.get("deadline")
        if deadline:
            try:
                deadline = date.fromisoformat(str(deadline))
            except (TypeError, ValueError):
                deadline = None
        priority = result.get("priority")
        if priority not in {"Low", "Medium", "High"}:
            priority = None
        estimated_time = result.get("estimated_time")
        if estimated_time is not None:
            try:
                estimated_time = max(float(estimated_time), 0.5)
            except (TypeError, ValueError):
                estimated_time = None
        return {
            "title": str(result.get("title") or "").strip(),
            "description": str(result.get("description") or "").strip(),
            "deadline": deadline,
            "priority": priority,
            "estimated_time": estimated_time,
            "deadline_ambiguous": str(result.get("deadline_ambiguous") or "").strip(),
        }
    except Exception:
        st.warning("I couldn't understand the task details. Please edit the recognized text or try speaking again.")
        return None


def load_quick_notes():
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT id, note_text, created_at
        FROM quick_notes
        ORDER BY created_at
        """
    )
    notes = cursor.fetchall()
    connection.close()
    return notes


def insert_quick_note(note_text):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT INTO quick_notes (note_text)
        VALUES (?)
        """,
        (note_text,)
    )
    connection.commit()
    connection.close()


def delete_quick_note(note_id):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("DELETE FROM quick_notes WHERE id = ?", (note_id,))
    connection.commit()
    connection.close()


def quick_note_error_message(error):
    message = str(error)
    for secret_name in ("SUPABASE_URL", "SUPABASE_KEY", "GEMINI_API_KEY"):
        secret_value = os.getenv(secret_name)
        if not secret_value:
            try:
                secret_value = st.secrets.get(secret_name)
            except (KeyError, FileNotFoundError):
                secret_value = None
        if secret_value:
            message = message.replace(str(secret_value), "[redacted]")
    return f"{type(error).__name__}: {message}"



def initialize_quick_note_state():
    defaults = {
        "quick_notes_view": "list",
        "quick_note_mode": "manual",
        "quick_note_voice_text": "",
        "quick_note_recorder_key": 0,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def show_quick_note_dialog():
    initialize_quick_note_state()
    st.subheader("📄 Add Quick Note")
    mode = st.radio(
        "How would you like to add it?",
        ["✍️ Type Manually", "🎙️ Add Using Voice"],
        index=0 if st.session_state.quick_note_mode == "manual" else 1,
        key="quick_note_add_mode",
        horizontal=True,
    )
    st.session_state.quick_note_mode = "manual" if mode.startswith("✍️") else "voice"

    if st.session_state.quick_note_mode == "voice":
        st.write("Speak the reminder exactly as you want it saved.")
        transcript = speech_to_text(
            language="en",
            start_prompt="🎙️ Start Speaking",
            stop_prompt="⏹️ Stop Recording",
            just_once=True,
            key=f"quick_note_recorder_{st.session_state.quick_note_recorder_key}",
        )
        if transcript:
            st.session_state.quick_note_voice_text = transcript
            st.session_state.quick_note_voice_input = transcript

        note_text = st.text_area(
            "Review your note",
            key="quick_note_voice_input",
        )
        if st.button("🎙️ Try Again", key="quick_note_retry"):
            st.session_state.quick_note_voice_text = ""
            st.session_state.quick_note_recorder_key += 1
            st.rerun()
    else:
        note_text = st.text_area("What should you remember?", key="quick_note_manual_input")

    add_col, cancel_col = st.columns(2)
    with add_col:
        if st.button("✅ Save Note", type="primary", key="quick_note_save"):
            if not note_text.strip():
                st.warning("Please enter a note.")
            else:
                try:
                    insert_quick_note(note_text.strip())
                except Exception as error:
                    st.error(f"Quick Notes storage error: {quick_note_error_message(error)}")
                else:
                    st.session_state.quick_note_voice_text = ""
                    st.session_state.quick_note_recorder_key += 1
                    st.session_state.quick_notes_view = "list"
                    st.success("Quick note added.")
                    st.rerun()
    with cancel_col:
        if st.button("❌ Cancel", key="quick_note_cancel"):
            st.session_state.quick_note_voice_text = ""
            st.session_state.quick_note_recorder_key += 1
            st.session_state.quick_notes_view = "list"
            st.rerun()


@st.dialog("📝 Quick Notes", width="small")
def render_quick_notes_panel():
    initialize_quick_note_state()
    if st.session_state.quick_notes_view == "add":
        show_quick_note_dialog()
        return

    with st.container(border=True):
        st.subheader("📝 Quick Notes")
        if st.button("+ Add Note", key="open_quick_note", use_container_width=True):
            st.session_state.quick_notes_view = "add"
            st.rerun()

        try:
            notes = load_quick_notes()
        except Exception as error:
            st.error(f"Quick Notes load error: {quick_note_error_message(error)}")
            return

        if not notes:
            st.caption("No quick notes yet.")
            return

        for display_number, note in enumerate(notes, start=1):
            note_id, note_text, _created_at = note
            note_col, delete_col = st.columns([6, 1])
            with note_col:
                st.write(f"{display_number}. {note_text}")
            with delete_col:
                if st.button("🗑️", key=f"delete_quick_note_{note_id}", help="Delete this note"):
                    try:
                        delete_quick_note(note_id)
                    except Exception as error:
                        st.error(f"Quick Note delete error: {quick_note_error_message(error)}")
                    else:
                        st.rerun()
            if display_number < len(notes):
                st.markdown("---")


def initialize_voice_state():
    defaults = {
        "dialog_mode": "manual",
        "voice_transcript": "",
        "voice_result": None,
        "voice_recorder_key": 0,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


@st.dialog("➕ Add a Task")
def show_add_task_dialog():
    initialize_voice_state()
    mode = st.radio(
        "How would you like to add it?",
        ["✍️ Type Manually", "🎙️ Add Using Voice"],
        index=0 if st.session_state.dialog_mode == "manual" else 1,
        key="dialog_mode_choice",
        horizontal=True,
    )
    st.session_state.dialog_mode = "manual" if mode.startswith("✍️") else "voice"

    if st.session_state.dialog_mode == "voice":
        st.write("Speak naturally, including any deadline, priority, or estimated time.")
        transcript = speech_to_text(
            language="en",
            start_prompt="🎙️ Start Speaking",
            stop_prompt="⏹️ Stop Recording",
            just_once=True,
            key=f"voice_recorder_{st.session_state.voice_recorder_key}",
        )
        if transcript and transcript != st.session_state.voice_transcript:
            st.session_state.voice_transcript = transcript
            st.session_state.voice_result = None

        if st.session_state.voice_transcript:
            st.markdown("**🎙️ You said:**")
            st.info(f'"{st.session_state.voice_transcript}"')
            if st.button("🎙️ Try Again", key="voice_retry"):
                st.session_state.voice_transcript = ""
                st.session_state.voice_result = None
                st.session_state.voice_recorder_key += 1
                st.rerun()
            if st.session_state.voice_result is None:
                with st.spinner("🤖 Gemini is interpreting your task..."):
                    st.session_state.voice_result = interpret_voice_task(st.session_state.voice_transcript)

        result = st.session_state.voice_result
        if result:
            st.subheader("🎙️ Voice Task")
            if result["deadline_ambiguous"]:
                st.warning(f"Deadline needs review: {result['deadline_ambiguous']}")
            task_name = st.text_input("Task", value=result["title"], key="voice_task_name")
            description = st.text_area("Description", value=result["description"], key="voice_description")
            deadline_enabled = st.checkbox(
                "Add a deadline",
                value=result["deadline"] is not None,
                key="voice_deadline_enabled",
            )
            deadline = st.date_input(
                "Deadline (edit if needed)",
                value=result["deadline"] or date.today(),
                key="voice_deadline",
            ) if deadline_enabled else None
            if deadline is None:
                st.caption("Deadline: not provided")
            priority_options = ["Low", "Medium", "High"]
            priority = st.selectbox(
                "Priority",
                priority_options,
                index=priority_options.index(result["priority"]) if result["priority"] in priority_options else 0,
                key="voice_priority",
            )
            estimated_time = st.number_input(
                "Estimated time (hours)",
                min_value=0.5,
                step=0.5,
                value=result["estimated_time"] or 0.5,
                key="voice_estimated_time",
            ) if result["estimated_time"] is not None else None
            if estimated_time is None:
                st.caption("Estimated time: not provided")

            edit_col, add_col, cancel_col = st.columns(3)
            with edit_col:
                st.button("✏️ Edit", key="voice_edit", help="The fields above are editable before saving.")
            with add_col:
                if st.button("✅ Add Task", type="primary", key="voice_add_task"):
                    if not task_name.strip():
                        st.warning("Please provide a task name.")
                    else:
                        insert_task(task_name.strip(), description.strip(), deadline, priority, estimated_time)
                        st.success("Task added successfully!")
                        st.rerun()
            with cancel_col:
                if st.button("❌ Cancel", key="voice_cancel"):
                    st.session_state.voice_transcript = ""
                    st.session_state.voice_result = None
                    st.session_state.voice_recorder_key += 1
                    st.rerun()
        elif st.session_state.voice_transcript:
            st.warning("Please edit the recognized text manually or try speaking again.")
        else:
            st.caption("No speech was detected. Please try again or use manual entry.")
        return

    task_name = st.text_input("What do you need to do?", key="dialog_task_name")
    description = st.text_area("Describe your task", key="dialog_description")
    deadline = st.date_input("When is it due?", key="dialog_deadline")
    priority = st.selectbox(
        "How important is it?",
        ["Low", "Medium", "High"],
        key="dialog_priority"
    )
    estimated_time = st.number_input(
        "Estimated time (hours)",
        min_value=0.5,
        step=0.5,
        key="dialog_estimated_time"
    )

    if st.button("➕ Add Task", type="primary", key="dialog_add_task"):
        if task_name:
            insert_task(task_name, description, deadline, priority, estimated_time)
            st.success("Task added successfully!")
            st.rerun()
        else:
            st.warning("Please enter a task name.")


def generate_subtasks(task_title):

    if client is None:
        st.error(
            "Gemini is not configured. Set GEMINI_API_KEY as an environment "
            "variable or Streamlit secret."
        )
        return ""

    prompt = f"""
You are an intelligent task management assistant.

Break the following task into meaningful, practical subtasks.

Task:
{task_title}

Rules:
- Give 4 to 7 subtasks.
- Each subtask must be specific and actionable.
- Make the subtasks relevant to the actual task.
- Do not use generic steps like "start the task" or "complete the task".
- Avoid repeating the task title as a subtask.
- Each subtask should describe a concrete action for this specific task.
- Return only the subtasks, one per line.
"""

    try:

        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt
        )

        return response.text

    except Exception as e:

        if "503" in str(e) or "UNAVAILABLE" in str(e):

            st.error(
                "⚠️ Gemini is temporarily busy. "
                "Please try again in a few seconds."
            )

            return ""

        else:

            st.error(
                f"❌ Gemini error: {e}"
            )

            return ""


def save_ai_subtasks(task_id, task_title):
    subtasks = generate_subtasks(task_title)
    if not subtasks:
        return False

    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        "DELETE FROM subtasks WHERE task_id = ? AND source = ?",
        (task_id, "ai")
    )

    for subtask in subtasks.split("\n"):
        subtask = subtask.strip()
        if subtask:
            cursor.execute(
                """
                INSERT INTO subtasks (task_id, subtask, source)
                VALUES (?, ?, ?)
                """,
                (task_id, subtask, "ai")
            )

    connection.commit()
    connection.close()
    return True


def generate_reschedule_suggestion(task, details):
    if client is None:
        st.error(
            "Gemini is not configured. Set GEMINI_API_KEY as an environment "
            "variable or Streamlit secret."
        )
        return ""

    prompt = f"""
You are helping reschedule a task that may be falling behind.

Task title: {task[1]}
Description: {task[2] or "None provided"}
Original deadline: {task[3]}
Estimated duration: {task[5]} hours
Actual worked duration: {details['worked_hours']:.2f} hours
Remaining estimated work: {details['remaining_hours']:.2f} hours
Current status: {task[6]}
Current date/time: {datetime.now().isoformat(timespec="minutes")}
Manual priority: {task[4]}
Python detected potential schedule risk: {details['is_behind']}

Create a concise, realistic, task-specific rescheduling plan for the remaining work.
Do not change the task priority.
Do not invent task requirements.
Do not claim the task is completed.
Do not provide generic motivational advice.
Focus on scheduling the remaining work in realistic work blocks.
Respect the existing deadline when possible.
If the original deadline is unrealistic, clearly say so and suggest a practical alternative.
"""

    try:
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt
        )
        return response.text
    except Exception as e:
        st.error(f"❌ Gemini error: {e}")
        return ""

header_left, header_right = st.columns([4, 1])
with header_left:
    st.markdown('<div class="dashboard-kicker">AI productivity workspace</div>', unsafe_allow_html=True)
    st.markdown('<div class="dashboard-title">RIVO</div>', unsafe_allow_html=True)
    st.markdown('<div class="dashboard-subtitle">Plan smarter. Work better. Stay on track.</div>', unsafe_allow_html=True)
with header_right:
    st.write("")
    theme_label = "🌙 Dark" if not theme_is_dark else "☀️ Light"
    if st.button(theme_label, key="theme_toggle"):
        st.session_state.theme = "dark" if not theme_is_dark else "light"
        st.rerun()

st.write("")
st.caption("Good morning 👋  Ready to get things done?")
action_one, action_two, action_three = st.columns(3)
with action_one:
    if st.button("➕ Add Task", type="primary", key="open_add_task"):
        show_add_task_dialog()
with action_two:
    if st.button("🎙️ Voice Task", key="open_voice_task"):
        st.session_state.dialog_mode = "voice"
        show_add_task_dialog()
with action_three:
    if st.button("📝 Quick Notes", key="open_quick_notes"):
        st.session_state.quick_notes_view = "list"
        render_quick_notes_panel()
def calculate_smart_score(task):

    priority = task[4]
    deadline = task[3]
    status = task[6]

    score = 0

    # Priority score
    if priority == "High":
        score += 30
    elif priority == "Medium":
        score += 20
    else:
        score += 10

    # Deadline score
    try:
        deadline_date = datetime.fromisoformat(deadline)
        days_left = (deadline_date.date() - datetime.now().date()).days

        if days_left < 0:
            score += 50
        elif days_left == 0:
            score += 40
        elif days_left == 1:
            score += 35
        elif days_left <= 3:
            score += 25
        elif days_left <= 7:
            score += 15
        else:
            score += 5

    except:
        pass

    # In-progress tasks get extra importance
    if status == "In Progress":
        score += 15

    return score


def calculate_worked_seconds(task):
    total_seconds = float(task[8] or 0)

    if task[6] != "In Progress" or not task[7]:
        return total_seconds

    try:
        start_time = datetime.fromisoformat(task[7].replace("Z", "+00:00"))
        current_time = datetime.now(start_time.tzinfo) if start_time.tzinfo else datetime.now()
        return total_seconds + max(0, (current_time - start_time).total_seconds())
    except (TypeError, ValueError):
        return total_seconds


def get_reschedule_details(task):
    if task[6] == "Completed" or not task[3]:
        return None

    try:
        deadline_date = datetime.fromisoformat(str(task[3])).date()
        estimated_hours = max(float(task[5] or 0), 0)
        worked_seconds = calculate_worked_seconds(task)
        worked_hours = worked_seconds / 3600
        remaining_hours = max(estimated_hours - worked_hours, 0)
        deadline_end = datetime.combine(deadline_date, datetime.max.time())
        hours_until_deadline = (deadline_end - datetime.now()).total_seconds() / 3600
        available_hours = max(hours_until_deadline, 0) / 24 * 2

        return {
            "worked_hours": worked_hours,
            "remaining_hours": remaining_hours,
            "hours_until_deadline": hours_until_deadline,
            "is_behind": (
                worked_seconds > 0
                and remaining_hours > 0
                and (
                    hours_until_deadline < 0
                    or remaining_hours > available_hours
                )
            ),
        }
    except (TypeError, ValueError):
        return None


def calculate_productivity_metrics(tasks):
    total_tasks = len(tasks)
    completed_tasks = sum(task[6] == "Completed" for task in tasks)
    pending_tasks = total_tasks - completed_tasks
    completion_rate = (completed_tasks / total_tasks * 100) if total_tasks else 0

    total_focus_seconds = 0
    for task in tasks:
        try:
            total_focus_seconds += max(0, calculate_worked_seconds(task))
        except (TypeError, ValueError, OverflowError):
            continue

    today = datetime.now().date()
    today_tasks = []
    for task in tasks:
        if not task[3]:
            continue
        try:
            deadline_date = datetime.fromisoformat(str(task[3])).date()
        except (TypeError, ValueError):
            continue
        if deadline_date == today:
            today_tasks.append(task)

    today_completed = sum(task[6] == "Completed" for task in today_tasks)
    today_progress = (today_completed / len(today_tasks)) if today_tasks else 0

    return {
        "completed_tasks": completed_tasks,
        "pending_tasks": pending_tasks,
        "completion_rate": completion_rate,
        "total_focus_seconds": total_focus_seconds,
        "today_progress": today_progress,
        "today_task_count": len(today_tasks),
    }


@st.dialog("📊 Productivity", width="small")
def render_productivity_section(tasks):
    metrics = calculate_productivity_metrics(tasks)
    total_focus_minutes = int(metrics["total_focus_seconds"] // 60)
    focus_hours, focus_minutes = divmod(total_focus_minutes, 60)
    focus_label = f"{focus_hours}h {focus_minutes}m" if focus_hours else f"{focus_minutes}m"

    with st.container(border=True):
        st.subheader("📊 Productivity")
        metric_left, metric_mid, metric_right = st.columns(3)
        with metric_left:
            st.markdown(
                f'<div class="metric-card"><div class="metric-label">✅ Completed</div>'
                f'<div class="metric-value">{metrics["completed_tasks"]}</div></div>',
                unsafe_allow_html=True,
            )
        with metric_mid:
            st.markdown(
                f'<div class="metric-card"><div class="metric-label">⏳ Pending</div>'
                f'<div class="metric-value">{metrics["pending_tasks"]}</div></div>',
                unsafe_allow_html=True,
            )
        with metric_right:
            st.markdown(
                f'<div class="metric-card"><div class="metric-label">📈 Rate</div>'
                f'<div class="metric-value">{metrics["completion_rate"]:.0f}%</div></div>',
                unsafe_allow_html=True,
            )

        st.markdown(f"**⏱️ Total Focus Time**  \n{focus_label}")
        st.markdown("**📅 Today's Progress**")
        if metrics["today_task_count"]:
            st.progress(metrics["today_progress"], text=f"{metrics['today_progress']:.0%}")
        else:
            st.progress(0, text="0%")
            st.caption("No tasks due today.")


def calculate_daily_reflection_stats(tasks, reflection_date):
    relevant_tasks = []
    for task in tasks:
        deadline_date = parse_task_deadline_date(task[3])
        if deadline_date == reflection_date:
            relevant_tasks.append(task)

    completed_tasks = sum(task[6] == "Completed" for task in relevant_tasks)
    pending_tasks = sum(task[6] != "Completed" for task in relevant_tasks)
    total_focus_seconds = 0
    for task in relevant_tasks:
        try:
            total_focus_seconds += max(0, calculate_worked_seconds(task))
        except (TypeError, ValueError, OverflowError):
            continue

    return {
        "completed_tasks": completed_tasks,
        "pending_tasks": pending_tasks,
        "total_focus_time": int(total_focus_seconds),
        "relevant_tasks": relevant_tasks,
    }


def generate_daily_reflection_analysis(mood, reflection_text, stats):
    if client is None:
        return ""

    task_lines = "\n".join(
        f"- {task[1]}: {task[6]}, priority {task[4]}, deadline {task[3]}"
        for task in stats["relevant_tasks"]
    ) or "No tasks were associated with this date."
    prompt = f"""
Write a concise productivity-focused daily analysis from only the supplied data.
Do not invent tasks, time, emotions, achievements, or reasons. Do not diagnose
mental or physical health. Mention unavailable information only as unavailable,
and keep the result to 2 or 3 sentences.

Mood: {mood}
User reflection: {reflection_text or "No reflection text provided."}
Completed tasks associated with this date: {stats["completed_tasks"]}
Pending tasks associated with this date: {stats["pending_tasks"]}
Actual tracked focus time in seconds: {stats["total_focus_time"]}
Task activity:
{task_lines}
"""

    try:
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt,
        )
        analysis = getattr(response, "text", None)
        return analysis.strip() if isinstance(analysis, str) else ""
    except Exception:
        return ""


def parse_task_deadline_date(deadline):
    if not deadline:
        return None

    try:
        deadline_text = str(deadline).strip()
        return date.fromisoformat(deadline_text[:10])
    except (TypeError, ValueError):
        return None


def get_calendar_tasks(tasks):
    tasks_by_date = {}
    numbered_tasks = {}
    for display_number, task in enumerate(tasks, start=1):
        numbered_tasks[task[0]] = display_number
        deadline_date = parse_task_deadline_date(task[3])
        if deadline_date:
            tasks_by_date.setdefault(deadline_date, []).append(task)
    return tasks_by_date, numbered_tasks


def shift_calendar_month(month_start, month_delta):
    month_index = month_start.year * 12 + month_start.month - 1 + month_delta
    year, month_index = divmod(month_index, 12)
    return date(year, month_index + 1, 1)


def select_calendar_date(calendar_date):
    st.session_state.calendar_selected_date = calendar_date


def navigate_calendar_month(month_delta):
    next_month = shift_calendar_month(st.session_state.calendar_month, month_delta)
    st.session_state.calendar_month = next_month
    st.session_state.calendar_selected_date = next_month


def select_calendar_today():
    today = datetime.now().date()
    st.session_state.calendar_month = date(today.year, today.month, 1)
    st.session_state.calendar_selected_date = today


@st.dialog("📅 Calendar", width="medium")
def render_calendar_section(tasks):
    today = datetime.now().date()
    st.session_state.setdefault("calendar_month", date(today.year, today.month, 1))
    st.session_state.setdefault("calendar_selected_date", today)

    tasks_by_date, numbered_tasks = get_calendar_tasks(tasks)
    month_start = st.session_state.calendar_month
    selected_date = st.session_state.calendar_selected_date

    previous_col, current_col, next_col = st.columns([1, 3, 1])
    with previous_col:
        st.button(
            "‹",
            key="calendar_previous",
            help="Previous month",
            on_click=navigate_calendar_month,
            args=(-1,),
        )
    with current_col:
        st.markdown(
            f"<div style='text-align:center; font-weight:700; padding:.2rem 0'>"
            f"{month_start.strftime('%B %Y')}</div>",
            unsafe_allow_html=True,
        )
        st.button(
            "Today",
            key="calendar_today",
            use_container_width=True,
            on_click=select_calendar_today,
        )
    with next_col:
        st.button(
            "›",
            key="calendar_next",
            help="Next month",
            on_click=navigate_calendar_month,
            args=(1,),
        )

    weekday_columns = st.columns(7)
    for weekday_column, weekday_name in zip(weekday_columns, ("M", "T", "W", "T", "F", "S", "S")):
        with weekday_column:
            st.caption(weekday_name)

    month_days = calendar_module.monthrange(month_start.year, month_start.month)[1]
    leading_days = month_start.weekday()
    calendar_cells = [None] * leading_days + [
        date(month_start.year, month_start.month, day)
        for day in range(1, month_days + 1)
    ]
    while len(calendar_cells) % 7:
        calendar_cells.append(None)

    for week_start in range(0, len(calendar_cells), 7):
        day_columns = st.columns(7)
        for day_column, calendar_date in zip(day_columns, calendar_cells[week_start:week_start + 7]):
            with day_column:
                if calendar_date is None:
                    st.write("")
                    continue
                date_tasks = tasks_by_date.get(calendar_date, [])
                task_marker = f" •{len(date_tasks)}" if date_tasks else ""
                button_type = "primary" if calendar_date == today else "secondary"
                st.button(
                    f"{calendar_date.day}{task_marker}",
                    key=f"calendar_day_{calendar_date.isoformat()}",
                    type=button_type,
                    use_container_width=True,
                    on_click=select_calendar_date,
                    args=(calendar_date,),
                )

    st.divider()
    selected_date = st.session_state.calendar_selected_date
    selected_tasks = tasks_by_date.get(selected_date, [])
    selected_date_label = f"{selected_date.strftime('%B')} {selected_date.day}, {selected_date.year}"
    st.markdown(f"**📋 Tasks for {selected_date_label}**")
    if not selected_tasks:
        st.caption("No tasks due on this date.")
    else:
        for task in selected_tasks:
            display_number = numbered_tasks.get(task[0])
            deadline_text = str(task[3]) if task[3] else "No deadline"
            st.markdown(
                f"**{display_number}. {task[1]}**  \n"
                f"Priority: {task[4]}  \n"
                f"Deadline: {deadline_text}  \n"
                f"Status: {task[6]}"
            )


@st.dialog("🌱 Mood & Reflection")
def show_reflection_dialog(current_tasks):
    completed_count = sum(task[6] == "Completed" for task in current_tasks)
    remaining_count = len(current_tasks) - completed_count
    st.write("**Today's factual summary**")
    st.write(f"✅ Completed: {completed_count}")
    st.write(f"⏳ Remaining: {remaining_count}")

    today = datetime.now().date().isoformat()
    reflection_storage_available = True
    saved_reflection = None
    try:
        reflection_connection = get_connection()
        reflection_cursor = reflection_connection.cursor()
        reflection_cursor.execute(
            """
            SELECT id, reflection_date, feeling, delay_reasons, note, created_at
            FROM daily_reflections
            WHERE reflection_date = ?
            """,
            (today,)
        )
        saved_reflection = reflection_cursor.fetchone()
        if not saved_reflection or len(saved_reflection) < 10:
            saved_reflection = None
        reflection_connection.close()
    except Exception:
        reflection_storage_available = False
        st.warning("Reflection storage is not configured yet. Run the provided Supabase SQL first.")

    if saved_reflection:
        st.info("A reflection has already been saved for today. You can update it below.")

    delay_options = [
        "⏰ Underestimated the time",
        "🧩 Task was more difficult than expected",
        "📚 Too many tasks",
        "🧠 Didn't know where to start",
        "🔔 Got distracted",
        "🛑 Needed more breaks",
        "✍️ Other",
    ]
    if "reflection_feeling" not in st.session_state:
        st.session_state.reflection_feeling = saved_reflection[2] if saved_reflection else "Select one..."
    if "reflection_delay_reasons" not in st.session_state:
        saved_reasons = saved_reflection[3] if saved_reflection else []
        st.session_state.reflection_delay_reasons = [reason for reason in (saved_reasons or []) if reason in delay_options]
    if "reflection_note" not in st.session_state:
        st.session_state.reflection_note = saved_reflection[4] if saved_reflection else ""

    feeling = st.radio(
        "How was today?",
        ["Select one...", "😊 Easy", "😐 Normal", "😵 Overloaded"],
        key="reflection_feeling"
    )
    selected_delay_reasons = st.multiselect(
        "What caused the delay? (optional)",
        delay_options,
        key="reflection_delay_reasons"
    )
    reflection_note = st.text_area(
        "Anything else you want to note? (optional)",
        key="reflection_note"
    )

    if saved_reflection:
        saved_focus_seconds = int(saved_reflection[7] or 0)
        saved_focus_hours, saved_focus_minutes = divmod(saved_focus_seconds // 60, 60)
        saved_focus_label = (
            f"{saved_focus_hours}h {saved_focus_minutes}m"
            if saved_focus_hours else f"{saved_focus_minutes}m"
        )
        st.markdown("**📊 Today's Work**")
        st.write(f"Completed: {saved_reflection[5] or 0}")
        st.write(f"Pending: {saved_reflection[6] or 0}")
        st.write(f"Focus Time: {saved_focus_label}")
        if saved_reflection[8]:
            st.markdown("**🧠 Daily Insight**")
            st.info(saved_reflection[8])

    if st.button("💾 Save Reflection", type="primary", key="dialog_save_reflection"):
        if feeling == "Select one...":
            st.warning("Please select how today felt before saving.")
        elif not reflection_storage_available:
            st.error("Reflection could not be saved until the daily_reflections table is created.")
        else:
            try:
                reflection_date = datetime.now().date()
                daily_stats = calculate_daily_reflection_stats(current_tasks, reflection_date)
                ai_analysis = generate_daily_reflection_analysis(
                    feeling,
                    reflection_note.strip(),
                    daily_stats,
                )
                reflection_connection = get_connection()
                reflection_cursor = reflection_connection.cursor()
                reflection_cursor.execute(
                    """
                    UPSERT INTO daily_reflections
                    (reflection_date, feeling, delay_reasons, note,
                     completed_tasks, pending_tasks, total_focus_time, ai_analysis)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        today,
                        feeling,
                        selected_delay_reasons,
                        reflection_note.strip(),
                        daily_stats["completed_tasks"],
                        daily_stats["pending_tasks"],
                        daily_stats["total_focus_time"],
                        ai_analysis,
                    )
                )
                reflection_connection.commit()
                reflection_connection.close()
                st.success("✅ Today's reflection saved.")
                st.markdown("**📊 Today's Work**")
                st.write(f"Completed: {daily_stats['completed_tasks']}")
                st.write(f"Pending: {daily_stats['pending_tasks']}")
                focus_minutes = daily_stats["total_focus_time"] // 60
                focus_hours, focus_minutes = divmod(focus_minutes, 60)
                st.write(f"Focus Time: {focus_hours}h {focus_minutes}m")
                if ai_analysis:
                    st.markdown("**🧠 Daily Insight**")
                    st.info(ai_analysis)
                elif client is not None:
                    st.warning("Today's reflection was saved, but a Daily Insight could not be generated.")
            except Exception as e:
                st.error(f"Reflection could not be saved: {e}")


connection = get_connection()
cursor = connection.cursor()

cursor.execute("""
SELECT id, title, description, deadline, priority, estimated_time, status, start_time, total_time
FROM tasks
ORDER BY deadline
""")

tasks = cursor.fetchall()

connection.close()

active_tasks = sorted(
    (task for task in tasks if task[6] != "Completed"),
    key=calculate_smart_score,
    reverse=True,
)
completed_tasks = [task for task in tasks if task[6] == "Completed"]
tasks = active_tasks + completed_tasks

active_count = sum(task[6] != "Completed" for task in tasks)
today = datetime.now().date()
due_today_count = sum(parse_task_deadline_date(task[3]) == today for task in tasks if task[6] != "Completed")
estimated_workload = sum(
    max(float(task[5] or 0), 0)
    for task in tasks
    if task[6] != "Completed" and str(task[5] or "").replace(".", "", 1).isdigit()
)
estimated_hours, estimated_minutes = divmod(int(estimated_workload * 60), 60)

with st.container(border=True):
    st.markdown("### 🎯 My Workspace")
    workspace_left, workspace_mid, workspace_right = st.columns(3)
    with workspace_left:
        st.metric("Active Tasks", active_count)
    with workspace_mid:
        st.metric("Due Today", due_today_count)
    with workspace_right:
        st.metric("Estimated Workload", f"{estimated_hours}h {estimated_minutes}m")
    if st.button("📋 My Tasks", type="primary", key="open_tasks_workspace"):
        st.session_state.tasks_view_open = True

feature_left, feature_mid, feature_right = st.columns(3)
with feature_left:
    if st.button("📅 Calendar", key="open_calendar"):
        render_calendar_section(tasks)
with feature_mid:
    if st.button("🌙 Reflection", key="open_reflection"):
        show_reflection_dialog(tasks)
with feature_right:
    if st.button("📊 Productivity", key="open_productivity"):
        render_productivity_section(tasks)

st.markdown("### 📈 At A Glance")
glance_left, glance_mid, glance_right = st.columns(3)
with glance_left:
    st.markdown(f'<div class="metric-card"><div class="metric-label">🟢 Active Tasks</div><div class="metric-value">{active_count}</div></div>', unsafe_allow_html=True)
with glance_mid:
    focus_minutes = int(sum(max(calculate_worked_seconds(task), 0) for task in tasks) // 60)
    focus_hours, focus_minutes = divmod(focus_minutes, 60)
    st.markdown(f'<div class="metric-card"><div class="metric-label">⏱ Focus Time</div><div class="metric-value">{focus_hours}h {focus_minutes}m</div></div>', unsafe_allow_html=True)
with glance_right:
    completed_count = sum(task[6] == "Completed" for task in tasks)
    completion_rate = completed_count / len(tasks) * 100 if tasks else 0
    st.markdown(f'<div class="metric-card"><div class="metric-label">✓ Completion Rate</div><div class="metric-value">{completion_rate:.0f}%</div></div>', unsafe_allow_html=True)

if st.session_state.tasks_view_open:
    st.header("📋 My Tasks")
    if st.button("✕ Close Tasks", key="close_tasks_workspace"):
        st.session_state.tasks_view_open = False
        st.rerun()


if tasks and st.session_state.tasks_view_open:
    for display_number, task in enumerate(tasks, start=1):

        if st.button(
            "🧠 Break into Subtasks",
            key=f"ai_break_{task[0]}"
        ):

            with st.spinner("🤖 Gemini is analyzing your task..."):
                generated = save_ai_subtasks(task[0], task[1])

            if generated:
                st.success("✅ AI subtasks generated and saved!")

        connection = get_connection()
        cursor = connection.cursor()
    
        cursor.execute(
            """
            SELECT id, subtask, completed, source
            FROM subtasks
            WHERE task_id = ?
            """,
            (task[0],)
        )
    
        saved_subtasks = cursor.fetchall()
    
        connection.close()
    
        if tasks:
            if saved_subtasks:
                st.subheader("🧠 AI Suggested Subtasks")
    
            for subtask in saved_subtasks:
                subtask_col, delete_col = st.columns([8, 1])
                with subtask_col:
                    checkbox = st.checkbox(
                        subtask[1],
                        value=(subtask[2] == 1),
                        key=f"subtask_{subtask[0]}"
                    )

                connection = get_connection()
                cursor = connection.cursor()
                cursor.execute(
                    """
                    UPDATE subtasks
                    SET completed = ?
                    WHERE id = ?
                    """,
                    (1 if checkbox else 0, subtask[0])
                )
                connection.commit()
                connection.close()

                with delete_col:
                    if st.button("🗑️", key=f"delete_subtask_{subtask[0]}", help="Remove this subtask"):
                        connection = get_connection()
                        cursor = connection.cursor()
                        cursor.execute("DELETE FROM subtasks WHERE id = ?", (subtask[0],))
                        connection.commit()
                        connection.close()
                        st.rerun()

            custom_col, custom_button_col = st.columns([8, 1])
            with custom_col:
                custom_subtask = st.text_input(
                    "Add My Own Subtask",
                    key=f"custom_subtask_{task[0]}",
                    placeholder="Enter your subtask...",
                    label_visibility="collapsed",
                )
            with custom_button_col:
                if st.button("Add", key=f"add_subtask_{task[0]}"):
                    if custom_subtask.strip():
                        connection = get_connection()
                        cursor = connection.cursor()
                        cursor.execute(
                            """
                            INSERT INTO subtasks (task_id, subtask, source)
                            VALUES (?, ?, ?)
                            """,
                            (task[0], custom_subtask.strip(), "manual")
                        )
                        connection.commit()
                        connection.close()
                        st.rerun()

            if st.button("🔄 Regenerate Suggestions", key=f"regenerate_subtasks_{task[0]}"):
                with st.spinner("🤖 Gemini is generating fresh suggestions..."):
                    generated = save_ai_subtasks(task[0], task[1])
                if generated:
                    st.success("✅ AI suggestions regenerated. Your subtasks were kept.")
                    st.rerun()
    
            # Get updated progress from database
            connection = get_connection()
            cursor = connection.cursor()
    
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM subtasks
                WHERE task_id = ?
                """,
                (task[0],)
            )
    
            total_subtasks = cursor.fetchone()[0]
    
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM subtasks
                WHERE task_id = ? AND completed = 1
                """,
                (task[0],)
            )
    
            completed_count = cursor.fetchone()[0]
    
            connection.close()
    
            if total_subtasks > 0:
    
                    progress = completed_count / total_subtasks
    
                    st.write(
                    f"({int(progress * 100)}%)"
                    f"({int(progress * 100)}%)"
                )

                    st.progress(progress)

                    st.write(
                        f"📊 Progress: {completed_count}/{total_subtasks} "
                        f"({int(progress * 100)}%)"
                    )
    
            smart_score = calculate_smart_score(task)
    
            st.write("---")
    
                # I'm Stuck Mode
            if task[6] != "Completed":
    
                if st.button("🆘 I'm Stuck", key=f"stuck_{task[0]}"):
                    st.session_state.stuck_tasks.add(task[0])
    
                if task[0] in st.session_state.stuck_tasks:
                    st.subheader("😵 What's stopping you?")
    
                    stuck_reason = st.radio(
                        "Choose a reason:",
                        [
                            "Don't understand it",
                            "Task is too big",
                            "Don't know where to start",
                            "Need a break"
                        ],
                        key=f"stuck_reason_{task[0]}"
                    )
    
                    st.write(f"🧠 You selected: {stuck_reason}")
    
                    if stuck_reason == "Don't understand it":
                        st.info(
                            "Read the task description and identify the specific "
                            "part that is unclear before taking the next step."
                        )
                    elif stuck_reason == "Task is too big":
                        if task[0] not in st.session_state.stuck_breakdown_done:
                            with st.spinner("🤖 Gemini is breaking this task into smaller steps..."):
                                generated = save_ai_subtasks(task[0], task[1])

                            if generated:
                                st.session_state.stuck_breakdown_done.add(task[0])
                                st.success("✅ Task broken into smaller steps!")
                        else:
                            st.info("The task has been broken into smaller steps below.")
                    elif stuck_reason == "Don't know where to start":
                        st.info(
                            f"Start by writing down the first concrete action needed "
                            f"for '{task[1]}'."
                        )
                    elif stuck_reason == "Need a break":
                        st.info(
                            "Take a short break, then return and choose one small "
                            "next action."
                        )
    
            with st.container(border=True):
                st.subheader(f"{display_number}. {task[1]}")
        
                st.write("**Description:**", task[2])
                st.write("**Deadline:**", task[3])
                st.write("**Priority:**", task[4])
                st.write("**Smart Score:**", smart_score)
                st.write("**Estimated time:**", task[5], "hours")
                st.write("**Status:**", task[6])
        
                @st.fragment(run_every="1s", key=f"timer_{task[0]}")
                def render_worked_time(current_task):
                    total_seconds = calculate_worked_seconds(current_task)

                    hours = int(total_seconds // 3600)
                    minutes = int((total_seconds % 3600) // 60)
                    seconds = int(total_seconds % 60)

                    st.write(
                        f"**⏱️ Actual time worked:** {hours}h {minutes}m {seconds}s"
                    )

                render_worked_time(task)

            reschedule_details = get_reschedule_details(task)
            task_id = task[0]
            suggestion = st.session_state.reschedule_suggestions.get(task_id)
            accepted_schedule = st.session_state.reschedule_accepted.get(task_id)

            if (
                reschedule_details
                and task_id not in st.session_state.reschedule_dismissed
                and not accepted_schedule
            ):
                if reschedule_details["is_behind"]:
                    st.info("⚠️ This task may be falling behind.")

                if st.button(
                    "🔄 Reschedule Task",
                    key=f"reschedule_{task_id}"
                ):
                    with st.spinner("🤖 Gemini is preparing a realistic schedule..."):
                        suggestion = generate_reschedule_suggestion(task, reschedule_details)

                    if suggestion:
                        st.session_state.reschedule_suggestions[task_id] = suggestion

            suggestion = st.session_state.reschedule_suggestions.get(task_id)

            if suggestion:
                st.subheader("🧠 AI Rescheduling Suggestion")
                st.write(suggestion)

                if st.button("✅ Accept Reschedule", key=f"accept_reschedule_{task_id}"):
                    st.session_state.reschedule_accepted[task_id] = suggestion
                    st.session_state.reschedule_suggestions.pop(task_id, None)
                    st.rerun()

                if st.button("↩️ Keep Current Schedule", key=f"keep_schedule_{task_id}"):
                    st.session_state.reschedule_dismissed.add(task_id)
                    st.session_state.reschedule_suggestions.pop(task_id, None)
                    st.rerun()

            if accepted_schedule:
                st.success(
                    "✅ Reschedule accepted for this session. "
                    "The original deadline and priority remain unchanged."
                )
    
            if task[6] == "Pending":
    
                if st.button("▶ Start Task", key=f"start_{task[0]}"):
    
                    connection = get_connection()
                    cursor = connection.cursor()
    
                    current_time = datetime.now()
    
                    cursor.execute(
                        """
                        UPDATE tasks
                        SET status = ?, start_time = ?
                        WHERE id = ?
                        """,
                        ("In Progress", current_time.isoformat(), task[0])
                    )
    
                    connection.commit()
                    connection.close()
    
                    st.rerun()
    
            elif task[6] == "In Progress":
    
                st.info("🟡 Task is currently in progress")
    
                if st.button("⏸️ Pause Task", key=f"pause_{task[0]}"):
    
                    connection = get_connection()
                    cursor = connection.cursor()
    
                    total_seconds = calculate_worked_seconds(task)

                    cursor.execute(
                        "UPDATE tasks SET status = ?, total_time = ? WHERE id = ?",
                        ("Paused", total_seconds, task[0])
                    )
    
                    connection.commit()
                    connection.close()
    
                    st.rerun()
    
    
                if st.button("✓ Complete Task", key=f"complete_{task[0]}"):
    
                    connection = get_connection()
                    cursor = connection.cursor()
    
                    total_seconds = calculate_worked_seconds(task)

                    cursor.execute(
                        "UPDATE tasks SET status = ?, total_time = ? WHERE id = ?",
                        ("Completed", total_seconds, task[0])
                    )
    
                    connection.commit()
                    connection.close()
    
                    st.rerun()
    
    
            elif task[6] == "Paused":
    
                st.warning("🟠 Task is currently paused")
    
                if st.button("▶️ Resume Task", key=f"resume_{task[0]}"):
    
                    connection = get_connection()
                    cursor = connection.cursor()
    
                    current_time = datetime.now()
    
                    cursor.execute(
                        """
                        UPDATE tasks
                        SET status = ?, start_time = ?
                        WHERE id = ?
                        """,
                        ("In Progress", current_time.isoformat(), task[0])
                    )
    
                    connection.commit()
                    connection.close()
    
                    st.rerun()
    
    
            elif task[6] == "Completed":
    
                st.success("🟢 Task Completed!")
    
                if st.button("🗑️ Delete Task", key=f"delete_{task[0]}"):
    
                    connection = get_connection()
                    cursor = connection.cursor()
    
                    cursor.execute(
                        "DELETE FROM tasks WHERE id = ?",
                        (task[0],)
                    )
    
                    connection.commit()
                    connection.close()
    
                    st.success("Task deleted successfully!")
    
                    st.rerun()
    
elif not tasks:

    st.info("No tasks added yet.")


