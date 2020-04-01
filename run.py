import sys
import pandas as pd
import services.videoDownloader as videoDownloader
import services.createIntervals as intervalCreator
import services.mfccExtractor as mfccExtractor
import services.ampExtractor as ampExtractor
import services.speech2text as speech2text
import services.pitchExtractor as pitchExtractor
import services.runModels as runModels
import services.excitementClassifier as exciteModel
import services.postProcessing as postProcessing
import helpers.librosaHelper as librosaHelper
import helpers.dbHelper as dbHelper

# This is the commander, it will string together all the services 
# INPUT: youtube url
# USAGE: python run.py [youtube url]

# Get YT url
vidUrl = sys.argv[1]

# Testing flag ... will not update db if PROD = FALSE
PROD = False
if len(sys.argv) > 2:
  if sys.argv[2] == 'prod':
    PROD = True
# python run.py test -> runs the Trump video and NOT write to db
if sys.argv[1] == 'test':
  # Trump video url
  vidUrl = 'https://www.youtube.com/watch?v=JZRXESV3R74'

# If no url provided exit
if not vidUrl:
  print('Please enter a youtube video url')
  exit()

# get video id, we will use the video id as the name for all files generated
vidId = vidUrl.replace('https://www.youtube.com/watch?v=', '')

# Download youtube video
videoPath = videoDownloader.getVideoPath(vidId)
videoDownloader.downloadVid(vidUrl, vidId)

# Save audio
audioPath = videoDownloader.getAudioPath(vidId)
videoDownloader.writeAudio(vidId)

# Get the length of the video
vidDuration = int(videoDownloader.getVideoDuration(videoPath))

# # Create 4 second intervals
INTERVAL_LENGTH = 4
OVERLAP_LENGTH = 2

# Get intervals -> [[start, end], [start, end]]
intervals = intervalCreator.getIntervals(vidDuration, INTERVAL_LENGTH, OVERLAP_LENGTH)
# insert intervals into db
intervalCreator.insertIntervals(vidUrl, intervals)

# Generate and save as librosa
print("Generating librosa")
librosaPath = librosaHelper.getLibrosaPath(vidId)

if not librosaHelper.librosaExists(librosaPath):
  audio, sampleRate = librosaHelper.createLibrosa(audioPath)
  librosaHelper.saveLibrosa(audio, sampleRate, librosaPath)

# Feature extraction
print("Extracting Features...")
# Retrieve db rows and store as a dataframe
df = dbHelper.getRowsAsDf("SELECT * from clips where url = '{:}' ORDER BY start ASC".format(vidUrl))
# Drop null columns with features to be populated
feature_list = ['mfcc', 'amplitude', 'pitch', 'word', 'subjectivity', 'polarity', 'pred_excitement', 'pred_highlight_rf', 'pred_highlight_nn']
df.drop(columns=feature_list, axis=1, inplace=True)

# Feature extraction: add video title
df['video_title'] = videoDownloader.getVideoTitle(vidUrl)
print(videoDownloader.getVideoTitle(vidUrl))

# Feature extraction: mfcc values
print("Extracting mfcc...")
mfccVals = mfccExtractor.getMfcc(librosaPath, intervals)
df['mfcc'] = mfccVals

# Feature extraction: amp values
print("Extracting amplitudes...")
ampVals = ampExtractor.getAmp(librosaPath, intervals)
df['amplitude'] = ampVals

# Feature extraction: pitch values
print("Extracting pitches...")
pitchVals = pitchExtractor.getPitch(audioPath, intervals)
df['pitch'] = pitchVals

# Feature extraction: speech to text
print("Extracting speech 2 text data...")
speech2text_df = speech2text.getText(audioPath, intervals)
df = pd.concat([df, speech2text_df], axis=1)

# Feature extraction: Run predicted excitement model
print("Classifying commentator excitement...")
predExcitement = exciteModel.predictExcitement(df['mfcc'].tolist())
df['pred_excitement'] = predExcitement

# Run our highlight models
print("Running our Models")
features_df = df[['pitch', 'amplitude', 'subjectivity', 'polarity', 'pred_excitement']]
print("Running Random Forest..")
rf_predictions = runModels.getRandomForestPredictions(features_df)
print(rf_predictions)
df['pred_highlight_rf'] = rf_predictions

print("Running Neural Network..")
nn_predictions = runModels.getNeuralNetworkPredictions(features_df)
df['pred_highlight_nn'] = nn_predictions

# Run Post Processing (this saves highlight-timestamps arrays to the datastore)
highlight_pred_df = df[['start', 'end', 'pred_highlight_rf', 'pred_highlight_nn']]
postProcessing.getHighlightTimestamps(highlight_pred_df, vidId)

print(df)

# Write the new features to db
if PROD:
  for feature in feature_list:
    print('sending {} to db ...'.format(feature))
    dbHelper.updateColumn(df, feature)
