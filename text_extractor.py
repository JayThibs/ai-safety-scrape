import os
from hashlib import new
import re
import pickle
from tika import parser
from bs4 import BeautifulSoup
from nltk.tokenize import word_tokenize


def tikaTextExtractor(file_path):
    """Extracts text from a PDF using tika."""
    print("Extracting text from file: " + file_path)
    parsed_tika = parser.from_file(file_path)
    return parsed_tika["content"]


def splitText(text):
    """Splits text into paragraphs."""
    return text.split("\n\n")


def multiplePeriods(text):
    """Returns True if there are multiple periods in a row."""
    return re.search(r"\.\.+", text)


def tableTitle(text):
    """Returns True if the text is a table title."""
    return re.search(r"Table\s+\d+", text)


def figureTitle(text):
    """Returns True if the text is a figure title."""
    return re.search(r"Figure\s+\d+", text)


def photoTitle(text):
    """Returns True if the text is a photo title."""
    return re.search(r"Photo\s+\d+", text)


def cleanText(text):
    """Removes HTML tags and special characters from text."""

    text = text.replace("\n", " ")
    text = text.replace("\t", " ")
    text = text.replace("\r", " ")
    text = text.replace("\xa0", " ")
    text = text.replace("\u200b", " ")
    text = text.replace("\u200c", " ")
    text = BeautifulSoup(text, "html.parser").get_text(
        separator=" "
    )  # remove html tags
    text = re.sub("\w{25,}", " ", text)  # remove long words
    text = re.sub("cid\d+", " ", text)  # remove cids
    text = re.sub(" s ", " ", text)  # remove s because of s tags
    text = re.sub(r"\s+", " ", text)  # remove extra spaces
    text = re.sub(r"", " ", text)  # remove bullet points
    text = re.sub(r"•", " ", text)  # remove numbers

    if multiplePeriods(text) is not None:
        return ""  # eliminates titles from paragraph list
    elif tableTitle(text) is not None:
        return ""
    elif figureTitle(text) is not None:
        return ""
    elif photoTitle(text) is not None:
        return ""

    # remove whitespace at the beginning and end of the text
    if len(text) > 25:
        if text[0] == " ":
            text = text[1:]
        if text[-1] == " ":
            text = text[:-1]
        return text
    else:
        return ""


def biggest_multiple(multiple_of, input_number):
    """Returns the biggest multiple of a given number."""
    return (input_number // multiple_of) * multiple_of


def extractText(file_path, overwrite=False):
    """Extracts text from a PDF using tika and returns a list of paragraphs."""
    newTextList = []
    if not os.path.exists(file_path[:-4] + ".pkl") or overwrite:
        text = tikaTextExtractor(file_path)
        print("Extracted text from file: " + file_path)
        print("Splitting text into paragraphs")
        text = splitText(text)
        print("Number of paragraphs: " + str(len(text)))
        max_spacy_token_length = 400
        for i in range(len(text)):
            cleaned_text = cleanText(text[i])
            cleaned_text_tokens = len(word_tokenize(cleaned_text))
            # if cleaned_text_tokens > max_spacy_token_length:
            #     num_text_splits = biggest_multiple(
            #         max_spacy_token_length, cleaned_text_tokens
            #     )
            #     for j in range(num_text_splits):
            #         # TODO: This could be improved by splitting texts based on last period to make sure that sentences are not split in the middle.
            #         # The only issue is to the sentences with words like Mr. or Mrs.
            #         newSplit = cleaned_text[
            #             j * max_spacy_token_length : (j + 1) * max_spacy_token_length
            #         ]
            #         newTextList.append(newSplit)
            # newTextList.append(cleaned_text[(j + 1) * max_spacy_token_length :])

            if (
                cleaned_text_tokens >= 5
                and cleaned_text_tokens <= max_spacy_token_length
            ):
                newTextList.append(cleaned_text)
        print("Saving text to file: " + file_path[:-4] + ".pkl")
        print("Total number of paragraphs: " + str(len(newTextList)))
        with open(file_path[:-4] + ".pkl", "wb") as f:
            pickle.dump(newTextList, f)
    else:
        text_list = pickle.load(open(file_path[:-4] + ".pkl", "rb"))
        print(
            "Text has already been extracted from this PDF. Now grabbing the pickle file for faster processing: "
            + file_path
        )
        newTextList.extend(text_list)
    return newTextList
