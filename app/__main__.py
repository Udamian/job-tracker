import uvicorn

if __name__ == "__main__":
    # Desarrollo: solo 127.0.0.1 y sin --reload.
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False)
