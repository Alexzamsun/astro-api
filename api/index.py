from fastapi import FastAPI
from pydantic import BaseModel
from lunar_python import Solar, BaZi
import pytz, datetime as dt

app = FastAPI()

class BaziReq(BaseModel):
    datetime_utc: str
    timezone: str

@app.post("/api/bazi/chart")
def bazi_chart(req: BaziReq):
    t = dt.datetime.fromisoformat(req.datetime_utc.replace("Z","+00:00"))
    local = t.astimezone(pytz.timezone(req.timezone))
    solar = Solar.fromYmdHms(local.year, local.month, local.day, local.hour, local.minute, local.second)
    bazi = BaZi.fromSolar(solar)
    return {
        "pillars": {
            "year": {"stem": bazi.getYearGan(), "branch": bazi.getYearZhi()},
            "month":{"stem": bazi.getMonthGan(),"branch": bazi.getMonthZhi()},
            "day":  {"stem": bazi.getDayGan(),  "branch": bazi.getDayZhi()},
            "hour": {"stem": bazi.getTimeGan(), "branch": bazi.getTimeZhi()},
        },
        "meta": {"algo":"lunar_python","tz":req.timezone}
    }
