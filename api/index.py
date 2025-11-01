from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel
from lunar_python import Solar, Bazi
import pytz, datetime as dt

app = FastAPI()

class BaziReq(BaseModel):
    datetime_utc: str  # e.g. "2025-01-15T08:30:00Z"
    timezone: str      # e.g. "Asia/Singapore"

def _parse_iso_utc(s: str) -> dt.datetime:
    """把各种常见写法规范成有时区的 UTC 时间。"""
    if not isinstance(s, str):
        raise HTTPException(status_code=400, detail="datetime_utc must be a string")

    s = s.strip()
    # 允许 "Z"、"+00:00"、没有时区（视为 UTC）
    if s.endswith("Z"):
        s = s.replace("Z", "+00:00")
    try:
        t = dt.datetime.fromisoformat(s)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="datetime_utc must be ISO-8601, e.g. 2025-01-15T08:30:00Z"
        )
    if t.tzinfo is None:
        # 没有时区就当成 UTC
        t = t.replace(tzinfo=dt.timezone.utc)
    return t.astimezone(dt.timezone.utc)

def _to_local(utc_dt: dt.datetime, tz_name: str) -> dt.datetime:
    try:
        tz = pytz.timezone(tz_name)
    except Exception:
        raise HTTPException(
            status_code=400,
            detail=f"invalid timezone '{tz_name}'. Try e.g. 'Asia/Singapore'."
        )
    return utc_dt.astimezone(tz)

def _calc_bazi(datetime_utc: str, timezone: str):
    # 统一在这里解析和校验
    utc_time = _parse_iso_utc(datetime_utc)
    local_time = _to_local(utc_time, timezone)

    solar = Solar.fromYmdHms(
        local_time.year, local_time.month, local_time.day,
        local_time.hour, local_time.minute, local_time.second
    )
    bazi = Bazi.fromSolar(solar)

    return {
        "pillars": {
            "year":  {"stem": bazi.getYearGan(),  "branch": bazi.getYearZhi()},
            "month": {"stem": bazi.getMonthGan(), "branch": bazi.getMonthZhi()},
            "day":   {"stem": bazi.getDayGan(),   "branch": bazi.getDayZhi()},
            "hour":  {"stem": bazi.getTimeGan(),  "branch": bazi.getTimeZhi()},
        },
        "local_time": local_time.strftime("%Y-%m-%d %H:%M:%S"),
        "timezone": timezone,
    }

@app.get("/favicon.ico")
def favicon():
    return Response(status_code=204)

@app.get("/")
def health():
    return {"ok": True, "msg": "Astro API is running."}

@app.post("/bazi/chart")
def post_bazi(req: BaziReq):
    return _calc_bazi(req.datetime_utc, req.timezone)

@app.get("/bazi/chart")
def get_bazi_chart(datetime_utc: str, timezone: str):
    return _calc_bazi(datetime_utc, timezone)
