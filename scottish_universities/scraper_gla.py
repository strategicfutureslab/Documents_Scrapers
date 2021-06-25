import requests
from bs4 import BeautifulSoup
import csv
import re
from datetime import datetime
import multiprocessing as mp
import time

start_time = time.monotonic()

orga = 'University of Glasgow'

##################################################
# Scraping Authors
##################################################

base_url_auth = 'https://eprints.gla.ac.uk/view/author/index.'
auth_out = 'data/gla_authors.csv'

curr_id = -1

def new_id():
    global curr_id
    curr_id += 1
    return 'GLA%i'%curr_id

def format_author_name(name):
    split = name.split(', ')
    new_name = split[1]+' '+split[0]
    if new_name.startswith('Professor '):
        new_name = new_name[10:]
    if new_name.startswith('Miss ') or new_name.startswith('Prof '):
        new_name = new_name[5:]
    if new_name.startswith('Mrs '):
        new_name = new_name[4:]
    if new_name.startswith('Dr ') or new_name.startswith('Mr ') or new_name.startswith('Ms '):
        new_name = new_name[3:]
    return new_name

def fetch_authors_page(url):
    print('Fetching authors from %s'%(url))
    text = requests.get(url).text
    soup = BeautifulSoup(text, 'html.parser')
    authors = soup.find(id='eprints_content').find('table').find_all('li')
    return [{'id':new_id(), 'name':format_author_name(a.find('a').text), 'url':'https://eprints.gla.ac.uk/view/author/'+a.find('a')['href'], 'organisation':orga} for a in authors]

def fetch_authors():
    authors = []
    for i in range(ord('A'), ord('Z')+1):
        authors += fetch_authors_page(base_url_auth+chr(i)+'.html')
    for s in ['=D6', '==017D']: # additional characters
        authors += fetch_authors_page(base_url_auth+s+'.html')
    print('Found %i profiles'%len(authors))
    with open(auth_out, 'w') as outFile:
        w = csv.DictWriter(outFile, authors[0].keys(), quoting=csv.QUOTE_ALL)
        w.writeheader()
        w.writerows(authors)

# fetch_authors()

##################################################
# Scraping Papers
##################################################

raw_papers_out = 'data/gla_papers_raw/gla_papers_raw'

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
    if len(results) < 1:
        exit(1) # stop if no result to check issue
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

def get_year(s):
    m = re.search('\(([0-9]{4}?)\)', s)
    if m:
        return m.group(1)

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
    content = soup.find(id='eprints_content')
    title = get_text(content.find('h1'))
    summary = content.find(class_='ep_summary_content_main')
    abst = content.find('h2', string='Abstract')
    abstract = get_text(abst.find_next('p')) if abst != None else ''
    authors = get_text(content.find(string="Authors:").find_next('td'))
    cite = get_text(summary.find('p', class_='ep_block'))
    date = parse_date(get_year(cite))
    return {'title':title,'authors':authors,'date':date,'abstract':abstract,'url':url,'organisation':orga}

def get_author_papers(auth_url, auth_id):
    print('Starting author %s'%auth_id)
    text = requests.get(auth_url).text
    soup = BeautifulSoup(text, 'html.parser')
    papers = [p for p in soup.find(class_='ep_view_page_view_author').find_all('p', recursive=False)]
    paper_urls = [p.find('a', recursive=False)['href'] for p in papers]
    if(len(paper_urls)>0):
        papers = distributed_fetch(paper_urls, get_paper)
        for p in papers:
            p['author_id'] = auth_id
    else:
        print('No publications')
    return papers

def fetch_papers():
    with open(auth_out, 'r') as inFile:
        author_urls = [(row['url'],row['id']) for row in csv.DictReader(inFile)]
        papers = []
        for i,a_u in enumerate(author_urls):
            if i > 5199: # where last execution stopped
                papers += get_author_papers(a_u[0], a_u[1])
                if((i+1)%100 == 0):
                    with open(raw_papers_out+'_'+str(i)+'.csv', 'w') as outFile:
                        w = csv.DictWriter(outFile, papers[0].keys(), quoting=csv.QUOTE_ALL)
                        w.writeheader()
                        w.writerows(papers)
                        papers = []
        with open(raw_papers_out+'_last.csv', 'w') as outFile:
            w = csv.DictWriter(outFile, papers[0].keys(), quoting=csv.QUOTE_ALL)
            w.writeheader()
            w.writerows(papers)
            papers = []

# fetch_papers()

##################################################
# Merge raw papers
##################################################

raw_papers_out_merged = 'data/gla_papers_raw/gla_papers_raw.csv'

def merge_raw_papers():
    papers = []
    for i in range(99, 14000, 100): # custom range to fit with split files
        with open(raw_papers_out+'_'+str(i)+'.csv', 'r') as inFile:
            p = [{k:v for k,v in r.items()} for r in csv.DictReader(inFile)]
            print('%i papers found'%len(p))
            papers += p
    with open(raw_papers_out+'_last.csv', 'r') as inFile:
        p = [{k:v for k,v in r.items()} for r in csv.DictReader(inFile)]
        print('%i papers found'%len(p))
        papers += p
    print('%i papers found in total'%len(papers))
    with open(raw_papers_out_merged, 'w') as outFile:
        w = csv.DictWriter(outFile, papers[0].keys(), quoting=csv.QUOTE_ALL)
        w.writeheader()
        w.writerows(papers)

# merge_raw_papers()

##################################################
# Eliminating duplicates
##################################################

papers_out = 'data/gla_papers.csv'

def clean_duplicates():
    with open(raw_papers_out_merged, 'r') as inFile:
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