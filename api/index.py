from fastapi import FastAPI
from fastapi.responses import Response
from pydantic import BaseModel
from lunar_python import Solar, EightChar   # ← 关键：用 EightChar
import pytz
from datetime import datetime as dt

app = FastAPI()

class BaziReq(BaseModel):
    datetime_utc: str
    timezone: str

@app.get("/favicon.ico")
def favicon():
    # 明确返回 204，避免 Vercel 预取 favicon 导致 500
    return Response(status_code=204)

@app.get("/")
def health():
    return {"ok": True, "msg": "Astro API is running."}

@app.post("/bazi/chart")
def get_bazi(req: BaziReq):
    try:
        # 统一处理 Z 结尾
        utc_time = dt.fromisoformat(req.datetime_utc.replace("Z", "+00:00"))
        tz = pytz.timezone(req.timezone)
        local_time = utc_time.astimezone(tz)

        # 构造 Solar 和 EightChar
        solar = Solar.fromYmdHms(
            local_time.year, local_time.month, local_time.day,
            local_time.hour, local_time.minute, local_time.second
        )
        ec = EightChar.fromSolar(solar)

        return {
            "pillars": {
                "year":  {"stem": ec.getYearGan(),  "branch": ec.getYearZhi()},
                "month": {"stem": ec.getMonthGan(), "branch": ec.getMonthZhi()},
                "day":   {"stem": ec.getDayGan(),   "branch": ec.getDayZhi()},
                "hour":  {"stem": ec.getTimeGan(),  "branch": ec.getTimeZhi()},
            },
            "local_time": local_time.strftime("%Y-%m-%d %H:%M:%S"),
            "timezone": req.timezone,
        }
    except Exception as e:
        # 不让函数崩掉，返回可读错误，便于定位
        return {"error": str(e)}
