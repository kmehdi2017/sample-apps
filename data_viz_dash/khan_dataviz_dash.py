# -*- coding: utf-8 -*-
"""
Data 608, Fall 2018
author: Mehdi Khan
"""
import dash
import dash_core_components as dcc
import dash_html_components as htm
import pandas as pd
import numpy as np
#import matplotlib.pyplot as plt 
#import seaborn as sns
#import plotly
#import plotly.offline as py
#import plotly.tools as tls
import plotly.graph_objs as go
import dash.dependencies
from sodapy import Socrata

#import cufflinks as cf
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
server = app.server

intro = '''**This project uses a Dash application to visualize data from the New York City tree census to help  
arborist studying the health of various tree species. The tabs below contain graphs to answer two questions:**   
    *  What proportion of trees are in good, fair, or poor health in various borough? and  
    *  Are stewards having an impact on the health of trees?  
    **Please click on the appropriate tab to see the visualization for each question**'''
pd.set_option('display.max_columns',None)
pd.set_option('display.max_rows',None)

client = Socrata("data.cityofnewyork.us", None)
results = client.get("5rq2-4hqu", limit=5000)
results_df = pd.DataFrame.from_records(results)
#results_df.columns
data = results_df #pd.read_json('https://data.cityofnewyork.us/resource/nwxe-4ae8.json')



app.layout = htm.Div([
        htm.H4(children='Data visualization with Dash', style={'textAlign': 'center','color': 'darkgreen' }),
        htm.H6(children='|| Mehdi Khan ||', style={'textAlign': 'center','color': 'darkblue' }),
        htm.Div(style={'textAlign': 'center'},children=[
               dcc.Markdown(intro)
                ]),
        htm.Div(id='tavdiv',style={'width': '80%',                                   
                                   'margin': 'auto',
                                   'textAlign': 'center'
                                   },children=[
        dcc.Tabs(id='tabs', children=[
            dcc.Tab(label='Question 1', children=[htm.Div(style={'textAlign': 'center'},children=[
                    htm.Div(style={'textAlign': 'center','width': '60%', 
                                   'color':'darkblue','font-size': '14px', 'margin': 'auto'},children=[
                            htm.Br(),
                            htm.P('By default the graph below shows the health status of all trees and their proportion in different borough, for specific trees please select a species from the dropdown below:')
                    ]),
                    dcc.Dropdown(id='drpdwn1',style={'width':'60%','margin': 'auto'}, options=[ {'label': i,'value': i} for i in data.spc_common.unique()],value='All',multi=False,placeholder="Select a tree species..")
                    ]), 
                    dcc.Graph(id="figure1",config={'displayModeBar': 'true',
                                                   'modeBarButtonsToRemove': ['pan2d', 'lasso2d','toImage','sendDataToCloud'],
                                                   'displaylogo': 'false',
                                                    })
                    ]),
            dcc.Tab(label='Question 2', children=[htm.Div(style={'textAlign': 'center'},children=[
                    htm.Div(style={'textAlign': 'center','width': '70%', 
                                   'color':'darkblue','font-size': '14px', 'margin': 'auto'},children=[
                            htm.Br(),
                            htm.P('The graph below shows the proportion of trees in a particular health status for a steward category (number of stewards). The default view present health status vs stewards for all trees. For specific trees please select a species from the dropdown below:')
                    ]),
                    dcc.Dropdown(id='drpdwn2',style={'width':'60%','margin': 'auto' },options=[ {'label': i,'value': i} for i in data.spc_common.unique()],value='All',multi=False,placeholder="Select a tree species..")
                    ]),
                      dcc.Graph(id="figure2",config={'displayModeBar': 'true',
                                                   'modeBarButtonsToRemove': ['pan2d', 'lasso2d','toImage','sendDataToCloud'],
                                                   'displaylogo': 'false',
                                                    })
                    
                    ])  
                
                ])
            ])
        ])
#datasubset = data[['boroname','spc_common','health','steward']]    
#df1= datasubset.groupby(['health','steward']).size().groupby(level=0).apply(lambda x:100 *x/x.sum()).unstack()
#df1 = df1.reset_index(drop=False)
#t = datasubset.groupby(['health','steward']).size()
#t2 = pd.DataFrame(t)
#t2=t2.reset_index()
#t2=t2.rename(columns={0:'count'})
#t2.columns
#
#plt.scatter(t2.health, t2.steward, s=t2.count)



@app.callback(
    dash.dependencies.Output('figure1', 'figure'),
    [dash.dependencies.Input('drpdwn1', 'value')])
def update_output(value):
    if (value == 'All'):
        datasubset = data[['boroname','spc_common','health','steward']]
        title = '<b>Health of all tree species in various borough</B>'
    else:
        datasubset = data.loc[data.spc_common==value,['boroname','spc_common','health','steward']]
        title = '<b>Health of ' +"'"+ value +"'"+' in various borough</b>'
    df = datasubset.groupby(['health','boroname'])['spc_common'].size().groupby(level=0).apply(lambda x:100 *x/x.sum()).unstack()
    df = df.reset_index(drop=False)
    df = df.fillna(0)
    d = []
    for  column in df.columns[1:]:
      txt = round(df[column],1).astype(str)
      txt = [t + '%' for t in txt]     
      d.append(go.Bar(x=df[df.columns[0]],y=round(df[column],1), name=column, text=txt, textposition="outside", hoverinfo='text'))
    figure= {'data':d,'layout': {'title': title, 'hovermode':'closest','xaxis':{'title':'Health Status'},'yaxis':{'title':'Percentage of Trees'}
    
                                                                    }
                                                    } 
    return(figure)

@app.callback(
    dash.dependencies.Output('figure2', 'figure'),
    [dash.dependencies.Input('drpdwn2', 'value')])
def update_output2(value):
    if (value == 'All'):
        datasubset = data[['boroname','spc_common','health','steward']]
        title = '<b>steward vs Health for all tree species</B>'
    else:
        datasubset = data.loc[data.spc_common==value,['boroname','spc_common','health','steward']]
        title = '<b>steward vs Health for ' +"'"+ value +"'"+'</b>'
    df = datasubset.groupby(['health','steward'])['spc_common'].size().groupby(level=0).apply(lambda x:100 *x/x.sum()).unstack()
    df = df.reset_index(drop=False)
    df = df.fillna(0)
    d = []
    for  column in df.columns[1:]:
      txt = round(df[column],1).astype(str)
      txt = [t + '%' for t in txt]     
      d.append(go.Bar(x=df[df.columns[0]],y=round(df[column],1), name=column, text=txt, textposition="outside", hoverinfo='text'))
    figure= {'data':d,'layout': {'title': title, 'hovermode':'closest', 'xaxis':{'title':'Health Status'},'yaxis':{'title':'Percentage of Trees'}}
                                                    } 
    return(figure)

if __name__ == '__main__':
    app.run_server(debug=True)