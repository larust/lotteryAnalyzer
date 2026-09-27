"""Compatibility Flask entry point: python app.py or flask --app app run."""

from lottery_analyzer.web import create_app

app = create_app()

if __name__ == "__main__":
    app.run()
