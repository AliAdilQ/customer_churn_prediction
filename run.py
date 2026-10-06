"""Local development entry point. Debugging is opt-in and disabled by default."""

import os

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "5000")),
        debug=app.config["APP_ENV"] != "production" and os.getenv("FLASK_DEBUG") == "1",
    )
