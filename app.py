"""Local development entrypoint. On Vercel, api/index.py is used instead."""
from api.index import app

if __name__ == "__main__":
    import os
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
