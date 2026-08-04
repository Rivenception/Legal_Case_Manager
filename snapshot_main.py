"""
Entry point for the read-only "case snapshot" executable built by
build_snapshot.py. Not used for normal day-to-day running of the app —
see run.py for that.
"""
import os
import socket
import sys
import threading
import webbrowser


def _resource_path(relative):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative)


def _find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def main():
    os.environ["SNAPSHOT_MODE"] = "true"
    os.environ["CASE_TRACKER_INSTANCE_DIR"] = _resource_path("instance")

    from app import create_app

    app = create_app()
    port = _find_free_port()
    url = f"http://127.0.0.1:{port}/"

    print("=" * 60)
    print("Family Case Tracker — read-only snapshot")
    print("=" * 60)
    print(f"Opening {url} in your browser...")
    print("Log in with the Read_Only account (see the credentials file")
    print("that came with this program).")
    print()
    print("To stop the program, close this window.")
    print("=" * 60)

    threading.Timer(1.2, lambda: webbrowser.open(url)).start()
    app.run(host="127.0.0.1", port=port, debug=False)


if __name__ == "__main__":
    main()
