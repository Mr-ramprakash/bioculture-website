"""Vercel Python Functions entry point for the existing FastAPI application."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from chatbot.main import app

