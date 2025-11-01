from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel
from lunar_python import Solar, Bazi
import pytz, datetime as dt

app = FastAPI()

class BaziReq(BaseModel):
    datetime_utc: str  # e.g. "2025-01-15T08:30:00Z"
    timezone: str      # e.g. "Asia/Singapore"

def parse_datetime(datetime_str: str) -> dt.datetime:
    """兼容带Z、+00:00或无时区的ISO时间"""
    s = datetime_str.strip()
    if s.endswith("Z"):
        s = s.replace("Z", "+00:00")
    try:
        parsed = dt.datetime.fromisoformat(s)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid datetime format, use ISO-8601 like 2025-01-15T08:30:00Z")
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)

def convert_timezone(utc_dt: dt.datetime, tz_name: str) -> dt.datetime:
    try:
        tz = pytz.timezone(tz_name)
    except Exception:
        raise HTTPException(status_code=400, detail=f"Invalid timezone '{tz_name}'")
    return utc_dt.astimezone(tz)

@app.get("/")
def health():
    return {"ok": True, "msg": "Astro API is running."}

@app.post("/bazi/chart")
def calc_bazi(req: BaziReq):
    try:
        utc_time = parse_datetime(req.datetime_utc)
        local_time = convert_timezone(utc_time, req.timezone)

        solar = Solar.fromYmdHms(local_time.year, local_time.month, local_time.day,
                                 local_time.hour, local_time.minute, local_time.second)
        bazi = Bazi.fromSolar(solar)

        return {
            "pillars": {
                "year": {"stem": bazi.getYearGan(), "branch": bazi.getYearZhi()},
                "month": {"stem": bazi.getMonthGan(), "branch": bazi.getMonthZhi()},
                "day": {"stem": bazi.getDayGan(), "branch": bazi.getDayZhi()},
                "hour": {"stem": bazi.getTimeGan(), "branch": bazi.getTimeZhi()},
            },
            "local_time": local_time.strftime("%Y-%m-%d %H:%M:%S"),
            "timezone": req.timezone
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
