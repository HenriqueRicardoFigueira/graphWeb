#!/usr/bin/python
# -*- coding: utf-8 -*-
import unicodedata
import requests
import json
import bsonjs
import datetime,time
import multiprocessing as mtp
import networkx as nx
import matplotlib.pyplot as plt
import networkx.drawing
import operator
from itertools import chain
from bson.json_util import dumps, loads
from bson.raw_bson import RawBSONDocument
from pymongo import MongoClient
from joblib import Parallel, delayed
from networkx.algorithms.approximation import clique
from flask import Flask, session, request, render_template, redirect, url_for, Response

api_key = "7CA772628D17EB61985E3FBF61D124B6"

urlfriend = "http://api.steampowered.com/ISteamUser/GetFriendList/v0001/?key={}&steamid={}&relationship=friend"
urlGame =   "http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?key={}&steamid={}&format=json"


app = Flask(__name__)
app.secret_key = 'M@rekdsd*&6465445646asd!#$%'

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
        k = cursor.update({"user_id":user_id},{"$push":{"friend_List":{"user_id":friendClean,"friend_List":friendsaux,"game_List":gamelistaux}}})
        print k

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

def createBD(user_id):
    print user_id

    cursor = db[user_id]
    
    friends = "http://api.steampowered.com/ISteamUser/GetFriendList/v0001/?key={}&steamid={}&relationship=friend".format(api_key,user_id)
    urlGames = "http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?key={}&steamid={}&format=json".format(api_key,user_id)
    
    #pega amigos do usuario
    responseFriends = requests.get(friends)
    userFriendList = []

    #trata retorno de friends da steam pq tem 3 nvs
    try:
        userId_ListAux = responseFriends.json()
        userId_ListAuxNv1 = userId_ListAux.get("friendslist")
        userId_ListAuxNv2 = userId_ListAuxNv1.get("friends")
        userId_List = list(userId_ListAuxNv2)
    except:
        db[user_id].drop({})
        return redirect("/private")
    
    #pega os jogos do usuario
    responseGames = requests.get(urlGames)
    response = responseGames.json()

    usergames_ListAuxNv1 = response.get("response")
    usergames_ListAuxNv2 = usergames_ListAuxNv1.get("games")
    usergames_List = usergames_ListAuxNv2

    if usergames_List == []:
        db[user_id].drop({})
        return redirect("/private")

    cursor.insert_one({"user_id":user_id})

    for i in usergames_List:
        cursor.update({"user_id":user_id},{"$push":{"game_List":i}})
    
    for friend in userId_List:
        id = friend.get("steamid")
        userFriendList.append(id)
    
    urlList = Parallel(n_jobs=mtp.cpu_count())(delayed(requester)(urlfriend,x)for x in userFriendList)

    cleanFriendList = {}

    for x in urlList:
        pai = x.keys()[0]
        try:
            friends = x.get(pai)
        except AttributeError, x:
            # print "key vazia {}".format(x)
            continue

        
        userId_friendsListNv1 = friends.get("friendslist")
        friendsFinalList = []
        try:
            userId_friendsListNv2 = userId_friendsListNv1.get("friends")
            userId_friendsList = list(userId_friendsListNv2)
            
            for friends in userId_friendsList:
                friendsFinalList.append(friends.get("steamid"))
        except AttributeError, x:
            # print "key vazia {}".format(x)
            continue
        
        cleanFriendList[pai] = friendsFinalList

    cleanFriendList = byteify(cleanFriendList)
    FriendGameList = Parallel(n_jobs=mtp.cpu_count())(delayed(requester)(urlGame,x)for x in userFriendList)
    gamedict = {}

    for games in FriendGameList:
        key = games.keys()[0]
        element = games[key]
        game_List = []
        try:
            game_ListAuxNv1 = element.get("response")
            game_ListAuxNv2 = game_ListAuxNv1.get("games")
            game_List = game_ListAuxNv2
        except TypeError:
            continue
        gamedict[key] = game_List


    gamedict = byteify(gamedict)
    insertFriendsNV2(user_id,userFriendList,cursor,cleanFriendList,gamedict)

def graph(user_id):
    G = nx.Graph()

    #cria pai
    G.add_node(user_id)


    booking = dumps(db[user_id].find({},{"friend_List.user_id":1,"_id":0}))
    booking2 = loads(booking)
    friendsnv1 = booking2[0].get("friend_List")

    cleanFriends = []
    for node in friendsnv1:
        id = node.get("user_id")
        cleanFriends.append(id)

    for node in cleanFriends:
        G.add_node(node)
        G.add_edge(user_id, node)

    # print len(cleanFriends)

    for id in cleanFriends:

        userlistFriend = getbffList(id,user_id)

        #for node in userlistFriend:
            #G.add_node(node)

        # print userlistFriend
        for node in userlistFriend:
            if node in cleanFriends:
                G.add_edge(id, node)

    aux = {}
    for (node, val) in G.degree():
        aux[node] = val


    sorted_x = sorted(aux.items(), key=operator.itemgetter(1))

    sort = sorted_x[-11:-1]

    sort_aux  = []
    for item in sort:
        sort_aux.append(item[0])

    x = sort_aux

    x = byteify(x)
    gamesP = {}

    for id in x:
        aux = getgameList(id,user_id)
        if aux != None:
            games = []
            for game in aux:
                x = game.get("appid")
                games.append(x)
            gamesP[id] = games


    gameList = []
    gameFreq = {}

    for id in gamesP.keys():
        user_list_games = gamesP.get(id)
        for game_user in user_list_games:
            if game_user in gameList:
                gameFreq[game_user] = gameFreq[game_user]+1
            else:
                gameFreq[game_user] = 1
                gameList.append(game_user)

    user_gamesAux = db[user_id].find({"user_id":user_id},{"game_List":1,"_id":0})

    user_gamesAuxNV1 = dumps(user_gamesAux)
    user_gamesAuxNV2 = loads(user_gamesAuxNV1)

    user_gamesAuxNV2 = byteify(user_gamesAuxNV2)[0]

    user_gamesAuxNV2 = user_gamesAuxNV2.get("game_List")

    games_user = []
    for game in user_gamesAuxNV2:
        x = game.get("appid")
        games_user.append(x)

    gameFreqAux = []
    for k in gameList:
        if gameFreq[k] > 3:
            gameFreqAux.append(k)

    recomendations = []
    for FreqName in gameFreqAux:
        if FreqName not in games_user:
            frequencia = gameFreq[FreqName]
            aux ={ 
                "game":FreqName,
                "frequencia":frequencia
            }
            recomendations.append(aux)
    
    return recomendations




@app.route("/",methods=['POST','GET'])
@app.route("/index",methods=['POST','GET'])
def index():
    if request.method == "GET":
        return render_template('index.html')

@app.route("/search",methods=['POST','GET'])
def find():
    if request.method == "POST":
        user = request.form.get('user_name')
        user_steamID = getUserId(user)

        cursor = db[user_steamID].find({})
        if list(cursor) != []:
            return redirect("/graph/{}".format(user_steamID))
        else:
            return redirect("/createDB/{}".format(user_steamID))
    else:
        return redirect("/")

@app.route("/createDB/<string:user_id>",methods=['POST','GET'])
def dbCreator(user_id):
    if request.method == "GET":
        createBD(user_id)
        return redirect("/graph/{}".format(user_id))
    else:
        return redirect("/")



@app.route("/graph/<string:user_id>",methods=['POST','GET'])
def graphMaker(user_id):
    if request.method == "GET":
        cursor = db[user_id].find({})
        if list(cursor) != []:
            content_page = graph(user_id)
            return render_template('dashboard.html',content_page=content_page)
        else:
            return redirect("/private")
    else:
        return redirect("/")

@app.route("/private",methods=['POST','GET'])
def private():
    if request.method == "GET":
        return render_template("private.html")
    else:
        return redirect("/")

@app.route("/plot/<string:user_id>",methods=['POST','GET'])
def plot(user_id):
    if request.method == "GET":
        user_friendList = db[user_id].find({"user_id":user_id},{"friend_List.user_id":1,"_id":0})
        user_friendList =  list(user_friendList)[0]
        content_page = []
        listF = []
        for x in user_friendList.get("friend_List"):
            listF.append(x.get("user_id"))

        aux1 = {
            "id":user_id,
            "friend_List":listF,
            "pai":True
        }
        content_page.append(aux1)
        itemsFriends = []
        for item in listF:
            friends = getbffList(item,user_id)
            aux = {
                "id":item,
                "friend_List":friends
            }
            itemsFriends.append(aux)
        content_page.append(itemsFriends)
        

        return render_template('ploty.html',content_page=content_page)

if __name__ == "__main__":
    app.run(debug=False, threaded=False)