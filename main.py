import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import train #, prediction

# FastAPI app instance 만들기
app = FastAPI()


# An origin is the combination of protocol (http, https),
#  domain (myapp.com, localhost, localhost.tiangolo.com),
#  and port (80, 443, 8080).
origin = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origin, # 허용되는 origin
    allow_methods=["*"], # 허용되는 HTTP method ['GET']
    allow_headers=["*"], # 허용되는 HTTP request header
    allow_credentials=True, # 여러 origin에 대해서 쿠키가 허용되게 할 것인가
)

#app.include_router(predict.router)
app.include_router(train.router)

@app.get("/")
def hello_world():
    return {"message": "Hello World"}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=["app/"],
    )