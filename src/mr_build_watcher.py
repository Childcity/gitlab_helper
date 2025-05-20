from datetime import date
import gitlab
import time
import json
import os
from plyer import notification
import argparse
from markdown2 import markdown


def load_state(state_file):
    if os.path.exists(state_file):
        with open(state_file, "r") as f:
            try:
                return dict(json.load(f))
            except json.JSONDecodeError:
                pass
    return {}


def save_state(state, state_file):
    with open(state_file, "w") as f:
        json.dump(state, f, indent=4, sort_keys=True)


def get_first_link_text(text_markdown):
    import xml.etree.ElementTree as ET

    try:
        parsed_body = markdown(text_markdown)
        parsed_body = ET.fromstring(f"<root>{parsed_body}</root>")
        link_tag = parsed_body.find(".//a")
        if link_tag is not None:
            return link_tag.text
    except ET.ParseError as e:
        print(f"Error parsing XML: {e}")
        return text_markdown


def notify_user(title, message):
    try:
        notification.notify(title=title, message=message, timeout=10)
    except Exception as e:
        print("Desktop notification failed:", e)


def process_jenkins_comment(mr_full, note, skip_rebuild):
    print(f"|{mr_full.iid}|: {note.body}")
    notify_user(
        f"MR {mr_full.iid}",
        f"{get_first_link_text(note.body)}",
    )

    if not skip_rebuild and any(
        s in note.body for s in ["Build failed", "Build aborted"]
    ):
        mr_full.notes.create({"body": "#ci rebuild"})


# Main watcher logic
def check_comments(gl, state):
    user = gl.user
    assigned_mrs = gl.mergerequests.list(assignee_id=user.id, state="opened", all=True)

    for mr in assigned_mrs:
        project = gl.projects.get(mr.project_id)
        mr_full = project.mergerequests.get(mr.iid)

        notes = mr_full.notes.list(order_by="created_at", sort="asc", all=True)

        mr_state = state.get(str(mr.iid), {})
        last_seen = mr_state.get("last_seen", "")
        last_note = mr_state.get("last_note", "")
        skip_rebuild = mr_state.get("skip_rebuild", False)
        new_last_seen = last_seen

        for note in notes:
            created_at = note.created_at
            note_author = note.author["name"]

            if "Jenkins" in note_author:
                last_note = note.body

                if created_at > last_seen:
                    if created_at > new_last_seen:
                        new_last_seen = created_at
                        process_jenkins_comment(mr_full, note, skip_rebuild)

        state[str(mr.iid)] = {
            "active_title": mr.title,
            "last_seen": new_last_seen,
            "web_url": mr.web_url,
            "last_note:": last_note,
            "skip_rebuild": skip_rebuild,
        }


if __name__ == "__main__":
    state_file = None
    state = None

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
        import traceback

        print(f"An error occurred: {e}\n")
        traceback.print_exc()
    finally:
        if state_file:
            save_state(state, state_file)
