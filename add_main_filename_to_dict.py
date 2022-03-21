import json

main_tex_dict = json.load(open("main_tex_dict.json"))
arxiv_dict = json.load(open("arxiv_dict.json"))
# new_dict = {}

# for paper_id in main_tex_dict:
#     new_dict[paper_id] = {"main_tex_filename": main_tex_dict[paper_id]}

# json.dump(new_dict, open("main_tex_dict.json", "w"))
# i = 0
# for paper_id in main_tex_dict:
#     main_paper_id = paper_id[:-2]
#     try:
#         if main_paper_id in arxiv_dict:
#             # print(main_tex_dict[paper_id]["main_tex_filename"])
#             arxiv_dict[main_paper_id]["main_tex_filename"] = main_tex_dict[paper_id][
#                 "main_tex_filename"
#             ]
#     except KeyError:
#         pass

for paper_id in arxiv_dict:
    try:
        # if "main_tex_filename" not in arxiv_dict[paper_id]:
        # arxiv_dict[paper_id]["bibliography_bib"] = ""
        # arxiv_dict[paper_id]["bibliography_bbl"] = ""
        # arxiv_dict[paper_id]["arxiv_citations"] = []
        if "author" in arxiv_dict[paper_id]:
            arxiv_dict[paper_id] = {
                "authors" if k == "author" else k: v
                for k, v in arxiv_dict[paper_id].items()
            }
            del arxiv_dict[paper_id]["author"]
    except KeyError:
        pass

# print(arxiv_dict)
json.dump(arxiv_dict, open("arxiv_dict.json", "w"))
