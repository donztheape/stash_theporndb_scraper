#!/usr/bin/python3

###########################################
### NZBGET POST-PROCESSING SCRIPT       ###

# A simple script to ask Stash to scan for new content, initiate a scrape from TPDB, and run a generate task for the new content.
# Note that your NZBGet system must have the requirements for the scrapeScenes.py script, so run pip install -r requirements.txt on that system before running.
# Filetype is ".py3" so that NZBGet can be forced to use python3 to execute, as python2 is the default on most systems. If the "python" command runs python3 on your NZBGet system, change the extension to ".py".  Otherwise, ou may need to set the ShellOveride field in the ExtensionScripts section of your NZBGet config to include ".py3=/usr/bin/python3" (or whatever your path to python3 is) to force use of python3.

### NZBGET POST-PROCESSING SCRIPT       ###
###########################################


import sys
import os
import StashInterface
import scrapeScenes
import time


# Exit codes used by NZBGet
POSTPROCESS_SUCCESS=93
POSTPROCESS_NONE=95
POSTPROCESS_ERROR=94


#Check par and unpack status for errors
#if os.environ['NZBPP_PARSTATUS'] == '1' or os.environ['NZBPP_PARSTATUS'] == '4' or os.environ['NZBPP_UNPACKSTATUS'] == '1':
    #print('[WARNING] Download of "%s" has failed, exiting' % (os.environ['NZBPP_NZBNAME']))
   # sys.exit(POSTPROCESS_NONE)
#
scrapeScenes.main(['-no'])
# StashInterface.main(['-s','-w'])
# time.sleep(30)
# scrapeScenes.main(['-no'])
StashInterface.main(["-d"]) # Gets favourites performers in Stash and checks if there are any recent torrents matching them
StashInterface.main(['-g'])
StashInterface.main(["-at"])
# StashInterface.main(["-dd"]) # Does deep download (searches favourites performers and tries to download up to the deep_download_limit - not just recent torrents))
# StashInterface.main(["-pdd"]) #  Does deep download but for a list of performers in performers_deep_download (searches favourites performers and tries to download up to the deep_download_limit - not just recent torrents)) 
# StashInterface.main(["-pairdd"]) # Downloads torrents that have scenes matching two or more favourites performers (looking for matching pairs)
# StashInterface.main(["-pairpdd"]) # Downloads torrents that have scenes matching two or more performers from the list performers_deep_download(looking for matching pairs)


# StashInterface.main(["-pdd"])
sys.exit(POSTPROCESS_SUCCESS)
