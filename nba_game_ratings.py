# load packages
import requests
from bs4 import BeautifulSoup

from scipy.stats import binom
from scipy.stats import norm
import statsmodels.api as sm

import pandas as pd
import numpy as np
from functools import partial

import time
import datetime

from bokeh.models import ColumnDataSource, Button
# from bokeh.models.widgets import DataTable, TableColumn, Panel, Tabs, Div, Button
from bokeh.models.widgets import DataTable, TableColumn, Div, Button
from bokeh.models.layouts import TabPanel, Tabs

from bokeh.io import output_file, show
from bokeh.layouts import column, Spacer, layout
from bokeh.plotting import curdoc

from train_model import simulate_df, model_prep, train_model
from standings_data import call_bball_ref, standings_frame, calculate_probabilities, setup_prob
from scrape_scoreboard import pull_scoreboard, parse_current_time, parse_score, parse_channel, create_score_frame, matchup
from rate_games import score_games, adjust_rating, display_frame, final_scoreboard
from bokeh_script import launch_bokeh

# run everything
def main():
    # step 1: train model
    sim_df = simulate_df()
    sim_df_x = model_prep(sim_df)
    lm, maxval, minval = train_model(sim_df, sim_df_x)
    # step 2: standings data
    soup, totalgames, table_ids = call_bball_ref()
    east_frame = standings_frame(soup, totalgames, idval=table_ids['east'])
    west_frame = standings_frame(soup, totalgames, idval=table_ids['west'])
    combined_frame = pd.concat([setup_prob(east_frame, totalgames),setup_prob(west_frame, totalgames)],axis=0)
    # step 3: scrape scoreboard
    games = pull_scoreboard()
    game_df = create_score_frame(games, combined_frame)
    # step 4: rate games
    current_df, pre_df, post_df = final_scoreboard(game_df, sim_df, combined_frame, lm, minval, maxval)
    # step 5: bokeh script
    launch_bokeh(current_df, pre_df, post_df, sim_df, combined_frame, lm, minval, maxval)

main()
