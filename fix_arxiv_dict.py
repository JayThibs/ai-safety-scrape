import json

arxiv_dict = json.load(open("arxiv_dict_updated.json"))

# with open("arxiv_dict_updated_copy.json", "w") as f:
#     json.dump(arxiv_dict, f)

new_arxiv_data = []
i = 0
for k, v in arxiv_dict.items():
    arxiv_dict[k]["abstract"] = arxiv_dict[k]["abstract"].replace("\n", " ")
    arxiv_dict[k]["id"] = k
    item = arxiv_dict[k]
    try:
        if item["paper_version"]:
            pass
    except:
        try:
            if item["url"]:
                item["paper_version"] = item["url"].split("/")[-1]
                arxiv_dict[k] = item
                continue
        except:
            pass
        item["paper_version"] = ""
        arxiv_dict[k] = item
        pass
    new_arxiv_data.append(arxiv_dict[k])

print(new_arxiv_data[0]["paper_version"])

for i, item in enumerate(new_arxiv_data):
    


# print(new_arxiv_data[0])

with open("arxiv_dict_updated.json", "w") as f:
    json.dump(arxiv_dict, f)

with open("arxiv_data_list.json", "w") as f:
    json.dump(new_arxiv_data, f)
