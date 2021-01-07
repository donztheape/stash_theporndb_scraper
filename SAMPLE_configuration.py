#Server configuration
use_https = True # Set to False for HTTP
server_ip= "<IP_ADDRESS>"  #Don't include the '<' or '>'
server_port = "<PORT>" #Don't include the '<' or '>'
username="<USERNAME>" #Don't include the '<' or '>'
password="<PASSWORD>" #Don't include the '<' or '>'
ignore_ssl_warnings= True # Set to True if your Stash uses SSL w/ a self-signed cert

qbit_username="" #Don't include the '<' or '>'
qbit_password="" #Don't include the '<' or '>'
qbit_ip= "http://localhost:6969/" # IP address of qbit web api
qbit_category="x" # category for qbittorrent, (in qbittorent set where to download files)
jacket_api_key="" # Jackett API key
jacket_api_url="127.0.0.1:9117" # API IP and port for Jackett (searches for torrents)
downloads_wanted_tags="oil, squirt" # tags to always add to the downloaded list. Downloads will get all of the favourites performers from stash plus search for these tags.
downloads_remove_tags="lesbian, lesx" # tags to always remove. if a search result matches something here then it will be removed from the download list
# performers_deep_download="Genevieve Sinn, Vanessa Sky, Sofie Reyez, Jesse Jane, Marsha May, assh lee, August Ames, Alexis Texas, Shyla Stylez, Kaisa Nord, Sophie Dee, Payton Preslee, Joslyn James, Kesha Ortega, Lana Rhoades, Monique Alexander, MJFresh, Lilly Hall, Mandy Muse, Osa Lovely, Gabriella Paltrova, Alexis Texas, Avery Black, Maya Bijou, Misha Cross, Janey Doe, Asa Akira,  Katya Rodriguez, Jessice Portman, Missy Martinez, Lisa Ann, Summer Brielle, Kiara Cole, Aliya Brynn, Valerie Steele, Dillion Harper, Savannah Sixx, Alexis Fawx, Brooklyn Gray, Kitty Carrera, Hime Marie, Liya Silver, Tiffany Watson, Cytherea, Aria Kai, Kendra Lust, Ariana Marie, Rose Monroe, Nicole Aniston, Joanna Angel, Savannah Bond, Jessa Rhodes, Ashley Adams, Ivy Lebelle, Skylar Vox, August Taylor, Lily Lane, Veronica Avluv, Bardot, Jillian Janson, Riley Reid, Kissa Sins, Madison Ivy, Diamond Jackson, Brandi Love, Bonnie Rotten, Katrina Jade, Honey Gold, Teanna Trump, Natalie Knight, Jessie Saint, Luna Star, Gabbie Carter, Jane Wilde, Angela White, Leigh Raven, Naomi Swann, Carmen Caliente, Nia Nacci, Janice Griffith, Kimmy Granger, Holly Hendrix, Eliza Ibarra, Mia Malkova, Chloe Couture" 
performers_deep_download="Bonnie Rotten, kira noir, Demi Sutra,Veronica Avluv, angela white, Lena Paul, Kenzie Reeves, Payton Preslee, Lilly Ford, Lilly Lit, Lily Lit, Lily Ford, Adira Allure, Kimmy Granger, Jill Kassidy, Chloe Cherry, Luna Star, Janice Griffith, Holly Hendrix, Scarlit Scandal, Leigh Raven"
# performers_deep_download="Karmen Karma"
# performers to download if -PDD parameter used
deep_download_limit=10
empty_search_try_limit=10

# Configuration options
scrape_tag= "Scraped From ThePornDB"  #Tag to be added to scraped scenes.  Set to None (without quotes) to disable
unmatched_tag = "Missing From ThePornDB" #Tag to be added to scenes that aren't matched at TPDB.  Set to None (without quotes)  to disable.
disambiguate_only = False # Set to True to run script only on scenes tagged due to ambiguous scraping. Useful for doing manual disambgiuation.  Must set ambiguous_tag for this to work
verify_aliases_only = False # Set to True to scrape only scenes that were skipped due to unconfirmed aliases - set confirm_questionable_aliases to True before using
rescrape_scenes= False # If False, script will not rescrape scenes previously scraped successfully.  Must set scrape_tag for this to work
retry_unmatched = False # If False, script will not rescrape scenes previously unmatched.  Must set unmatched_tag for this to work
debug_mode = False

#Set what fields we scrape
set_details = True
set_date = True
set_cover_image = True
set_performers = True
set_studio = True
set_tags = True
set_title = True
set_url = True

#Set what content we add to Stash, if found in ThePornDB but not in Stash
add_studio = True  
add_tags = False  # Script will still add scrape_tag and ambiguous_tag, if set.  Will also tag ambiguous performers if set to True.
add_performers = True 

#Disambiguation options
#The script tries to disambiguate using title, studio, and date (or just filename if parse_with_filename is True).  If this combo still returns more than one result, these options are used.  Set both to False to skip scenes with ambiguous results
auto_disambiguate = False  #Set to True to try to pick the top result from ThePornDB automatically.  Will not set ambiguous_tag
manual_disambiguate = False #Set to True to prompt for a selection.  (Overwritten by auto_disambiguate)
ambiguous_tag = "ThePornDB Ambiguous" #Tag to be added to scenes we skip due to ambiguous scraping.  Set to None (without quotes) to disable
#Disambiguation options for when a specific performer can't be verified
tag_ambiguous_performers = True  # If True, will tag ambiguous performers (performers listed on ThePornDB only for a single site, not across sites)
confirm_questionable_aliases = True #If True, when TPBD lists an alias that we can't verify, manually prompt for config.  Otherwise they are tagged for later reprocessing
trust_tpbd_aliases = True #If True, when TPBD lists an alias that we can't verify, just trust TBPD to be correct.  May lead to incorrect tagging

#Other config options
parse_with_filename = True # If True, will query ThePornDB based on file name, rather than title, studio, and date
dirs_in_query = 0 # The number of directories up the path to be included in the query for a filename parse query.  For example, if the file  is at \performer\mysite\video.mp4 and dirs_in_query is 1, query would be "mysite video."  If set to two, query would be "performer mysite video", etc.
only_add_female_performers = True  #If True, only female performers are added (note, exception is made if performer name is already in title and name is found on ThePornDB)
scrape_performers_freeones = True #If True, will try to scrape newly added performers with the freeones scraper
get_images_babepedia = True #If True, will try to grab an image from babepedia before the one from ThePornDB
include_performers_in_title = True #If True, performers will be added at the beggining of the title
clean_filename = True #If True, will try to clean up filenames before attempting scrape. Often unnecessary, as ThePornDB already does this
compact_studio_names = True # If True, this will remove spaces from studio names added from ThePornDB
proxies={} # Leave empty or specify proxy like this: {'http':'http://user:pass@10.10.10.10:8000','https':'https://user:pass@10.10.10.10:8000'}
