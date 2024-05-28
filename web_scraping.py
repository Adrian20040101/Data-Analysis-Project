import requests
from bs4 import BeautifulSoup
import pandas as pd

years = [1968, 1972, 1976, 1980, 1984, 1988, 1992, 1996, 2000, 2004, 2008, 2012, 2016, 2020]


def get_matches(year):
    web_link = f'https://en.wikipedia.org/wiki/UEFA_Euro_{year}'
    response = requests.get(web_link)
    content = response.text
    soup = BeautifulSoup(content, 'lxml')

    # grab rows containing match information including home team, score and away team
    matches = soup.find_all('div', class_='footballbox')

    home_teams = []
    scores = []
    away_teams = []

    # split the retrieved data
    for match in matches:
        home_teams.append(match.find('th', class_='fhome').get_text())
        scores.append(match.find('th', class_='fscore').get_text())
        away_teams.append(match.find('th', class_='faway').get_text())

    # create a dictionary containing the scrpaed data
    dict_matches = {'home': home_teams, 'score': scores, 'away': away_teams}

    # build a dataframe using the dict
    df_matches = pd.DataFrame(dict_matches)

    # add the year in which the game has been played for clarity
    df_matches['year'] = year

    return df_matches


historical_data = []
[historical_data.append(get_matches(year)) for year in years]

# create a dataframe containing the information about all games played at past Euros
df_historical_data = pd.concat(historical_data, ignore_index=True)
df_historical_data.to_csv('uefa_euro_historical_data.csv', index=False)

# create a dataframe containing Euro 2024 fixtures
fixtures = [get_matches(2024)]
df_fixtures = pd.concat(fixtures, ignore_index=True)
df_fixtures.to_csv('uefa_euro_2024_fixtures.csv', index=False)

# clean the historical data and the fixtures
df_historical_data['home'] = df_historical_data['home'].str.strip()
df_historical_data['away'] = df_historical_data['away'].str.strip()
df_fixtures['home'] = df_fixtures['home'].str.strip()
df_fixtures['away'] = df_fixtures['away'].str.strip()

# remove the after extra time (a.e.t.) notation from games that went to extra time
df_historical_data['score'] = df_historical_data['score'].str.replace(r'\s*\(a\.e\.t\.[^\)]*\)[^\.,]*', '', regex=True)

# split score column into home team goals and away team goals to get rid of the hyphen and work only with numeric data
df_historical_data[['homegoals', 'awaygoals']] = df_historical_data['score'].str.split('–', expand=True)

# drop the score column now (specify axis to delete an entire column)
df_historical_data.drop('score', axis=1, inplace=True)

# change the data type of the newly created columns from string to int
df_historical_data = df_historical_data.astype({'homegoals': int, 'awaygoals': int, 'year': int})

# add a new column called totalgoals
df_historical_data['totalgoals'] = df_historical_data['homegoals'] + df_historical_data['awaygoals']

# save the cleanup changes
df_historical_data.to_csv('uefa_euro_historical_data.csv', index=False)
df_fixtures.to_csv('uefa_euro_2024_fixtures.csv', index=False)
