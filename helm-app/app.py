from fastapi import FastAPI


app = FastAPI()


@app.get('/healthz')
@app.get('/readyz')
async def health():
    return 'OK'


@app.get('/')
async def root():
    return 'Hello'
