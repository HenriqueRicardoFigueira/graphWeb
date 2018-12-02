#!/usr/bin/python3
import json
import requests
import unicodedata
import requests
import json
import bsonjs
import datetime,time
import multiprocessing as mtp
import operator
from math import *
from itertools import chain
from bson.json_util import dumps, loads
from bson.raw_bson import RawBSONDocument
from pymongo import MongoClient
from joblib import Parallel, delayed
from pymongo import MongoClient
from graph_tool.all import *
import random


api_key = "7CA772628D17EB61985E3FBF61D124B6"

urlfriend = "http://api.steampowered.com/ISteamUser/GetFriendList/v0001/?key={}&steamid={}&relationship=friend"
urlGame =   "http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?key={}&steamid={}&format=json"

#banco config
client = MongoClient('localhost', 27017)
db = client["steam_api"]

def getUserId(name):
    global api_key
    urlId = "http://api.steampowered.com/ISteamUser/ResolveVanityURL/v0001/?key={}&vanityurl={}".format(api_key,name)
    response = requests.get(urlId)
    responseId = response.json()
    user_idResponse = responseId.get("response")
    user_id = user_idResponse.get("steamid")
    return user_id


def getbffList(id,user_id):
    final = db[user_id].aggregate([
        {"$match": {"friend_List.user_id": id}},
        {"$addFields" : {"friend_List":{"$filter":{
            "input": "$friend_List",
            "as": "friend_List",
            "cond": {"$eq": ["$$friend_List.user_id", id]}
        }}}}
    ])

    bookingfinal = dumps(final)
    bookingfinal2 = loads(bookingfinal)

    userlistFriend = bookingfinal2[0].get("friend_List")[0].get("friend_List")
    return userlistFriend

def getgameList(id,user_id):
    final = db[user_id].find({"user_id":user_id},{"friend_List":{"$elemMatch":{"user_id": id}}})

    bookingfinal = dumps(final)
    bookingfinal2 = loads(bookingfinal)
    try:
        userlistFriend = bookingfinal2[0].get("friend_List")[0].get("game_List")
    except IndexError:
        userlistFriend = []
        pass
    return userlistFriend

#funcao request
def requester(url,user_id):
    global api_key
    urlFinal = url.format(api_key,user_id)
    resp = requests.get(urlFinal)
    respFormated = resp.json()
    aux = {}
    aux[user_id] = respFormated
    return aux

#funcao inserir no banco
def insertFriends(user_id,friend_list,cursor):
    for friend in friend_list:
        pai = x.keys()[0]
        friends = x.get(pai)
        cursor.update({"user_id":user_id},{"$push":{"friend_List":{"user_id":friend,"friend_List":"","game_List":""}}})

#funcao inserir no banco nv2
def insertFriendsNV2(user_id,friend_list,cursor,friendsNV2,gamelist):
    for friend in friend_list:
        friendClean = byteify(friend)
        try:
            friendsaux = friendsNV2[friendClean]
            gamelistaux = gamelist[friendClean]
        except KeyError, x:
            continue
        cursor.update({"user_id":user_id},{"$push":{"friend_List":{"user_id":friendClean,"friend_List":friendsaux,"game_List":gamelistaux}}})

#limpar json
def byteify(input):
    if isinstance(input, dict):
        return {byteify(key): byteify(value)
                for key, value in input.iteritems()}
    elif isinstance(input, list):
        return [byteify(element) for element in input]
    elif isinstance(input, unicode):
        return input.encode('utf-8')
    else:
        return input

def graph(user_id):
    # G = nx.Graph()
    g = Graph(directed=False)
    v_prop = g.new_vertex_property("string")
    name_v_map = {}

    #cria pai
    v1 = g.add_vertex()
    v_prop[v1] = user_id
    name_v_map[user_id] = v1
    # G.add_node(user_id)


    booking = dumps(db[user_id].find({},{"friend_List.user_id":1,"_id":0}))
    booking2 = loads(booking)
    friendsnv1 = booking2[0].get("friend_List")

    cleanFriends = []
    
    for node in friendsnv1:
        id = node.get("user_id")
        cleanFriends.append(id)

    for node in cleanFriends:
        # G.add_node(node)
        
        v = g.add_vertex()
        v_prop[v] = node
        name_v_map[node] = v
        
        # G.add_edge(user_id, node)
        g.add_edge(name_v_map[user_id], name_v_map[node])

    # print len(cleanFriends)

    for id in cleanFriends:
        userlistFriend = getbffList(id,user_id)
        
        #for node in userlistFriend:
            #G.add_node(node)

        # print userlistFriend

        for node in userlistFriend:
            if node in cleanFriends:
                # G.add_edge(id,node)
                g.add_edge(name_v_map[user_id], name_v_map[node])

    # pos = arf_layout(g)
    # graph_draw(g, pos=pos, vertex_fill_color="blue", edge_color="black", output="blockmodel.pdf", output_size=(300, 300))

    # graph_draw(g, vertex_fill_color="blue", edge_color="black", output="blockmodel.pdf")

    # pos = triangulation(np.random.random((1000,2)))
    # pos = arf_layout(g)
    # graph_draw(g, pos=pos, output="rewire_orig.pdf", output_size=(300, 300))

    # pos = sfdp_layout(g, cooling_step=0.75, epsilon=1e-15)
    # graph_draw(g, pos=pos, output_size=(300,300), output="complete.pdf")

    points = random.randint(2,500) * 4
    g, pos = geometric_graph(points, 0.3)
    graph_draw(g, pos=pos, output_size=(300,300), output="geometric.pdf")


if __name__ == "__main__":
    user_id = getUserId("vnc10")
    graph(user_id)