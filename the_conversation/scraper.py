from datetime import datetime
import requests
from bs4 import BeautifulSoup
import json
import multiprocessing as mp
import re

# Cleans a string from all HTML tags,
# remove all quote characters (exc. apostrophes),
# and set all whitespaces to a single space character
def clean_html(text):
    clean_tags = re.compile('<.*?>')
    clean_whitespace = re.compile('\s+')
    clean_quotation = re.compile('”|“|"|’|‘')
    return re.sub(clean_whitespace, ' ', 
        re.sub(clean_quotation, ' ',
        re.sub(clean_tags, ' ', text)))

# Given url will scrape article data and return it as dictionary
def scrap_article(url, num, tot):
    if num % 1000 == 0:
        print('Article %i of %i'%(num,tot))
    text = requests.get(url).text
    soup = BeautifulSoup(text, 'html.parser')
    t = soup.find(class_='entry-title')
    art_title = clean_html(t.text).strip() if t else ""
    i = soup.find(id='article')['data-id']
    art_id = i if i else ""
    d = soup.find(itemprop='datePublished')
    art_date = datetime.strptime(clean_html(d.text).strip(), '%B %d, %Y %I.%M%p %Z').date().strftime('%Y-%m-%d') if d else ""
    article = soup.find(itemprop='articleBody').find_all(['h2', 'p'])
    art_text = [clean_html(a.text.strip()) for a in article]
    authors = soup.findAll(class_='author-name')
    art_auths = [clean_html(a.text.strip()) for a in authors]
    return {'url':url, 'title':art_title, 'date':art_date, 'id':art_id, 'text':art_text, 'authors':art_auths}

# Given a set of urls will fetch articles in parallel
def get_articles(urls):
    articles = []
    def process_result(r):
        articles.append(r)
    pool = mp.Pool(mp.cpu_count())
    for i, url in enumerate(urls):
        pool.apply_async(scrap_article, args=(url, i, len(urls)), callback=process_result)
    pool.close()
    pool.join()
    print('Found %i articles'%len(articles))
    return articles

# Given an index url will fetch the article urls listed there
def get_articles_urls(url):
    print('Fetching urls from %s'%(url))
    text = requests.get(url).text
    soup = BeautifulSoup(text, 'html.parser')
    articles = soup.findAll('article')
    return [{'url':'https://theconversation.com'+a.find(class_='article--header').find('h2').find('a')['href'], 'id':a['data-id']} for a in articles]

# Given info on an edition (name and number of index pages) will fetch all article urls for that edition
def get_urls(country):
    url_base = 'https://theconversation.com/%s/home-page/articles?page='%country[0]
    article_urls = []
    for i in range(1, country[1]+1):
        article_urls += get_articles_urls(url_base+str(i))
    with open('data/urls/urls_%s.json'%country[0], 'w') as out:
        json.dump(article_urls, out)


# Main function retrieving all article urls
def retrieve_urls():
    countries = [['uk', 1131], ['au', 1561], ['ca', 158], ['us', 517], ['global', 28]]
    pool = mp.Pool(mp.cpu_count()-1)
    pool.map(get_urls, [c for c in countries])
    pool.close()

# Function checking article urls from all editions and removing possible duplicates
def clean_duplicates():
    countries = ['uk','au','us','ca','global']
    for c in countries:
        with open('data/urls/urls_%s_raw.json'%c, 'r') as inFile:
            data = json.load(inFile)
            ids = []
            urls = []
            for d in data:
                if d['id'] not in ids:
                    ids.append(d['id'])
                    urls.append(d['url'])
            print('%s: %i articles'%(c,len(ids)))
            with open('data/urls/urls_%s.json'%c, 'w') as outFile:
                json.dump(urls, outFile)

# Main function scraping all articles
def scrap_articles():
    # countries = ['uk','au','us','ca','global']
    countries = ['us','ca','global','au']
    c_name = {'uk':'UK','au':'Australia','us':'US','ca':'Canada','global':'Global'}
    for c in countries:
        with open('data/urls/urls_%s.json'%c, 'r') as inFile:
            print('Starting %s'%c)
            urls = json.load(inFile)
            articles = get_articles(urls)
            for a in articles:
                a['edition'] = c_name[c]
            with open('data/articlesEdition/articles_%s.json'%c, 'w') as outFile:
                json.dump(articles, outFile)
            print('Finished %s'%c)

# scrap_articles()