import json
import csv
import os
from datetime import datetime
from collections import defaultdict, Counter
import re
import multiprocessing as mp
from langdetect import detect
from langdetect.lang_detect_exception import LangDetectException

# Function reading a date string and formating it to just the year
def transform_date_year(dateString):
    if dateString == '':
        return ''
    else:
        return datetime.strptime(dateString, '%Y-%m-%d').date().strftime('%Y')

# Cleans a string from all HTML tags,
# remove all quote characters (exc. apostrophes),
# and set all whitespaces to a single space character
def clean_text(text):
    clean_tags = re.compile('<.*?>')
    clean_whitespace = re.compile('\s+')
    clean_quotation = re.compile('”|“|"|’|‘')
    return re.sub(clean_whitespace, ' ', 
        re.sub(clean_quotation, ' ',
        re.sub(clean_tags, ' ', text)))

# List of editions
countries = ['uk','global','au','us','ca']

# Function printing any duplicate articles
def find_duplicates():
    ids = []
    for c in countries:
        with open('data/articlesEdition/articles_%s.json'%c, 'r') as inFile:
            data = json.load(inFile)
            ids += [d['id'] for d in data]
    print([(u,cnt) for u, cnt in Counter(ids).items() if cnt > 1])

# Function spliting articles into separate JSON file: one file per edition and per year
def split_by_year():
    for c in countries:
        with open('data/articlesEdition/articles_%s.json'%c, 'r') as inFile:
            data = json.load(inFile)
            print('%s: %i articles'%(c,len(data)))
            nested = defaultdict(list)
            for d in data:
                nested[transform_date_year(d['date'])].append(d)
            for y in nested.keys():
                print(' - %s: %i articles'%(y, len(nested[y])))
                with open('data/articlesEditionYear/articles_%s_%s.json'%(c,y), 'w') as outFile:
                    json.dump(nested[y], outFile)

# Function changing year-edition JSON files into year-edition CSV file
def format_csv():
    filePath = 'data/articlesEditionYear/'
    for f in os.listdir(filePath):
        fileName = f.split('.')[0]
        with open(filePath+fileName+'.json', 'r') as inFile:
            data = json.load(inFile)
            for d in data:
                d['text'] = clean_text(' '.join(d['text']))
                d['authors'] = ' & '.join(d['authors'])
            with open('data/articlesEditionYearCSV/'+fileName+'.csv', 'w') as outFile:
                w = csv.DictWriter(outFile, data[0].keys(), quoting=csv.QUOTE_ALL)
                w.writeheader()
                w.writerows(data)

# Function dividing articles from year-edition JSON files into sub-articles with length at least threshold words
# Saves sub-articles in year-edition CSV files;
def divide_docs(threshold):
    filePath = 'data/articlesEditionYear/'
    for f in os.listdir(filePath):
        fileName = f.split('.')[0]
        with open(filePath+fileName+'.json', 'r') as inFile:
            data = json.load(inFile)
            new_docs = []
            for d in data:
                i = 1
                text = []
                for t in d['text']:
                    text += t.split(' ')
                    if len(text) >= threshold:
                        new_docs.append({
                            'id':'%s-%i'%(d['id'],i), 'url':d['url'], 'title':d['title'], 'date':d['date'], 
                            'authors':' & '.join(d['authors']), 'edition':d['edition'], 'text':' '.join(text)})
                        i += 1
                        text = []
                if len(text) > 0:
                        new_docs.append({
                            'id':'%s-%i'%(d['id'],i), 'url':d['url'], 'title':d['title'], 'date':d['date'], 
                            'authors':' & '.join(d['authors']), 'edition':d['edition'], 'text':' '.join(text)})
            with open('data/articlesEditionYearCSV/%s_%i.csv'%(fileName,threshold), 'w') as outFile:
                w = csv.DictWriter(outFile, new_docs[0].keys(), quoting=csv.QUOTE_ALL)
                w.writeheader()
                w.writerows(new_docs)

# Function merging multiple year-edition[-divided] CSV files into a single CSV file
def merge_CSVs(editions, years, threshold=None, outFileName='data/articles.csv'):
    doc_words = '' if threshold == None else '_%i'%threshold
    data = []
    for e in editions:
        for y in years:
            try:
                with open('data/articlesEditionYearCSV/articles_%s_%s%s.csv'%(e,y,doc_words), 'r') as inFile:
                    data += [{k:v for k,v in row.items()} for row in csv.DictReader(inFile)]
            except FileNotFoundError:
                print('Skipping data/articlesEditionYearCSV/articles_%s_%s%s.csv: not found'%(e,y,doc_words))
    with open(outFileName, 'w') as outFile:
        w = csv.DictWriter(outFile, data[0].keys(), quoting=csv.QUOTE_ALL)
        w.writeheader()
        w.writerows(data)
    
# Function detecting the language of string
def detect_lang(s):
    try:
        return detect(s) if len(s) > 0 and not all(list(map(str.isdigit, s))) else 'en'
    except LangDetectException:
        return 'n/a'

# Function detecting if the language of an article in English
# does multiple tries and normalise result to account for stochastic prediction
def detect_en_article(article):
    tries = 2
    count_en = 0
    for _ in range(tries):
        if detect_lang(article['text']) == 'en':
            count_en += 1
    en_cert = count_en/tries
    if en_cert < 1:
        print('Article %s - English: %f'%(article['id'],en_cert))
    return (en_cert > 0.5, article['id'])

# Consumer function for parallel detection of language across articles
# Logs progess every 1000 article
def classify_article(article, i, tot):
    res = detect_en_article(article)
    if i%1000 == 0:
        print('%f done'%(i/tot))
    return res

# Function reading a CSV file and separating into two CSV files:
# - one for English articles
# - one for non-english articles
def separate_non_english(csv_filename, en_filename, noen_filename):
    noen_id = []
    def process_result(r):
        if not r[0]:
            noen_id.append(r[1])
    with open(csv_filename, 'r') as inFile:
        articles = [{k:v for k,v in row.items()} for row in csv.DictReader(inFile)]
        keys = articles[0].keys()
        total_art = len(articles)
        pool = mp.Pool(mp.cpu_count()-1)
        for i,a in enumerate(articles):
            pool.apply_async(classify_article, args=(a, i, total_art), callback=process_result)
        pool.close()
        pool.join()
        en_art = [a for a in articles if not a['id'] in noen_id]
        noen_art = [a for a in articles if a['id'] in noen_id]
        print('Total articles: %i'%len(articles))
        print('English articles: %i - Non-English articles: %i'%(len(en_art),len(noen_art)))
        with open(en_filename, 'w') as outFile:
            w = csv.DictWriter(outFile, keys, quoting=csv.QUOTE_ALL)
            w.writeheader()
            w.writerows(en_art)
        with open(noen_filename, 'w') as outFile:
            w = csv.DictWriter(outFile, keys, quoting=csv.QUOTE_ALL)
            w.writeheader()
            w.writerows(noen_art) 


# find_duplicates()
# split_by_year()
# format_csv()
# divide_docs(400)
# merge_CSVs(['uk','us','ca','au'],['2019','2018'],threshold=300)
# separate_non_english('data/articles.csv','data/articles_en.csv','data/articles_noen.csv')