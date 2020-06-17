#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue May 12 12:16:35 2020

@author: davidraxen
"""
import re
import logging
import pandas as pd
import wikipedia
import datetime
from dateutil.relativedelta import relativedelta
import numpy as np
logging.basicConfig(filename='myProgramLog.txt', level=logging.DEBUG, format=' %(asctime)s - %(levelname)s - %(message)s')
logging.debug('Start of program')
import requests, sys, bs4

pd.options.mode.chained_assignment = None  # default='warn'



def StructEvent(c):
    ''' Takes the String that includes all events that happened in a game 
    and structures it as dictionaries within dictionaries that contains all 
    events that occured for resp. team in a game.
    -- Needs to be remade as a List of dictionaries so multiple events can occur
    in the same minute --
    '''
    
    #Add a space between names and events if there is none.
    clean = re.compile(r"([a-zćș])(Goal|Yellowcard|Redcard|Yellow-Redcard|Penaltymissed|Penaltyscored)")
    c = re.sub(clean, r'\1 \2', c)
    #Remove space for players with the same lastname like A. Cole & J. Cole -> A.Cole J.Cole 
    #This should be changed and removed so it picks up names like van Nistelroy and Del Piero also
    #c = c.replace(". ", ".")
    
    #Add a space if there is none between names and ' or )
    clean = re.compile(r"([']|[)])([a-zA-ZßÅÄÖÜÉŠ])")
    c = re.sub(clean, r'\1 \2', c)
    #Fix small error where the format for minutes was (12) and not 12'
    clean2 = re.compile("\((\d+)\)")
    c = re.sub(clean2, r"\1'", c)
    
    
    events = ["Goal", "Yellowcard", "Redcard", "Yellow-redcard", "Penaltymissed", "Penaltyscored"]
    c = c.split()
    d = []
    for i in range(1, len(c)):
        if i > 0 and c[i][0].isalpha() and c[i] not in events and c[i-1][0].isalpha() and c[i-1] not in events and ")" not in c[i-1]:
            c[i] = c[i-1] + " " + c[i]
            c[i] = c[i].replace("\'", "?")
        else:
            d.append(c[i-1])
    d.append(c[-1])
    c = d
           
        
    #Fix issue where the image was in a different order than usual
    
    if c[0] in events:
        temp = []
        j = 0
        for i in range(0, len(c)):
            if c[i] not in events and "\'" not in c[i] and ")" not in c[i]:
                b = list(range(j,i+1))
                b = b[-1:] + b[:-1]
                temp += b
                j = i + 1
        c = [c[i] for i in temp]               
                
    b = []
    k, v = "", ""
    for i in range(len(c)):
        if "\'" in c[i] and c[i][0].isdigit():
            if "," in c[i-2] and "," in c[i-1]:
                K = c[i].replace(",", "").replace("\'", "")
                b.append({K: {k: v}})
            elif "," in c[i-1]:
                K = c[i].replace(",", "").replace("\'", "")
                b.append({K: {k: v}})
            elif "Yellow-redcard" in c[i-1]:
                v = c[i-1]
                K = c[i].replace(",", "").replace("\'", "")
                b.append({K: {k: v}})
            elif "," in c[i-2] or "'" in c[i-2] or "(" in c[i-2]:
                v = c[i-1]
                if v == "Goal":
                    if i+1 < len(c) and "(" in c[i+1]:
                        v = {v: c[i+1]}
                    else:
                        v = {v: np.nan}
                K = c[i].replace(",", "").replace("\'", "")
                b.append({K: {k: v}})
            else:
                k, v = c[i-2], c[i-1]
                if v == "Goal":
                    if i+1 < len(c) and "(" in c[i+1]:
                        v = {v: c[i+1]}
                    else:
                        v = {v: np.nan}
                K = c[i].replace(",", "").replace("\'", "")
                b.append({K: {k: v}})
                if type(v) is dict:
                    v = list(v.keys())[0] #Make sure that all goals After a penalty isn't counted as a penalty!
    return b

def replaceImageWithTitle(res):
    ''' Replace all images in html-text for 
    their "alt"-tag to get all information in tables. '''
    pattern = "(\<img\salt\=)(.*?)(\s\/\>)"
    pattern2 = "(?<=\<img\salt\=\")(.*?)(?=\")"
    flupp = re.findall(pattern, res)
    pics = {}
    for tup in flupp:
        tup = ''.join(tup)
        pics[tup] = re.search(pattern2, tup).group(0).replace(" ", "")
    for k, v in pics.items():
        res = res.replace(k, v)
    return res, list(pics.values())

def CleanStad(df, images):
    for i in df.index:
        if "Stadium: " not in df.iloc[i, 9]:
            temp = df.iloc[i, 8].split(",")
            df.iloc[i, 9] = "Stadium: " + temp[0] + df.iloc[i, 9]
            if len(temp) > 1:
                df.iloc[i, 8] = temp[1].lstrip()
            else:
                df.iloc[i, 8] = ""
        if "Attendance: " not in df.iloc[i, 9]:
            if "Referee: " not in df.iloc[i, 9]:
                df.iloc[i, 9] = df.iloc[i, 9] + "Attendance: Referee: "
            else: 
                df.iloc[i, 9] = df.iloc[i, 9].replace("Referee:", "Attendance: Referee:")
    #Regex'es to find information in the 10th column.
    Referee = "(?<=Referee\:\s).*|$"
    Stadium = "(?<=Stadium\:\s).*?(?=[A-ZÖ][a-zö]+\:)|$"
    Attendance = "(?<=Attendance\:\s).*?(?=[A-ZÖ][a-zö]+\:)|$"
    RefereeNation = "(?<=\().*?(?=\))|$"
    RefereeNation2 = "\s\((.*)|$"

    df["Stadium"] = df.iloc[:, 9].apply(lambda x: re.search(Stadium, x).group(0).split("[")[0])
    df["Attendance"] = df.iloc[:, 9].apply(lambda x: re.search(Attendance, x).group(0).split(" (")[0])
                                        
    df["RefereeNation"] = df.iloc[:, 9].apply(lambda x: re.search(RefereeNation, x).group(0) if 
                                              x[-1] == ")" else "") #Should include a check for if last word in split x is in temp
    df.iloc[:, 9] = df.iloc[:, 9].apply(lambda x: re.sub(RefereeNation2, '', x))
    df["Referee"] = df.iloc[:, 9].apply(lambda x: re.search(Referee, x).group(0).split("Man of")[0].split("[")[0])
    
    #Handle cases where referees nation was shown using image rather than text.
    for i in df.index:
        if " " in  df["Referee"][i]:
            if df["Referee"][i].split()[0] in images:
                df["RefereeNation"][i] = df["Referee"][i].split()[0]
                df["Referee"][i] = " ".join(df["Referee"][i].split()[1:])
            if df["Referee"][i].split()[-1] in images:
                df["RefereeNation"][i] = df["Referee"][i].split()[-1]
                df["Referee"][i] = " ".join(df["Referee"][i].split()[:-1])
    #Handle exception in Attendance and correct a mistake in the data.
    for i in df.index:
        if df["Attendance"][i] == "None":
            df["Attendance"][i] = "0"
        if len(df["Attendance"][i]) > 0 and len(df["Referee"][i]) > 0:
            if df["Attendance"][i][0] == "N" and df["Referee"][i][0].isdigit():
                df["Attendance"][i],  df["Referee"][i] =  df["Referee"][i], df["Attendance"][i]
    #Convert Attendace "string" to numbers.
    df["Attendance"] = df["Attendance"].apply(lambda x: np.nan if x == "" else
                                              int(x.replace(",", ""))) 

def ExtractDate(df):
    df["Date"] = np.nan
    for i in df.index:
        c = df.iloc[:,0][i].split()
       # d = str(df.iloc[:,1][i]).split()
       # if not d[0].isdigit():
        #    d = "00:00"
        if "v" in df.iloc[:,4][i]:
        #if c[0] == "TBC" or "v" in df.iloc[:,4][i]:
            df["Date"][i] = np.nan
        else:
            df["Date"][i] =" ".join(c[:3]) + " " #+ d[0]
    try:
        df["Date"] = pd.to_datetime(df['Date'])
    except: pd.errors.ParserError
    

def Competition(df, seasons, eu_comp):
    df["Competition"] = np.nan
    tCount = 0        
    lst = [str(i) for i in list(range(1,40))]
    season = seasons[0]
    for i in df.index:
        if df["Season"][i] != season:
            tCount = 0
            season = df["Season"][i]
        c = df.iloc[:,0][i].split()
        if len(df["HomeTeamNation"][i]) > 1 and ((c[-1] in lst and df["Date"][i].month > 8) or c[-1] == "round" or
                                                 ("leg" in c or ("inal" in c[-1] and df["Date"][i].month < 7))):
                df["Competition"][i] = "European Competition"
        if len(df["HomeTeamNation"][i]) < 1 and c[-1] in lst:
                df["Competition"][i] = "Premier League"
        if len(df["HomeTeamNation"][i]) < 1 and c[-2] == "Third" and df["Date"][i].month != 1:
                tCount = 1
        if len(df["HomeTeamNation"][i]) < 1 and c[-2] == "Third" and df["Date"][i].month == 1:
                tCount = 2
        if len(df["HomeTeamNation"][i]) < 1 and tCount == 1:
                df["Competition"][i] = "League Cup"
        if len(df["HomeTeamNation"][i]) < 1 and tCount == 2:
                df["Competition"][i] = "FA Cup"
    for season in seasons:
        for i in df.index:
            if df["Season"][i] != "2012-13":
                if df["Season"][i] == season and df["Competition"][i] == "European Competition":
                    df["Competition"][i] = eu_comp[season]
            else:
                if df["Competition"][i] == "European Competition":
                    c = df.iloc[:,0][i].split()
                    if c[-1] in lst:
                        df["Competition"][i] = "UEFA Champions League"
                    else:
                        df["Competition"][i] = "UEFA Europa League"
    return df
            
    
def ExtractNation(df, images):
    df["HomeTeamNation"] = np.nan
    df["HomeTeam"] = np.nan
    df["AwayTeamNation"] = np.nan
    df["AwayTeam"] = np.nan
    for i in df.index:
        #HomeTeam & HomeTeamNation
        if " " in  df.iloc[:,2][i]:
            if df.iloc[:,2][i].split()[0] in images:
                df["HomeTeamNation"][i] = df.iloc[:,2][i].split()[0]
                df["HomeTeam"][i] = " ".join(df.iloc[:,2][i].split()[1:])
            elif df.iloc[:,2][i].split()[-1] in images:
                df["HomeTeamNation"][i] = df.iloc[:,2][i].split()[-1]
                df["HomeTeam"][i] = " ".join(df.iloc[:,2][i].split()[:-1])
            else:
                df["HomeTeamNation"][i] = ""
                df["HomeTeam"][i] = df.iloc[:,2][i]
        else:
            df["HomeTeamNation"][i] = ""
            df["HomeTeam"][i] = df.iloc[:,2][i]
        if " " in  df.iloc[:,6][i]:
            if df.iloc[:,6][i].split()[0] in images:
                df["AwayTeamNation"][i] = df.iloc[:,6][i].split()[0]
                df["AwayTeam"][i] = " ".join(df.iloc[:,6][i].split()[1:])
            elif df.iloc[:,6][i].split()[-1] in images:
                df["AwayTeamNation"][i] = df.iloc[:,6][i].split()[-1]
                df["AwayTeam"][i] = " ".join(df.iloc[:,6][i].split()[:-1])
            else:
                df["AwayTeamNation"][i] = ""
                df["AwayTeam"][i] = df.iloc[:,6][i]
        #And a couple of exceptions.
        else:
            df["AwayTeamNation"][i] = ""
            df["AwayTeam"][i] = df.iloc[:,6][i]
        if df["HomeTeamNation"][i] == "" and df["AwayTeamNation"][i] != "":
            df["HomeTeamNation"][i] = df.iloc[:,2][i].split()[-1]
            df["HomeTeam"][i] = " ".join(df.iloc[:,2][i].split()[:-1])
        if df["HomeTeamNation"][i] != "" and df["AwayTeamNation"][i] == "":
            df["AwayTeamNation"][i] = df.iloc[:,6][i].split()[0]
            df["AwayTeam"][i] = " ".join(df.iloc[:,6][i].split()[1:])
        if df["RefereeNation"][i] != "" and df["HomeTeamNation"][i] == "" and df["AwayTeamNation"][i] == "":
            df["HomeTeamNation"][i] = df["RefereeNation"][i]
            df["AwayTeamNation"][i] = "England"
        if df["HomeTeamNation"][i] == "Chelsea":
            df["HomeTeamNation"][i] = "England"
            df["HomeTeam"][i] = "Chelsea"
        if df["AwayTeamNation"][i] == "Chelsea":
            df["AwayTeamNation"][i] = "England"
            df["AwayTeam"][i] = "Chelsea"


def CreateEventDf(df):
    ''' Create a DataFrame where each event in a game is a row 
    - should probably create an inner function to not write everything twice '''            
    column_names = ["Date", "Season", "Manager", "Competition", "HomeTeam", "AwayTeam", "Home/Away", "Minute", "Player", "Event", "Extra"]
    events = pd.DataFrame(columns = column_names)
    c = 0 #counter
    for l in df.index:   
        #print(l)
        if type(df.HomeEvents[l]) is list:
            for i in df.HomeEvents[l]:
                events = events.append(pd.Series([np.nan]), ignore_index = True)
                events["Home/Away"][c] = "H"
                events["Date"][c] = df["Date"][l]
                events["HomeTeam"][c] = df["HomeTeam"][l]
                events["AwayTeam"][c] = df["AwayTeam"][l]
                events["Season"][c] = df["Season"][l]
                events["Competition"][c] = df["Competition"][l]
                events["Manager"][c] = df["Manager"][l]
                for K, k in i.items():
                    events["Minute"][c] = K  # i is the minute for the event.
                    for V, v in k.items():
                        events["Player"][c] = V # V is the player who did something
                        if type(v) is dict:
                            for X, x in v.items():
                                events["Event"][c] = X # X is a Goal
                                events["Extra"][c] = x # Extra info o.g or penalty
                                c += 1
                        else:
                            events["Event"][c] = v # v is a foul
                            events["Extra"][c] = np.nan # Extra info o.g or penalty
                            c += 1
        if type(df.AwayEvents[l]) is list:
            for i in df.AwayEvents[l]:
                events = events.append(pd.Series([np.nan]), ignore_index = True)
                events["Home/Away"][c] = "A"
                events["Date"][c] = df["Date"][l]
                events["HomeTeam"][c] = df["HomeTeam"][l]
                events["AwayTeam"][c] = df["AwayTeam"][l]
                events["Season"][c] = df["Season"][l]
                events["Competition"][c] = df["Competition"][l]
                events["Manager"][c] = df["Manager"][l]
                for K, k in i.items():
                    events["Minute"][c] = K  # i is the minute for the event.
                    for V, v in k.items():
                        events["Player"][c] = V # V is the player who did something
                        if type(v) is dict:
                            for X, x in v.items():
                                events["Event"][c] = X # X is a Goal
                                events["Extra"][c] = x # Extra info o.g or penalty
                                c += 1
                        else:
                            events["Event"][c] = v # v is a foul
                            events["Extra"][c] = np.nan # Extra info o.g or penalty
                            c += 1
    events["Player"] = events["Player"].apply(lambda x: x.replace("?", "'"))
    for i in events.index:
        if events["Player"][i] == "Cole":
            if (events["HomeTeam"][i] == "Chelsea" and events["Home/Away"][i] == "H") or (events["AwayTeam"][i] == "Chelsea" and events["Home/Away"][i] == "A"):
                if events["Date"][i].year < 2008 and events["Date"][i].year > 2003:
                    events["Player"][i] = "J. Cole"
                elif events["Date"][i].year < 2004:
                    events["Player"][i] = "C. Cole"
                else:
                    events["Player"][i] = "A. Cole"
    events["Extra"] = events["Extra"].apply(lambda x: np.nan if pd.isna(x) else ("P" if "pen" in x else "O.G"))

    return events

def GetBirthday(x):
    if x == "Frank Lampard":
        x = "Frank Lampard chelsea football" #For some reason works when Frank Lampard Jr doesn't
    if x == "Ryan Bertrand":
        x = "Ryan Bertrand chelsea football"
    if x == "Josh McEachran":
        x = "Josh McEachran chelsea football"        
    re_bday = '''(?<=\<span class\=\"bday\"\>)(.*?)(?=\<\/span\>)'''
    try:
        search = wikipedia.search(x + " football" + " chelsea")
        page = wikipedia.page(search[0])
        page_html = page.html(features="lxml")
        bday = re.search(re_bday, page_html)[0]
    except:
        try:
            link = "https://en.wikipedia.org/wiki/" + search[0].replace(" ", "_")
            res = requests.get(link)
            res.raise_for_status()
            page_html = res.text
            bday = re.search(re_bday, page_html)[0]
        except:
            return np.nan
    return bday


def getSubs(x):
    x = str(x).replace("—", "0").replace(" ", "").replace(")", "").replace("(", "+").replace(".0", "")
    if "+" not in x:
        x = x + "+0"
    return int(x.split("+")[1])

def getStarts(x):
    x = str(x).replace("—", "0").replace(" ", "").replace(")", "").replace("(", "+").replace(".0", "")
    if "+" not in x:
        x = x + "+0"
        if x == "+0":
            return np.nan
    return int(x.split("+")[0])
