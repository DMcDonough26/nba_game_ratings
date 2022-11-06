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

# 1. train a model

def simulate_df():

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

    # sample ratings
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

def train_model(sim_df, sim_df_x):
    lm = sm.OLS(sim_df['Rating'],sm.add_constant(sim_df_x)).fit()

    # Calculating min/max of predicted train values so I can later normalize predictions to a ten-point scale
    maxval = lm.predict().max()
    minval = lm.predict().min()

    return lm, maxval, minval
