from datetime import date
import gitlab
import time
import json
import os
from plyer import notification
import argparse


# Load or initialize state
def load_state(state_file):
    if os.path.exists(state_file):
        with open(state_file, "r") as f:
            return json.load(f)
    return {}


def save_state(state, state_file):
    with open(state_file, "w") as f:
        json.dump(state, f)


# Notify
def notify_user(title, message):
    print(f"[Notification] {title}: {message}")
    try:
        notification.notify(title=title, message=message, timeout=10)
    except Exception as e:
        print("Desktop notification failed:", e)


# Main watcher logic
def check_comments(gl: gitlab.Gitlab, state):
    user = gl.user
    assigned_mrs = gl.mergerequests.list(assignee_id=user.id, state="opened", all=True)

    for mr in assigned_mrs:
        project = gl.projects.get(mr.project_id)
        mr_full = project.mergerequests.get(mr.iid)
        notes = mr_full.notes.list(order_by="created_at", sort="asc", all=True)

        last_seen = state.get(str(mr.id), "")
        new_last_seen = last_seen

        for note in notes:
            created_at = note.created_at
            # if created_at > last_seen and note.author["id"] != user.id:
            if created_at > last_seen:
                notify_user(
                    f"New comment in MR !{mr.iid}",
                    f"{note.author['name']} said: {note.body[:100]}",
                )
                if created_at > new_last_seen:
                    new_last_seen = created_at

        state[str(mr.id)] = new_last_seen


if __name__ == "__main__":
    state_file = None

    try:
        parser = argparse.ArgumentParser(description="GitLab MR Comment Watcher")
        parser.add_argument(
            "--gitlab-url", default="https://gitlab.com", help="GitLab instance URL"
        )
        parser.add_argument(
            "--private-token",
            default="glpat-******",
            help="Private token for GitLab API",
        )
        parser.add_argument(
            "--check-interval",
            type=int,
            default=5,
            help="Interval to check for comments (in seconds)",
        )
        parser.add_argument(
            "--state-file",
            default="comment_watcher_state.json",
            help="File to save watcher state",
        )
        args = parser.parse_args()

        gl = gitlab.Gitlab(args.gitlab_url, private_token=args.private_token)
        gl.auth()

        state_file = args.state_file
        state = load_state(state_file)

        while True:
            print(f"{time.strftime('%H:%M:%S')} Checking for new comments...")
            check_comments(gl, state)
            save_state(state, state_file)
            time.sleep(args.check_interval)

    except KeyboardInterrupt:
        print("Watcher stopped.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if state_file:
            save_state(state, state_file)
