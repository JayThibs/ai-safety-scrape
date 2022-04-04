import json
from utils import *
from tqdm import tqdm
import multiprocessing as mp


if __name__ == "__main__":
    arxiv_dict = json.load(open("arxiv_dict_updated.json"))

    new_arxiv_data = []

    # pool = mp.Pool(processes=mp.cpu_count())
    # for _ in tqdm(pool.imap_unordered(add_md_text, ls("out")), total=len(ls("out"))):
    #     pass

    for mdfile in tqdm(ls("out")):
        mdfile = mdfile.split("/")[-1]
        id = mdfile.split("v")[0]
        # print(arxiv_dict[id]["text"])
        with open(f"out/{mdfile}", "r") as f:
            text = f.read()
        arxiv_dict[id]["text"] = text
        # print(arxiv_dict[id]["text"])

    for k, v in tqdm(arxiv_dict.copy().items()):
        print(k)
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
                else:
                    item["paper_version"] = ""
                    arxiv_dict[k] = item
            except:
                pass
            pass
        mdfile = f"out/{item['paper_version']}.md"
        if os.path.exists(mdfile):
            arxiv_dict[k]["good_extraction"] = True
        else:
            arxiv_dict[k]["good_extraction"] = False
        try:
            if arxiv_dict[k]["citation_level"] == 0:
                arxiv_dict[k]["citation_level"] = "0"
        except:
            del arxiv_dict[k]
            continue
        new_arxiv_data.append(arxiv_dict[k])

    # print(arxiv_dict["1903.01567"]["text"])
    for i in range(0, 5):
        print(str(i) + "/ 5")
        print(new_arxiv_data[i]["text"])
        print("----------------------------------------")

    print(len(new_arxiv_data))
    count = 0
    for i in range(0, len(new_arxiv_data)):
        try:
            if new_arxiv_data[i]["citation_level"] == "0":
                count += 1
        except:
            pass
    print(count)

    with open("arxiv_dict_fixed.json", "w") as f:
        json.dump(arxiv_dict, f)

    with open("arxiv_data_list.json", "w") as f:
        json.dump(new_arxiv_data, f)
