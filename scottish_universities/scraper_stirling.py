import requests
from bs4 import BeautifulSoup
import csv
import re
from datetime import datetime
import multiprocessing as mp
import time

"""
Make sure to check the n_pages_auth
This is the total number of pages that has profiles
"""
start_time = time.monotonic()

orga = 'University of Stirling'

##################################################
# Scraping Authors
##################################################

base_url_auth = 'https://www.stir.ac.uk/people/?page='
n_pages_auth = 1
auth_out = 'data/stir_authors.csv'

curr_id = -1

def new_id():
    global curr_id
    curr_id += 1
    return 'STIR%i'%curr_id

def fetch_authors_page(url):
    print('Fetching authors from %s'%(url))
    text = requests.get(url).text
    soup = BeautifulSoup(text, 'html.parser')
    authors = soup.find_all(class_='c-staff-overview')
    return [{'id':new_id(), 'name':a.find('a').text, 'url':'https://www.stir.ac.uk/' + a.find('a')['href'], 'organisation':orga} for a in authors]

def fetch_authors():
    authors = []
    for i in range(n_pages_auth):
        authors += fetch_authors_page(base_url_auth+str(i))
    print('Found %i profiles'%len(authors))
    with open(auth_out, 'w', encoding='utf-8', newline='') as outFile:
        w = csv.DictWriter(outFile, authors[0].keys(), quoting=csv.QUOTE_ALL)
        w.writeheader()
        w.writerows(authors)




##################################################
# Scraping Papers
##################################################

research_output_page = '#outputs'
raw_papers_out = 'data/stir_papers_raw.csv'

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
    title = get_text(soup.find('dc_title'))
    authors = get_text(soup.find(class_='dc_contributor_author'))
    abstract = get_text(soup.find(class_='dc_description_abstract'))
    status = soup.find(class_='status')
    date = parse_date(get_text(status.find(class_='dc_date_issued')))
    return {'title':title,'authors':authors,'date':date,'abstract':abstract,'url':url,'organisation':orga}


def get_author_papers(auth_url, auth_id):
    print('Starting author %s'%auth_id)
    print(auth_url)
    i = 0
    paper_urls = []
    paper_urls_temp = []
    while True:
        text = requests.get(auth_url+research_output_page+str(i)).text
        soup = BeautifulSoup(text, 'html.parser')
        papers = [p for p in soup.find_all('p', {'class': True}) if 'c-search-result__link' in p['class']]
        if len(papers) == 0:
            break
        else:
            paper_urls_temp += [p.find('a')['href'] for p in papers]
            i += 1
    for url in paper_urls_temp:
        print(url)
        if 'c-link' in url['class']:
            print(url.find('a')['href'])
            paper_urls.append(url.find('a')['href'])
            print('***************** paper_urls *******************')
            print(paper_urls)
        else:
            print('no links found')
    papers = distributed_fetch(paper_urls, get_paper)
    for p in papers:
        p['author_id'] = auth_id
    return papers

def fetch_papers():
    with open(auth_out, 'r', encoding='utf-8') as inFile:
        author_urls = [(row['url'],row['id']) for row in csv.DictReader(inFile)]
        papers = []
        for a_u in author_urls:
            papers += get_author_papers(a_u[0], a_u[1])
        with open(raw_papers_out, 'w', encoding='utf-8', newline='') as outFile:
            w = csv.DictWriter(outFile, papers[0].keys(), quoting=csv.QUOTE_ALL)
            w.writeheader()
            w.writerows(papers)



##################################################
# Eliminating duplicates
##################################################

papers_out = 'data/stir_papers.csv'

def clean_duplicates():
    with open(raw_papers_out, 'r', encoding='utf-8') as inFile:
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
        with open(papers_out, 'w', encoding='utf-8', newline='') as outFile:
            w = csv.DictWriter(outFile, uniq_papers[0].keys(), quoting=csv.QUOTE_ALL)
            w.writeheader()
            w.writerows(uniq_papers)




if __name__ == '__main__':
    fetch_authors()
    fetch_papers()
    #clean_duplicates()
    print('Time taken (s): ', (time.monotonic() - start_time))
