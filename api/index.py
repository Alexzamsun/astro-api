# api/index.py
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from lunar_python import Solar, Lunar, EightChar
import pytz
import datetime as dt
import traceback

app = FastAPI()


# ========= 请求模型（用于 POST JSON） =========
class BaziReq(BaseModel):
    datetime_utc: str  # 例: "2025-01-15T08:30:00Z" 或 "2025-01-15T08:30:00+00:00"
    timezone: str      # 例: "Asia/Singapore"


# ========= 工具函数 =========
def parse_datetime_utc(s: str) -> dt.datetime:
    """
    解析 ISO8601 的 UTC 字符串，并返回 tz-aware 的 UTC datetime
    允许 "Z" 或 "+00:00" 结尾。若无时区则抛错（必须是 UTC）。
    """
    s = (s or "").strip()
    if not s:
        raise HTTPException(status_code=400, detail="'datetime_utc' is required (ISO8601, UTC).")

    # 兼容 ...Z 结尾
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"

    try:
        parsed = dt.datetime.fromisoformat(s)
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid 'datetime_utc' (ISO8601 required, e.g. '2025-01-15T08:30:00Z')."
        )

    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise HTTPException(status_code=400, detail="'datetime_utc' must be timezone-aware (UTC).")

    # 统一转换为 UTC
    return parsed.astimezone(dt.timezone.utc)


def get_tz(tz_name: str):
    name = (tz_name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="'timezone' is required.")
    try:
        return pytz.timezone(name)
    except Exception:
        raise HTTPException(status_code=400, detail=f"Invalid timezone '{tz_name}'.")


def calc_bazi(datetime_utc: str, timezone: str):
    """
    计算八字：UTC → 本地时区 → Solar → Lunar → EightChar
    兼容 lunar_python==1.6.11（用 EightChar.fromLunar）。
    """
    # 1) 解析 UTC
    utc_dt = parse_datetime_utc(datetime_utc)

    # 2) 转本地时区
    tz = get_tz(timezone)
    local_dt = utc_dt.astimezone(tz)

    # 3) 构造 Solar
    solar = Solar.fromYmdHms(
        local_dt.year, local_dt.month, local_dt.day,
        local_dt.hour, local_dt.minute, local_dt.second
    )

    # 4) Solar -> Lunar（1.6.x 正确姿势）
    lunar = solar.getLunar()

    # 5) Lunar -> EightChar
    ec = EightChar.fromLunar(lunar)

    # 6) 组织返回
    return {
        "pillars": {
            "year":  {"stem": ec.getYearGan(),  "branch": ec.getYearZhi()},
            "month": {"stem": ec.getMonthGan(), "branch": ec.getMonthZhi()},
            "day":   {"stem": ec.getDayGan(),   "branch": ec.getDayZhi()},
            "hour":  {"stem": ec.getTimeGan(),  "branch": ec.getTimeZhi()},
        },
        "local_time": local_dt.strftime("%Y-%m-%d %H:%M:%S"),
        "timezone": timezone,
    }


# ========= 健康检查 =========
@app.get("/")
def health():
    return {"ok": True, "msg": "Astro API is running."}


# ========= 路由：POST（JSON Body）=========
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


# ========= 路由：GET（Query 传参）=========
# 例子：
# https://astro-api-pied.vercel.app/api/bazi/chart?datetime_utc=2025-01-15T08:30:00Z&timezone=Asia/Singapore
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
