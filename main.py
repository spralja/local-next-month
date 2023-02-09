from string import Template
from datetime import date
from typing import List
import sys

from bs4 import BeautifulSoup
import requests
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

spotify = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials())

def create_url(id:int, start_date:date, end_date:date, page:int):
    """
    This function createas a 'songkick' url for scraping artists in a certian time frame in a certain area
    """
    URL_TEMPLATE = Template('https://www.songkick.com/metro-areas/$id?utf8=%E2%9C%93&filters%5BminDate%5D=$start_month%2F$start_day%2F$start_year&filters%5BmaxDate%5D=$end_month%2F$end_day%2F$end_year&page=$page#metro-area-calendar')
    return URL_TEMPLATE.substitute(
        id=str(id),
        start_day=start_date.day,
        start_month=start_date.month,
        start_year=start_date.year,
        end_day=end_date.day,
        end_month=end_date.month,
        end_year=end_date.year,
        page=str(page),
    )



def is_last_page(response:requests.models.Response):
    """
    This function checks whether the page is out of bounds
    """
    for tag in BeautifulSoup(response.text).find_all('p'):
        if tag.getText().find('Your search returned no results') != -1:
            return True


def get_metro_area_pages(id:int, start_date:date, end_date:date):
    """
    Get all pages available for the time frame and city, max of 30
    """
    pages = []
    for i in range(1, 31):
        response = requests.get(create_url(id=id, start_date=start_date, end_date=end_date, page=i))
        if is_last_page(response): break
            
        pages.append(response.text)
        
    return pages

def get_metro_area_concerts(id:int, start_date:date, end_date:date):
    """
    Get an list of concert names from songkick for the given time frame and given area
    """
    pages = get_metro_area_pages(id=id, start_date=start_date, end_date=end_date)
    concerts = []
    for page in pages:
        strongs = BeautifulSoup(page).find_all('strong')
        for strong in strongs:
            concerts.append(strong.string)
            
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
    client_id=SpotifyClientCredentials().client_id
    URL_TEMPLATE = Template('https://accounts.spotify.com/authorize?client_id=$client_id&response_type=code&redirect_uri=$redirect_uri&scope=$scopes')
    url = URL_TEMPLATE.substitute(client_id=client_id, redirect_uri=redirect_uri, scopes='%20'.join(scopes))
    return url


def main(id:str, start_year:str, start_month:str, start_day:str, end_year:str, end_month:str, end_day:str):
    concerts = get_metro_area_concerts(
        id=int(id), 
        start_date=date(int(start_year), int(start_month), int(start_day)),
        end_date=date(int(end_year), int(end_month), int(end_day)),
    )

    artists = get_spotify_artist_uri(concerts)
    tracks = get_top_track_from_artists(artists)
    auth_url = get_authorization_url('https://open.spotify.com/', ['playlist-modify-private'])
    print(auth_url)
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
    spotify = spotipy.Spotify(auth=access_token, client_credentials_manager=SpotifyClientCredentials())
    user = input('user: ')
    playlist = spotify.user_playlist_create(user=user, name='Local Next Month: March', public=False, description='Tracks from artists playing in your area in March')

    spotify.user_playlist_add_tracks(user=user, playlist_id=playlist['id'], tracks=tracks[:100])
    spotify.user_playlist_add_tracks(user=user, playlist_id=playlist['id'], tracks=tracks[100:])

if __name__ == '__main__':
    main(*sys.argv[1:])

