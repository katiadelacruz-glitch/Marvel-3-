# Marvel — Reflective & Grammar Coach Chatbot (Flask, Python 3.11.9)

Marvel is a Spanish learning companion that promotes reflection over answers, nudges grammar awareness by level (A1–B2), and keeps responses short (≤150 words) with a warm Caribbean tone.

## Quick Start (PyCharm on Windows / macOS / Linux)

1. **Unzip** this folder somewhere simple (e.g., `C:\Projects\marvel`).
2. **Open in PyCharm** → *Open* the folder.
3. **Create a virtual env (Python 3.11.9)**  
   PyCharm usually prompts to create a venv. If not: *Settings* → *Project: Interpreter* → *Add* → *Virtualenv* (select Python 3.11).
4. **Install dependencies** (PyCharm will auto‑install from `requirements.txt`, or run in the terminal):  
   ```bash
   pip install -r requirements.txt
   ```
5. **Create a `.env`** from `.env.example` and set your key:
   ```text
   OPENAI_API_KEY=sk-...
   LLM_MODEL=gpt-mini-5
   SECRET_KEY=change-this
   ```
   > On PowerShell (temporary): `$env:OPENAI_API_KEY="sk-..."`  
   > To persist via CMD: `setx OPENAI_API_KEY "sk-..."` then open a new terminal.
6. **Run the app** (choose one):
   - PyCharm ▶ run configuration for `app.py`, or
   - Terminal:
     ```bash
     python app.py
     # or
     flask --app app.py run
     ```
7. Open your browser at **http://127.0.0.1:5000**.

## Project Structure

```
Marvel_Reflective_Grammar_Coach/
├─ app.py
├─ requirements.txt
├─ .env.example
├─ README.md
├─ static/
│  └─ app.css
└─ templates/
   ├─ base.html
   ├─ index.html
   └─ message.html
```

## Notes
- Default model is `gpt-mini-5` per your spec. If your OpenAI account uses a different name (e.g., `gpt-4o-mini`), change `LLM_MODEL` in `.env`.
- Responses are capped to 150 words and always **in Spanish**. The UI lets students pick level (A1–B2).
- Marvel never writes assignments or gives direct corrections; it guides reflection.

