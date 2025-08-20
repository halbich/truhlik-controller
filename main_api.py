import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse

from services.relay import get_relays_status, init_relay

app = FastAPI(
    title="Truhlik API",
    root_path="/api",
)

init_relay()

@app.get("/")
async def root():
    return {
        "relays": get_relays_status(),
    }


favicon_path = 'favicon.ico'


@app.get('/favicon.ico', include_in_schema=False)
async def favicon():
    return FileResponse(favicon_path)


if __name__ == "__main__":
    uvicorn.run("main_api:app", host="0.0.0.0", port=8081)
