# NEXDO - AI-Powered Intelligent Task Manager

> Plan smarter. Work better. Stay on track.

## Overview

NEXDO is an AI-powered intelligent task management web application built with Streamlit. It helps users organize tasks, understand what to work on next, break large tasks into smaller subtasks, manage time, and adapt schedules when needed.

## Key Features

- Create tasks manually or with voice input.
- Set manual priority, deadlines, and estimated time.
- Start, pause, resume, and complete tasks.
- Track actual worked time independently for each task.
- Get a Smart Score and a **What Should I Do Now?** recommendation.
- Break tasks into meaningful subtasks with Google Gemini.
- Track subtask completion progress.
- Use **I'm Stuck** assistance for common blockers.
- Get AI-assisted scheduling and rescheduling suggestions.
- Record an end-of-day reflection.
- Add lightweight **Quick Notes / Small Tasks** separately from regular tasks.
- Add Quick Notes by typing or voice.
- Review voice-created task and note content before saving.
- See regular tasks with dynamic display numbering based on their current order.
- Switch between light and dark themes.

## How NEXDO Works

1. Add a task manually or provide its details by voice.
2. Review and manage the task's priority, deadline, and estimated time.
3. Break the task into smaller subtasks when needed.
4. Work using the task timer.
5. Track actual progress and subtask completion.
6. Receive recommendations or use **I'm Stuck** assistance.
7. Request an AI-assisted rescheduling suggestion when a task is falling behind.
8. Reflect on the day using the end-of-day reflection workflow.

Quick Notes follow a separate, lightweight flow. They contain only note text and do not participate in task timers, priorities, deadlines, Smart Scores, subtasks, scheduling, or task statistics.

## AI Integration

Google Gemini provides AI-powered assistance for:

- Breaking task titles into meaningful subtasks.
- Interpreting task information extracted from voice input, including title, description, deadline, priority, and estimated time.
- Generating task-specific rescheduling suggestions.

Quick Note voice input is intentionally kept as plain recognized text and does not use the main task metadata extraction flow.

## Database

Supabase provides persistent data storage through the project's database adapter.

- Regular tasks are stored in the `tasks` table.
- Subtasks are stored separately in the `subtasks` table.
- Daily reflections use the `daily_reflections` table.
- Quick Notes are stored separately in the `quick_notes` table.

Visible task and note numbering is generated at render time from the current displayed list. It is not stored in the database and does not replace database record IDs.

## Technology Stack

- Python
- Streamlit
- Supabase
- Google Gemini API
- `streamlit-mic-recorder` for browser voice input
- Git and GitHub

## Project Structure

| File | Purpose |
| --- | --- |
| `app.py` | Empty placeholder file in the current project. The active application is implemented in `app1.py`. |
| `app1.py` | Main Streamlit application containing the NEXDO dashboard, task workflows, timers, Gemini features, voice task creation, Quick Notes, reflection, and theme support. |
| `database.py` | Supabase connection and compatibility adapter used by the Streamlit application for task, subtask, reflection, and Quick Notes database operations. |
| `requirements.txt` | Python dependencies required by the application. |
| `.gitignore` | Excludes secrets, local databases, virtual environments, Python cache files, and editor/OS files from version control. |

## Installation / Setup

### 1. Clone the repository

```bash
git clone <YOUR_REPOSITORY_URL>
cd AI_Task_Manager
```

### 2. Create a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Streamlit secrets

Create `.streamlit/secrets.toml` locally. Do not commit this file.

```toml
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"
SUPABASE_URL = "YOUR_SUPABASE_URL"
SUPABASE_KEY = "YOUR_SUPABASE_KEY"
```

The application also supports these values through environment variables. Use your own credentials and keep them private.

The Supabase database must contain the tables required by the enabled features, including `tasks`, `subtasks`, `daily_reflections`, and `quick_notes`.

### 5. Run the application

```bash
streamlit run app1.py
```

## Running the Application

The active Streamlit entry point is `app1.py`:

```bash
streamlit run app1.py
```

The application opens in the browser at the local Streamlit address shown in the terminal.

## Security Notes

- Store Gemini and Supabase credentials in local Streamlit secrets or environment variables.
- Never hard-code API keys, database keys, passwords, or private configuration in source files.
- Never commit `.streamlit/secrets.toml`, `.env` files, or other secret-bearing files to GitHub.
- Use appropriate Supabase authentication and Row Level Security policies for production deployments.

## Future Enhancements

- More detailed productivity analytics.
- Richer productivity insights and trends.
- Additional personalization options.
- Further mobile-friendly improvements.

## Author / Project

**NEXDO** - AI-Powered Intelligent Task Manager
