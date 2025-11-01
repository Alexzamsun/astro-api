from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.responses import Response
from lunar_python import Solar, Bazi
import pytz, datetime as dt

app = FastAPI()

class BaziReq(BaseModel):
    datetime_utc: str
    timezone: str

# 已有的 POST
@app.post("/bazi/chart")
def bazi_chart(req: BaziReq):
    return _calc_bazi(req.datetime_utc, req.timezone)

# 新增：GET 兼容
@app.get("/bazi/chart")
def bazi_chart_get(datetime_utc: str, timezone: str):
    return _calc_bazi(datetime_utc, timezone)

def _calc_bazi(datetime_utc: str, timezone: str):
    try:
        utc_time = dt.datetime.fromisoformat(datetime_utc.replace("Z", "+00:00"))
        local_tz = pytz.timezone(timezone)
        local_time = utc_time.astimezone(local_tz)

        solar = Solar.fromYmdHms(local_time.year, local_time.month, local_time.day,
                                 local_time.hour, local_time.minute, local_time.second)
        bazi = Bazi.fromSolar(solar)

        return {
            "pillars": {
                "year":  {"stem": bazi.getYearGan(),  "branch": bazi.getYearZhi()},
                "month": {"stem": bazi.getMonthGan(), "branch": bazi.getMonthZhi()},
                "day":   {"stem": bazi.getDayGan(),   "branch": bazi.getDayZhi()},
                "hour":  {"stem": bazi.getTimeGan(),  "branch": bazi.getTimeZhi()}
            },
            "local_time": local_time.strftime("%Y-%m-%d %H:%M:%S"),
            "timezone": timezone
        }
    except Exception as e:
        return {"error": str(e)}
