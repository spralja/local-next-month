from string import Template
from datetime import date
import calendar
from typing import List, Iterable
import sys
import shelve
import random
import os

from bs4 import BeautifulSoup
import requests
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials


class clientCAPI:
    def __init__(self, base_url=os.environ.get('LOCAL_NEXT_MONTH_CAPI_BASE_URL')):
        self.base_url = base_url

    def _create_url(self, metro_id: int, start_date: date, end_date: date, page: int):
        """
        This function constructs the url endpoint which returns artists in a certian time frame in a certain area
        """
        URL_TEMPLATE = Template('${base_url}metro-areas/$metro_id?utf8=%E2%9C%93&filters%5BminDate%5D=$start_month%2F$start_day%2F$start_year&filters%5BmaxDate%5D=$end_month%2F$end_day%2F$end_year&page=$page#metro-area-calendar')
        return URL_TEMPLATE.substitute(
            base_url=self.base_url,
            metro_id=str(metro_id),
            start_day=start_date.day,
            start_month=start_date.month,
            start_year=start_date.year,
            end_day=end_date.day,
            end_month=end_date.month,
            end_year=end_date.year,
            page=str(page),
        )
    
    @staticmethod
    def _is_last_page(response: requests.models.Response):
        """
        This function checks whether the page is out of bounds
        """
        for tag in BeautifulSoup(response.text, features="html.parser").find_all('p'):
            if tag.getText().find('Your search returned no results') != -1:
                return True
    
    def _get_metro_area_pages(self, metro_id: int, start_date: date, end_date: date):
        """
        Get all pages available for the time frame and city, max of 30
        """
        pages = []
        for i in range(1, 31):
            print(self._create_url(metro_id, start_date, end_date, i))
            response = requests.get(self._create_url(metro_id, start_date, end_date, i))
            if self._is_last_page(response): break
                
            pages.append(response.text)
            
        return pages
    
    def get_metro_area_concerts(self, metro_id: int, year: int, month: int):
        """
        Get a list of concert names for the given (month, year) and given area
        """
        key = f'{metro_id}-{year}-{month}'
        with shelve.open('database') as db:
            if key in db:
                concerts = db[key]

                random.shuffle(concerts)

                return concerts
            else: 
                db[key] = []
        
        start_date = date(year, month, 1)
        end_date = date(year, month, calendar.monthrange(year, month)[1])
        pages = self._get_metro_area_pages(metro_id, start_date, end_date)
        concerts = []
        for page in pages:
            strongs = BeautifulSoup(page).find_all('strong')
            for strong in strongs:
                concerts.append(strong.string)
        
        random.shuffle(concerts)

        with shelve.open('database') as db:
            db[key] = concerts
        
        return concerts


def get_spotify_artist_uri(concerts:List[str]):
    """
    Takes a list of concert names and matches them to the spotify api using the search service, only exact matches are accepted
    returns the list artists (uri only)
    """
    spotify_artist_uris = []
    for concert in concerts:
        request = spotify.search(concert, type='artist', limit=1)
        if not request['artists']['items']: continue
        [artist] = request['artists']['items']
        if artist['name'] == concert:
            spotify_artist_uris.append(artist['uri'])
            
    return spotify_artist_uris


def get_top_track_from_artists(artists:List[str]):
    """
    Takes a list of artist uris and returns a list that includes each artists top song (uri only)
    """
    tracks = []
    for artist in artists:
        top_track = spotify.artist_top_tracks(artist)['tracks'][0]['uri']
        tracks.append(top_track)
            
    return tracks


def get_authorization_url(redirect_uri:str, scopes:List[str]):
    """
    Creates the authorisation url for the user
    """
    client_id = SpotifyClientCredentials().client_id
    URL_TEMPLATE = Template('https://accounts.spotify.com/authorize?client_id=$client_id&response_type=code&redirect_uri=$redirect_uri&scope=$scopes')
    url = URL_TEMPLATE.substitute(client_id=client_id, redirect_uri=redirect_uri, scopes='%20'.join(scopes))
    return url


def split_list_by_n(array: List, n: int):
    """
    Splits a list into some segments where each segment is n long, and then the last segmet is the remainder
    """
    split = []
    i = 0
    j = n
    while i <= len(array):
        split.append(array[i:min(len(array), j)])
        i += n
        j += n

    return split


def create_playlist(ids: Iterable[str], user: str, year: int, month: int, name: str, description: str):
    """
    creates a playlist using the give metro-area ids for the given user, between the given time frame, with the given name and description
    """

    playlist = spotify.user_playlist_create(user=user, name=name, public=False, description=description)

    capi = clientCAPI()

    concerts = []
    for metro_id in ids:
        concerts += capi.get_metro_area_concerts(metro_id, year, month)

    artists = get_spotify_artist_uri(concerts)
    tracks = get_top_track_from_artists(artists)

    for tracks100 in split_list_by_n(tracks, 100):
        spotify.user_playlist_add_tracks(user=user, playlist_id=playlist['id'], tracks=tracks100)

"""
import logging
import http.client

http.client.HTTPConnection.debuglevel = 1

logging.basicConfig(level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.DEBUG)
logging.getLogger("urllib3").setLevel(logging.DEBUG)
"""

def main(year: str, month: str, *ids: List[str]):
    start_date = date(int(year), int(month), 1)
    end_date = date(int(year), int(month), calendar.monthrange(int(year), int(month))[1])

    auth_url = get_authorization_url('https://open.spotify.com/', ['playlist-modify-private'])

    print()
    print('link:', auth_url)
    print()

    code = input('code: ')

    response = requests.post(
    'https://accounts.spotify.com/api/token', 
    {
        'grant_type':'authorization_code',
        'code':code,
        'redirect_uri':'https://open.spotify.com/',
        'client_id':SpotifyClientCredentials().client_id,
        'client_secret':SpotifyClientCredentials().client_secret,
    
    })

    access_token = response.json()['access_token']
    print(access_token)
    # Singleton
    global spotify 
    spotify = spotipy.Spotify(auth=access_token, client_credentials_manager=SpotifyClientCredentials(), status_forcelist=[], retries=0, status_retries=0)
    
    user_id = spotify.me()['id']

    playlist_name = f'Local Next Month: {calendar.month_name[int(month)]}'
    playlist_description = f'A playlist with tracks from artists playing in the local area in {calendar.month_name[int(month)]} {year}. Created by local-next-month https://github.com/spralja/local-next-month/'

    create_playlist(ids, user_id, int(year), int(month), name=playlist_name, description=playlist_description)

    print('success')


if __name__ == '__main__':
    main(*sys.argv[1:])

