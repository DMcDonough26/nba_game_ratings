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
from bokeh.models.widgets import DataTable, TableColumn, Panel, Tabs, Div, Button
from bokeh.io import output_file, show
from bokeh.layouts import column, Spacer, layout
from bokeh.plotting import curdoc

from scrape_scoreboard import pull_scoreboard, parse_current_time, parse_score, parse_channel, create_score_frame, matchup
from rate_games import score_games, adjust_rating, display_frame, final_scoreboard


# bokeh/run scoreboard
def launch_bokeh(current_df, pre_df, post_df, sim_df, combined_frame, lm, minval, maxval):
    # timestamp
    div0 = Div(text = "Last Updated At: "+datetime.datetime.now().strftime('%I:%M'),
    width=900,height=30)

    # current games
    div1 = Div(
        text="""
            <p>Current Games:</p>
            """,
    width=900,
    height=30,
    )

    c1 = [TableColumn(field=Ci, title=Ci) for Ci in current_df.columns] # bokeh columns
    d1 = DataTable(columns=c1, source=ColumnDataSource(current_df),width=800,height=(current_df.shape[0]+1)*30) # bokeh table

    # upcoming games
    div2 = Div(
        text="""
            <p>Upcoming Games:</p>
            """,
    width=900,
    height=30,
    )
    c2 = [TableColumn(field=Ci, title=Ci) for Ci in pre_df.columns] # bokeh columns
    d2 = DataTable(columns=c2, source=ColumnDataSource(pre_df),width=800,height=(pre_df.shape[0]+1)*30) # bokeh table

    # finished games
    div3 = Div(
        text="""
            <p>Finished Games:</p>
            """,
    width=900,
    height=30,
    )
    c3 = [TableColumn(field=Ci, title=Ci) for Ci in post_df.columns] # bokeh columns
    d3 = DataTable(columns=c3, source=ColumnDataSource(post_df),width=800,height=(post_df.shape[0]+1)*30) # bokeh table

    # update function
    def update_func(sim_df, combined_frame, lm, minval, maxval):
        # pull Scoreboard
        new_games = pull_scoreboard()
        new_game_df = create_score_frame(new_games, combined_frame)
        # step 4: rate games
        new_current_df, new_pre_df, new_post_df = final_scoreboard(new_game_df, sim_df, combined_frame, lm, minval, maxval)

        # update timestamp
        div0.text = "Last Updated At: "+datetime.datetime.now().strftime('%I:%M')

        # update current games
        new_c1 = [TableColumn(field=Ci, title=Ci) for Ci in new_current_df.columns]
        d1.columns=new_c1
        d1.source.data = dict(new_current_df)
        d1.height=(new_current_df.shape[0]+1)*30

        # update pre games
        new_c2 = [TableColumn(field=Ci, title=Ci) for Ci in new_pre_df.columns]
        d2.columns=new_c2
        d2.source.data = dict(new_pre_df)
        d2.height=(new_pre_df.shape[0]+1)*30

        # update post games
        new_c3 = [TableColumn(field=Ci, title=Ci) for Ci in new_post_df.columns]
        d3.columns=new_c3
        d3.source.data = dict(new_post_df)
        d3.height=(new_post_df.shape[0]+1)*30

    button = Button(label="Refresh", width=800)
    button.on_click(partial(update_func,sim_df=sim_df, combined_frame=combined_frame, lm=lm, minval=minval, maxval=maxval))

    curdoc().add_root(Tabs(tabs=[Panel(child=layout([column(button,div0,div1,d1,Spacer(width=0, height=10),div2,d2,Spacer(width=0, height=10), div3,d3)], sizing_mode='fixed'),title="NBA Scoreboard")],sizing_mode='scale_height'))
