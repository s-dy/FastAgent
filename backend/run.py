import uvicorn
from dotenv import load_dotenv
import os

load_dotenv()
from app.config import settings
if settings.HF_ENDPOINT:
    os.environ["HF_ENDPOINT"] = settings.HF_ENDPOINT

if __name__ == "__main__":
    # 启动Uvicorn服务器
    # --reload: 代码变更时自动重启，方便开发
    # --host 0.0.0.0: 监听所有网络接口，允许局域网访问
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)
