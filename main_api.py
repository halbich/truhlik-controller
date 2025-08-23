import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse
from starlette.responses import JSONResponse
from typing import Optional

from services.relay import get_relays_status, init_relay, set_relay, get_last_update, check_schedule

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
async def relays_status(last: Optional[int] = 0):
    try:
        server_last = get_last_update()
        if last and int(last) == server_last:
            return JSONResponse(status_code=304, content=None)
        return JSONResponse(get_relays_status())
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# --- Nastavení stavu relé ---
@app.post("/relay/{relay_id}/set_status")
async def set_relay_status(relay_id: int, is_on: bool, last: Optional[int] = 0):
    try:
        result: dict = set_relay(relay_id, is_on)
        return {"state": result, "last": get_last_update()}
    except Exception as e:
        return {"error": str(e)}


# --- Spuštění kontroly rozvrhu ---
@app.post("/check_schedule")
async def post_check_schedule():
    try:
        result: dict = check_schedule()
        return result
    except Exception as e:
        return {"error": str(e)}


favicon_path = 'favicon.ico'


@app.get('/favicon.ico', include_in_schema=False)
async def favicon():
    return FileResponse(favicon_path)


if __name__ == "__main__":
    uvicorn.run("main_api:app", host="0.0.0.0", port=8081)
