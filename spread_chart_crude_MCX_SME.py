# -*- coding: utf-8 -*-
"""
Created on Sat May 12 05:13:49 2018

@author: Administrator
"""
import pandas as pd
import numpy as np
import os
from matplotlib import mlab
import matplotlib.pyplot as plt
import time
from datetime import datetime
from datetime import timedelta
from dateutil import tz
import pytz

from plotly.offline import download_plotlyjs, init_notebook_mode, plot, iplot

import plotly.plotly as py
import plotly.graph_objs as go
import glob, os

#local_tz = pytz.timezone('Europe/Moscow')
users_tz = tz.tzlocal()
#from_zone = tz.tzutc()
#to_zone = tz.tzlocal()

os.chdir(r'F:\Himanshu\backtest\commodities')

data_files=[]

dt_frame=[]


data_PB = pd.read_csv("Crude oil MCX.csv", header=0)
data_ZS = pd.read_csv("Crude oil SME.csv", header=0)

data_PB['DateTime'] = pd.to_datetime(data_PB['Date']) 
data_ZS['DateTime'] = pd.to_datetime(data_ZS['Date']) 

data_PB = data_PB.sort_values(by=['DateTime'])
data_ZS = data_ZS.sort_values(by=['DateTime'])

data_PB.rename(columns={'Price':'Price_PB', 'Open':'Open_PB','High':'High_PB', 'Low':'Low_PB'}, inplace=True)

#del data_PB['Date']
del data_PB['Vol.']
del data_PB['Change %']

data_ZS.rename(columns={'Price':'Price_ZS', 'Open':'Open_ZS','High':'High_ZS', 'Low':'Low_ZS'}, inplace=True)

del data_ZS['Date']
del data_ZS['Vol.']
del data_ZS['Change %']

data = pd.merge(data_PB, data_ZS, on='DateTime')

##### CALCULATE SPDs ####
data['spd'] = data['Price_PB'] - data['Price_ZS']  

'''
data['PB_Long'] = 0
data['PB_Short'] = 0

data['PB_Long_Trade'] = 0
data['PB_Short_Trade'] = 0

data['ZS_Long_Trade'] = 0
data['ZS_Short_Trade'] = 0

data['ZS_Long_Signal'] = 0
data['ZS_Short_Signal'] = 0

BUY_SPD_TH = -2 # -0.2 Ask1_cf - Bid1_ok    <= -1.00 
SELL_SPD_TH = 2 # Bid1_cf - Ask1_ok 

#BUY_SPD_TH = -2.3
#SELL_SPD_TH = 10

# Entry FORMULA
#spread_buy = Ask1_cf - Bid1_ok     #   Buy in CF (Buy Trade) , Sell in OK (Sell Trade) --> Ask1_Cf - Bid1_ok < 0 (Entry) 
#spread_sell = Bid1_cf - Ask1_ok    #  Sell in CF (Sell Trade) , Buy in OK (Buy Trade)  --> Bid1_cf - Ask1_ok > 0  (Entry)

cf_long_pos = 0 # 0 - no pos, 1 - curr pos, 2 - sq off / exit
cf_short_pos = 0

cf_long_tradepx = 0
cf_short_tradepx = 0

ok_long_tradepx = 0
ok_short_tradepx = 0

for i in data.index:
    
        ### CASE 1 : CF LONG & OK SHORT ###############
        if data.loc[i,'spd'] <  BUY_SPD_TH and cf_long_pos == 0: # SPREAD OPENS UP - NEW LONG POS - ENTRY
          
            ## CF LONG POS
            cf_long_pos = 1
            cf_long_tradepx = data.loc[i,'ask1_cf']
            data.loc[i,'CF_Long'] = cf_long_pos
            data.loc[i,'CF_Long_Trade'] = cf_long_tradepx
            
            ## OK SHORT POS 
            ok_short_tradepx = data.loc[i,'bid1_ok']
            data.loc[i,'OK_Short_Trade'] = ok_short_tradepx
            
            data.loc[i,'CF_Long_Signal'] = 1
            
            
        elif cf_long_pos == 1  and data.loc[i,'bspd'] >=0: # SPREAD CONVERGE BACK , SQ OFF WITH SHORT POS 
  
            ## CF SHORT POS (SQ)
            cf_long_pos = 2
            data.loc[i,'CF_Long'] = cf_long_pos
            data.loc[i,'CF_Short_Trade'] = data.loc[i,'bid1_cf']
            
            ## OK LONG POS (SQ)
            data.loc[i,'OK_Long_Trade'] = data.loc[i,'ask1_ok']
            cf_long_pos = 0
            
        elif cf_long_pos == 1 and data.loc[i,'bspd'] < 0:   # carry forward trade price
            
            data.loc[i,'CF_Long'] = cf_long_pos
            data.loc[i,'CF_Long_Trade'] = cf_long_tradepx
            data.loc[i,'OK_Short_Trade'] = ok_short_tradepx
                   
         ### CASE 2 : CF SHORT & OK LONG ################
        if data.loc[i,'sspd'] >  SELL_SPD_TH and cf_short_pos == 0: # SPREAD OPENS UP - NEW SHORT POS
          
            ## CF SHORT POS
            cf_short_pos = 1
            cf_short_tradepx = data.loc[i,'bid1_cf']
            data.loc[i,'CF_Short'] = cf_short_pos
            data.loc[i,'CF_Short_Trade'] = cf_short_tradepx
            
            ## OK LONG POS 
            ok_long_tradepx = data.loc[i,'ask1_ok']
            data.loc[i,'OK_Long_Trade'] = ok_long_tradepx
            
            data.loc[i,'CF_Short_Signal'] = 1
            
            
        elif cf_short_pos == 1  and data.loc[i,'sspd'] <= 0: # SPREAD CONVERGE BACK , SQ OFF WITH SHORT POS 
  
            ## CF LONG POS (SQ)
            cf_short_pos = 2
            data.loc[i,'CF_Short'] = cf_short_pos
            data.loc[i,'CF_Long_Trade'] = data.loc[i,'ask1_cf']
            
            ## OK SHORT POS (SQ)
            data.loc[i,'OK_Short_Trade'] = data.loc[i,'bid1_ok']
            cf_short_pos = 0
            
        elif cf_short_pos == 1 and data.loc[i,'sspd'] > 0:   # carry forward long trade
            
            data.loc[i,'CF_Short'] = cf_short_pos
            data.loc[i,'CF_Short_Trade'] = cf_short_tradepx
            data.loc[i,'OK_Long_Trade'] = ok_long_tradepx
            


data['CF_Long_PnL'] = 0
data['CF_Short_PnL'] = 0
data['OK_Long_PnL'] = 0
data['OK_Short_PnL'] = 0

### PNL CALCULATION - CASE 1 : CF LONG , OK SHORT ###

data['CF_Long_PnL'] = np.where( data['CF_Long'] == 2 , data['CF_Short_Trade'] - data['CF_Long_Trade'].shift(1)  , data['CF_Long_PnL'] )
data['OK_Short_PnL'] = np.where( data['CF_Long'] == 2 , data['OK_Short_Trade'].shift(1) - data['OK_Long_Trade']  , data['OK_Short_PnL'] )

####################################################################################################################################################

### CASE 2 : SHORT CF , LONG OKEX ### XXX NOT IN USE
#data['CF_Long_Trade'] = np.where( data['CF_Short'] == 2 , data['ask1_cf'] , data['CF_Long_Trade'] )
#data['OK_Short_Trade'] = np.where( data['CF_Short'] == 2 , data['bid1_ok'] , data['OK_Short_Trade'] )

### PNL CALCULATION - CASE 2 : CF SHORT , OK LONG ###

data['CF_Short_PnL'] = np.where( data['CF_Short'] == 2 , data['CF_Short_Trade'].shift(1) - data['CF_Long_Trade']  , data['CF_Short_PnL'] )
data['OK_Long_PnL'] = np.where( data['CF_Short'] == 2 , data['OK_Short_Trade'] - data['OK_Long_Trade'].shift(1)  , data['OK_Long_PnL'] )

########### PNL SUMMARY #############

data['CF_PnL'] = 0
data['OK_PnL'] = 0
data['PnL'] = 0
data['Cum_PnL'] = 0
data['Cum_CF_PnL'] = 0
data['Cum_OK_PnL'] = 0


data['CF_PnL'] = data['CF_Long_PnL']  + data['CF_Short_PnL']
data['OK_PnL'] = data['OK_Long_PnL']  + data['OK_Short_PnL']
data['PnL'] = data['OK_PnL']  + data['CF_PnL']
data['Cum_PnL'] = data['PnL'].cumsum()
data['Cum_CF_PnL'] = data['CF_PnL'].cumsum()
data['Cum_OK_PnL'] = data['OK_PnL'].cumsum()

### BACK TEST CODE END ###
########################################################################################################################################################
######### PLOTTING CODE ######
### ENTRY SIGNALS ###

CF_Long_Entry = data.loc[(data['CF_Long_Signal'] == 1)] #CF_Long_Trade , OK_Short_Trade
CF_Short_Entry = data.loc[(data['CF_Short_Signal'] == 1)] #CF_Short_Trade, OK_Long_Trade

### EXIT SIGNALS ###

CF_Long_Exit = data.loc[(data['CF_Long'] == 2)] #CF_Short_Trade , OK_Long_Trade
CF_Short_Exit = data.loc[(data['CF_Short'] == 2)] #CF_Long_Trade , OK_Short_Trade

Exit_all = []

Exit_all.append(CF_Long_Exit)
Exit_all.append(CF_Short_Exit)

Exit_Final = pd.concat(Exit_all)

##################### ENTRY MARKERS ###########################

trace11 = go.Scatter(x=CF_Long_Entry.DateTime, y=CF_Long_Entry['CF_Long_Trade'],  name='CF_Long_Trade', mode = 'markers', marker={'color': 'blue', 'symbol': 205, 'size': 15}, yaxis='y2')
trace12 = go.Scatter(x=CF_Long_Entry.DateTime, y=CF_Long_Entry['OK_Short_Trade'],  name='OK_Short_Trade', mode = 'markers', marker={'color': 'red', 'symbol': 205, 'size': 15}, yaxis='y2')

trace13 = go.Scatter(x=CF_Short_Entry.DateTime, y=CF_Short_Entry['CF_Short_Trade'],  name='CF_Short_Trade', mode = 'markers', marker={'color': 'red', 'symbol': 205, 'size': 15}, yaxis='y2')
trace14 = go.Scatter(x=CF_Short_Entry.DateTime, y=CF_Short_Entry['OK_Long_Trade'],  name='OK_Long_Trade', mode = 'markers', marker={'color': 'blue', 'symbol': 205, 'size': 15}, yaxis='y2')

####################### EXIT MARKERS ##########################################################################

trace15 = go.Scatter(x=CF_Long_Exit.DateTime, y=CF_Long_Exit['CF_Short_Trade'],  name='CF_Short_Trade', mode = 'markers', marker={'color': 'red', 'symbol': 213, 'size': 15}, yaxis='y2')
trace16 = go.Scatter(x=CF_Long_Exit.DateTime, y=CF_Long_Exit['OK_Long_Trade'],  name='OK_Long_Trade', mode = 'markers', marker={'color': 'blue', 'symbol': 213, 'size': 15}, yaxis='y2')

trace17 = go.Scatter(x=CF_Short_Exit.DateTime, y=CF_Short_Exit['CF_Long_Trade'],  name='CF_Long_Trade', mode = 'markers', marker={'color': 'blue', 'symbol': 213, 'size': 15}, yaxis='y2')
trace18 = go.Scatter(x=CF_Short_Exit.DateTime, y=CF_Short_Exit['OK_Short_Trade'],  name='OK_Short_Trade', mode = 'markers', marker={'color': 'red', 'symbol': 213, 'size': 15}, yaxis='y2')

################################################################################################

trace3 = go.Scatter(x=data['DateTime'], y=data['bid1_ok'],  name='bid1_ok', yaxis='y2')
trace4 = go.Scatter(x=data['DateTime'], y=data['ask1_ok'],  name='ask1_ok', yaxis='y2')

trace5 = go.Scatter(x=data['DateTime'], y=data['bid1_cf'],  name='bid1_cf', yaxis='y2')
trace6 = go.Scatter(x=data['DateTime'], y=data['ask1_cf'],  name='ask1_cf', yaxis='y2')

trace7 = go.Scatter(x=data['DateTime'], y=data['bspd'],  name='bspd')
trace8 = go.Scatter(x=data['DateTime'], y=data['sspd'],  name='sspd')

trace10 = go.Scatter(x=data['DateTime'], y=data['diffspd'],  name='diffspd')

### PLOT PNL ###

trace19 = go.Scatter(x=data['DateTime'], y=data['Cum_CF_PnL'],  name='CF_PnL', yaxis='y3') 
trace20 = go.Scatter(x=data['DateTime'], y=data['Cum_OK_PnL'],  name='OK_PnL', yaxis='y3')
trace21 = go.Scatter(x=data['DateTime'], y=data['Cum_PnL'],  name='PnL', yaxis='y3')

#trace19 = go.Scatter(x=Exit_Final['DateTime'], y=Exit_Final['Cum_CF_PnL'],  name='CF_PnL', yaxis='y3')
#trace20 = go.Scatter(x=Exit_Final['DateTime'], y=Exit_Final['Cum_OK_PnL'],  name='OK_PnL', yaxis='y3')
#trace21 = go.Scatter(x=Exit_Final['DateTime'], y=Exit_Final['Cum_PnL'],  name='PnL', yaxis='y3')

##############

layout = go.Layout(
    title='OKEX CRYPTO ETH',
    yaxis=dict(
        title='yaxis title'
    ),
    yaxis2=dict(
        title='yaxis2 title',
        titlefont=dict(
            color='rgb(148, 103, 189)'
        ),
        tickfont=dict(
            color='rgb(148, 103, 189)'
        ),
        overlaying='y',
        side='right'
    ),
    yaxis3=dict(
        title='yaxis3 title',
        titlefont=dict(
            color='rgb(99, 123, 139)'
        ),
        tickfont=dict(
            color='rgb(110, 88, 159)'
        ),
        overlaying='y',
        side='right'
    )
)


#data_all = [trace3, trace4, trace5, trace6, trace7, trace8, trace10, trace11, trace12, trace13, trace14, trace15, trace16, trace17, trace18, trace19, trace20, trace21]

data_all = [trace3, trace4, trace5, trace6, trace7, trace8, trace11, trace12, trace13, trace14, trace15, trace16, trace17, trace18, trace19, trace20, trace21]

#data_all = [trace19, trace20, trace21, trace3, trace4, trace5, trace6]
'''

layout = go.Layout(
    title='OKEX CRYPTO ETH',
    yaxis=dict(
        title='yaxis title'
    ),
    yaxis2=dict(
        title='yaxis2 title',
        titlefont=dict(
            color='rgb(148, 103, 189)'
        ),
        tickfont=dict(
            color='rgb(148, 103, 189)'
        ),
        overlaying='y',
        side='right'
    ),
    yaxis3=dict(
        title='yaxis3 title',
        titlefont=dict(
            color='rgb(99, 123, 139)'
        ),
        tickfont=dict(
            color='rgb(110, 88, 159)'
        ),
        overlaying='y',
        side='right'
    )
)

#data['spd'] = data['Price_PB'] - data['Price_ZS']  
        
trace1 = go.Scatter(x=data['DateTime'], y=data['spd'],  name='SPD', yaxis='y') 
trace2 = go.Scatter(x=data['DateTime'], y=data['Price_PB'],  name='Price_PB', yaxis='y2')
trace3 = go.Scatter(x=data['DateTime'], y=data['Price_ZS'],  name='Price_ZS', yaxis='y3')       

data_all = [trace1, trace2, trace3] 

fig = go.Figure(data=data_all, layout=layout)
plot(fig, filename = 'COMM' + '.html')    

