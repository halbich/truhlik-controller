import uvicorn
from fastapi import FastAPI


from services.relay import get_relays_status



app = FastAPI(
    title="Truhlik API",
    root_path="/api",
)




@app.get("/")
async def root():

    return {
        "relays": get_relays_status(),
    }


if __name__ == "__main__":
    uvicorn.run("main_api:app", host="0.0.0.0", port=8081)
