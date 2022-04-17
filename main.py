from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from Scraper import Scraper

app = FastAPI()  # create app instance
dates = Scraper()

# allowed domains
origins = [
    # "https://vast-reaches-22877.herokuapp.com",
    # "http://localhost:3000"
    "http://google.com"
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
async def read_item(lat: float, lon: float):
    # return python dictionary, auto converted to json
    return dates.get_dates_meetup(lat, lon)
