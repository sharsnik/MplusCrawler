# -*- coding: utf-8 -*-
"""
Created on Fri Apr  8 00:43:54 2022

@author: Shars
"""

import requests
import re
import time
import pickle
import matplotlib.pyplot as plt
import numpy as np
import scipy
from scipy import stats


from bs4 import BeautifulSoup
from selenium import webdriver    
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException

NUM_USERS = 100
USERS_PER_PAGE = 20

CLASSES = ["death-knight", "demon-hunter", "druid", "monk", "paladin", "warrior"]
DUNGEON_NAMES = ["De Other Side", "Halls of Attonement", "Mists of Trina Scithe", "The Necrotic Wake", "Plaguefall", "Sanguine Depths", "Spires of Ascension", "Theater of Pain", "Streets of Wonder", "Soleah's Gambit"]
DUNGEON_IDS = [12291, 12287, 12290, 12286, 12289, 12284, 12285, 12293, 12441, 12442]
CLASS_COLORS = ['#C41E3A', '#A330C9', '#FF7C0A', '#00FF98', '#F48CBA', '#C69B6D']

RAIDER_IO_STUB = "https://raider.io/mythic-plus-character-rankings/season-sl-3/world/{}/tank/{}#content"
# = "\"name\":\"([^\"]*)\",\"class\""
RAIDER_IO_CHARACTER_REGEX = "\"path\":\"\/characters\/([^/]*)\/([^/]*)\/([^\"]*)\",\"realm\""
DPS_REGEX = "damage-done\">\n([^<]*)</a>\n\n</td><td nowrap=\"\" class=\"keystone-cell"
PARSE_REGEX = "damage-done\">([^<]*)</a>\n</td><td class=\"rank\"><a class=\"character-table-link"
SPEC_REGEX = "\-([^\"]*)\" class=\"tiny-icon sprite actor-sprite-"

CHROME_DRIVER_PATH = 'C:/Users/Shars/MplusCrawler/ChromeDriver/'


WARCRAFTLOGS_STUB = "https://www.warcraftlogs.com/character/{}/{}/{}?zone=25&new=true#boss={}&metric=dps"

# Step one is to crawl raider.io leaderboards for each class and compile a list of characters

usePages = range(0, int(NUM_USERS/USERS_PER_PAGE))

allUsers = {}
for className in CLASSES:
    thisUsers = []
    
    for i in usePages:
        topUserList = requests.get(RAIDER_IO_STUB.format(className, i))        
        topUsers = re.findall(RAIDER_IO_CHARACTER_REGEX, topUserList.text)
        
        thisUsers.extend(topUsers)
        
        print("Loading top users... Class {}, page {}".format(className, i));
    
    allUsers[className] = thisUsers

# Step two is to crawl warcraftlogs and grab as many logs from these people as we can

options = webdriver.ChromeOptions()
options.add_argument('--headless')
browser = webdriver.Chrome(options=options, executable_path='{}chromedriver.exe'.format(CHROME_DRIVER_PATH))


allDPS = {}
for className in CLASSES:
    total = 0
    thisDPS = {}
    allDPS[className] = []
    for dungeon in DUNGEON_IDS:
        thisDPS[dungeon] = []
    
    thisUsers = allUsers[className]
    
    index = 0
    for region, realm, name in thisUsers:
        print("Looking up DPS... Class {}, user {} -> {}... total entries: {}".format(className, index, name, total));

        for dungeon in DUNGEON_IDS:
            browser.get(WARCRAFTLOGS_STUB.format(region, realm, name, dungeon))
            delay = 3
            try:
                myElem = WebDriverWait(browser, delay).until(EC.presence_of_element_located((By.ID, 'boss-table_wrapper')))
            except TimeoutException:
                print("Timed out:")
            html = browser.page_source
            
            topDPS = re.findall(DPS_REGEX, html)            
            topDPS = [float(re.sub(",", "", number)) for number in topDPS]
            
            topParses = re.findall(PARSE_REGEX, html)            
            topParses = [float(re.sub(",", "", number)) for number in topParses]
            
            topSpecs = re.findall(SPEC_REGEX, html)
            
            topUsers = [(dps, parse, spec) for dps, parse, spec in zip(topDPS, topParses, topSpecs)]
            
            total += len(topUsers)
            
            if len(topDPS) == 0 and not "No data" in html:
                print("    WARNING: Some sort of error occured... skipping {}".format(WARCRAFTLOGS_STUB.format(region, realm, name, dungeon)));
            
            thisDPS[dungeon].extend(topUsers)
        
        time.sleep(10)
        
        index += 1
    
    allDPS[className] = thisDPS

browser.quit()

f = open("data/tankDPS.pkl","wb")
pickle.dump(allDPS,f)
f.close()

# Display results

f = open("data/tankDPS.pkl","rb")
allDPS = pickle.load(f)
f.close()
useDungeon = ["Halls of Attonement", "Mists of Trina Scithe", "The Necrotic Wake"]
useDungeon = ["Spires of Ascension", "Theater of Pain"]
useDungeon = []

'''useSpecs = ['Affliction', 'Arcane', 'Arms', 'Assassination', 'Balance',
       'BeastMastery', 'Demonology', 'Destruction',
       'Discipline', 'Elemental', 'Enhancement', 'Feral', 'Fire', 'Frost',
       'Fury', 'Havoc', 'Holy', 'Marksmanship', 'Outlaw',
       'Restoration', 'Retribution', 'Shadow', 'Subtlety',
       'Survival', 'Unholy', 'Windwalker']'''
useSpecs = ['Protection', 'Guardian', 'Vengeance', 'Blood', 'Brewmaster'];

classDPS = {}
allSpecs = []
boxData = []
meanData = []
classIndex = 0
for className in CLASSES:
    classDPS[className] = []
    dungeonIndex = 0
    for dungeon in DUNGEON_IDS:
        thisSpec = [spec[2] for spec in allDPS[className][dungeon]]        
        if len(useDungeon) == 0 or DUNGEON_NAMES[dungeonIndex] in useDungeon:
            useIndices = np.where(np.isin(thisSpec, useSpecs))
            classDPS[className].extend([float(i[0]) for i in np.array(allDPS[className][dungeon])[useIndices]])
        dungeonIndex += 1
        
    kde = scipy.stats.gaussian_kde(classDPS[className])
    x = np.linspace(min(classDPS[className]), max(classDPS[className]), 100)
    
    allSpecs.extend([spec[2] for spec in allDPS[className][dungeon]] )
    
    boxData.append(classDPS[className])
    meanData.append(np.median(classDPS[className]))
    
    distribution = kde(x)
        
    plt.plot(x, distribution, color=CLASS_COLORS[classIndex])
    
    classIndex += 1
plt.show()

sortClasses = np.argsort(meanData)
sortedBoxData = np.array(boxData)[sortClasses]
sortedColors = np.array(CLASS_COLORS)[sortClasses]
sortedLabels = np.array(CLASSES)[sortClasses]

bestClass = max(meanData)

scaledBoxData = []
for data in sortedBoxData:
    scaledBoxData.append(data / bestClass * 100)

boxPlot = plt.boxplot(scaledBoxData, vert=False, patch_artist=True, labels = sortedLabels, showfliers = False, whis=0)
index = 0
for patch in boxPlot['boxes']:
        patch.set_facecolor(sortedColors[index])
        index += 1
plt.xlim([0, plt.gca().get_xlim()[1]])
plt.show()