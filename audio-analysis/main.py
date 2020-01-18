import videoHelper
import pandas as pd
import sys
import lib.etl.dfHelper as dfHelper
import pymysql
from sqlalchemy import create_engine

# Pass `python main.py log` as optional arg to see print statements
TESTING = False
if len(sys.argv) == 2:
    if sys.argv[1] == 'log':
        TESTING = True #Define if you are testing or not. Make sure to check videoHelper.py for testing too

# analyzeVideoSound creates a video object and outputs all the nice analysis stuff ...
# inputs:
# url <- YouTube url of video to extract audio from
# tag <- True if video is highlight, else False
#
# outputs:
# Summary statistics wip ...

def analyzeVideoSound(url, tag):
    video = videoHelper.videoObject(url, tag, TESTING)
    print(video.getFilename())
    video.getAudio()
    video.getTextAnalysis()
    video.getAmplitudeAnalysis()

    if (TESTING):
        df1 = pd.DataFrame(video.word_list)
        # We do not need two end_time_s_x and end_time_s_y columns :)
        df2 = pd.DataFrame(video.amplitude_list).drop(columns=['end_time_s'])
        join_condition = ['start_time_s', 'url']
        # print(df1)
        # print(df2)
        df3 = dfHelper.customLeftJoin(df1, df2, join_condition)
        if (df3.shape[0] == df1.shape[0]):
            print('Join successful!')
        else:
            print('Join failed ... each word does not have an amplitude')
        print(df3)
        df3.to_csv("data_export.csv", header=True)

        engine = create_engine('mysql+pymysql://root:root@localhost/climactic_test')
        df3.to_sql("test_table", con=engine, if_exists='replace')


    

##### Prompt for Highlight Video and Tagging #####
answer = input("Option 1. single | Option 2. csv | Option 3. test \n")

#If user wants to upload only a single video
if answer == 'single' or answer == '1':
    url = input("Provide YT Link: ")
    tag = input("Provide highlight tag (True/False): ")
    print("Link: ", url)
    print("Tag: ", tag)
    analyzeVideoSound(url, tag)

#If user wants to upload only a CSV of videos
elif answer == 'csv' or answer == '2':
    inputCSV = input("Provide csv with file and path \n")
    tuplesDF = pd.read_csv(inputCSV)
    print(tuplesDF.head())
    i = 0
    while i < len(tuplesDF.index):
        print("\n For Video #", i+1, ":")
        url = tuplesDF.loc[i, 'YT_LINK']
        tag = tuplesDF.loc[i, 'H_TAG']
        print("Link: ", url, " | Tag: ", tag)
        analyzeVideoSound(url, tag)
        i += 1
        print("\n --------------------------------")

elif answer == 'test' or answer == '3':
    analyzeVideoSound("https://www.youtube.com/watch?v=JZRXESV3R74", True)