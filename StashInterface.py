from datetime import datetime
import requests
import logging
import sys
import time
import base64
import math
import re
import argparse
import json
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from qbittorrent import Client
import numpy as np
from six.moves import cPickle as pickle
from configuration import empty_search_try_limit

#Utility Functions
def lreplace(pattern, sub, string):
    """
    Replaces 'pattern' in 'string' with 'sub' if 'pattern' starts 'string'.
    """
    return re.sub('^%s' % pattern, sub, string)

def scrubFileName(file_name):
    scrubbedWords = ['MP4-(.+?)$', ' XXX ', '1080p', '720p', 'WMV-(.+?)$', '-UNKNOWN', ' x264-(.+?)$', 'DVDRip','WEBRIP', 'WEB', '\[PRiVATE\]', 'HEVC', 'x265', 'PRT-xpost', '-xpost', '480p', ' SD', ' HD', '\'', '&']
    clean_name = ""
    clean_name = re.sub('\.', ' ', file_name) ##replace periods
    for word in scrubbedWords: ##delete scrubbedWords
        clean_name = re.sub(word,'',clean_name,0,re.IGNORECASE)
    clean_name = clean_name.strip() #trim
    return clean_name

def keyIsSet(json_object, fields):  #checks if field exists for json_object.  If "fields" is a list, drills down through a tree defined by the list
    if json_object:
        if isinstance(fields, list):
            for field in fields:
                if field in json_object and json_object[field] != None:
                    json_object = json_object[field]
                else:
                    return False
            return True
        else:
            if fields in json_object and json_object[fields] != None:
                return True
    return False

def listToLower(input_list):
    output_list = []
    for item in input_list:
        if isinstance(item, str):
            output_list.append(item.lower())
        else:
            output_list.append(item)
    return output_list

# Save
def saveDictionaryToFile(dictionary, file_name):
    file_name_numpy = file_name + ".npy"
    np.save(file_name_numpy, dictionary) 

# Load
def loadDictionaryFromFile(file_name):
    file_name_numpy = file_name + ".npy"
    try:
        read_dictionary = np.load(file_name_numpy,allow_pickle='TRUE').item()
    except:
        read_dictionary = {}
    return read_dictionary

def save_dict(di_, filename_):
    with open(filename_, 'wb') as f:
        pickle.dump(di_, f)

def load_dict(filename_):
    with open(filename_, 'rb') as f:
        ret_di = pickle.load(f)
    return ret_di

#Stash GraphQL Class
class stash_interface:
    performers = []
    studios = []
    tags = []
    server = ""
    username = ""
    password = ""
    ignore_ssl_warnings = ""
    http_auth_type = ""
    auth_token = ""
    proxies = {}
    min_buildtime = datetime(2020, 6, 22) 
    qbit_username = ""
    qbit_password = ""
    qbit_ip = ""
    qbit_category = ""
    jacket_api_key = ""
    jacket_api_url = ""

    headers = {
        "Accept-Encoding": "gzip, deflate, br",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Connection": "keep-alive",
        "DNT": "1"
        }

    def __init__(self, server_url, user = "", pword = "", ignore_ssl = "", qbit_ip = "", qbit_username="", qbit_password = "", qbit_category="", jacket_api_key="", jacket_api_url="", downloads_wanted_tags="", downloads_remove_tags ="", performers_deep_download="", deep_download_limit=10, debug = False):
        self.server = server_url
        self.username = user
        self.password = pword
        self.ignore_ssl_warnings = ignore_ssl
        if ignore_ssl: requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
        self.debug_mode = debug
        self.qbit_username = qbit_username
        self.qbit_password = qbit_password
        self.qbit_ip = qbit_ip
        self.qbit_category = qbit_category
        self.jacket_api_key = jacket_api_key
        self.jacket_api_url = jacket_api_url
        self.downloads_wanted_tags = [x.strip() for x in downloads_wanted_tags.split(",")]
        self.downloads_remove_tags = [x.strip() for x in downloads_remove_tags.split(",")]
        self.performers_deep_download = [x.strip() for x in performers_deep_download.split(",")]
        self.deep_download_limit = deep_download_limit
        self.setAuth()
        self.checkVersion()
        self.populatePerformers()
        self.populateTags()
        self.populateStudios()

    def setProxies(self, proxies):
        self.proxies = proxies

    def setAuth(self):
        r = requests.get(self.server+"/playground", verify= not self.ignore_ssl_warnings)
        if len(r.history)>0 and r.history[-1].status_code == 302:
            self.http_auth_type="jwt"
            self.jwtAuth()
        elif r.status_code == 200:
            self.http_auth_type="none"
        else:
            self.http_auth_type="basic"
        return

    def jwtAuth(self):
        response = requests.post(self.server+"/login", data = {'username':self.username, 'password':self.password}, verify= not self.ignore_ssl_warnings)
        self.auth_token=response.cookies.get('session',None)
        if not self.auth_token:
            logging.error("Error authenticating with Stash.  Double check your IP, Port, Username, and Password", exc_info=self.debug_mode)
            sys.exit()
    
    #GraphQL Functions    
    def callGraphQL(self, query, variables = None):
        if "mutation" in query: self.waitForIdle() #Check that the DB is not locked
        return self.__callGraphQL(query, variables)

    def __callGraphQL(self, query, variables, retry = True):
        graphql_server = self.server+"/graphql"
        json = {}
        json['query'] = query
        if variables:
            json['variables'] = variables
        
        try:
            if self.http_auth_type == "basic":
                response = requests.post(graphql_server, json=json, headers=self.headers, auth=(self.username, self.password), verify= not self.ignore_ssl_warnings)
            elif self.http_auth_type == "jwt":
                response = requests.post(graphql_server, json=json, headers=self.headers, cookies={'session':self.auth_token}, verify= not self.ignore_ssl_warnings)
            else:
                response = requests.post(graphql_server, json=json, headers=self.headers, verify= not self.ignore_ssl_warnings)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("error", None):
                    for error in result["error"]["errors"]:
                        logging.error("GraphQL error:  {}".format(error), exc_info=self.debug_mode)
                if result.get("data", None):
                    return result
            elif retry and response.status_code == 401 and self.http_auth_type == "jwt":
                self.jwtAuth()
                return self.__callGraphQL(query, variables, False)
            else:
                logging.error("GraphQL query failed to run by returning code of {}. Query: {}.  Variables: {}".format(response.status_code, query, variables), exc_info=self.debug_mode)
                raise Exception("GraphQL error")
        except requests.exceptions.SSLError:
            proceed = input("Caught certificate error trying to talk to Stash. Add ignore_ssl_warnings=True to your configuration.py to ignore permanently. Ignore for now? (yes/no):")
            if proceed == 'y' or proceed == 'Y' or proceed =='Yes' or proceed =='yes':
                self.ignore_ssl_warnings =True
                requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
                return self.callGraphQL(query, variables)
            else:
                print("Exiting.")
                sys.exit()

    def waitForIdle(self):
        jobStatus = self.getStatus()
        if jobStatus['status']!="Idle":  #Check that the DB is not locked
            print("Stash is busy.  Retrying in 10 seconds.  Status:"+jobStatus['status']+"; Progress:"+'{:.0%}'.format(jobStatus['progress']))
            time.sleep(10)
            self.waitForIdle()
    
    def getStatus(self): 
        query = """
    {
    jobStatus{
      progress
      status
      message
      }
    }
    """
        result = self.callGraphQL(query)
        return result["data"]["jobStatus"]

    def scan(self, useFileMetadata = False): 
        if useFileMetadata:
            variables = {'input': {"useFileMetadata":True,"scanGeneratePreviews":False,"scanGenerateImagePreviews":False,"scanGenerateSprites":False}}
            
        else:
            variables = {'input': {"useFileMetadata":False,"scanGeneratePreviews":False,"scanGenerateImagePreviews":False,"scanGenerateSprites":False}}
        query = """
        mutation metadataScan($input:ScanMetadataInput!) {
            metadataScan(input: $input)
        }
        """
        result = self.callGraphQL(query, variables)
    
    def clean(self): 
        query = """
            mutation metadataClean{
                metadataClean
            }
        """
        result = self.callGraphQL(query)

    def generate(self, generateInput = None): 
        if generateInput:
            variables = generateInput
        else:
            variables = {'input': { 
                'sprites': True,
                'previews': True,
                'imagePreviews': False,
                'markers': True,
                'transcodes': False
                #'thumbnails': False
                }}
        
        query = """
            mutation metadataGenerate($input:GenerateMetadataInput!) {
                metadataGenerate(input: $input)
            }
        """
        result = self.callGraphQL(query, variables)

    def get_performers(self, performerInput=None):
        if performerInput:
            variables = performerInput
        else:
            variables = {
                "filter": {
                    "page": 1,
                    "per_page": 120,
                    "sort": "scenes_count",
                    "direction": "ASC",
                },
                "performer_filter": {"filter_favorites": True},
            }

        query = """
            query FindPerformers($filter: FindFilterType, $performer_filter: PerformerFilterType) {\n  findPerformers(filter: $filter, performer_filter: $performer_filter) {\n    count\n    performers {\n      ...PerformerData\n      __typename\n    }\n    __typename\n  }\n}\n\nfragment PerformerData on Performer {\n  id\n  checksum\n  name\n  url\n  gender\n  twitter\n  instagram\n  birthdate\n  ethnicity\n  country\n  eye_color\n  height\n  measurements\n  fake_tits\n  career_length\n  tattoos\n  piercings\n  aliases\n  favorite\n  image_path\n  scene_count\n  __typename\n}\n
        """
        result = self.callGraphQL(query, variables)
        return result["data"]["findPerformers"]["performers"]

    def qbit_api(self, username, password):
        # qb = Client("localhost:9120")
        qb = Client(self.qbit_ip)
        qb.login(username, password)
        return qb

    def download(self, deep_search = False, performer_pair_mode = False, search_list = []):
        try:
            performers = self.get_performers()
            keep_list, remove_list = self.get_keep_list(performers, deep_search=deep_search, search_list=search_list)
            results = {}
            if deep_search:
                if (len(search_list) > 0):
                    for search_term in search_list:
                        if performer_pair_mode:
                            new_results = self.get_search_results(keep_list, remove_list, search_term, search_list)
                            self.download_to_torrent(new_results)
                        else:
                            new_results = self.get_search_results(keep_list, remove_list, search_term)
                            self.download_to_torrent(new_results)
                else:
                    for search_term in keep_list:
                        if performer_pair_mode:
                            new_results = self.get_search_results(keep_list, remove_list, search_term, keep_list)
                            self.download_to_torrent(new_results)
                        else:
                            new_results = self.get_search_results(keep_list, remove_list, search_term)
                            self.download_to_torrent(new_results)
            else:
                results = self.get_search_results(keep_list, remove_list)
                self.download_to_torrent(results)
        except Exception as e:
            print('Exception: ' + str(e))

    def download_to_torrent(self, results):
        api = self.qbit_api(self.qbit_username, self.qbit_password)
        for result in results:
            try:
                print("Downloading: " + result)
                api.download_from_link(results[result], category=self.qbit_catagory)
            except Exception as e:
                print(e)

    def get_keep_list(self, performers, deep_search= False, search_list=[]):
        try:
            keep_list = []
            remove_list = []

            # always add tags to remove 
            remove_list.extend(self.downloads_remove_tags)

            if (len(search_list) > 0):
                return search_list, remove_list

            for performer in performers:
                if deep_search:
                    if int(performer["scene_count"]) < 10:
                        keep_list.append(performer["name"])
                        if performer['aliases'] is not None:
                            aliases = performer['aliases'].split(',')
                            for alias in aliases:
                                if (len(alias.strip().split(" ")) > 1): # only add if more than one word
                                    keep_list.append(alias.strip())
                else:
                    keep_list.append(performer["name"])
                    if performer['aliases'] is not None:
                        aliases = performer['aliases'].split(',')
                        for alias in aliases:
                            if (len(alias.strip().split(" ")) > 1): # only add if more than one word
                                keep_list.append(alias.strip())

            if deep_search:
                return keep_list, remove_list

            # Add tags to download
            keep_list.extend(self.downloads_wanted_tags)

            return keep_list, remove_list
        except Exception as e:
            print('Exception: ' + str(e))

    def get_search_results(self, keep_list, remove_list, query=None, paired_performers = [], date=None):
        search_string = "1080p "
        if query is not None:
            search_string = search_string + query + " "
        if date is not None:
            search_string = search_string + query + " "
            y = str(date.year)[2:]
            m = str(date.month)
            if len(m) == 1:
                m = "0" + m
            d = str(date.day)
            if len(d) == 1:
                d = "0" + d
            search_string = search_string + " " + y + " " + m + " " + d

        results_to_keep = []
        params = (
            ("apikey", self.jacket_api_key),
            ("Query", search_string),
            ("Category[]", ["6000", "100004"]),
            ("Tracker[]", "rarbg"),
            ("_", "1599256674666"),
        )

        tries = 0
        results = []
        while tries < empty_search_try_limit and len(results) == 0:
            jacket_url = "http://" + self.jacket_api_url + "/api/v2.0/indexers/all/results"
            response = requests.get(
                    jacket_url, params=params
                )

            response.raise_for_status()
            # access JSOn content
            jsonResponse = response.json()
            results = jsonResponse["Results"]
            tries = tries + 1
            if tries == empty_search_try_limit:
                print("max search tries hit for: " + search_string)

        if len(paired_performers) > 0:
            # Look for scenes with two matching performers within
            for result in results:
                    keep_this_result = False
                    for performer in paired_performers:
                        if performer != query:
                            if result["Title"].lower().__contains__(performer.lower().replace(" ", ".")):
                                keep_this_result = True
                                print('Adding to DL list:   ' + result["Title"] + 'Because of keep keyword:   ' + performer)
                            elif result["Title"].lower().__contains__(performer.lower()):
                                keep_this_result = True
                                print('Adding to DL list:   ' + result["Title"] + 'Because of keep keyword:   ' + performer)
                    if keep_this_result:
                        results_to_keep.append(result)
        else:
            for result in results:
                keep_this_result = False
                # print(result.filename)
                for keep in keep_list:
                    if result["Title"].lower().__contains__(keep.lower().replace(" ", ".")):
                        keep_this_result = True
                        print('Adding to DL list:   ' + result["Title"] + 'Because of keep keyword:   ' + keep)
                    elif result["Title"].lower().__contains__(keep.lower()):
                        keep_this_result = True
                        print('Adding to DL list:   ' + result["Title"] + 'Because of keep keyword:   ' + keep)
                if keep_this_result:
                    results_to_keep.append(result)


        final_keep_list = []

        for result in results_to_keep:
            # print(result.filename)
            keep = True
            for remove in remove_list:
                if result["Title"].lower().__contains__(remove.lower().replace(" ", ".")):
                    keep = False
                    print('Removing from DL list:   ' + result["Title"] + 'Because of remove keyword:   ' + remove)
                elif result["Title"].lower().__contains__(remove.lower()):
                    keep = False
                    print('Removing from DL list:   ' + result["Title"] + 'Because of remove keyword:   ' + remove)
            if keep:
                # Check if we already have this file
                findScenes_params = {}
                findScenes_params['filter'] = {'q':result['Title'][:-10], 'sort':"created_at", 'direction':'DESC'}
                findScenes_params['scene_filter'] = {}
                matching_scenes = self.findScenes(**findScenes_params)
                if (len(matching_scenes) == 0):
                    final_keep_list.append(result)

        if query:
            final_keep_list.sort(key=lambda x: x['Seeders'], reverse=True)
            final_keep_list = final_keep_list[:self.deep_download_limit]

        result_dict = {}
        for result in final_keep_list:
            result_dict[result["Title"]] = result["MagnetUri"]
            # result_dict[result["MagnetUri"]] = result["Title"]

        return result_dict

    def autoTag(self, autoTagInput= None):
        if autoTagInput:
            variables = autoTagInput
        else:
            variables = {'input': { 
                'performers': ['*'],
                'studios': ['*'],
                'tags': ['*']
                }}

        query = """
            mutation metadataAutoTag($input:AutoTagMetadataInput!) {
                metadataAutoTag(input: $input)
            }
        """
        result = self.callGraphQL(query, variables)

    def checkVersion(self):
        query = """
    {
    version{
        version
        build_time
        }
    }
    """
        result = self.callGraphQL(query)
        self.version_buildtime = datetime.strptime(result["data"]["version"]["build_time"], '%Y-%m-%d %H:%M:%S')
        if self.version_buildtime < stash_interface.min_buildtime:
            logging.error("Your Stash version appears too low to use this script.  Please upgrade to the latest \"development\" build and try again.", exc_info=self.debug_mode)
            sys.exit()

    def populatePerformers(self):  
        stashPerformers =[]
        query = """
    {
        allPerformers
      {
        id
        name
        aliases
        image_path
      }
    }
    """
        result = self.callGraphQL(query)
        stashPerformers = result["data"]["allPerformers"]
        for performer in stashPerformers:
            if isinstance(performer['aliases'], str): performer['aliases'] = [alias.strip() for alias in performer['aliases'].split(',')] #Convert comma delimited string to list
        
        self.performers = stashPerformers

    def populateStudios(self):
        stashStudios = []
        query = """
    {
        allStudios
      {
        id
        name
        url
        image_path
      }
    }
    """ 
        result = self.callGraphQL(query)
        self.studios = result["data"]["allStudios"]

    def populateTags(self):
        stashTags = []
        query = """
    {
        allTags
      {
        id
        name
      }
    }
    """
        result = self.callGraphQL(query)
        self.tags = result["data"]["allTags"]  

    def findScenes(self, **kwargs):
        stashScenes =[]
        variables = {}
        max_scenes = kwargs.get("max_scenes", None)
        accepted_variables = {'filter':'FindFilterType!','scene_filter': 'SceneFilterType!','scene_ids':'[Int!]'}

        variables['filter'] = {} #Add filter to support pages, if necessary
                
        #Add accepted variables to our passsed variables
        for index, (accepted_variable, variable_type) in enumerate(accepted_variables.items()):
            if accepted_variable in kwargs:
                variables[accepted_variable] = kwargs[accepted_variable]

        #Set page and per_page, if not set
        variables['filter'] = variables.get('filter', {})
        variables['filter']['page'] = variables['filter'].get('page', 1)
        if max_scenes:
            variables['filter']['per_page'] = variables['filter'].get('per_page',  min(100, max_scenes))
        else:
            variables['filter']['per_page'] = variables['filter'].get('per_page',  100)
            
        #Build our query string (e.g., "findScenes(filter:FindFilterType!){" )
        query_string = "query("+", ".join(":".join(("$"+str(k),accepted_variables[k])) for k,v in variables.items())+'){'

        #Build our findScenes string
        findScenes_string = "findScenes("+", ".join(":".join((str(k),"$"+str(k))) for k,v in variables.items())+'){'

        try:
            query = query_string+findScenes_string+"""
                count
                scenes{
                  id
                  title
                  oshash
                  details
                  url
                  date
                  rating
                  path
                  studio {
                    id
                    name
                    }
                  gallery
                    {
                        id
                    }
                  movies
                    {
                        movie 
                        {
                            id
                        }
                    scene_index
                    }
                  performers
                    {
                        name
                        id
                    }
                  tags
                    {
                        name
                        id
                    }
                }
              }
            }
            """
            result = self.callGraphQL(query, variables)

            stashScenes = result["data"]["findScenes"]["scenes"]
            if not max_scenes: max_scenes = result["data"]["findScenes"]["count"]
            total_pages = math.ceil(max_scenes / variables['filter']['per_page'])
            # print("Getting Stash Scenes Page: "+str(variables['filter']['page'])+" of "+str(total_pages))
            if (variables['filter']['page'] < total_pages and len(stashScenes)<max_scenes):  #If we're not at the last page or max_scenes, recurse with page +1 
                variables['filter']['page'] = variables['filter']['page']+1
                stashScenes = stashScenes+self.findScenes(**variables)

        except:
            logging.error("Unexpected error getting stash scene:", exc_info=self.debug_mode)
            
        return stashScenes  
        
    def updateSceneData(self, scene_data):
        query = """
    mutation sceneUpdate($input:SceneUpdateInput!) {
      sceneUpdate(input: $input){
        title
      }
    }
    """

        variables = {'input': scene_data}
        result = self.callGraphQL(query, variables)
        
    def addPerformer(self, performer_data):
        result = None
        update_data = performer_data
        if update_data.get('aliases', None):
            update_data['aliases'] = ', '.join(update_data['aliases'])
        
        query = """
    mutation performerCreate($input:PerformerCreateInput!) {
      performerCreate(input: $input){
        id 
      }
    }
    """
        variables = {'input': update_data}
        
        try:
            result = self.callGraphQL(query, variables)
            self.populatePerformers()
            return result["data"]["performerCreate"]["id"]

        except:
            logging.error("Error in adding performer", exc_info=self.debug_mode)
            logging.error(variables)
            logging.error(result)

    def getPerformerImage(self, url):  #UNTESTED
        if self.http_auth_type == "basic":
            return base64.b64encode(requests.get(url,proxies=self.proxies, auth=requests.auth.HTTPBasicAuth(self.username, self.password), 
                                verify= not self.ignore_ssl_warnings).content)
        elif self.http_auth_type == "jwt":
            return base64.b64encode(requests.get(url,proxies=self.proxies, headers=self.headers, cookies={'session':self.auth_token}, verify= not self.ignore_ssl_warnings).content)
        else:
            return base64.b64encode(requests.get(url,proxies=self.proxies, verify= not self.ignore_ssl_warnings).content)        
        
    def addStudio(self, studio_data):
        query = """
        mutation studioCreate($input:StudioCreateInput!) {
          studioCreate(input: $input){
            id       
          }
        }
        """

        variables = {'input': studio_data}
        try:
            result = self.callGraphQL(query, variables)
            self.populateStudios()
            return result["data"]["studioCreate"]["id"]
        except Exception as e:
            logging.error("Error in adding studio:", exc_info=self.debug_mode)
            logging.error(variables)

    def addTag(self, tag_data):
        query = """
        mutation tagCreate($input:TagCreateInput!) {
          tagCreate(input: $input){
            id       
          }
        }
        """
        variables = {'input': tag_data}

        try:
            result = self.callGraphQL(query, variables)
            self.populateTags()
            return result["data"]["tagCreate"]["id"]
        except Exception as e:
            logging.error("Error in adding tags", exc_info=self.debug_mode)
            logging.error(variables)
    
    def deleteTagByName(self, name):
        tag_data = {}
        tag_data['id'] = self.getTagByName(name)
        if tag_data['id']:
            return deleteTag(tag_data)
        return False
    
    def deleteTagByID(self, id):
        tag_data = {}
        tag_data['id'] = id
        if tag_data['id']:
            return deleteTag(tag_data)
        return False

    def deleteTag(self, input_tag_data):  
        tag_data = {}
        tag_data["id"] = input_tag_data["id"]
        
        query = """
        mutation tagDestroy($input:TagDestroyInput!) {
          tagDestroy(input: $input)
        }
        """
        variables = {'input': tag_data}

        try:
            result = self.callGraphQL(query, variables)
            self.populateTags()
            return result["data"]["tagDestroy"]
        except Exception as e:
            logging.error("Error in deleting tag", exc_info=self.debug_mode)
            logging.error(variables)
    
    def deletePerformer(self, input_data):  
        performer_data = {}
        performer_data["id"] = input_data["id"]
        
        query = """
        mutation performerDestroy($input:PerformerDestroyInput!) {
          performerDestroy(input: $input)
        }
        """
        variables = {'input': performer_data}

        try:
            result = self.callGraphQL(query, variables)
            self.populateTags()
            return result["data"]["performerDestroy"]
        except Exception as e:
            logging.error("Error in deleting performer", exc_info=self.debug_mode)
            logging.error(variables)
    
    def deleteScene(self, input_data, delete_file = False):  
        scene_data = {}
        scene_data["id"] = input_data["id"]
        scene_data['delete_file']=delete_file
        scene_data['delete_generated']=True
        
        query = """
        mutation sceneDestroy($input:SceneDestroyInput!) {
          sceneDestroy(input: $input)
        }
        """
        variables = {'input': scene_data}

        try:
            result = self.callGraphQL(query, variables)
            self.populateTags()
            return result["data"]["sceneDestroy"]
        except Exception as e:
            logging.error("Error in deleting scene", exc_info=self.debug_mode)
            logging.error(variables)

    def updatePerformer(self, performer_data):
        update_data = performer_data
        if update_data.get('aliases', None):
            update_data['aliases'] = ', '.join(update_data['aliases'])
        if update_data.get('image_path', None):
            update_data.pop('image_path',None)

        query = """
    mutation performerUpdate($input:PerformerUpdateInput!) {
      performerUpdate(input: $input){
        id
        name
        aliases
        image_path 
      }
    }
    """
        variables = {'input': update_data}
        result = self.callGraphQL(query, variables)
        return result["data"]["performerUpdate"]

    
    def scrapePerformerFreeones(self, name):
        query = """   
        {
        scrapePerformerList(scraper_id:"builtin_freeones", query:\""""+name+"""\")
        { name url twitter instagram birthdate ethnicity country eye_color height measurements fake_tits career_length tattoos piercings aliases }
        }"""
        result = self.callGraphQL(query)
        try:
            if len(result['data']["scrapePerformerList"])!=0:
                query = """   
                query ScrapePerformer($scraped_performer: ScrapedPerformerInput!){
                    scrapePerformer(scraper_id:"builtin_freeones", scraped_performer: $scraped_performer)
                    { url twitter instagram birthdate ethnicity country eye_color height measurements fake_tits career_length tattoos piercings aliases }
                }"""
                variables = {'scraped_performer': result['data']['scrapePerformerList'][0]}
                result = self.callGraphQL(query, variables)
                if keyIsSet(result['data'], ['scrapePerformer', 'aliases']):
                    result["data"]["scrapePerformer"]['aliases'] = [alias.strip() for alias in result["data"]["scrapePerformer"]['aliases'].split(',')]
                return result["data"]["scrapePerformer"]
            else:
                return None
        except Exception as e:
            logging.error("Error in scraping Freeones", exc_info=self.debug_mode)
            logging.error(variables)
        
    def __getPerformerByName(self, name, check_aliases = False):  # A private function that allows disabling of checking for aliases
        
        for performer in self.performers:
            if performer['name'].lower() == name: # Check input name against performer name
                return performer
            elif check_aliases and keyIsSet(performer, "aliases"):  # Check input name against performer aliases
                performer_aliases_lower = listToLower(performer["aliases"])
                if name in performer_aliases_lower:
                    return performer
    
    def getPerformerByName(self, name, aliases = []):
        name = name.lower()
        input_aliases_lower = listToLower(aliases)
        
        result = self.__getPerformerByName(name, True)
        if result:  # This matches input name with existing name or alias 
            return result
        
        for input_alias in input_aliases_lower: # For each alias, recurse w/ name = alias, but disable alias to alias mapping
            result = self.__getPerformerByName(input_alias, False)
            if result:
                return result
        
        return None            

    def getStudioByName(self, name):
        for studio in self.studios:
            if studio['name'].lower().strip() == name.lower().strip():
                return studio
        return None
    
    def getTagByName(self, name, add_tag_if_missing = False):
        logging.debug("Getting tag id for tag \'"+name+"\'.")
        search_name = name.lower().replace('-', ' ').replace('(', '').replace(')', '').strip().replace(' ', '')
        for tag in self.tags:
            if search_name == tag['name'].lower().replace('-', ' ').replace('(', '').replace(')', '').strip().replace(' ', ''):
                logging.debug("Found the tag.  ID is "+tag['id'])
                return tag
        
        # Add the Tag to Stash
        if add_tag_if_missing:
            stash_tag = {}
            stash_tag["name"] = name
            print("Did not find " + name + " in Stash.  Adding Tag.")
            self.addTag(stash_tag)
            return self.getTagByName(name)

        return None

    def createSceneUpdateData(self, scene_data):  #Scene data returned from stash has a different format than what is accepted by the UpdateScene graphQL query.  This converts one format to another
        scene_update_data = {}
        if keyIsSet(scene_data, "id"): scene_update_data["id"] = scene_data["id"]
        if keyIsSet(scene_data, "title"): scene_update_data["title"] = scene_data["title"]
        if keyIsSet(scene_data, "details"): scene_update_data["details"] = scene_data["details"]
        if keyIsSet(scene_data, "url"): scene_update_data["url"] = scene_data["url"]
        if keyIsSet(scene_data, "date"): scene_update_data["date"] = scene_data["date"]
        if keyIsSet(scene_data, "rating"): scene_update_data["rating"] = scene_data["rating"]
        if keyIsSet(scene_data, "studio"): scene_update_data["studio_id"] = scene_data["studio"]["id"]
        if keyIsSet(scene_data, "gallery"): scene_update_data["gallery_id"] = scene_data["gallery"]["id"]
        if keyIsSet(scene_data, "movies"):
            scene_update_data["movies"] = []
            for entry in scene_data["movies"]:
                update_date_movie = {}
                update_date_movie["movie_id"]=entry["movie"]["id"]
                update_date_movie["scene_index"]=entry["scene_index"]
                scene_update_data["movies"].append(update_date_movie)
        else:
            scene_update_data["movies"] = []
        
        if keyIsSet(scene_data, "performers"):
            scene_update_data["performer_ids"] = []
            for performer in scene_data["performers"]:
                scene_update_data["performer_ids"].append(performer["id"])
        else:
            scene_update_data["performer_ids"] = []
        if keyIsSet(scene_data, "tags"):
            scene_update_data["tag_ids"] = []
            for tag in scene_data["tags"]:
                scene_update_data["tag_ids"].append(tag["id"])
        else:
            scene_update_data["tag_ids"] = []
        return scene_update_data

class config_class:
    ###############################################
    # DEFAULT CONFIGURATION OPTIONS.  DO NOT EDIT #
    ###############################################
    use_https = False # Set to false for HTTP
    server_ip= "<IP ADDRESS>"
    server_port = "<PORT>"
    username=""
    password=""
    debug_mode = True
    ignore_ssl_warnings= True # Set to True if your Stash uses SSL w/ a self-signed cert
    qbit_username = ""
    qbit_password = ""
    qbit_ip = ""
    qbit_category=""
    jacket_api_key="" 
    jacket_api_url=""
    downloads_wanted_tags=""
    downloads_remove_tags=""
    performers_deep_download=""
    deep_download_limit=10


    def loadConfig(self):
        try:  # Try to load configuration.py values
            import configuration
            for key, value in vars(configuration).items():
                if key[0:2] == "__": 
                    continue
                if (key == "server_ip" or key == "server_port") and ("<" in value or ">" in value):
                    logging.warning("Please remove '<' and '>' from your server_ip and server_port lines in configuration.py")
                    sys.exit()
                if isinstance(value, type(vars(config_class).get(key, None))):
                    vars(self)[key]=value
            return True
        except ImportError:
            logging.error("No configuration found.  Double check your configuration.py file exists.")
            create_config = input("Create configuruation.py? (yes/no):")
            if create_config == 'y' or create_config == 'Y' or create_config =='Yes' or create_config =='yes':
                createConfig()
            else:
                logging.error("No configuration found.  Exiting.")
                sys.exit()
        except NameError as err:
            logging.error("Invalid configuration.py.  Make sure you use 'True' and 'False' (capitalized)", exc_info=config_class.debug_mode)
            sys.exit()
            
    def createConfig(self):        
        self.server_ip = input("What's your Stash server's IP address? (no port please):")
        self.server_port = input("What's your Stash server's port?:")
        https_input = input("Does your Stash server use HTTPS? (yes/no):")
        self.use_https = False
        if https_input == 'y' or https_input == 'Y' or https_input =='Yes' or https_input =='yes':
            self.use_https = True
        self.username = input ("What's your Stash server's username? (Just press enter if you don't use one):")
        self.password = input ("What's your Stash server's username? (Just press enter if you don't use one):")

        f = open("configuration.py", "w")
        f.write("""
#Server configuration
use_https = {4} # Set to False for HTTP
server_ip= "{0}"
server_port = "{1}"
username="{2}"
password="{3}
ignore_ssl_warnings= True # Set to True if your Stash uses SSL w/ a self-signed cert
"
""".format(server_ip, server_port, username, password, use_https))
        f.close()
        print("Configuration file created.  All values are currently at defaults.  It is highly recommended that you edit the configuration.py to your liking.  Otherwise, just re-run the script to use the defaults.")
        sys.exit()

def parseArgs(args):
    my_parser = argparse.ArgumentParser(description='Python Interface for Stash')

    #TODO:  Add functions: Scan, Generate, Clean
    # Add the arguments
    my_parser.add_argument('-s',
                       '--scan',
                       action='store_true',
                       help='scan for new content')
    my_parser.add_argument('-c',
                       '--clean',
                       action='store_true',
                       help='clean the database')
    my_parser.add_argument('-g',
                       '--generate',
                       action='store_true',
                       help='generate')
    my_parser.add_argument('-w',
                       '--wait',
                       action='store_true',
                       help='wait for idle before completing')
    my_parser.add_argument('-at',
                       '--auto_tag',
                       nargs='?',
                       const='pst',
                       action='store',
                       help='auto tag; pass nothing for performs, studios, and tags; pass \'p\' for performers, \'s\' for studios, \'t\' for tags, or any combination;  example: \'-at ps\' tags performers and studios')
    my_parser.add_argument(
        "-d",
        "--download",
        action="store_true",
        help="searches for new torrents matching favourited performers and adds them to qBittorrent",
    )
    my_parser.add_argument(
        "-dd",
        "--deepdownload",
        action="store_true",
        help="deep searchers torrents matching list of favourited performers and adds them to qBittorrent",
    )
    my_parser.add_argument(
        "-pdd",
        "--deepdownloadbyperformer",
        action="store_true",
        help="deep searchers torrents matching list of a list of performers and adds them to qBittorrent",
    )
    my_parser.add_argument(
        "-pairpdd",
        "--paireddeepdownloadbyperformer",
        action="store_true",
        help="deep searchers torrents matching list of a list of performers that are in scenes with other performers by a list and adds them to qBittorrent",
    )
    my_parser.add_argument(
        "-pairdd",
        "--paireddeepdownload",
        action="store_true",
        help="deep searchers torrents matching favourited performers that are in scenes with other favourited performers and adds them to qBittorrent",
    )
    # Execute the parse_args() method to collect our args
    parsed_args = my_parser.parse_args(args)
    #Set variables accordingly
    return parsed_args

#Globals
my_stash = None
ENCODING = 'utf-8'
config = config_class()

def main(args):
    logging.basicConfig(level=logging.DEBUG)
    try:
        global my_stash
        config.loadConfig()
        args = parseArgs(args)

        if not config.debug_mode: logging.getLogger().setLevel("WARNING")

        if config.use_https:
            server = 'https://'+str(config.server_ip)+':'+str(config.server_port)
        else:
            server = 'http://'+str(config.server_ip)+':'+str(config.server_port)
        
        my_stash = stash_interface(server, config.username, config.password, config.ignore_ssl_warnings, config.qbit_ip, config.qbit_username, config.qbit_password, config.qbit_category, config.jacket_api_key,  config.jacket_api_url, config.downloads_wanted_tags, config.downloads_remove_tags, config.performers_deep_download, config.deep_download_limit)
        if args.scan: 
            print("Scanning...")
            my_stash.waitForIdle()
            my_stash.scan()
        if args.generate: 
            print("Generating...")
            my_stash.waitForIdle()
            my_stash.generate()
        if args.clean: 
            print("Cleaning...")
            my_stash.waitForIdle()
            my_stash.clean()
        if args.auto_tag:
            print("Auto Tagging...")
            variables = {'input': { 
                'performers': [],
                'studios': [],
                'tags': []
                }}
            if 'p' in args.auto_tag: variables["input"]['performers'] = ['*']
            if 's' in args.auto_tag: variables["input"]['studios'] = ['*']
            if 't' in args.auto_tag: variables["input"]['tags'] = ['*']
            my_stash.waitForIdle()
            my_stash.autoTag()
        if args.download:
            print("Downloading new torrents...")
            my_stash.waitForIdle()
            my_stash.download()
        if args.deepdownload:
            print("Downloading new torrents with deep search...")
            my_stash.waitForIdle()
            my_stash.download(True)
        if args.deepdownloadbyperformer:
            print("Downloading new torrents with deep search on list of performers...")
            my_stash.waitForIdle()
            my_stash.download(True, False, my_stash.performers_deep_download)
        if args.paireddeepdownload:
            print("Downloading new torrents that have favourited performers in scenes with other favourited performers...")
            my_stash.waitForIdle()
            my_stash.download(True, True)
        if args.paireddeepdownloadbyperformer:
            print("Downloading new torrents with deep search on list of performers that are in scenes together...")
            my_stash.waitForIdle()
            my_stash.download(True, True, my_stash.performers_deep_download)
        if args.wait:
            my_stash.waitForIdle()
        print("Success! Finished.")

    except Exception as e:
        logging.error("""Something went wrong.  Have you:
        • Checked to make sure you're running the "development" branch of Stash, not "latest"?
        • Checked that you can connect to Stash at the same IP and port listed in your configuration.py?
        If you've check both of these, run the script again with the --debug flag.  Then post the output of that in the Discord and hopefully someone can help.
        """, exc_info=config.debug_mode)

if __name__ == "__main__":
    main(sys.argv[1:])
