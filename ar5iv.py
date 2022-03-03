# Grabbing files from ar5iv in case source (LaTeX doesn't work)


def grab_text_from_webpage(url):
    with request.urlopen(url) as response:
        html = response.read()
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text(separator=" ")


df_arxiv["Url"].str.replace("arxiv", "ar5iv")
arxiv_paper = grab_text_from_webpage("http://ar5iv.org/abs/2002.11328")
arxiv_paper_list = arxiv_paper.split("\n\n")
list_text = (
    BeautifulSoup(arxiv_paper, "html.parser").get_text(separator=" ").split("\n")
)
"".join(list_text)
