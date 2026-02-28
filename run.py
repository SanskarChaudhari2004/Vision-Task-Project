"""Entry point script for running the Vision Task server."""
from vision_task import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
