from fastapi import FastAPI
from pydantic import BaseModel
from lunar_python import Solar, BaZi
import pytz
from datetime import datetime

app = FastAPI()

class BaziReq(BaseModel):
    datetime_utc: str
    timezone: str

@app.get("/")
def health():
    return {"ok": True, "msg": "Astro API is running."}

@app.post("/bazi/chart")
def get_bazi(req: BaziReq):
    try:
        utc_time = datetime.fromisoformat(req.datetime_utc.replace("Z", "+00:00"))
        tz = pytz.timezone(req.timezone)
        local_time = utc_time.astimezone(tz)

        solar = Solar.fromYmdHms(local_time.year, local_time.month, local_time.day,
                                 local_time.hour, local_time.minute, local_time.second)
        bazi = BaZi.fromSolar(solar)

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
    except Exception as e:
        return {"error": str(e)}
