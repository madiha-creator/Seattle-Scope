# Seattle-Scope

## Run the integrated frontend locally

Install the Python dependencies, then run the FastAPI backend in one terminal:

```powershell
py -m pip install -r requirements.txt
py -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

In VS Code, open `static\index.html` with Live Server on port 5500. The frontend
uses `http://127.0.0.1:8000/api/` on that local origin and uses same-origin
`/api/` requests when deployed with FastAPI.

## Deploy frontend and backend together on Vercel

Vercel uses `vercel.json` to build the static frontend, cache, and output files
into `dist`. The FastAPI app in `backend.main:app` serves the API and registers
that directory as its frontend. The root `requirements.txt` includes the
FastAPI runtime dependencies.