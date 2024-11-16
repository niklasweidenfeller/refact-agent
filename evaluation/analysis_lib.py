""" Utilities for evaluating the experiments """

import os

# SAP Gen AI Hub LLM instance
from gen_ai_hub.proxy.langchain.openai import ChatOpenAI
from gen_ai_hub.proxy.core.proxy_clients import get_proxy_client

# remove terms that are directly related to the code, such
# as function names, class names, file names, etc.
TERMS_TO_REMOVE = [
    "tennisgamedefactored1", "tennisgamedefactored2", "tennisgamedefactored3",
    "tennisgame1", "tennisgame2", "tennisgame3", "tennisgame", 
    "tennis.py", 
    "update_quality", "update_item_quality", "updatequality", 
    "`chance`", 
    "currentcategory", 
    "tojsonobject", 
    "yahtzee.java", 
    "wonpoint", 

    ".java", 
    ".py", 

    "gildedrose", 
    "src/gilded_rose.js", 
    "gilded_rose.js", 
    ".js", 

    "default_stack_size", 
    "getscore", 
    "yahtzee"
]

def remove_specific_terms(term: str) -> str:
    """ Remove specific terms from a given string """
    output = term.lower()
    for to_remove in TERMS_TO_REMOVE:
        output = output.replace(to_remove, "")
    return output.replace("  ", " ").strip()


# Get a SAP Gen AI Hub LLM instance
proxy_client = get_proxy_client('gen-ai-hub')
language_model = ChatOpenAI(
    deployment_id=os.getenv("AI_CORE_DEPLOYMENT_ID"),
    proxy_client=proxy_client,
    temperature=0.0
)


def label_clusters_llm(cluster: list[str]) -> str:
    """ Label a cluster of sentences using a language model """
    res = language_model.invoke(
        f"Respond with a cluster label for following cluster of sentences: \n {cluster}"
    )
    return res.content


def summarize_clusters(cluster_labels: list[str]) -> list[str]:
    """ Summarize cluster labels using a language model """
    r = language_model.invoke(
        f"""
        For each of the cluster labels, respond with a 3-word summary of the cluster.
        In your response, return only the summarized labels, not the original labels.
        Do not include any bullet points or numbers in your response.
        Cluster labels: {cluster_labels}
        """
    )
    return r.content.split("\n")
