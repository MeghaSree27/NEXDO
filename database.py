import os

from supabase import create_client


def _setting(name):
    value = os.getenv(name)
    if value:
        return value

    try:
        import streamlit as st
        return st.secrets[name]
    except (ImportError, KeyError, FileNotFoundError):
        return None


def _require_settings():
    url = _setting("SUPABASE_URL")
    key = _setting("SUPABASE_KEY")
    if not url or not key:
        raise RuntimeError(
            "Supabase is not configured. Set SUPABASE_URL and SUPABASE_KEY "
            "as environment variables or Streamlit secrets."
        )
    return url, key


class _SupabaseCursor:
    def __init__(self, client):
        self.client = client
        self._rows = []
        self._count = None
        self._single = None
        self._single_query = False

    def execute(self, query, parameters=()):
        normalized = " ".join(query.split()).upper()
        self._rows = []
        self._count = None
        self._single = None
        self._single_query = False

        if normalized.startswith("INSERT INTO TASKS"):
            values = dict(zip(
                ("title", "description", "deadline", "priority", "estimated_time", "status"),
                parameters,
            ))
            self.client.table("tasks").insert(values).execute()
        elif normalized.startswith("INSERT INTO QUICK_NOTES"):
            self.client.table("quick_notes").insert({
                "note_text": parameters[0],
            }).execute()
        elif normalized.startswith("SELECT ID, NOTE_TEXT"):
            response = (
                self.client.table("quick_notes")
                .select("id, note_text, created_at")
                .order("created_at")
                .execute()
            )
            self._rows = [
                (row.get("id"), row.get("note_text"), row.get("created_at"))
                for row in (response.data or [])
            ]
        elif normalized.startswith("DELETE FROM QUICK_NOTES"):
            self.client.table("quick_notes").delete().eq("id", parameters[0]).execute()
        elif normalized.startswith("SELECT ID, TITLE"):
            response = (
                self.client.table("tasks")
                .select("id, title, description, deadline, priority, estimated_time, status, start_time, total_time")
                .order("deadline")
                .execute()
            )
            self._rows = [
                tuple(row.get(column) for column in (
                    "id", "title", "description", "deadline", "priority",
                    "estimated_time", "status", "start_time", "total_time",
                ))
                for row in (response.data or [])
            ]
        elif normalized.startswith("DELETE FROM SUBTASKS"):
            query = self.client.table("subtasks").delete().eq("task_id", parameters[0])
            if "SOURCE" in normalized:
                query = query.eq("source", parameters[1])
            query.execute()
        elif normalized.startswith("INSERT INTO SUBTASKS"):
            self.client.table("subtasks").insert({
                "task_id": parameters[0],
                "subtask": parameters[1],
                "source": parameters[2] if len(parameters) > 2 else "ai",
            }).execute()
        elif normalized.startswith("SELECT ID, SUBTASK, COMPLETED"):
            response = (
                self.client.table("subtasks")
                .select("id, subtask, completed, source")
                .eq("task_id", parameters[0])
                .execute()
            )
            self._rows = [
                (row.get("id"), row.get("subtask"), row.get("completed"), row.get("source"))
                for row in (response.data or [])
            ]
        elif normalized.startswith("UPDATE SUBTASKS"):
            self.client.table("subtasks").update({
                "completed": parameters[0],
            }).eq("id", parameters[1]).execute()
        elif normalized.startswith("SELECT COUNT(*) FROM SUBTASKS WHERE TASK_ID = ? AND COMPLETED"):
            response = (
                self.client.table("subtasks")
                .select("id", count="exact")
                .eq("task_id", parameters[0])
                .eq("completed", 1)
                .execute()
            )
            self._count = response.count or 0
        elif normalized.startswith("SELECT COUNT(*) FROM SUBTASKS"):
            response = (
                self.client.table("subtasks")
                .select("id", count="exact")
                .eq("task_id", parameters[0])
                .execute()
            )
            self._count = response.count or 0
        elif normalized.startswith("UPDATE TASKS"):
            updates = {"status": parameters[0]}
            if "START_TIME" in normalized:
                updates["start_time"] = parameters[1]
                task_id = parameters[2]
            elif "TOTAL_TIME" in normalized:
                updates["total_time"] = parameters[1]
                task_id = parameters[2]
            else:
                task_id = parameters[1]
            self.client.table("tasks").update(updates).eq("id", task_id).execute()
        elif normalized.startswith("DELETE FROM TASKS"):
            self.client.table("tasks").delete().eq("id", parameters[0]).execute()
        elif normalized.startswith("SELECT ID, REFLECTION_DATE"):
            self._single_query = True
            response = (
                self.client.table("daily_reflections")
                .select(
                    "id, reflection_date, feeling, delay_reasons, note, "
                    "completed_tasks, pending_tasks, total_focus_time, ai_analysis, created_at"
                )
                .eq("reflection_date", parameters[0])
                .limit(1)
                .execute()
            )
            self._rows = [
                tuple(row.get(column) for column in (
                    "id", "reflection_date", "feeling", "delay_reasons", "note",
                    "completed_tasks", "pending_tasks", "total_focus_time", "ai_analysis", "created_at",
                ))
                for row in (response.data or [])
            ]
            self._single = self._rows[0] if self._rows else None
        elif normalized.startswith("UPSERT INTO DAILY_REFLECTIONS"):
            self.client.table("daily_reflections").upsert({
                "reflection_date": parameters[0],
                "feeling": parameters[1],
                "delay_reasons": parameters[2],
                "note": parameters[3],
                "completed_tasks": parameters[4],
                "pending_tasks": parameters[5],
                "total_focus_time": parameters[6],
                "ai_analysis": parameters[7],
            }, on_conflict="reflection_date").execute()
        else:
            raise ValueError(f"Unsupported database operation: {query.strip()}")

    def fetchall(self):
        return self._rows

    def fetchone(self):
        if self._single_query:
            return self._single
        if self._single is not None:
            return self._single
        return (self._count,)


class _SupabaseConnection:
    def __init__(self, client):
        self.client = client

    def cursor(self):
        return _SupabaseCursor(self.client)

    def commit(self):
        pass

    def close(self):
        pass


def get_connection():
    url, key = _require_settings()
    return _SupabaseConnection(create_client(url, key))


def create_table():
    """Tables are managed by Supabase migrations, not application startup."""
    return None
