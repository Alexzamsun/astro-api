from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from lunar_python import Solar, Bazi
import pytz, datetime as dt
import traceback, sys

app = FastAPI()

class BaziReq(BaseModel):
    datetime_utc: str  # 例如: "2025-01-15T08:30:00Z"
    timezone: str      # 例如: "Asia/Singapore"

def parse_datetime(datetime_str: str) -> dt.datetime:
    """兼容 'Z'、'+00:00' 或不带时区的 ISO 时间；最终返回 UTC aware datetime"""
    s = (datetime_str or "").strip()
    if not s:
        raise HTTPException(status_code=400, detail="`datetime_utc` is required")
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        parsed = dt.datetime.fromisoformat(s)
    except Exception:
        raise HTTPException(status_code=400,
                            detail="Invalid datetime format, use ISO-8601 like 2025-01-15T08:30:00Z")
    if parsed.tzinfo is None:
        # 如果用户没带时区，就当作 UTC
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)

def convert_timezone(utc_dt: dt.datetime, tz_name: str) -> dt.datetime:
    if not tz_name:
        raise HTTPException(status_code=400, detail="`timezone` is required")
    try:
        tz = pytz.timezone(tz_name)
    except Exception:
        raise HTTPException(status_code=400, detail=f"Invalid timezone '{tz_name}'")
    return utc_dt.astimezone(tz)

def calc_bazi_core(datetime_utc: str, timezone: str):
    utc_time   = parse_datetime(datetime_utc)
    local_time = convert_timezone(utc_time, timezone)

    # lunar_python
    solar = Solar.fromYmdHms(local_time.year, local_time.month, local_time.day,
                             local_time.hour, local_time.minute, local_time.second)
    bazi = Bazi.fromSolar(solar)

    return {
        "pillars": {
            "year":  {"stem": bazi.getYearGan(),  "branch": bazi.getYearZhi()},
            "month": {"stem": bazi.getMonthGan(), "branch": bazi.getMonthZhi()},
            "day":   {"stem": bazi.getDayGan(),   "branch": bazi.getDayZhi()},
            "hour":  {"stem": bazi.getTimeGan(),  "branch": bazi.getTimeZhi()},
        },
        "local_time": local_time.strftime("%Y-%m-%d %H:%M:%S"),
        "timezone": timezone
    }

@app.get("/")
def health():
    return {"ok": True, "msg": "Astro API is running."}

# 方便浏览器直接测
@app.get("/bazi/chart")
def bazi_chart_get(datetime_utc: str, timezone: str):
    try:
        return calc_bazi_core(datetime_utc, timezone)
    except HTTPException as e:
        raise e
    except Exception:
        # 把完整异常打到 Runtime Logs（Vercel 的 Runtime Logs 面板可见）
        print(traceback.format_exc(), file=sys.stderr, flush=True)
        raise HTTPException(status_code=500, detail="Internal error")

# 正式接口（POST）
@app.post("/bazi/chart")
def bazi_chart_post(req: BaziReq):
    try:
        return calc_bazi_core(req.datetime_utc, req.timezone)
    except HTTPException as e:
        raise e
    except Exception:
        print(traceback.
