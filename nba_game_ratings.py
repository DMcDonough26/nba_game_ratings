import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
import random
from scipy.stats import binom
from scipy.stats import norm
import statsmodels.api as sm
import warnings
warnings.filterwarnings("ignore")
import time
from IPython.display import clear_output
import datetime


def create_model_data():
    np.random.seed(0)
    minutes = np.random.randint(0,48,100)

    # I used the mean and standard deviation of historical point spread data to simulate lead
    np.random.seed(0)
    lead = abs(np.random.normal(3.09,6.43,100).round())

    # I wanted to express matchup as an ordinal scale rather than an interval scale so I made this a categorical variable
    np.random.seed(0)
    matchup_dict = {1:'A',2:'B',3:'C',4:'D',5:'E'}
    matchups = pd.Series(np.random.randint(1,6,100)).apply(lambda x: matchup_dict[x])

    sim_df = pd.DataFrame({'Matchup':matchups,'Minutes':minutes,'Lead':lead})

    ratings = pd.Series([
    1,3,3,1,1,3,3,4,2,4,
    4,2,4,4,5,5,2,3,4,1,
    1,4,1,4,1,3,5,4,1,1,
    3,3,5,3,3,4,2,1,2,2,
    3,1,3,2,4,1,5,1,3,2,
    4,3,5,5,3,5,3,3,2,2,
    5,1,3,1,5,5,3,1,1,1,
    3,1,1,1,5,2,4,3,1,4,
    5,4,5,5,1,1,4,3,1,3,
    4,1,3,3,4,4,4,2,3,2])

    sim_df = pd.concat([sim_df,ratings],axis=1)
    sim_df.columns = ['Matchup','Minutes','Lead','Rating']

    return sim_df

def model_prep(model_df, train_df=None):
    # add an interaction term between minutes and lead
    model_df['Min_Lead'] = model_df['Minutes'] * model_df['Lead']

    # dummy matchups and normalize numeric variables
    if train_df is None:
        model_df = pd.concat([pd.get_dummies(model_df['Matchup']),model_df[['Minutes','Lead','Min_Lead']]],axis=1)
        for column in ['Minutes','Lead','Min_Lead']:
            model_df[column] = (model_df[column] - model_df[column].mean())/model_df[column].std()

    else:
        # need alternate way to dummy matchups
        dummy_df = pd.get_dummies(model_df['Matchup'])
        for letter in ['A','B','C','D','E']:
            if letter in dummy_df.columns:
                pass
            else:
                dummy_df[letter] = 0


        model_df = pd.concat([dummy_df,model_df[['Minutes','Lead','Min_Lead']]],axis=1)
        for column in ['Minutes','Lead','Min_Lead']:
            model_df[column] = (model_df[column] - train_df[column].mean())/train_df[column].std()

    return model_df

def standings_frame(soup, totalgames, idval):
    table = soup.findAll(id=idval)[0]
    teams = table.findAll('a')
    teamlist = []
    for i in range(len(teams)):
        teamlist.append(str(teams[i]).split(">")[1].split("<")[0])

    data = table.findAll('td')
    winlist = []
    losslist = []
    winpctlist = []
    [winlist.append(int(str(data[x*7]).split(">")[1].split("<")[0])) for x in range(15)]
    [losslist.append(int(str(data[1+x*7]).split(">")[1].split("<")[0])) for x in range(15)]
    [winpctlist.append(float(str(data[2+x*7]).split(">")[1].split("<")[0])) for x in range(15)]

    conf_frame = pd.DataFrame({'team':teamlist,'win':winlist,'loss':losslist,'win_pct':winpctlist})
    conf_frame['team_short'] = conf_frame['team'].apply(lambda x: x.split(' ')[-1])

    # adjust for two-word name for portland
    conf_frame['team_short'] = conf_frame['team_short'].apply(lambda x: 'Trail Blazers' if x == 'Blazers' else x)
    conf_frame['remaining'] = totalgames - (conf_frame['win'] + conf_frame['loss'])

    return conf_frame

def calculate_probabilities(conf_frame, totalgames, direction):
    # the purpose of this function is to solve for the number of games need to make the playoffs

    # initialize variables
    if direction == 'up':
        wins_needed = 0
    else:
        wins_needed = int(totalgames)

    current_gap = 0
    while (True):
        # calculate required number of wins to make the playoffs
        conf_frame['required'] = wins_needed-conf_frame['win']

        # floor at zero for teams that have already made it
        conf_frame['required'].apply(lambda x: max(x,0))

        # set probabilities to zero for each iteration
        conf_frame['prob'] = 0

        # calculate probabilities at current iteration
        for i in range(len(conf_frame)):
            conf_frame.iloc[i,7] = (1-binom.cdf(conf_frame.iloc[i]['required']-1,\
                                                conf_frame.iloc[i]['remaining'],conf_frame.iloc[i]['win_pct'])).round(2)

        # calculate how far off the sum of probabilities is from the target of 800%
        prior_gap = int(current_gap)
        current_gap = 8 - conf_frame['prob'].sum()

        # increment games needed until you reach a stopping point
        if direction == 'up':
            if current_gap < 0:
                wins_needed += 1
            else:
                break

        else:
            if current_gap > 0:
                wins_needed -= 1
            else:
                break


    return current_gap, conf_frame

def setup_prob(conf_frame, totalgames):
    # calculate incrementing both upwards and downwards and choose the better solution

    current_gap_up, frame_up = calculate_probabilities(conf_frame, totalgames, 'up')
    current_gap_down, frame_down = calculate_probabilities(conf_frame, totalgames, 'down')

    if current_gap_up <= current_gap_down:
        return frame_up
    else:
        return frame_down

def pull_scoreboard():
    url = "https://www.cbssports.com/nba/scoreboard/"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    games = soup.find_all(attrs={"class": "live-update"})
    return games

def parse_current_time(game):
    # returns number of minutes remaining in the game

    current_time = game.find_all(attrs={"class": "game-status emphasis"})

    if str(current_time[0]).split('<span>')[0].split('\n')[1].strip() == 'Halftime':
        final_minutes = 24
    elif str(current_time[0]).split('<span>')[0].split('\n')[1].strip().split(' ')[0] == 'End':
        quarter = int(str(current_time[0]).split('<span>')[0].split('\n')[1].strip().split(' ')[1])
        final_minutes = (4-quarter )*12
    else:
        span_split = str(current_time[0]).split('<span>')
        quarter = int(span_split[0][-1])
        span_split2 = str(current_time[0]).split('/span> ')
        time_split = span_split2[1].split(':')
        if len(time_split)==1:
            minutes = 0
            seconds = int(span_split2[1].split('.')[0])
        else:
            minutes = int(time_split[0])
            seconds = int(time_split[1].split('\n')[0])

        final_minutes = (4-quarter)*12 + minutes + round((seconds/60))
    return final_minutes

def parse_score(game):
    # returns team scores and size of lead

    away_score = int(game.findAll(attrs={'class':'in-progress-table'})[0].findAll('td')[5].string)
    home_score = int(game.findAll(attrs={'class':'in-progress-table'})[0].findAll('td')[11].string)
    lead = abs(away_score - home_score)
    return away_score, home_score, lead

def parse_channel(game):
    # returns channel for national broadcasts or 'league pass"

    channel = game.find_all(attrs={"class": "broadcaster"})[0].string.split('\n')[1].strip()
    if len(channel) > 0:
        if channel == 'NBAt':
            return "NBA TV"
        else:
            return channel
    else:
        return "League Pass"

def create_score_frame(games, combined_frame):
    # parse html into dataframe

    score_minutes = []
    away_scores = []
    home_scores = []
    score_leads = []
    away_teams = []
    home_teams = []
    away_probs = []
    home_probs = []
    status = []
    channels = []
    tipoffs = []

    for game in games:
            current_time = game.find_all(attrs={"class": "game-status emphasis"})
            if len(current_time) > 0:
                score_minutes.append(parse_current_time(game))
                away_score, home_score, lead = parse_score(game)
                away_scores.append(away_score)
                home_scores.append(home_score)
                score_leads.append(lead)
                status.append('Current')
                tipoffs.append('NA')

            else:
                pre_time = game.find_all(attrs={"class": "game-status pregame-date"})

                if len(pre_time):
                    tipoffs.append(str(pre_time[0].string).split('\n')[1].strip())
                    score_minutes.append(48)
                    away_scores.append(0)
                    home_scores.append(0)
                    score_leads.append(0)
                    status.append('Pre')
                else:
                    score_minutes.append(0)
                    away_score, home_score, lead = parse_score(game)
                    away_scores.append(away_score)
                    home_scores.append(home_score)
                    score_leads.append(lead)
                    status.append('Post')
                    tipoffs.append('NA')
            away_team = game.find_all(attrs={"class": "in-progress-table"})[0].find_all("a")[1].string
            away_teams.append(away_team)
            home_team = game.find_all(attrs={"class": "in-progress-table"})[0].find_all("a")[3].string
            home_teams.append(home_team)

            away_probs.append(combined_frame[combined_frame['team_short']==away_team]['prob'].values[0])
            home_probs.append(combined_frame[combined_frame['team_short']==home_team]['prob'].values[0])
            channels.append(parse_channel(game))

    game_df = pd.DataFrame({'Status':status,'Minutes':score_minutes,'Lead':score_leads,'Away Team':away_teams,'Home Team':home_teams,\
                            'Away Prob':away_probs,'Home Prob':home_probs,'Away Score':away_scores,'Home Score':home_scores,\
                           'Channel':channels,'Tipoff':tipoffs})

    return game_df

def matchup(x):
    away_prob = x['Away Prob']
    home_prob = x['Home Prob']
    if min(away_prob,home_prob) >= 0.9:
        return 'A'
    elif ((max(away_prob,home_prob) >= 0.9) & (min(away_prob,home_prob) < 0.9) & (min(away_prob,home_prob) >= .05)):
        return 'B'
    elif ((max(away_prob,home_prob) < .9) & (min(away_prob,home_prob) >= .05)):
        return 'C'
    elif ((max(away_prob,home_prob) >= .05) & (min(away_prob,home_prob) < .05)):
        return 'D'
    elif (max(away_prob,home_prob) < .05):
        return 'E'

def score_games(game_df, sim_df, lm):
    # rate games

    game_df['Matchup'] = game_df.apply(matchup, axis=1)

    score_df = model_prep(game_df, sim_df)
    game_df['Rating'] = lm.predict(sm.add_constant(score_df, has_constant='add'))
    return game_df

def adjust_rating(x, minval, maxval):
    # normalize ratings to ten-point scale

    return round((x-minval)/(maxval-minval)*10,1)

def display_frame(game_df, pre=False):
    # create output dataframe format

    if pre==False:
        game_df.sort_values(by='Rating', ascending=False, inplace=True)
        return_df = game_df[['Matchup','Minutes','Away Team','Home Team','Away Score',\
                                                      'Home Score','Channel','Rating']]
        return_df.columns = ['Matchup','Min Left','Away Team','Home Team','Away Score','Home Score','Channel','Rating']
        return return_df
    else:
        return_df = game_df[['Matchup','Tipoff','Away Team','Home Team','Channel','Rating']]
        return return_df

def final_scoreboard(sim_df, combined_frame, lm, minval, maxval):

    games = pull_scoreboard()
    game_df = create_score_frame(games, combined_frame)


    # post games
    current_df = game_df[game_df['Status']=='Current'].copy()
    if len(current_df) > 0:
        current_df = score_games(current_df, sim_df, lm)
        current_df['Rating'] = current_df['Rating'].apply(adjust_rating, args=(minval,maxval))
        current_df = display_frame(current_df)

    # pre games
    pre_df = game_df[game_df['Status']=='Pre'].copy()
    if len(pre_df) > 0:
        pre_df['Matchup'] = pre_df.apply(matchup, axis=1)
        pre_df = score_games(pre_df, sim_df, lm)
        pre_df['Rating'] = pre_df['Rating'].apply(adjust_rating, args=(minval,maxval))
        pre_df = display_frame(pre_df, True)

    # post games
    post_df = game_df[game_df['Status']=='Post'].copy()
    if len(post_df) > 0:
        post_df = score_games(post_df, sim_df, lm)
        post_df['Rating'] = post_df['Rating'].apply(adjust_rating, args=(minval,maxval))
        post_df = display_frame(post_df)

    now = datetime.datetime.now()
    print("\nLast Updated At: ",now.strftime('%I:%M'),'\n')

    if len(current_df) > 0:
        print('Current Games:')
        print(current_df)

    if len(pre_df) > 0:
        print('\nUpcoming Games:')
        print(pre_df)

    if len(post_df) > 0:
        print('\nFinished Games:')
        print(post_df)

def run_scoreboard(sim_df, combined_frame, lm, minval, maxval):
    i = 0
    while (True):
        i += 1
        if i <= 1:
            refresh_rate = int(input("Home often (in minutes) do you want to refresh?\n"))
        if i > 1:
            time.sleep(refresh_rate*60)
        clear_output()
        final_scoreboard(sim_df, combined_frame, lm, minval, maxval)

def main():
    sim_df = create_model_data()
    sim_df_x = model_prep(sim_df)
    lm = sm.OLS(sim_df['Rating'],sm.add_constant(sim_df_x)).fit()

    # Calculating min/max of predicted train values so I can later normalize predictions to a ten-point scale
    maxval = lm.predict().max()
    minval = lm.predict().min()

    # pull standings from basketball reference
    url = "https://www.basketball-reference.com/leagues/NBA_2021_standings.html"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    # specify total games this season so that I can calculate games remaining per team
    totalgames = 72

    table_ids = {'east':'confs_standings_E','west':'confs_standings_W'}

    east_frame = standings_frame(soup, totalgames, idval=table_ids['east'])
    west_frame = standings_frame(soup, totalgames, idval=table_ids['west'])

    combined_frame = pd.concat([setup_prob(east_frame, totalgames),setup_prob(west_frame, totalgames)],axis=0)

    run_scoreboard(sim_df, combined_frame, lm, minval, maxval)

main()
