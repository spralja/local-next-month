# local-next-month
Service for generating a playlist with the most popular song of the artists playing next month in an area

scrape songkick -> get list of concerts
get list of concerts -> using spotify search api for exact matches -> get list of spotify artist uris
-> get most popular song using spotify api -> list with tracks for the playlist

authorize user using spotify api oatuh... -> create playlist -> add tracks to playlist

Example script for area around Roskilde, Denmark:
`py main.py 2023 3 28617 53750 105376 36187 176770 98656`
