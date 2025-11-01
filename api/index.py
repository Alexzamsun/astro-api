from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
import pytz
import datetime as dt
import traceback

app = FastAPI()

@app.get("/")
@app.get("/api")
def health():
    return {"ok": True, "msg": "Astro API is running."}

def calc_bazi(datetime_utc: str, timezone: str):
    # 延迟导入，避免冷启动直接炸
    try:
        from lunar_python import Solar, BaZi
    except Exception as e:
        return {"error": f"import lunar_python failed: {repr(e)}"}

    try:
        # 你的时间解析 + 转时区代码...
        # ...
        solar = Solar.fromYmdHms(local_dt.year, local_dt.month, local_dt.day,
                                 local_dt.hour, local_dt.minute, local_dt.second)
        bazi = BaZi.fromSolar(solar)
        return {
            "pillars": {
                "year":  {"stem": bazi.getYearGan(),  "branch": bazi.getYearZhi()},
                "month": {"stem": bazi.getMonthGan(), "branch": bazi.getMonthZhi()},
                "day":   {"stem": bazi.getDayGan(),   "branch": bazi.getDayZhi()},
                "time":  {"stem": bazi.getTimeGan(),  "branch": bazi.getTimeZhi()},
            },
            "local_time": local_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "timezone": timezone,
        }
    except Exception as e:
        return {"error": str(e), "trace": traceback.format_exc()}

@app.get("/api/bazi/chart")
def bazi_chart_get(datetime_utc: str, timezone: str):
    result = calc_bazi(datetime_utc, timezone)
    if "error" in result:
        return JSONResponse(result, status_code=400)
    return result

@app.post("/api/bazi/chart")
def bazi_chart_post(req: dict):
    result = calc_bazi(req.get("datetime_utc", ""), req.get("timezone", ""))
    if "error" in result:
        return JSONResponse(result, status_code=400)
    return result
