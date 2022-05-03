from knowledgeGraph import get_entity, get_relation, show
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
                generate_knowledgeGraph(lstDescrition)
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
    for text in lstText:
        text=text.strip()+"."
        if(isCorrectSentence(text)):
            print(text)
            output = get_entity(text)
            print(output)
            output = get_relation(text)
            print(output)
            show(text)
            s=input()
#-----------------------------------------------------------------------------------------------------------------------
def isCorrectSentence(sentence):
    matches = tool.check(sentence)
    if len(matches):
        return False
    return True
#-----------------------------------------------------------------------------------------------------------------------
indexGen()
