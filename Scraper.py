import os
import sys
from pymongo import MongoClient
from bs4 import BeautifulSoup
from selenium import webdriver
import requests
import json
import geocoder
from fastapi import HTTPException
import random


class Scraper:

    @staticmethod
    def upsert_mongo(collection, search_key, insert_data):
        connect_str = 'mongodb+srv://takemeout:takemeout@takemeout.7kosh.mongodb.net/userTable?retryWrites=true&w=majority'
        cluster = MongoClient(connect_str)
        db = cluster["userTable"]
        collection = db[collection]

        collection.update_one(search_key, {'$set': insert_data}, upsert=True)

        # testing
        results = collection.find(search_key)
        # for result in results:
        # print(result)

    @staticmethod
    def create_headless_firefox_browser():
        # firefox_options = webdriver.FirefoxOptions()
        # firefox_options.add_argument('--headless')
        # driver = webdriver.Firefox(options=firefox_options)

        chrome_options = webdriver.ChromeOptions()
        chrome_options.binary_location = os.environ.get("GOOGLE_CHROME_BIN")
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--no-sandbox")
        try:
            driver = webdriver.Chrome(executable_path=os.environ.get("CHROMEDRIVER_PATH"),
                                      chrome_options=chrome_options)
        except Exception:
            driver = webdriver.Chrome(options=chrome_options)

        return driver

    @staticmethod
    def get_state_abrev(state):
        us_state_to_abbrev = {
            "Alabama": "AL",
            "Alaska": "AK",
            "Arizona": "AZ",
            "Arkansas": "AR",
            "California": "CA",
            "Colorado": "CO",
            "Connecticut": "CT",
            "Delaware": "DE",
            "Florida": "FL",
            "Georgia": "GA",
            "Hawaii": "HI",
            "Idaho": "ID",
            "Illinois": "IL",
            "Indiana": "IN",
            "Iowa": "IA",
            "Kansas": "KS",
            "Kentucky": "KY",
            "Louisiana": "LA",
            "Maine": "ME",
            "Maryland": "MD",
            "Massachusetts": "MA",
            "Michigan": "MI",
            "Minnesota": "MN",
            "Mississippi": "MS",
            "Missouri": "MO",
            "Montana": "MT",
            "Nebraska": "NE",
            "Nevada": "NV",
            "New Hampshire": "NH",
            "New Jersey": "NJ",
            "New Mexico": "NM",
            "New York": "NY",
            "North Carolina": "NC",
            "North Dakota": "ND",
            "Ohio": "OH",
            "Oklahoma": "OK",
            "Oregon": "OR",
            "Pennsylvania": "PA",
            "Rhode Island": "RI",
            "South Carolina": "SC",
            "South Dakota": "SD",
            "Tennessee": "TN",
            "Texas": "TX",
            "Utah": "UT",
            "Vermont": "VT",
            "Virginia": "VA",
            "Washington": "WA",
            "West Virginia": "WV",
            "Wisconsin": "WI",
            "Wyoming": "WY",
            "District of Columbia": "DC",
            "American Samoa": "AS",
            "Guam": "GU",
            "Northern Mariana Islands": "MP",
            "Puerto Rico": "PR",
            "United States Minor Outlying Islands": "UM",
            "U.S. Virgin Islands": "VI",
        }
        return us_state_to_abbrev.get(state)

    @staticmethod
    def get_indoor_outdoor(date_type):
        indoor = ['theater', 'winery', 'museum', 'bowling', 'range', 'bar']
        outdoor = ['garden', 'park', 'zoo', 'trail', 'aquarium']

        date_type = date_type.lower()

        # any(ele.startswith(type) or ele.endswith(type) for ele in indoor)

        if [ele for ele in indoor if (ele in date_type)]:
            return 'indoor'
        elif [ele for ele in outdoor if (ele in date_type)]:
            return 'outdoor'
        else:
            return None

    @staticmethod
    def get_reverse_geocode(latitude, longitude, state_abrev=False, country_abrev=False):
        g = geocoder.osm([latitude, longitude], method='reverse')
        # print(json.dumps(g.json, indent=4))
        city = g.city
        state = g.state
        country = g.country
        if state_abrev:
            state = Scraper.get_state_abrev(g.state)
        if country_abrev:
            country = g.country_code

        return city, state, country

    @staticmethod
    def get_lat_long(address):
        g = geocoder.osm(address)
        # print(json.dumps(g.json, indent=4))
        return g.lat, g.lng

    # dates is a list of dictionaries
    @staticmethod
    def filter_dates(dates, date_filter):
        '''dates = [{
            'name': title,
            'photoRef': img_url,
            'url': date_url,
            'time': time,
            'type': date_type,
            'indoor_outdoor': indoor_outdoor,
            'vicinity': vicinity,
            'details': details
        }]'''

        filtered_dates = []

        for date in dates:
            date_name = date['name'].lower()
            date_type = date['type'].lower()
            # print('Checking "', date_name, '" and "', date_type, '" against', date_filter)

            if [ele for ele in date_filter if (ele in date_name)]:
                filtered_dates.append(date)
            elif [ele for ele in date_filter if (ele in date_type)]:
                filtered_dates.append(date)

        if not filtered_dates:
            print('no dates found in filter')

        return filtered_dates

    def get_dates_tripbuzz(self, latitude, longitude, date_filter):
        try:
            city, state, country = self.get_reverse_geocode(latitude, longitude, state_abrev=True)
        except Exception as e:
            raise e

        print(city, state, country)
        location_string = city + '-' + state
        location_string.replace(" ", "-")
        domain = 'https://www.tripbuzz.com'
        query = '/date-ideas/'

        url = domain + query + location_string
        dates = []  # holds image, url, time, title

        pages_processed = 1
        while url is not None and pages_processed < 3:
            print('+++++++++++Getting Page #', pages_processed, '+++++++++++')
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_2) AppleWebKit/601.3.9 (KHTML, like Gecko) '
                              'Version/9.0.2 Safari/601.3.9'}

            try:
                r = requests.get(url, headers=headers, timeout=3)
            except requests.exceptions.ConnectTimeout as e:
                print(e)
                raise HTTPException(status_code=504,
                                    detail='Request timeout')
            soup = BeautifulSoup(r.content, 'lxml')

            # filtering exactly for class city-box to remove sponsored results
            results = soup.find_all(lambda tag: tag.name == 'div' and tag.get('class') == ['city-box'])

            result_count = 0
            for item in results:
                print('-----------Getting Event #', result_count + 1, '--------------')

                # image url extraction
                image_block = item.find('a', {'class': 'visual'})
                image_block = str(image_block)

                img_url = domain + image_block[image_block.find("(") + len("("):image_block.find(")")]

                # url extraction
                url_block = item.find('h3', {'itemprop': 'name'})
                date_url = domain + url_block.select('a')[0].get('href')

                # time extraction
                # need to use another api to get business hours
                time = None

                # title extraction
                title = url_block.find('a').get_text()

                # detail extraction
                details = [item.find('div', {'class': 'city-text'}).get_text()]

                # type extraction
                date_type = item.find('span', {'class': 'text-blue'}).get_text()

                indoor_outdoor = self.get_indoor_outdoor(date_type)

                # address extraction (vicinity)
                vicinity = item.find('span', {'class': 'city-address'}).get_text()
                lat, lon = self.get_lat_long(vicinity)

                dates.append({
                    'name': title,
                    'photoRef': img_url,
                    'url': date_url,
                    'time': time,
                    'type': date_type,
                    'indoor_outdoor': indoor_outdoor,
                    'vicinity': vicinity,
                    'location': {
                        'lat': lat,
                        'lon': lon
                    },
                    'details': details
                })

                result_count += 1

                # end processing list of dates

            # extracting next page
            # todo if there is no next page break out of parsing loop
            page_block = soup.find('div', {'class': 'paginate'})
            pages = page_block.select('a')
            next_page = domain + pages[-1].get('href')
            if url == next_page:
                url = None
            else:
                url = next_page

            pages_processed += 1

            # end processing pages

        date_header = {
            'location': {
                'lat': latitude,
                'lon': longitude
            },
            'country': country,
            'state': state,
            'city': city,
            'source': domain
        }
        dates_dict = {
            'dates': dates
        }
        date_collection = date_header | dates_dict
        # self.get_lat_long(dates[0]['vicinity'])

        # upsert entry to mongodb
        # self.upsert_mongo('dates', date_header, dates_dict)

        # return filtered data but upload original findings to mongoDB first

        # todo check if random tag is set, random dates first before filtering

        if date_filter is not None:
            dates = self.filter_dates(dates, date_filter)

        random.shuffle(dates)
        date_collection['dates'] = dates

        return date_collection

    def get_dates_meetup(self, latitude, longitude):
        import time
        # todo get lat, long from a port
        # tyler, tx
        # latitude = 32.3512601
        # longitude = -95.3010624

        # san jose
        # latitude = 37.3393857
        # longitude = -121.8949555

        # dallas
        # latitude = 32.779167
        # longitude = -96.808891

        # get geocode from lat, long
        try:
            city, state, country = self.get_reverse_geocode(latitude, longitude, country_abrev=True)
        except Exception as e:
            print(e)
            sys.exit()
        # sys.exit()
        print(city, state, country)
        '''country = 'us'
        state = 'tx'
        city = 'tyler'''

        location_string = country + '--' + state + '--' + city
        location_string.replace(" ", "+")
        domain = 'https://www.meetup.com'
        html_query = 'https://www.meetup.com/find/?location='
        html_query2 = '&source=EVENTS'
        url = html_query + location_string + html_query2

        # appear as a browser
        browser = self.create_headless_firefox_browser()
        browser.get(url)

        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_2) AppleWebKit/601.3.9 (KHTML, like Gecko) '
                          'Version/9.0.2 Safari/601.3.9'}
        time.sleep(1)
        html = browser.page_source
        soup = BeautifulSoup(html, 'lxml')
        print(url)
        # unable to find location
        # todo check if string contains city, statecode
        if len(soup.select('.py-4.text-gray6.font-normal')[0].get_text()) == 22:
            location_string = country + '--' + city
            url = html_query + location_string + html_query2
            # print(url)
            browser = self.create_headless_firefox_browser()
            browser.get(url)
            time.sleep(1)
            html = browser.page_source
            soup = BeautifulSoup(html, 'lxml')

        if len(soup.select('.py-4.text-gray6.font-normal')[0].get_text()) == 22:
            print('unable to find location')
            # sys.exit()

        result_count = 0
        dates = []

        for item in soup.select('#event-card-in-search-results'):
            try:
                print('-----------Getting Event #', result_count + 1, '--------------')
                # image url
                all_imgs = item.find_all('img')
                for image in all_imgs:
                    try:
                        img_url = image['src']
                    except Exception as e:
                        img_url = None
                    # print(img_url)

                # event link
                date_url = item.get('href')
                # print(date_url)

                # date(time)
                time = item.select('time')[0].get_text()
                # print(time)

                # title
                title = item.select('.text-gray7')[0].get_text()
                # print(title)

                # group name
                group_name = item.select('.text-gray6')[0].get_text()
                # print(group_name)

                # details
                details = []
                date_page = requests.get(date_url, headers=headers)
                soup = BeautifulSoup(date_page.content, 'lxml')
                for text in soup.select('.break-words'):
                    try:
                        for paragraph in text.select('.mb-4'):
                            details.append(paragraph.get_text())
                            # print(details[-1])
                    except Exception as e:
                        print('')

                dates.append({'image': img_url, 'url': date_url, 'time': time, 'title': title, 'details': details})

                result_count += 1

                if result_count == 5:
                    break

            except Exception as e:
                # raise e
                print('')

        date_header = {
            'country': country,
            'state': state,
            'city': city,
            'source': domain
        }
        dates_dict = {
            'dates': dates
        }
        date_collection = date_header | dates_dict
        json_date_collection = json.dumps(date_collection)
        print(json_date_collection)
        print('Number of results: ', result_count)

        self.upsert_mongo('dates', date_header, dates_dict)
        return date_collection

        '''client = pymongo.MongoClient(<CONNECTION STRING>)
        db = client.<DATABASE>
        collection = db.<COLLECTION>
        
        result = collection.bulk_write(json_date_collection)
        client.close()'''
