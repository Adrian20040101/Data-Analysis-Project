import pandas as pd
import pickle
from scipy.stats import poisson
from main import dict_tables

groups_table = pickle.load(open('groups.txt', 'rb'))
df_historical_data = pd.read_csv('uefa_euro_historical_data.csv')
df_fixtures = pd.read_csv('uefa_euro_2024_fixtures.csv')

# split all wc matches into separate dataframes by home/away
df_home = df_historical_data[['home', 'homegoals', 'awaygoals']]
df_away = df_historical_data[['away', 'homegoals', 'awaygoals']]

# rename columns in newly created dataframes for clarity
df_home = df_home.rename(columns={'home': 'team', 'homegoals': 'goals_scored', 'awaygoals': 'goals_against'})
df_away = df_away.rename(columns={'away': 'team', 'homegoals': 'goals_against', 'awaygoals': 'goals_scored'})

# concat both newly created dataframes to compute the mean for the goals scored and goals against, setting up the team
# strength
df_team_strength = pd.concat([df_home, df_away], ignore_index=True).groupby('team').mean()

# keep columns for goals scored and goals conceded to the dict_tables
# clean the Germany name so that it doesn't contain the (H)
for group in dict_tables:
    dict_tables[group]['GF'] = 0
    dict_tables[group]['GA'] = 0
    dict_tables[group]['Team'] = dict_tables[group]['Team'].str.replace(r'\s*\(H\)', '', regex=True)


# function that predict the points and goals for each nation based on the goals scored (win/draw/loss)
def predict_points_and_goals(home, away):
    if home in df_team_strength.index and away in df_team_strength.index:
        # compute the lambda for the poisson distribution
        lambda_home = df_team_strength.at[home, 'goals_scored'] * df_team_strength.at[away, 'goals_against']
        lambda_away = df_team_strength.at[away, 'goals_scored'] * df_team_strength.at[home, 'goals_against']
        prob_home, prob_draw, prob_away = 0, 0, 0
        goals_home_total, goals_away_total = 0, 0
        for goals_home in range(0, 11):  # considering teams don't score more than 10 goals in a game
            for goals_away in range(0, 11):
                prob = poisson.pmf(goals_home, lambda_home) * poisson.pmf(goals_away, lambda_away)
                if goals_home == goals_away:
                    prob_draw += prob
                elif goals_home > goals_away:
                    prob_home += prob
                elif goals_away > goals_home:
                    prob_away += prob
                goals_home_total += prob * goals_home
                goals_away_total += prob * goals_away

        points_home = 3 * prob_home + prob_draw
        points_away = 3 * prob_away + prob_draw
        return points_home, points_away, goals_home_total, goals_away_total
    else:
        return 0, 0, 0, 0


# split the fixtures into groups and knockout stages
df_group_stages = df_fixtures[:36].copy()
df_round_of_16 = df_fixtures[36:44].copy()
df_quarter_finals = df_fixtures[44:48].copy()
df_semi_finals = df_fixtures[48:50].copy()
df_final = df_fixtures[50:].copy()

# simulate all games in the group stage and update the group tables
# important mention: Serbia in their current country format (formerly Yugoslavia) and Georgia
# have not participated in Euros before, therefore games played against these teams will result in no points
# added to either side
for group in dict_tables:
    teams_in_group = dict_tables[group]['Team'].values
    df_group_fixtures = df_group_stages[df_group_stages['home'].isin(teams_in_group)]
    for index, row in df_group_fixtures.iterrows():
        home, away = row['home'], row['away']
        points_home, points_away, goals_home, goals_away = predict_points_and_goals(home, away)
        dict_tables[group].loc[dict_tables[group]['Team'] == home, 'Pts'] += int(points_home)
        dict_tables[group].loc[dict_tables[group]['Team'] == away, 'Pts'] += int(points_away)
        dict_tables[group].loc[dict_tables[group]['Team'] == home, 'GF'] += int(goals_home)
        dict_tables[group].loc[dict_tables[group]['Team'] == home, 'GA'] += int(goals_away)
        dict_tables[group].loc[dict_tables[group]['Team'] == away, 'GF'] += int(goals_away)
        dict_tables[group].loc[dict_tables[group]['Team'] == away, 'GA'] += int(goals_home)

    dict_tables[group]['GD'] = dict_tables[group]['GF'] - dict_tables[group]['GA']
    dict_tables[group] = dict_tables[group].sort_values(by=['Pts', 'GD', 'GF'], ascending=False).reset_index(drop=True)
    dict_tables[group] = dict_tables[group][['Team', 'Pts', 'GF', 'GA', 'GD']]
    dict_tables[group] = dict_tables[group].round(0)

# after simulating the group stage games, determine the best third-placed teams
third_place_teams = []

for group in dict_tables:
    third_place_team = dict_tables[group].iloc[2]
    third_place_teams.append(third_place_team)

df_third_place_teams = pd.DataFrame(third_place_teams)
df_third_place_teams = df_third_place_teams.sort_values(by=['Pts', 'GD', 'GF'], ascending=False).reset_index(drop=True)

# the top 4 third-placed teams advance to the knockout stage
top_four_third_place_teams = df_third_place_teams.loc[:3, 'Team'].tolist()

# update the knock-out fixture with 3rd place, runners-up and group winner
for group in dict_tables:
    group_winner = dict_tables[group].loc[0, 'Team']
    runners_up = dict_tables[group].loc[1, 'Team']

    # update the group winners and runners-up
    df_round_of_16.replace({f'Winner {group}': group_winner, f'Runner-up {group}': runners_up}, inplace=True)

    # manually update the best 4 third placed teams
    df_round_of_16.replace({'3rd Group D/E/F': top_four_third_place_teams[0],
                            '3rd Group A/D/E/F': top_four_third_place_teams[1],
                            '3rd Group A/B/C': top_four_third_place_teams[2],
                            '3rd Group A/B/C/D': top_four_third_place_teams[3]}, inplace=True)

    # add a winner column to store the winner of the knockout game in the round of 16, which initially is unknown
    df_round_of_16['winner'] = '?'


# function to determine the winner of the knockout games
def get_winner(df_updated_fixtures):
    for index, row in df_updated_fixtures.iterrows():
        home, away = row['home'], row['away']
        points_home, points_away, goals_home, goals_away = predict_points_and_goals(home, away)
        if points_home > points_away:
            winner = home
        else:
            winner = away
        df_updated_fixtures.loc[index, 'winner'] = winner
    return df_updated_fixtures


# save the current state of the knockout phase (round-of-16)
df_round_of_16 = get_winner(df_round_of_16)
print('======================= ROUND OF 16 =======================\n')
print(df_round_of_16)
print('\n')

# function to update the fixtures table based on knockout phase
def update_table(df_current_fixtures, df_next_fixtures):
    for index, row in df_current_fixtures.iterrows():
        winner = df_current_fixtures.loc[index, 'winner']
        match = df_current_fixtures.loc[index, 'score']
        df_next_fixtures.replace({f'Winner {match}': winner}, inplace=True)
    df_next_fixtures['winner'] = '?'
    return df_next_fixtures


# update the table and save the current state of the knockout phase (quarter-finals)
df_quarter_finals = update_table(df_round_of_16, df_quarter_finals)
df_quarter_finals = get_winner(df_quarter_finals)
print('\n======================= QUARTER FINALS =======================\n')
print(df_quarter_finals)
print('\n')

# update the table and save the current state of the knockout phase (semi-finals)
df_semi_finals = update_table(df_quarter_finals, df_semi_finals)
df_semi_finals = get_winner(df_semi_finals)
print('\n======================= SEMI FINALS =======================\n')
print(df_semi_finals)
print('\n')

# update the table and save the current state of the knockout phase (final)
df_final = update_table(df_semi_finals, df_final)
df_final = get_winner(df_final)
print('\n======================= FINAL =======================\n')
print(df_final)
print('\n')

print(str(df_final['winner'].iloc[0]), 'are Euro 2024 Champions. Congratulations!')
