from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from lunar_python import Solar
import pytz
import datetime as dt
import traceback

app = FastAPI()

# ---------- 请求模型（用于 POST JSON） ----------
class BaziReq(BaseModel):
    datetime_utc: str  # 例： "2025-01-15T08:30:00Z" 或 "2025-01-15T08:30:00+00:00"
    timezone: str      # 例： "Asia/Singapore"

# ---------- 工具：解析 ISO8601（必须是 UTC、tz-aware） ----------
def parse_datetime_utc(s: str) -> dt.datetime:
    s = (s or "").strip()
    if not s:
        raise HTTPException(status_code=400, detail="'datetime_utc' is required (ISO8601, UTC).")

    # 支持带 Z 的写法
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"

    try:
        parsed = dt.datetime.fromisoformat(s)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid 'datetime_utc' (ISO8601 required).")

    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise HTTPException(status_code=400, detail="'datetime_utc' must be timezone-aware (UTC).")

    # 归一为 UTC
    return parsed.astimezone(dt.timezone.utc)

# ---------- 工具：校验/获取时区 ----------
def get_tz(tz_name: str):
    name = (tz_name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="'timezone' is required.")
    try:
        return pytz.timezone(name)
    except Exception:
        raise HTTPException(status_code=400, detail=f"Invalid timezone '{tz_name}'.")

# ---------- 计算八字 ----------
def calc_bazi(datetime_utc: str, timezone: str):
    # 1) 解析 UTC
    utc_dt = parse_datetime_utc(datetime_utc)
    # 2) 转换到目标时区的本地时间
    tz = get_tz(timezone)
    local_dt = utc_dt.astimezone(tz)

    # 3) 转 Solar → Lunar → EightChar
    solar = Solar.fromYmdHms(
        local_dt.year, local_dt.month, local_dt.day,
        local_dt.hour, local_dt.minute, local_dt.second
    )
    lunar = solar.getLunar()
    ec = lunar.getEightChar()  # EightChar 对象

    return {
        "pillars": {
            "year":  {"stem": ec.getYearGan(),   "branch": ec.getYearZhi()},
            "month": {"stem": ec.getMonthGan(),  "branch": ec.getMonthZhi()},
            "day":   {"stem": ec.getDayGan(),    "branch": ec.getDayZhi()},
            "hour":  {"stem": ec.getTimeGan(),   "branch": ec.getTimeZhi()},
        },
        "local_time": local_dt.strftime("%Y-%m-%d %H:%M:%S"),
        "timezone": timezone,
    }

# ---------- 健康检查 ----------
@app.get("/")
def health():
    return {"ok": True, "msg": "Astro API is running."}

# ---------- POST（JSON Body） ----------
@app.post("/api/bazi/chart")
def bazi_chart_post(req: BaziReq):
    try:
        return calc_bazi(req.datetime_utc, req.timezone)
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={"error": str(e), "trace": traceback.format_exc()}
        )

# ---------- GET（便于直接在浏览器调试） ----------
# 例子：
# /api/bazi/chart?datetime_utc=2025-01-15T08:30:00Z&timezone=Asia/Singapore
@app.get("/api/bazi/chart")
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
