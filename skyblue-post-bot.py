#!/usr/bin/env python
# coding: utf-8

# In[ ]:


# This Python 3 environment comes with many helpful analytics libraries installed
# It is defined by the kaggle/python Docker image: https://github.com/kaggle/docker-python
# For example, here's several helpful packages to load

import numpy as np # linear algebra
import pandas as pd # data processing, CSV file I/O (e.g. pd.read_csv)

# Input data files are available in the read-only "../input/" directory
# For example, running this (by clicking run or pressing Shift+Enter) will list all files under the input directory

import os
for dirname, _, filenames in os.walk('/kaggle/input'):
    for filename in filenames:
        print(os.path.join(dirname, filename))

# You can write up to 20GB to the current directory (/kaggle/working/) that gets preserved as output when you create a version using "Save & Run All" 
# You can also write temporary files to /kaggle/temp/, but they won't be saved outside of the current session






from atproto import Client

def authenticate_client():
    """
    Authenticate the Bluesky client using credentials.
    """
    # Use environment variables for GitHub Actions
    handle = "katakurikpowder.bsky.social"  # Replace with your Bluesky handle
    password = os.getenv("BLUESKY_PASSWORD")  # Add to GitHub Secrets

    client = Client()
    try:
        client.login(handle, password)
        print("Authenticated successfully!")
        return client
    except Exception as e:
        print("Error during client initialization:", e)
        return None


# In[ ]:


from datetime import datetime, timedelta

def fetch_feed_daily(client, feed_uri):
    """
    Fetch posts from a specific feed for the current day using pagination.
    """
    all_posts = []
    cursor = None  # Start with no cursor (initial request)
    today = datetime.utcnow()
    start_of_day = today.replace(hour=0, minute=0, second=0, microsecond=0)

    while True:
        try:
            # Fetch posts from the feed with pagination
            data = client.app.bsky.feed.get_feed({
                'feed': feed_uri,
                'cursor': cursor,
                'limit': 30,  # Fetch 30 posts per page
            })

            # Process the feed
            feed = data.feed
            for post in feed:
                post_view = post.post
                post_record = post_view.record

                # Stop if the post is older than the start of the day
                if hasattr(post_record, 'createdAt'):
                    post_date = datetime.fromisoformat(post_record.createdAt.replace("Z", "+00:00"))
                    if post_date < start_of_day:
                        print(f"Stopped fetching older posts. Fetched {len(all_posts)} posts total.")
                        return all_posts

                all_posts.append(post)

            # Handle pagination
            cursor = data.cursor
            if not cursor:
                break  # No more pages to fetch

        except Exception as e:
            print("Error during feed fetching:", e)
            break

    print(f"Finished fetching. Total posts fetched: {len(all_posts)}")
    return all_posts


# In[ ]:


import spacy
from collections import Counter
import re

def extract_keywords_nlp(posts):
    """
    Extract meaningful keywords from posts using NLP techniques.
    """
    # Load spaCy language model
    nlp = spacy.load("en_core_web_sm")

    # Combine all post texts
    all_text = " ".join(
        post.post.record.text
        for post in posts
        if hasattr(post.post.record, 'text')
    )

    # Clean text: remove URLs, numbers, and short words
    cleaned_text = re.sub(r"http\S+|www\S+|\d+|\b\w{1,3}\b", "", all_text)

    # Process text using spaCy
    doc = nlp(cleaned_text)

    # Extract Named Entities (e.g., people, organizations, locations)
    named_entities = [ent.text for ent in doc.ents if ent.label_ in {"PERSON", "ORG", "GPE", "EVENT"}]

    # Extract Nouns, Verbs, and Adjectives
    pos_keywords = [token.text.lower() for token in doc if token.pos_ in {"NOUN", "VERB", "ADJ"} and not token.is_stop]

    # Combine entities and POS keywords
    all_keywords = named_entities + pos_keywords

    # Return the most common keywords
    return Counter(all_keywords).most_common(20)


# In[ ]:


import random
from collections import defaultdict

def identify_entity_relationships(posts):
    """
    Analyze relationships between entities by co-occurrences in posts.
    """
    nlp = spacy.load("en_core_web_sm")
    relationship_counts = defaultdict(int)
    for post in posts:
        if hasattr(post.post.record, 'text'):
            text = post.post.record.text
            doc = nlp(text)
            entities = [ent.text for ent in doc.ents if ent.label_ in {"PERSON", "ORG"}]
            for i in range(len(entities)):
                for j in range(i + 1, len(entities)):
                    pair = tuple(sorted([entities[i], entities[j]]))
                    relationship_counts[pair] += 1
    return sorted(relationship_counts.items(), key=lambda x: -x[1])

def generate_contextual_post(relationships, keywords):
    """
    Generate a post that considers relationships and context.
    """
    # Use top relationship pairs
    if relationships:
        top_relationship = relationships[0][0]  # Most common pair
        entity1, entity2 = top_relationship
    else:
        entity1, entity2 = "Someone", "Something"

    # Choose a template based on common contexts
    templates = [
        "{entity1} has nominated {entity2}—what do you think about this move?",
        "The partnership between {entity1} and {entity2} is stirring debate. What's your take?",
        "Breaking news: {entity1} and {entity2} are making headlines together!",
    ]

    # Randomly pick a template
    template = random.choice(templates)
    return template.format(entity1=entity1, entity2=entity2)


# In[ ]:


from datetime import datetime

def post_to_account(client, post_text):
    """
    Post generated content to your Bluesky account.
    """
    try:
        post_record = {
            "$type": "app.bsky.feed.post",
            "text": post_text,
            "createdAt": datetime.utcnow().isoformat() + "Z"
        }

        response = client.app.bsky.feed.post.create(
            repo=client.me.did,
            record=post_record
        )

        print("Post successful!")
    except Exception as e:
        print("Error posting to account:", e)


# In[ ]:


if __name__ == "__main__":
    # Authenticate
    client = authenticate_client()

    if client:
        # Fetch daily feed
        feed_uri = 'at://did:plc:7mtqkeetxgxqfyhyi2dnyga2/app.bsky.feed.generator/aaadhh6hwvaca'
        daily_posts = fetch_feed_daily(client, feed_uri)

        if daily_posts:
            # Extract keywords
            nlp_keywords = extract_keywords_nlp(daily_posts)
            print("Top Keywords:", nlp_keywords)

            # Analyze relationships and generate post
            relationships = identify_entity_relationships(daily_posts)
            contextual_post = generate_contextual_post(relationships, nlp_keywords)
            print("Generated Post:", contextual_post)

            # Post to Bluesky
            post_to_account(client, contextual_post)

