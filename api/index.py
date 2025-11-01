from fastapi import FastAPI
from pydantic import BaseModel
from lunar_python import Solar, BaZi   # 注意：BaZi（B 大写 Z 大写 i 小写）
import pytz, datetime as dt

app = FastAPI()

class BaziReq(BaseModel):
    datetime_utc: str  # ISO 格式 UTC 时间，如 "1985-07-18T01:20:00Z"
    timezone: str      # 例如 "Asia/Singapore"

@app.get("/")
def health():
    return {"ok": True}

@app.post("/bazi/chart")
def bazi_chart(req: BaziReq):
    # 解析 UTC → 转为本地时区
    t = dt.datetime.fromisoformat(req.datetime_utc.replace("Z", "+00:00"))
    local = t.astimezone(pytz.timezone(req.timezone))

    # 生成八字
    solar = Solar.fromYmdHms(local.year, local.month, local.day,
                             local.hour, local.minute, local.second)
    bazi = BaZi.fromSolar(solar)

    return {
        "pillars": {
            "year":  {"stem": bazi.getYearGan(),  "branch": bazi.getYearZhi()},
            "month": {"stem": bazi.getMonthGan(), "branch": bazi.getMonthZhi()},
            "day":   {"stem": bazi.getDayGan(),   "branch": bazi.getDayZhi()},
            "hour":  {"stem": bazi.getTimeGan(),  "branch": bazi.getTimeZhi()}
        },
        "meta": {"algo": "lunar_python", "tz": req.timezone}
    }
