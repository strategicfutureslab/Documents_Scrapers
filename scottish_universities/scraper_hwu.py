import requests
from bs4 import BeautifulSoup
import csv
import re
from datetime import datetime
import multiprocessing as mp
import time

start_time = time.monotonic()

orga = 'Heriot-Watt University'

##################################################
# Scraping Authors
##################################################

base_url_auth = 'https://researchportal.hw.ac.uk/en/persons/?format=&page='
n_pages_auth = 15
auth_out = 'data/hwu_authors.csv'

curr_id = -1

def new_id():
    global curr_id
    curr_id += 1
    return 'HWU%i'%curr_id

def fetch_authors_page(url):
    print('Fetching authors from %s'%(url))
    text = requests.get(url).text
    soup = BeautifulSoup(text, 'html.parser')
    authors = soup.find_all(rel="Person")
    return [{'id':new_id(), 'name':a.find('span').text, 'url':a['href'], 'organisation':orga} for a in authors]

def fetch_authors():
    authors = []
    for i in range(n_pages_auth):
        authors += fetch_authors_page(base_url_auth+str(i))
    print('Found %i profiles'%len(authors))
    with open(auth_out, 'w') as outFile:
        w = csv.DictWriter(outFile, authors[0].keys(), quoting=csv.QUOTE_ALL)
        w.writeheader()
        w.writerows(authors)

# fetch_authors()

##################################################
# Scraping Papers
##################################################

research_output_page = '/publications/?page='
raw_papers_out = 'data/hwu_papers_raw.csv'

def distributed_fetch(urls, fetch_callback):
    results = []
    def process_result(r):
        results.append(r)
    pool = mp.Pool(mp.cpu_count())
    for url in urls:
        pool.apply_async(fetch_callback, args=(url, ), callback=process_result)
    pool.close()
    pool.join()
    print('Found %i results'%len(results))
    return results

def clean_html(text):
    clean_tags = re.compile('<.*?>')
    clean_whitespace = re.compile('\s+')
    clean_quotation = re.compile('”|“|"|’|‘')
    return re.sub(clean_whitespace, ' ', 
        re.sub(clean_quotation, ' ',
        re.sub(clean_tags, ' ', text))).strip()

def get_text(dom_elt):
    if dom_elt != None:
        return clean_html(str(dom_elt))
    else:
        return ''

def parse_date(date):
    if date == '':
        return date
    else:
        try:
            datetime.strptime(date, '%Y')
            return date
        except ValueError:
            try:
                d = datetime.strptime(date, '%b %Y')
                return d.date().strftime('%Y')
            except ValueError:
                try:
                    d = datetime.strptime(date, '%d %b %Y')
                    return d.date().strftime('%Y')
                except ValueError:
                    try:
                        d = datetime.strptime(date, '%d %B %Y')
                        return d.date().strftime('%Y')
                    except ValueError:
                        try:
                            d = datetime.strptime(date, '%d/%m/%y')
                            return d.date().strftime('%Y')
                        except ValueError:
                            print('Unrecognised date format: %s'%date)
                            return date

def get_paper(url):
    text = requests.get(url).text
    soup = BeautifulSoup(text, 'html.parser')
    title = get_text(soup.find('h1'))
    authors = get_text(soup.find(class_='persons'))
    abstract = get_text(soup.find(class_='rendering_abstractportal'))
    status = soup.find(class_='status')
    date = parse_date(get_text(status.find(class_='date')))
    return {'title':title,'authors':authors,'date':date,'abstract':abstract,'url':url,'organisation':orga}

def get_author_papers(auth_url, auth_id):
    print('Starting author %s'%auth_id)
    i = 0
    paper_urls = []
    while True:
        text = requests.get(auth_url+research_output_page+str(i)).text
        soup = BeautifulSoup(text, 'html.parser')
        papers = [p for p in soup.find_all('h3') if 'title' in p['class']]
        if len(papers) == 0:
            break
        else:
            paper_urls += [p.find('a')['href'] for p in papers]
            i += 1
    papers = distributed_fetch(paper_urls, get_paper)
    for p in papers:
        p['author_id'] = auth_id
    return papers

def fetch_papers():
    with open(auth_out, 'r') as inFile:
        author_urls = [(row['url'],row['id']) for row in csv.DictReader(inFile)]
        papers = []
        for a_u in author_urls:
            papers += get_author_papers(a_u[0], a_u[1])
        with open(raw_papers_out, 'w') as outFile:
            w = csv.DictWriter(outFile, papers[0].keys(), quoting=csv.QUOTE_ALL)
            w.writeheader()
            w.writerows(papers)

# fetch_papers()

##################################################
# Eliminating duplicates
##################################################

papers_out = 'data/hwu_papers.csv'

def clean_duplicates():
    with open(raw_papers_out, 'r') as inFile:
        papers = [{k:v for k,v in r.items()} for r in csv.DictReader(inFile)]
        print('%i papers originally'%len(papers))
        uniq_urls = {p['url'] for p in papers}
        duplicate_papers = []
        for u in uniq_urls:
            duplicate_papers += [[p for p in papers if u == p['url']]]
        uniq_papers = []
        for p in duplicate_papers:
            paper = p[0]
            paper['author_ids'] = ' & '.join([d['author_id'] for d in p])
            paper.pop('author_id', None)
            uniq_papers += [paper]
        print('Found %i unique papers'%len(uniq_papers))
        with open(papers_out, 'w') as outFile:
            w = csv.DictWriter(outFile, uniq_papers[0].keys(), quoting=csv.QUOTE_ALL)
            w.writeheader()
            w.writerows(uniq_papers)

# clean_duplicates()

print('Time taken (s): ', (time.monotonic() - start_time))
