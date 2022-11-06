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

from train_model import model_prep
from scrape_scoreboard import matchup


# 4. rate games
def score_games(game_df, sim_df, lm):
    # rate games

    game_df['Matchup'] = game_df.apply(matchup, axis=1)

    score_df = model_prep(game_df, sim_df)
    game_df['Rating'] = lm.predict(sm.add_constant(score_df, has_constant='add'))
    return game_df

# normalize ratings
def adjust_rating(x, minval, maxval):
    # normalize ratings to ten-point scale

    return round((x-minval)/(maxval-minval)*10,1)

# adjust game dataframe
def display_frame(game_df):
    game_df.sort_values(by='Rating', ascending=False, inplace=True)
    return_df = game_df[['Matchup','Minutes','Away Team','Home Team','Away Score',\
                                                  'Home Score','Channel','Rating']]
    return_df.columns = ['Matchup','Min Left','Away Team','Home Team','Away Score','Home Score','Channel','Rating']
    return return_df

# separated based on game status
def final_scoreboard(game_df, sim_df, combined_frame, lm,minval,maxval):
    # current games
    current_df = game_df[game_df['Status']=='Current'].copy()
    if len(current_df) > 0:
        current_df = score_games(current_df, sim_df, lm)
        current_df['Rating'] = current_df['Rating'].apply(adjust_rating,args=(minval,maxval))
        current_df = display_frame(current_df)

    # pre games
    pre_df = game_df[game_df['Status']=='Pre'].copy()
    if len(pre_df) > 0:
        pre_df['Matchup'] = pre_df.apply(matchup, axis=1)
        pre_df = score_games(pre_df, sim_df, lm)
        pre_df['Rating'] = pre_df['Rating'].apply(adjust_rating,args=(minval,maxval))
        pre_df = display_frame(pre_df)

    # post games
    post_df = game_df[game_df['Status']=='Post'].copy()
    if len(post_df) > 0:
        post_df = score_games(post_df, sim_df, lm)
        post_df['Rating'] = post_df['Rating'].apply(adjust_rating,args=(minval,maxval))
        post_df = display_frame(post_df)

    return current_df, pre_df, post_df
