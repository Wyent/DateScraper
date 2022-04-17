from fastapi import FastAPI

from Scraper import Scraper


app = FastAPI()  # create app instance
dates = Scraper()


# define route, use / for landing page
@app.get("/")  # get operator decorator
async def read_item(lat: float, lon: float):
    # return python dictionary, auto converted to json
    return dates.get_dates_meetup(lat, lon)

