from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from lunar_python import Solar, Bazi
import pytz
import datetime as dt
import traceback

app = FastAPI()

# ---- Request model（用于 POST JSON）----
class BaziReq(BaseModel):
    datetime_utc: str  # e.g. "2025-01-15T08:30:00Z" 或 "2025-01-15T08:30:00+00:00"
    timezone: str      # e.g. "Asia/Singapore"

# ---- 工具：解析 ISO8601（支持 Z/偏移量）并确保 tz-aware ----
def parse_datetime_utc(s: str) -> dt.datetime:
    s = (s or "").strip()
    if not s:
        raise HTTPException(status_code=400, detail="`datetime_utc` is required (ISO8601, UTC).")
    # 兼容末尾 'Z'
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        parsed = dt.datetime.fromisoformat(s)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid `datetime_utc` (ISO8601 required).")
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise HTTPException(status_code=400, detail="`datetime_utc` must be timezone-aware (UTC).")
    # 统一成 UTC
    return parsed.astimezone(dt.timezone.utc)

# ---- 工具：校验并返回 pytz 时区 ----
def get_tz(tz_name: str):
    name = (tz_name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="`timezone` is required.")
    try:
        return pytz.timezone(name)
    except Exception:
        raise HTTPException(status_code=400, detail=f"Invalid timezone '{tz_name}'.")

# ---- 计算八字的核心 ----
def calc_bazi(datetime_utc: str, timezone: str):
    utc_dt = parse_datetime_utc(datetime_utc)
    tz = get_tz(timezone)
    local_dt = utc_dt.astimezone(tz)

    solar = Solar.fromYmdHms(local_dt.year, local_dt.month, local_dt.day,
                             local_dt.hour, local_dt.minute, local_dt.second)
    bazi = Bazi.fromSolar(solar)

    return {
        "pillars": {
            "year":  {"stem": bazi.getYearGan(),  "branch": bazi.getYearZhi()},
            "month": {"stem": bazi.getMonthGan(), "branch": bazi.getMonthZhi()},
            "day":   {"stem": bazi.getDayGan(),   "branch": bazi.getDayZhi()},
            "hour":  {"stem": bazi.getTimeGan(),  "branch": bazi.getTimeZhi()},
        },
        "local_time": local_dt.strftime("%Y-%m-%d %H:%M:%S"),
        "timezone": timezone
    }

# ---- 健康检查 ----
@app.get("/")
def health():
    return {"ok": True, "msg": "Astro API is running."}

# ---- POST（标准用法：JSON Body）----
@app.post("/bazi/chart")
def bazi_chart_post(req: BaziReq):
    try:
        return calc_bazi(req.datetime_utc, req.timezone)
    except HTTPException:
        raise
    except Exception as e:
        # 返回 400 + 可读错误，不吞栈
        return JSONResponse(
            status_code=400,
            content={"error": str(e), "trace": traceback.format_exc()}
        )

# ---- GET（便于浏览器直接测：用 query 参数）----
# 例子：/bazi/chart?datetime_utc=2025-01-15T08:30:00Z&timezone=Asia/Singapore
@app.get("/bazi/chart")
def bazi_chart_get(datetime_utc: str, timezone: str):
    try:
        return calc_bazi(datetime_utc, timezone)
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={"error": str(e), "trace": traceback.format_exc()}
        )
