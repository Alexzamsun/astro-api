from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import datetime as dt
import pytz
import traceback

# lunar_python 可能在不同版本里暴露的类名一致，但方法不同
# 我们统一从这里导入
from lunar_python import Solar, Lunar
try:
    # 有的版本类名是 EightChar
    from lunar_python import EightChar as _EightChar
except Exception:
    _EightChar = None

app = FastAPI()


class BaziReq(BaseModel):
    # 传 ISO8601 UTC，比如 "2025-01-15T08:30:00Z"
    datetime_utc: str
    # 传 IANA 时区，比如 "Asia/Singapore"
    timezone: str = "Asia/Singapore"


def _parse_datetime_utc(s: str) -> dt.datetime:
    s = (s or "").strip()
    if not s:
        raise HTTPException(status_code=400, detail="'datetime_utc' is required (ISO8601, UTC).")
    # 兼容没有 Z 的情况
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        parsed = dt.datetime.fromisoformat(s)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid 'datetime_utc' (ISO8601 required).")
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise HTTPException(status_code=400, detail="'datetime_utc' must be timezone-aware (UTC).")
    # 统一转成 UTC
    return parsed.astimezone(dt.timezone.utc)


def _get_tz(tz_name: str):
    name = (tz_name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="'timezone' is required.")
    try:
        return pytz.timezone(name)
    except Exception:
        raise HTTPException(status_code=400, detail=f"Invalid timezone '{tz_name}'.")


def _to_local(utc_dt: dt.datetime, tz) -> dt.datetime:
    # 返回带 tzinfo 的本地时间
    return utc_dt.astimezone(tz)


def _bazi_from_solar(local_dt: dt.datetime) -> dict:
    """
    兼容两种 API：
    - 有 fromSolar：直接用
    - 没有 fromSolar：先把阳历转 Lunar，再用 fromLunar
    """
    # 先构造 Solar
    solar = Solar.fromYmdHms(
        local_dt.year, local_dt.month, local_dt.day,
        local_dt.hour, local_dt.minute, local_dt.second
    )

    # 情况 A：EightChar.fromSolar 可用
    if _EightChar and hasattr(_EightChar, "fromSolar"):
        ec = _EightChar.fromSolar(solar)
        # 常见属性名：getYearGanZhi/getMonthGanZhi/getDayGanZhi/getTimeGanZhi
        return {
            "year":  {"stem": ec.getYearGan(),  "branch": ec.getYearZhi()},
            "month": {"stem": ec.getMonthGan(), "branch": ec.getMonthZhi()},
            "day":   {"stem": ec.getDayGan(),   "branch": ec.getDayZhi()},
            "hour":  {"stem": ec.getTimeGan(),  "branch": ec.getTimeZhi()},
        }

    # 情况 B：只有 fromLunar
    lunar = Lunar.fromDate(local_dt)  # 直接把 datetime 转 Lunar（库内部做换算）
    if _EightChar and hasattr(_EightChar, "fromLunar"):
        ec = _EightChar.fromLunar(lunar)
        return {
            "year":  {"stem": ec.getYearGan(),  "branch": ec.getYearZhi()},
            "month": {"stem": ec.getMonthGan(), "branch": ec.getMonthZhi()},
            "day":   {"stem": ec.getDayGan(),   "branch": ec.getDayZhi()},
            "hour":  {"stem": ec.getTimeGan(),  "branch": ec.getTimeZhi()},
        }

    # 如果上面两种都不可用，给出明确报错
    raise HTTPException(
        status_code=500,
        detail="Incompatible 'lunar_python' version: neither 'EightChar.fromSolar' nor 'fromLunar' found."
    )


def calc_bazi(datetime_utc: str, timezone: str) -> dict:
    utc_dt = _parse_datetime_utc(datetime_utc)
    tz = _get_tz(timezone)
    local_dt = _to_local(utc_dt, tz)

    pillars = _bazi_from_solar(local_dt)

    return {
        "pillars": pillars,
        "local_time": local_dt.strftime("%Y-%m-%d %H:%M:%S"),
        "timezone": timezone,
    }


@app.get("/")
def health():
    return {"ok": True, "msg": "Astro API is running."}


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


@app.get("/api/bazi/chart")
def bazi_chart_get(datetime_utc: str, timezone: str):
    # 例：/api/bazi/chart?datetime_utc=2025-01-15T08:30:00Z&timezone=Asia/Singapore
    try:
        return calc_bazi(datetime_utc, timezone)
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={"error": str(e), "trace": traceback.format_exc()}
        )
