# -*- coding: utf-8 -*-
"""Copy of GNN

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1zUq0vHwkg0SXbiuglpBXCvHwofBw_tVS
"""

!pip install torch-geometric
!pip install dgl

#import libraries
import pandas as pd
import networkx as nx
from google.colab import drive
import torch
from torch_geometric.utils import from_networkx
from torch_geometric.data import Data
import torch.nn.functional as F
from torch_geometric.nn import GCNConv
import matplotlib.pyplot as plt
from tqdm import tqdm
from sklearn.cluster import DBSCAN
from transformers import BertTokenizer, BertModel
import torch.nn as nn
import dgl
# from dgl.nn.pytorch import GraphConv
import torch.optim as optim
from collections import Counter
from wordcloud import WordCloud
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

drive.mount('/content/drive')

# Load your dataset
# songs_df = pd.read_csv('drive/MyDrive/KBHS_Group_Project/data/songs_dataset.csv')
artists_terms_df = pd.read_csv('drive/MyDrive/data/artist_terms.csv')
songs_pros_df = pd.read_csv('drive/MyDrive/data/song_preprocessed.csv')

songs_pros_df

artists_terms_df

songs_pros_df.shape

artists_terms_df.shape

songs_pros_df['song_id'].nunique()

artists_terms_df['artist_id'].nunique()

# Attributes to normalize
# attributes = ['duration', 'tempo', 'loudness']

# # Normalisation
# scaler = MinMaxScaler()
# songs_pros_df[attributes] = scaler.fit_transform(songs_pros_df[attributes])

# Initialize the NetworkX graph
nx_graph = nx.Graph()

for index, row in tqdm(songs_pros_df.iterrows()):
    song_id = row['song_id']
    artist_id = row['artist_id']
    song_title = row['song_title']
    artist_name = row['artist_name']
    decade = row['decade']

    # Add nodes for song and artist
    nx_graph.add_node(song_id, type='song', name=row['song_title'],tempo=row['tempo'], loudness=row['loudness'],
                      duration=row['duration'],song_hotttnesss=row['song_hotttnesss'])
    # nx_graph.add_node(song_title, type='title')
    nx_graph.add_node(decade, type='decade', year=row['year'])
    nx_graph.add_node(artist_id, type='artist',name=row['artist_name'],location=row['artist_location'],
                      artist_hotttnesss=row['artist_hotttnesss'], artist_familiarity=row['artist_familiarity'])
    # nx_graph.add_node(artist_name, type='artist_name')

    # Add edge between song and artist
    nx_graph.add_edge(song_id, artist_id, relationship='performedBy')
    # nx_graph.add_edge(song_id, song_title, relationship='hasTitle')
    # nx_graph.add_edge(artist_id, artist_name, relationship='artistName')
    nx_graph.add_edge(song_id, decade, relationship='ofDecade')

# Add artists and their terms
for index, row in tqdm(artists_terms_df.iterrows()):
    artist_id = row['artist_id']
    term = row['term']
    nx_graph.add_node(artist_id, type='artist')  # This line is added to ensure artist nodes exist before connecting terms
    nx_graph.add_node(term, type='term')
    nx_graph.add_edge(artist_id, term, relationship='categorize')

print(nx_graph)

g = dgl.from_networkx(nx_graph)

num_nodes = g.num_nodes()
num_features = 5  # Example feature size
node_features = torch.randn(num_nodes, num_features)

g.ndata['feat'] = node_features

class GNN(nn.Module):
    def __init__(self, in_feats, h_feats, num_classes):
        super(GNN, self).__init__()
        self.conv1 = GraphConv(in_feats, h_feats)
        self.conv2 = GraphConv(h_feats, num_classes)

    def forward(self, g, in_feat):
        h = self.conv1(g, in_feat)
        h = torch.relu(h)
        h = self.conv2(g, h)
        return h

model = GNN(in_feats=num_features, h_feats=10, num_classes=2)  # Example dimensions

labels = torch.randint(0, 2, (num_nodes,))

# Use cross entropy loss and Adam optimizer
loss_fn = nn.CrossEntropyLoss()
optimizer = optim.Adam(model.parameters(), lr=0.01)

for epoch in range(100):
    model.train()
    logits = model(g, g.ndata['feat'])
    loss = loss_fn(logits, labels)

    optimizer.zero_grad()
    loss.backward()
    optimizer.step()

    print('Epoch %d | Loss: %.4f' % (epoch, loss.item()))

torch.save(model.state_dict(), 'gnn_music_recommendation.pth')

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

def find_most_relevant_string(query, string_list):
    # Include the query in the list to compute the TF-IDF matrix
    all_strings = string_list + [query]

    # Compute the TF-IDF matrix
    vectorizer = TfidfVectorizer().fit_transform(all_strings)

    # Compute the cosine similarity matrix
    cosine_similarities = cosine_similarity(vectorizer[-1], vectorizer).flatten()

    # Get the index of the most similar string excluding the query itself
    most_similar_idx = np.argmax(cosine_similarities[:-1])

    return string_list[most_similar_idx]

string_list = list(songs_pros_df['song_title'].unique())+list(songs_pros_df['decade'].unique())+list(songs_pros_df['artist_name'].unique())+list(artists_terms_df['term'].unique())

string_list = [s.lower() for s in string_list]

model.load_state_dict(torch.load('gnn_music_recommendation.pth'))

model.eval()

relavant_songs = []

def recommend_songs(input_query, top_k=5):
    # Find the node IDs that match the input query
    input_query = input_query.lower()

    if input_query in string_list:
      most_relevant = input_query
    else:
      most_relevant = find_most_relevant_string(input_query, string_list)
    node_ids = [node for node in nx_graph.nodes if most_relevant.lower() in str(node).lower() or
                any(most_relevant.lower() in str(data).lower() for data in nx_graph.nodes[node].values())]
    if node_ids:
        node_id = node_ids[0]
        # Find related songs if the node is found
        if nx_graph.nodes[node_id]['type'] == 'song':
          related_songs=[node_id]
          remaining_slots = top_k - len(related_songs)

        related_songs = [neighbor for neighbor in nx_graph.neighbors(node_id) if nx_graph.nodes[neighbor]['type'] == 'song']

        relavant_songs.append(related_songs)

        # If there are more than top_k related songs, return the top_k related songs
        if len(related_songs) >= top_k:


          return related_songs[:top_k]

        # If there are less than top_k related songs, find similar songs to fill the remaining spots
        remaining_slots = top_k - len(related_songs)

    else:

        related_songs = []
        remaining_slots = top_k

    # Compute node embeddings
    with torch.no_grad():
        embeddings = model(g, g.ndata['feat'])

    # Get the embedding for the input query if it exists, otherwise use a dummy node
    if node_ids:
        input_node_embedding = embeddings[list(nx_graph.nodes).index(node_id)]
    else:
        input_node_embedding = torch.randn(1, num_features)

    # Compute cosine similarities between the input node and all other songs
    similarities = torch.nn.functional.cosine_similarity(input_node_embedding.unsqueeze(0), embeddings, dim=1)

    # Get the top_k most similar song nodes
    song_indices = [i for i, node in enumerate(nx_graph.nodes(data=True)) if node[1]['type'] == 'song' and node[0] not in related_songs]
    song_similarities = similarities[song_indices]
    top_k_song_indices = torch.topk(song_similarities, remaining_slots).indices

    # Map indices back to song IDs
    recommended_songs = related_songs + [list(nx_graph.nodes)[song_indices[i]] for i in top_k_song_indices]


    return recommended_songs

# Get user input
input_query = input("Enter your search query (e.g., 90s songs, artist name, song name): ")

# Get recommendations
recommendations = recommend_songs(input_query)
print(f'Recommendations for "{input_query}": {recommendations}')

filtered_df = songs_pros_df[songs_pros_df['song_id'].isin(recommendations)]
filtered_df

artist = list(filtered_df['artist_id'])
filtered_df_art = artists_terms_df[artists_terms_df['artist_id'].isin(artist)]
# Combine all terms into a single string
all_terms = ' '.join((filtered_df_art['term'].unique()).tolist()+filtered_df['decade'].tolist()+filtered_df['song_title'].tolist()+filtered_df['artist_name'].tolist())

# Generate the word cloud
wordcloud = WordCloud(width=800, height=400, background_color='white').generate(all_terms)

# Display the word cloud
plt.figure(figsize=(10, 5))
plt.imshow(wordcloud, interpolation='bilinear')
plt.title('Word Cloud')
plt.axis('off')
plt.show()

# def precision_recall(recommended_songs, relevant_songs):
#     recommended_set = set(recommended_songs)
#     relevant_set = set(relevant_songs)

#     true_positives = len(recommended_set & relevant_set)
#     precision = true_positives / len(recommended_set) if len(recommended_set) > 0 else 0
#     recall = true_positives / len(relevant_set) if len(relevant_set) > 0 else 0

#     return precision, recall

# relevant_songs = relavant_songs[0]

# precision, recall = precision_recall(recommendations, relevant_songs)
# print(f"Precision: {precision}, Recall: {recall}")



# Evaluate

def get_features(song_id):
    # Get song id features
    song_data = songs_pros_df[songs_pros_df['song_id'] == song_id]
    if song_data.empty:
        return None
    features = song_data[['song_hotttnesss', 'year', 'normalized_tempo', 'normalized_loudness', 'normalized_duration', 'artist_hotttnesss', 'artist_familiarity']].values
    # if np.isnan(features).any():
    #     return None
    return features

def intra_list_similarity(recommended_songs):
    features_list = [get_features(song_id) for song_id in recommended_songs]

    # Filter none values
    features_list = [f for f in features_list if f is not None]

    # make sure there's more than two songs recommended
    if len(features_list) < 2:
        return 0

    features_matrix = np.vstack(features_list)
    similarity_matrix = cosine_similarity(features_matrix)

    upper_triangular_indices = np.triu_indices(len(recommended_songs), k=1)
    upper_triangular_similarities = similarity_matrix[upper_triangular_indices]

    # Calculate the average similarity
    average_similarity = np.mean(upper_triangular_similarities)

    return average_similarity


# Recommendations
recommendations = filtered_df['song_id'].tolist()


intrlist = intra_list_similarity(recommendations)
print(f"Intra-list similarity for recommendations: {intrlist:.4f}")