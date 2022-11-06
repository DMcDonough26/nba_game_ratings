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
from bokeh.models.widgets import DataTable, TableColumn, Panel, Tabs, Div, Button
from bokeh.io import output_file, show
from bokeh.layouts import column, Spacer, layout
from bokeh.plotting import curdoc

# 2. compile standings data for model

# pull standings from basketball reference
def call_bball_ref():
    url = "https://www.basketball-reference.com/leagues/NBA_2023_standings.html"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    # specify total games this season so that I can calculate games remaining per team
    totalgames = 82

    table_ids = {'east':'confs_standings_E','west':'confs_standings_W'}

    return soup, totalgames, table_ids

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
