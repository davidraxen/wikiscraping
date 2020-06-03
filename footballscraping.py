#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# footballscraping.py - Get some stuff from wikipedia
import time
start_time = time.time()

import re
import logging
import pandas as pd
import numpy as np
import datetime
logging.basicConfig(filename='myProgramLog.txt', level=logging.DEBUG, format=' %(asctime)s - %(levelname)s - %(message)s')
logging.debug('Start of program')
import requests, sys, bs4
import drx

print("Loading data...") # display some text to make it clear stuff is happening

#Create df mostly including the date intervals for each manager.
res = requests.get("https://en.wikipedia.org/wiki/List_of_Chelsea_F.C._managers")
res.raise_for_status()
res, images = drx.replaceImageWithTitle(res.text)
managers = pd.read_html(res)
managers = managers[0]#
managers = managers.iloc[: , list(range(1,11))]
managers["Name"] = managers["Name"].apply(lambda x: x.split("[")[0])
managers["From"] = pd.to_datetime(managers['From'])
for i in managers.index:
    if managers["To"][i] == "present":
        managers["To"][i] = datetime.datetime.now()
managers["To"] = pd.to_datetime(managers['To'])
#--------------------------------------------------


#--- Creating seasons. Earlier seasons have tables in a different format. 
seasons = []
i = 0
j = 1
while j < 21:
    if len(str(i)) < 2:
        s = str(0)+str(i)
    else:
        s = str(i)
    if len(str(j)) < 2:
        t = str(0)+str(j)
    else:
        t = str(j)
    u = "20"+s+"-"+t
    i += 1
    j += 1
    seasons.append(u)

#--- Extract info for which european cup Chelsea played each season.    
res = requests.get("https://en.wikipedia.org/wiki/Chelsea_F.C._in_international_football_competitions")
res.raise_for_status()
res, images = drx.replaceImageWithTitle(res.text)
eu_cups = pd.read_html(res)
eu_cups = eu_cups[2]
eu_cups["Season"] = eu_cups["Season"].apply(lambda x: x.replace("–", "-"))

eu_comp = {}
for i in eu_cups.index:
    if eu_cups["Season"][i] in seasons and eu_cups["Season"][i] not in eu_comp:
        eu_comp[eu_cups["Season"][i]] = eu_cups["Competition"][i]
#-------------------------------------------------------------------        
    
#-- Download all tables from each seasons wiki-page.  
# Create some empty lists to store data from each season.
images = []  # List to store all "alt"-tags from images on the wikipages.
lst = []
g2 = pd.DataFrame() #g2 append each dataframe games (which is a dataframe with raw info 
                    # from all the games each season.)
players = pd.DataFrame() # - Not in use yet. 

# Regex to remove Notes from tables.
Note = """\<tr\sstyle\=\"font\-size\:85\%\"\>\<td\scolspan\=\"5\"\>\<i\>Note.*\<\/td\>\s\<\/tr\>"""
Positions = '''\<tr\>\s\<th\scolspan=\"16\"\sstyle\=\"background\:\#dcdcdc\;\"\>.*\s\<\/th\>\<\/tr\>'''


for i in seasons:
    season = "https://en.wikipedia.org/wiki/" + i + "_Chelsea_F.C._season"
    try:        
        res = requests.get(season)
        res.raise_for_status()
        res, images2 = drx.replaceImageWithTitle(res.text) #Replace images with their resp. "alt"-tag
        res = res.replace("8;", "8") #if 2018-19
        res = res.replace("wikitable sortable", "wikitable") #Needed to grab a table from 2013-14
        res = re.sub(Note, "", res) # Removes notes from tables to ensure that all games gets captured
        res = re.sub(Positions, "", res) # Cleans up a table with a little too much unformation.
        images += images2   # Add all new images for each season to the images list.
        images = list(set(images)) # Remove duplicates from list.
        tables = pd.read_html(res) # Store _All_ dataframes from wiki-page.
        games = pd.DataFrame() # Empty DataFrame for storing each game.
        lst2 = [] # Temporary list.
        
        # --- Append all separate games into One dataframe.
        for df in tables:
            if df.shape[0] > 1:
                if list(df.columns) == [0,1,2,3,4]:
                    rows = []
                    for row in range(len(df.columns)):
                        rows += list(df[row])
                    df = pd.DataFrame([rows])
                    if df.shape[1] < 12: #Skips some friendlies with a weird format. 
                        games = games.append(df, ignore_index = True)
                        games.iloc[:,1] = games.iloc[:,1].fillna("00:00 GMT")
                        games["Season"] = i
                else:
                    df["Season"] = i
                    lst2.append(df) 
        lst.append(lst2)
        g2 = g2.append(games, ignore_index = True)
        print("Season " +i+ " done")
    except: ValueError  

del Note, Positions    
print("Seasons loaded.")

#--- Creating DataFrame with all Players and how many games resp. Goals they scored in all competative fixtures.
lst2 = []
for l in lst:
    for df in l:
        if "Total" in df.columns and "Rnk" not in df.columns and "Rank" not in df.columns:
            df.columns = [' '.join(col).strip() for col in df.columns.values]
            #--- For one type of tables.
            if "Total Apps" in df.columns and "Total Goals" in df.columns:
                p = pd.DataFrame()
                p["Season"] = df["Season"]
                if "Nat Nat" in list(df.columns) and "Player Player" in list(df.columns):
                    p["Nation"] =  df.iloc[:,2]
                    p["Name"] =  df.iloc[:,3]
                for col in df.columns:
                    if "No." in col:
                        p["Number"] = df[col].astype(str) #Might be counter intuitive to put as strings. But needed to sort out fault values later on
                    if "Pos" in col:
                        p["Position"] = df[col]
                    if "Name " in col or ("Player" in col and "Nat Nat" not in list(df.columns)):
                        p["Nation"] = df[col].apply(lambda x: x.split()[0])
                        p["Name"] = df[col].apply(lambda x: x.split(" ", 1)[1])
                    #- Premier League 
                    if "eague" in col and "Apps" in col and "UEFA" not in col and "hamp" not in col and "up" not in col:
                        p["PremierLeagueApps"] = df[col].astype(str)
                    if "eague" in col and "Goal" in col and "UEFA" not in col and "hamp" not in col and "up" not in col:
                        p["PremierLeagueGoals"] = df[col].astype(str)
                    #- FA Cup 
                    if "FA Cup" in col and "Apps" in col:
                        p["FaCupApps"] = df[col].astype(str)
                    if "FA Cup" in col and "Goal" in col:
                        p["FaCupGoals"] = df[col].astype(str)
                    # -League Cup
                    if ("eague" in col or "EFL" in col) and "up" in col and "Apps" in col:
                        p["LeagueCupApps"] = df[col].astype(str)
                    if ("eague" in col or "EFL" in col) and "up" in col and "Goal" in col:
                        p["LeagueCupGoals"] = df[col].astype(str)
                    # - Champions League
                    if "hampion" in col and "Apps" in col:
                        p["ChampionsLeagueApps"] = df[col].astype(str)
                    if "hampion" in col and "Goal" in col:
                        p["ChampionsLeagueGoals"] = df[col].astype(str)   
                    # - UEFA Cup
                    if "UEFA Cup" in col and "Apps" in col:
                        p["UEFACupApps"] = df[col].astype(str)
                    if "UEFA Cup" in col and "Goal" in col:
                        p["UEFACupGoals"] = df[col].astype(str)
                     # - Europa League
                    if "Europa" in col and "Apps" in col:
                        p["EuropaLeagueApps"] = df[col].astype(str)
                    if "Europa" in col and "Goal" in col:
                        p["EuropaLeagueGoals"] = df[col].astype(str)
                players = players.append(p, ignore_index = True)
                players = players[players.Number.apply(lambda x: x.isnumeric())]
                players["PremierLeagueGoals"] = players["PremierLeagueGoals"].astype(int)

        if ("Rnk" in df.columns or "Rank" in df.columns) and df["Season"].iloc[0] not in players.Season.unique() and df.shape[0] > 3:
            df = df.rename({'Pos.': 'Pos', 'Name': 'Player'}, axis=1)  # Handle exception.
            df = df[df.Pos.notna()]
            lst2.append(df)

lst3 = []
i = 0
while i < len(lst2)-1:
    lst3.append(pd.merge(lst2[i], lst2[i+1], how='outer', on="Player"))
    i += 2
       
for df in lst3:
    df = df[:-2]
    p = pd.DataFrame()
    #assigning columns to the right place in the combined dataframe.
    #Should probably be an if statement checking that the said column
    #exists in the dataframe. - UEFA cup not included in this case for instance.
    p["Season"] = df["Season_x"]
    p["Number"] = df["No._x"]
    p["Position"] = df["Pos_x"]
    p["Nation"] = df["Player"].apply(lambda x: x.split()[0])
    p["Name"] = df["Player"].apply(lambda x: x.split(" ", 1)[1])
    p["PremierLeagueApps"] = df["Premier League_x"]
    p["PremierLeagueGoals"] = df["Premier League_y"]
    p["FaCupApps"] = df["FA Cup_x"]
    p["FaCupGoals"] = df["FA Cup_y"]
    p["LeagueCupApps"] = df["League Cup_x"]
    p["LeagueCupGoals"] = df["League Cup_y"]
    if "Champions League_x" in df.columns:
        p["ChampionsLeagueApp"] = df["Champions League_x"]
        p["ChampionsLeagueGoals"] = df["Champions League_y"]
    if "Europa League_x" in df.columns:
        p["EuropaLeagueApps"] = df["Europa League_x"]
        p["EuropaLeagueGoals"] = df["Europa League_y"]
    
    players = players.append(p, ignore_index = True)
     
#-- Fixing an issue with season 2013-14 only having last names.
p2011_12 = players[players["Season"] == "2011-12"]["Name"]
p2012_13 = players[players["Season"] == "2012-13"]["Name"]
p2014_15 = players[players["Season"] == "2014-15"]["Name"]
p2015_16 = players[players["Season"] == "2015-16"]["Name"]

for i in players.index:
    if players["Season"][i] == "2013-14":
        for j in p2011_12:
            if players["Name"][i] in j:
                players["Name"][i] = j
        for j in p2012_13:
            if players["Name"][i] in j:
                players["Name"][i] = j
        for j in p2014_15:
            if players["Name"][i] in j:
                players["Name"][i] = j
        for j in p2015_16:
            if players["Name"][i] in j:
                players["Name"][i] = j
del p2011_12, p2012_13, p2014_15, p2015_16

players = players.sort_values(by=["Season"]) 

t_dict = {}
for p in players.Name.unique():
    t_dict[p] = drx.GetBirthday(p)
    
players["Born"] = players["Name"].apply(lambda x: t_dict[x])
 
print("DataFrame with all players and no. games and goals per season. Done")

# ------- DONE AND DONE. COMMENT OUT AND COME BACK TO LATER.

df = g2.copy()
#-- Clean the DataFrame for the games.
drx.ExtractDate(df)


df["HomeEvents"] = df.iloc[:,3].apply(lambda x: np.nan if pd.isnull(x) else
                          drx.StructEvent(x))
df["AwayEvents"] = df.iloc[:,7].apply(lambda x: np.nan if pd.isnull(x) else
                          drx.StructEvent(x))


drx.CleanStad(df, images)

df["StadiumCity"] = df.iloc[:,8].apply(lambda x: x.split(",")[0]
                                        if "," in x else x)

drx.ExtractNation(df, images)

drx.Competition(df, seasons, eu_comp)

#--- Add Manager to games.

df["Manager"] = np.nan
for i in df.index:
    for j in managers.index:
        if df["Date"][i] >= managers["From"][j] and df["Date"][i] <= managers["To"][j]:
            df["Manager"][i] = managers["Name"][j]
#------------------------------------
# Create count of home and away goals columns.
df.iloc[:,4] = df.iloc[:,4].apply(lambda x: x.replace(" – ", "").split()[0])
df["HomeGoals"] = df.iloc[:,4].apply(lambda x: x.split("–")[0]if "–" in x else 
                                      x.split("-")[0] if "-" in x else x)
df["AwayGoals"] = df.iloc[:,4].apply(lambda x: x.split("–")[1]if "–" in x else 
                                      x.split("-")[1] if "-" in x else x)
for i in df.index:
    if len(df["HomeGoals"][i]) > 1 and len(df["AwayGoals"][i]) > 1:
        df["HomeGoals"][i], df["AwayGoals"][i] = int(df["HomeGoals"][i][0]), int(df["HomeGoals"][i][1])
    elif "v" in df["HomeGoals"][i]:
        df["HomeGoals"][i], df["AwayGoals"][i] = np.nan, np.nan
    else:
        df["HomeGoals"][i], df["AwayGoals"][i] = int(df["HomeGoals"][i]), int(df["AwayGoals"][i])
#--------------------------------------------


print("DataFrame for each game created.")

#----------------------------
#-- Create df with all events from games.
events = drx.CreateEventDf(df).iloc[:,:-1]

a = df.groupby("Season")["Competition"].value_counts()

df = df[['Season', 'Date', 'StadiumCity', 'Stadium', 'Attendance',
        'Referee', 'RefereeNation', 'HomeTeamNation', 'HomeTeam',
        'AwayTeamNation', 'AwayTeam', 'Competition', 'Manager', 'HomeGoals',
        'AwayGoals']]

#Deleting lingering variables.
del a, col, eu_comp, eu_cups, g2, i, images, images2, j, l, lst, lst2, lst3, p, res, row, rows, s, season, seasons, t, tables, u

#Saving -.csv's and excels of the data.
df.to_csv (r'Chelsea_games.csv', index = False, header=True)
events.to_csv (r'Chelsea_events.csv', index = False, header=True)
players.to_csv (r'Chelsea_players.csv', index = False, header=True)


with pd.ExcelWriter('ChelseaData.xlsx') as writer:  
    df.to_excel(writer, sheet_name='games')
    events.to_excel(writer, sheet_name='events')
    players.to_excel(writer, sheet_name='players')

print("Done! This took %s seconds" % (time.time() - start_time))
