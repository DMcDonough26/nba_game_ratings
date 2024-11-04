# load packages
import requests
from bs4 import BeautifulSoup

from scipy.stats import binom
from scipy.stats import norm
import statsmodels.api as sm

import pandas as pd
import numpy as np

import time
import datetime

from bokeh.models import ColumnDataSource, Button
# from bokeh.models.widgets import DataTable, TableColumn, Panel, Tabs, Div, Button
from bokeh.models.widgets import DataTable, TableColumn, Div, Button
from bokeh.models.layouts import TabPanel, Tabs

from bokeh.io import output_file, show
from bokeh.layouts import column, Spacer, layout
from bokeh.plotting import curdoc

# 3. scrape the scoreboard
def pull_scoreboard():
    url = "https://www.cbssports.com/nba/scoreboard/"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    games = soup.find_all(attrs={"class": "live-update"})
    return games

# establish time remaining
def parse_current_time(game):
    # returns number of minutes remaining in the game

    current_time = str(game.find_all(attrs={"class": "game-status emphasis"})).split('>')[1].split('<')[0]

    if current_time == 'Halftime':
        final_minutes = 24
    elif current_time.split(' ')[0] == 'End':
        quarter = int(current_time.split(' ')[1][0])
        final_minutes = (4-quarter)*12
    else:
        quarter = int(current_time.split(' ')[0][0])
        time_list = current_time.split(' ')[1].split(':')
        if len(time_list)==1:
            minutes = 0
            seconds = int(time_list[0].split('.')[0])
        else:
            minutes = int(time_list[0])
            seconds = int(time_list[1])

        final_minutes = (4-quarter)*12 + minutes + round((seconds/60))
    return final_minutes

# establish score
def parse_score(game):
    # returns team scores and size of lead

    away_score = int(game.findAll(attrs={'class':'in-progress-table'})[0].findAll('td')[5].string)
    home_score = int(game.findAll(attrs={'class':'in-progress-table'})[0].findAll('td')[11].string)
    lead = abs(away_score - home_score)
    return away_score, home_score, lead

# establish channel
def parse_channel(game):
    # returns channel for national broadcasts or 'league pass"
    channel = str(game.find_all(attrs={"class": "broadcaster"})[0]).split('>')[1].split('<')[0]
    if len(channel) > 0:
        if channel == 'NBAt':
            return "NBA TV"
        else:
            return channel
    else:
        return "League Pass"

# create score dataframe
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

                if len(pre_time) > 0:
                    tipoffs.append(str('NA')) # come back to this later
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
            try:
                channels.append(parse_channel(game))
            except:
                channels.append('NA')

    game_df = pd.DataFrame({'Status':status,'Minutes':score_minutes,'Lead':score_leads,'Away Team':away_teams,'Home Team':home_teams,\
                            'Away Prob':away_probs,'Home Prob':home_probs,'Away Score':away_scores,'Home Score':home_scores,\
                           'Channel':channels,'Tipoff':tipoffs})

    return game_df

# apply matchups
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
