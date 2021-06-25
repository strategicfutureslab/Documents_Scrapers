# Documents Scrapers [![CC BY-NC 4.0][cc-by-nc-shield]][cc-by-nc]
---

Collection of scripts scraping Scottish universities' public repositories for publication data.

## Heriot-Watt University

Website: [researchportal.hw.ac.uk](https://researchportal.hw.ac.uk/)

Script: `scraper_hwu.py`
- `fetch_authors()` gets list of authors with a profile on the website and saves their info in `hwu_authors.csv`:
    - `id` author's unique ID;
    - `name` author's full name;
    - `url` author's profile url;
    - `organisation` set to `Heriot-Watt University`;
- `fetch_papers()` reads list of author profiles and gets their list of research outputs to save in `hwu_papers_raw.csv`:
    - `title` research title;
    - `authors` full list of authors;
    - `date` year of publication;
    - `abstract` research abstract (*may be empty*);
    - `url` research url;
    - `organisation` set to `Heriot-Watt University`;
    - `author_id` unique id of the author from which the research was accessed;
- `clean_duplicates()` reads list of all the research outputs, merges duplicates (by url value) and saves them in `hwu_papers.csv`:
    - `title`, `authors`, `date`, `abstract`, `url` and `organisation` same as `hw_papers_raw.csv`;
    - `author_id` replaced by `author_ids`, the list of authors' unique ids (those with an entry in `hw_authors.csv`) concatenated with an ` & `.

## University of Edinburgh

Website: [research.ed.ac.uk](https://www.research.ed.ac.uk/)

Script: `scraper_edi.py`
- `fetch_authors()` ditto to Heriot-Watt University, saved in `edi_authors.csv`;
- `fetch_papers()` ditto to Heriot-Watt University, but too many authors to scrap in one go, so:
    - saves raw papers in `edi_papers_raw` directory every 100 authors;
    - you can therefore interrupt the script after a save;
    - and set which index to start from in the next run;
    - some profile url might have changed between the date you got the author data and the date you scrap their papers:
        - check their urls in `edi_authors.csv`:
            - if profile deleted (404 page): remove the row from `edi_authors.csv`;
            - if profile redirects to new name: update name and url in `edi_authors.csv`;
- `merge_raw_papers()` merges all files in `edi_papers_raw` directory in one (`edi_papers_raw.csv`);
- `clean_duplicates()` ditto to Heriot-Watt University, saved in `edi_papers.csv`

## University of Glasgow

Website: [eprints.gla.ac.uk](https://eprints.gla.ac.uk)

Script: `scraper_edi.py`
- `fetch_authors()` ditto to Heriot-Watt University, saved in `gla_authors.csv`;
- `fetch_papers()` ditto to University of Edinburgh, saves raw papers in `gla_papers_raw` directory;
- `merge_raw_papers()` merges all files in `gla_papers_raw` directory in one (`gla_papers_raw.csv`);
- `clean_duplicates()` ditto to Heriot-Watt University, saved in `gla_papers.csv`


---
This work is licensed under a [Creative Commons Attribution 4.0 International
License][cc-by-nc].

[![CC BY-NC 4.0][cc-by-nc-image]][cc-by-nc]

[cc-by-nc]: http://creativecommons.org/licenses/by-nc/4.0/
[cc-by-nc-image]: https://i.creativecommons.org/l/by-nc/4.0/88x31.png
[cc-by-nc-shield]: https://img.shields.io/badge/License-CC%20BY--NC%204.0-lightgrey.svg
