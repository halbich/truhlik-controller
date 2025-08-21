import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse
from starlette.responses import JSONResponse

from services.relay import get_relays_status, init_relay, set_relay

app = FastAPI(
    title="Truhlik API",
)

init_relay()


# --- HTML stránka ---
@app.get("/", include_in_schema=False)
async def root():
    return FileResponse("static/index.html")


# --- Stav všech relé (pro JS) ---
@app.get("/relays", include_in_schema=False)
async def relays_status():
    return JSONResponse(get_relays_status())


# --- Nastavení stavu relé ---
@app.post("/relay/{relay_id}/set_status")
async def set_relay_status(relay_id: int, is_on: bool):
    try:
        result: dict = set_relay(relay_id, is_on)
        return {"state": result}
    except Exception as e:
        return {"error": str(e)}


favicon_path = 'favicon.ico'


@app.get('/favicon.ico', include_in_schema=False)
async def favicon():
    return FileResponse(favicon_path)


if __name__ == "__main__":
    uvicorn.run("main_api:app", host="0.0.0.0", port=8081)
