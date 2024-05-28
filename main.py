import pandas as pd
from string import ascii_uppercase as alphabet
import pickle

tables = pd.read_html('https://en.wikipedia.org/wiki/UEFA_Euro_2024')

dict_tables = {}
for letter, i in zip(alphabet, range(18, 60, 7)):
    df = tables[i]
    df.rename(columns={'Teamvte': 'Team'}, inplace=True)
    df.pop('Qualification')
    dict_tables[f'Group {letter}'] = df

# save the extracted groups in a file using pickle
with open('groups.txt', 'wb') as file:
    pickle.dump(dict_tables, file)
