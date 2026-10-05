from fastapi import FastAPI

app = FastAPI(title="TaskPay API")


@app.get("/")
def root():
    return {
        "app": "TaskPay",
        "status": "running"
    }


@app.get("/health")
def health():
    return {
        "status": "ok"
    }
