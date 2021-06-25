# Documents Scrapers [![CC BY-NC 4.0][cc-by-nc-shield]][cc-by-nc]
---

## The Conversation Scraper

> Author: P. Le Bras<br>
> Date: 19/04/2021

### Notes

- The Conversation articles are under a [CC-BY-ND license](https://creativecommons.org/licenses/by-nc-nd/4.0/)
- The following editions are considered scrapped (English editions):
    - [The Conversation UK](https://theconversation.com/uk)
    - [The Conversation US](https://theconversation.com/us)
    - [The Conversation Australia](https://theconversation.com/au)
    - [The Conversation Canada](https://theconversation.com/ca)
    - [The Conversation Global Perspectives](https://theconversation.com/global)
    - Excluding New Zealand edition since it's mostly comprise duplicates of other stories

### Scraper Functions

`scraper.py`: fetches and saves data from The Conversation websites:
- `retrieve_urls()`: function to check the website pages listing articles and grab articles urls and ids. You need to update the page number limit for each edition;
- `clean_duplicates()`: checks for duplicates in the urls and ids retrieved to produce a cleaned list of unique article urls;
- `scrap_articles()`: uses the list of retrieved urls to fetch and save articles into JSON files. One file per edition.

`processor.py`: processes the articles scraped:
- `find_duplicates()`: prints any duplicate entry across all articles scraped, including across editions;
- `split_by_year()`: reads the articles from each edition and split them into separate JSON file, one file per edition and per year, also prints the number of articles;
- `format_csv()`: reads the articles from all the JSON files (split by year) to produce equivalent CSV files;
- `divide_docs(threshold)`: reads the articles from all the JSON files (split by year) to divide the article into sub articles with a text length of at least threshold words, the data is saved as CSV files;
- `mergeCSVs(editions,years[,threshold=None[,outFileName='data/articles.csv']])`: reads all articles corresponding to the list of editions and years provided (and the optional article word length threshold) to create a single CSV file (outFileName);
- `separate_non_english(CSVFile, englishCSVFile, nonenglishCSVFile)`: separates the articles read in `CSVFile` to put the english ones in `englishCSVFile` and the non-english in `nonenglishCSVFile`.

### Data Format

The data scraped in stored in JSON (temporarily) and then transformed into CSV ofr the pipeline.

In JSON, the data is structured as follow:
```json5
[{
    "url": string,
    "id": string,
    "date": "YYYY-MM-DD",
    "authors": [ string, ... ],
    "edition": "Australia" | "UK" | "US" | "Canada" | "Global",
    "text": [ string, ... ]
},...]
```

In CSV, the data is saved in the following columns:
```csv
id, url, title, date, authors, edition, text
string, string, string, "YYYY-MM-DD", "author1 & author2 ...", "Australia" | "UK" | "US" | "Canada" | "Global", string
...
```

---
This work is licensed under a [Creative Commons Attribution 4.0 International
License][cc-by-nc].

[![CC BY-NC 4.0][cc-by-nc-image]][cc-by-nc]

[cc-by-nc]: http://creativecommons.org/licenses/by-nc/4.0/
[cc-by-nc-image]: https://i.creativecommons.org/l/by-nc/4.0/88x31.png
[cc-by-nc-shield]: https://img.shields.io/badge/License-CC%20BY--NC%204.0-lightgrey.svg
