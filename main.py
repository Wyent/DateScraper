from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from Scraper import Scraper
from typing import Optional

app = FastAPI()  # create app instance
dates = Scraper()

# allowed domains
origins = [
    "https://vast-reaches-22877.herokuapp.com",
    "https://powerful-taiga-30378.herokuapp.com/"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=[]
)


# define route, use / for landing page
@app.get("/")  # get operator decorator
async def read_item(lat: float, lon: float, filter: Optional[str] = None):
    # return python dictionary, auto converted to json
    # return dates.get_dates_meetup(lat, lon)
    city, state, country = dates.get_reverse_geocode(lat, lon, country_abrev=True)
    if country != 'us':
        raise HTTPException(status_code=512,
                            detail='Country is not U.S')
    else:
        return dates.get_dates_tripbuzz(lat, lon, filter)
