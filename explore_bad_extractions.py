import json

arxiv = json.load(open("arxiv_data_list.json"))
i = 0
j = 0
for paper in arxiv:
    if paper["citation_level"] == "1":
        # print(paper["id"])
        # print(paper["text"])
        if len(paper["text"]) < 500 and paper["main_tex_filename"] != "":
            i += 1
            print(paper["id"])
            print(paper["text"])
        j += 1

print(i)
print(j)
