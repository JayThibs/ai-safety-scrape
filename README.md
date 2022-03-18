# arXiv Scrape of AI Safety Papers

How to use this repo:

1. Install depedencies with environment.yml.
2. Run `scrape_ai_alignment_content.ipynb` to download the paper tar files (containing .tex files and everything else).
3. Run `python arxiv_extractor.py`.

`extractor_functions.py`: This is a set of functions that extracts the data from the papers and converts the papers to a .md format.
