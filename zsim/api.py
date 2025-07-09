"""
此处为api入口文件，负责启动FastAPI应用，不要在这里定义路由或写其他业务逻辑。
所有路由应在api_src/routes目录下定义。
业务逻辑应在api_src/service目录下实现。
请确保在运行此文件时，FastAPI能够正确加载所有路由和服务。
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from zsim.api_src.routes import router as api_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["127.0.0.1"],  # Allow only loopback address
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api", tags=["ZSim API"])


@app.get("/health")
async def health_check():
    """
    Health check endpoint for the ZSim API.

    Returns:
        dict: A simple message indicating the API is running.
    """
    return {"message": "ZSim API is running!"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("zsim.api:app", host="127.0.0.1", port=8000, log_level="info", reload=True)
