# PantryPilot

Agentic Meal-Planning & Grocery Checkout (AP2-aligned)

## Documentation

* [Project Requirements Document](docs/PRD.md)

## Getting Started

1. **Create a virtual environment (optional but recommended).**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
   ```
2. **Install dependencies.**
   ```bash
   pip install -r requirements.txt
   ```
3. **Launch the Streamlit demo.**
   ```bash
   streamlit run streamlit_app.py
   ```

The demo walks through mandate creation, agent cart building, AP2 signing, and merchant verification flows described in the PRD.
