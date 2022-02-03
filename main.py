import os
from re import A
import time
import pickle
import tika
import multiprocessing as mp
from multiprocessing import freeze_support
from text_extractor import extractText
import argparse
from itertools import repeat


def main():

    parser = argparse.ArgumentParser(
        description="Adds custom flags for the text extractor."
    )
    # parser.add_argument(
    #     "-o",
    #     "--overwrite_pkls",
    #     type=bool,
    #     help="Overwrites saved pickle files of extracted text.",
    #     default=False,
    # )
    args = parser.parse_args()

    TEXTS_PATH = "./data/raw_texts/texts/"
    PROCESSED_TEXTS_PATH = "./data/processed/texts/"

    def list_of_text_filepaths(TEXTS_PATH):
        list_of_texts = []
        for file in os.listdir(TEXTS_PATH):
            if file.endswith(".txt"):
                list_of_texts.append(TEXTS_PATH + file)
        return list_of_texts

    list_of_texts = list_of_text_filepaths(TEXTS_PATH)

    # Multiprocessing
    start_time = time.time()
    results = []
    with mp.Pool(mp.cpu_count()) as pool:
        results.extend(pool.starmap(extractText, zip(list_of_texts), chunksize=1))
    print("--- %s seconds ---" % (time.time() - start_time))

    # Flatten the list of lists
    results = [item for sublist in results for item in sublist]

    # Save the results
    with open(PROCESSED_TEXTS_PATH + "all_texts.pkl", "wb") as f:
        pickle.dump(results, f)


if __name__ == "__main__":
    freeze_support()
    main()
