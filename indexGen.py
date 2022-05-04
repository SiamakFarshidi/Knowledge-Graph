from knowledgeGraph import get_entity, get_relation, show
from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search, Q, Index
import os
from elasticsearch_dsl.query import MatchAll
import re
import sys
import csv
import json
from inspect import getmembers, isfunction
from modulefinder import ModuleFinder
import language_tool_python
tool = language_tool_python.LanguageTool('en-US')
#-----------------------------------------------------------------------------------------------------------------------
def pythonLibraries(filePath):
    lstLibraries=set()
    finder = ModuleFinder()
    finder.run_script(filePath)
    for name, mod in finder.modules.items():
        #print('%s: ' % name, end='')
        lstLibraries.add(name)
        #print(','.join(list(mod.globalnames.keys())[:3]))
    #print('-'*50)
    #print('Modules not imported:')
    #print('\n'.join(finder.badmodules.keys()))
    return lstLibraries
#-----------------------------------------------------------------------------------------------------------------------
def cleanhtml(raw_html):
    CLEANR = re.compile('<.*?>')
    cleantext = re.sub(CLEANR, '', raw_html)
    cleantext=cleantext.replace('\n','').split('.')

    lstText=set()
    for txt in cleantext:
        if len(txt)>20:
            lstText.add(re.sub('[\W ]+', ' ', txt))

    cleantext=""
    for txt in lstText:
        cleantext += txt.strip()+". "

    return cleantext, lstText
#-----------------------------------------------------------------------------------------------------------------------
def indexGen():
    maxInt = sys.maxsize
    while True:
        # decrease the maxInt value by factor 10
        # as long as the OverflowError occurs.
        try:
            csv.field_size_limit(maxInt)
            break
        except OverflowError:
            maxInt = int(maxInt/10)
    with open('NotebookDatasets/text_code_URL.csv') as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        line_count = 0
        for row in csv_reader:
            if line_count == 0:
                #print(f'Column names are {", ".join(row)}')
                line_count += 1
            else:
                line_count += 1

                name= re.sub('[\W_ ]+', ' ', row[1]).replace('ipynb','')
                title= re.sub('[\W_ ]+', ' ', row[7])


                description,lstDescrition=cleanhtml(row[6]+row[8])

                url=row[9]
                temp_data = {}
                temp_data["name"] = name
                temp_data["full_name"] = title
                temp_data["stargazers_count"] = 0
                temp_data["forks_count"] = 0
                temp_data["description"] = description
                temp_data["id"] = row[0]
                temp_data["size"] = row[5]
                temp_data["language"] = row[2]
                temp_data["html_url"] = url
                temp_data["git_url"] = url
                temp_data["script"] = extractLibs(row[10])
                temp_data["entities"]= generate_knowledgeGraph(lstDescrition)

                filename= re.sub(r'[^A-Za-z0-9 ]+', '',name)+"_"+"_"+str( row[5])
                f = open("index_files/"+filename+".json", 'w+')
                f.write(json.dumps(temp_data))
                f.close()
                print(url)
#-----------------------------------------------------------------------------------------------------------------------
def extractLibs(PyScript):
    libraries=set()
    strLibSet=""
    patterns = ["import (.*?) as", "from (.*?) import", "def (.*?)\(","from.* import (.*?)$", "class (.*?):"]
    for line in PyScript.splitlines():
        for pattern in patterns:
            if type(re.search(pattern, line))!=type(None):
                substring = re.search(pattern, line).group(1)
                lst=substring.split(',')
                for item in lst:
                    if len(item)>1:
                        libraries.add(item.strip())

    for lib in libraries:
        strLibSet += lib + " "

    return strLibSet
#-----------------------------------------------------------------------------------------------------------------------
def generate_knowledgeGraph(lstText):
    lstEntities=set()
    entities=""
    for text in lstText:
        text=text.strip()+"."
        #if(isCorrectSentence(text)):
        #print("\n --------------------------------- \n")
        #print(text)
        if len(text)>40:
            output_entitiy = get_entity(text)
            output_relation = get_relation(text)
            if output_entitiy and output_relation and output_entitiy[0] and output_entitiy[1]:
                tupple=(output_entitiy, output_relation)
                lstEntities.add(tupple)
        #show(text)
        #s=input()
    for entity in lstEntities:
        entities += str(entity)+ " "
    return entities
#-----------------------------------------------------------------------------------------------------------------------
def isCorrectSentence(sentence):
    matches = tool.check(sentence)
    if len(matches):
        return False
    return True
#-----------------------------------------------------------------------------------------------------------------------
def indexingpipeline():
    es = Elasticsearch("http://localhost:9200")
    index = Index('notebooks', es)

    if not es.indices.exists(index='notebooks'):
        index.settings(
            index={'mapping': {'ignore_malformed': True}}
        )
        index.create()
    else:
        es.indices.close(index='notebooks')
        put = es.indices.put_settings(
            index='notebooks',
            body={
                "index": {
                    "mapping": {
                        "ignore_malformed": True
                    }
                }
            })
        es.indices.open(index='notebooks')
    cnt=0
    root=(os. getcwd()+"/index_files/")
    for path, subdirs, files in os.walk(root):
        for name in files:
            cnt=cnt+1
            indexfile= os.path.join(path, name)
            indexfile = open_file(indexfile)
            res = es.index(index="notebooks", id= indexfile["git_url"], body=indexfile)
            es.indices.refresh(index="notebooks")
            print(str(cnt)+" recode added! \n")
#-----------------------------------------------------------------------------------------------------------------------
def open_file(file):
    read_path = file
    with open(read_path, "r", errors='ignore') as read_file:
        data = json.load(read_file)
    return data
#-----------------------------------------------------------------------------------------------------------------------
def classifyIndexes():

    lstLowDescriptionFiles=[]
    lstNoDescriptionFiles=[]
    lstNoEntityFiles=[]
    lstNoScriptFiles=[]
    lstPerfectFiles=[]
    lstWorstFiles=[]

    root=(os. getcwd()+"/index_files/")
    for path, subdirs, files in os.walk(root):
        for name in files:
            indexfile= os.path.join(path, name)
            indexfile = open_file(indexfile)

            if len(indexfile['description'])>0 and len(indexfile['description'])<50 :
                lstLowDescriptionFiles.append(name)

            if indexfile['description']=="":
                lstNoDescriptionFiles.append(name)

            if indexfile['entities']=="":
                lstNoEntityFiles.append(name)

            if indexfile['script']=="":
                lstNoScriptFiles.append(name)

            if len(indexfile['description'])>50 and indexfile['entities']!="" and  indexfile['script']!="":
                lstPerfectFiles.append(name)

            if len(indexfile['description'])<50 and indexfile['entities']=="" and  indexfile['script']=="":
                lstWorstFiles.append(name)

    print("lstLowDescriptionFiles: " + str(len(lstLowDescriptionFiles)))
    print("lstNoDescriptionFiles: " + str(len(lstNoDescriptionFiles)))
    print("lstNoEntityFiles: " + str(len(lstNoEntityFiles)))
    print("lstNoScriptFiles: " + str(len(lstNoScriptFiles)))
    print("lstPerfetcFiles: " + str(len(lstPerfectFiles)))
    print("lstWorstFiles: " + str(len(lstWorstFiles)))

    for file in lstLowDescriptionFiles:
        indexfile = open_file(root+file)
        f = open("Analysis/Low_description_files/"+file, 'w')
        f.write(json.dumps(indexfile))
        f.close()

    for file in lstNoDescriptionFiles:
        indexfile = open_file(root+file)
        f = open("Analysis/No_description_files/"+file, 'w')
        f.write(json.dumps(indexfile))
        f.close()

    for file in lstNoEntityFiles:
        indexfile = open_file(root+file)
        f = open("Analysis/No_entity_files/"+file, 'w')
        f.write(json.dumps(indexfile))
        f.close()

    for file in lstNoScriptFiles:
        indexfile = open_file(root+file)
        f = open("Analysis/No_script_files/"+file, 'w')
        f.write(json.dumps(indexfile))
        f.close()

    for file in lstPerfectFiles:
        indexfile = open_file(root+file)
        f = open("Analysis/Perfect_files/"+file, 'w')
        f.write(json.dumps(indexfile))
        f.close()

    for file in lstWorstFiles:
        indexfile = open_file(root+file)
        f = open("Analysis/Worst_files/"+file, 'w')
        f.write(json.dumps(indexfile))
        f.close()
#-----------------------------------------------------------------------------------------------------------------------
#indexGen()
#indexingpipeline()
#-----------------------------------------------------------------------------------------------------------------------
# Testing and analysis
classifyIndexes()