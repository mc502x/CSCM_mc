"""Self-locating dev entrypoint for the Browser-pane preview (.claude/launch.json),
which invokes this script with an unspecified working directory."""

import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)
sys.path.insert(0, BASE_DIR)

from wsgi import app  # noqa: E402

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(sys.argv[1]) if len(sys.argv) > 1 else 5000)
