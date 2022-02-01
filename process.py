import os
import pickle
from tqdm import tqdm
import spacy
import multiprocessing as mp
from multiprocessing import freeze_support
from string import punctuation


def main():

    PROCESSED_TEXTS_PATH = os.path.join(os.getcwd(), "data/processed/texts")  # output

    with open(f"{PROCESSED_TEXTS_PATH}/all_texts.pkl", "rb") as f:
        results = pickle.load(f)

    print("Loading spacy model...")
    nlp = spacy.load("en_core_web_lg")
    sentences = []
    non_sentences = []  # to check if sentences are being parsed correctly
    i = 0

    print("Processing sentences...")
    for doc in tqdm(nlp.pipe(results, batch_size=512, n_process=-1)):
        num_docsents = 0
        is_sent = 0
        for sent in doc.sents:
            # print(sent.text)
            i += 1
            # print(i)
            if (
                (
                    sent.text[0].istitle()
                    # or sent.text[0] == "•"
                    or sent.text[0].isnumeric()
                    # or sent.text[0] == ""
                )
                and any(p in sent.text[-1] for p in punctuation)
                # and sent.text[0].isalpha()
            ):
                num_docsents += 1
                has_noun = 2
                has_verb = 1
                for token in sent:
                    if token.pos_ in ["NOUN", "PROPN", "PRON"]:
                        has_noun -= 1
                    if token.pos_ in ["VERB"]:
                        has_verb -= 1
                if has_noun <= 0 and has_verb <= 0:
                    is_sent += 1
            else:
                break
        if is_sent >= 1:
            sentences.append(doc.text)
        else:
            non_sentences.append(doc.text)
    # for sentence in sentences:
    #     print(sentence)

    with open(f"{PROCESSED_TEXTS_PATH}/esa_sentences.pkl", "wb") as f:
        pickle.dump(sentences, f)
    with open(f"{PROCESSED_TEXTS_PATH}/esa_non_sentences.pkl", "wb") as f:
        pickle.dump(non_sentences, f)

    with open(f"{PROCESSED_TEXTS_PATH}/esa_sentences.txt", "w") as f:
        for sentence in sentences:
            f.write(sentence + "\n")
    with open(f"{PROCESSED_TEXTS_PATH}/esa_non_sentences.txt", "w") as f:
        for sentence in non_sentences:
            f.write(sentence + "\n")

    print(os.listdir(PROCESSED_TEXTS_PATH))
    print("Done!")


if __name__ == "__main__":
    freeze_support()
    main()
