import argparse
import os
import json
import datetime
import time

from gevent.pywsgi import WSGIServer
from geventwebsocket.handler import WebSocketHandler

from flask import Flask, request, render_template, request, redirect, session

import numpy as np
import random
import hashlib

import readchar

import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

import key

app = Flask(__name__)
app.secret_key = key.SECRET_KEY

# from database.models.user import User
from database.db import DB

game_db = DB(json_path="database/blackjack-app-1ab6b-firebase-adminsdk-6iwas-253abd9bd1.json")

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/game", methods=["GET", "POST"])
def game():
    if request.form["username"] == "":
        redirect("/")
    if request.method == "GET":
        return redirect("/")
    else:
        input_username = request.form["username"]
        input_password = request.form["password"]
        # input_hashed_password = hash_password(request.form["password"])
        # user 情報が存在するかのチェック
        if game_db.check_user_existance(input_username=input_username, input_hashed_password=hash_password(input_password)):
            # 存在するとき、情報読み取る
            user_info_dict = game_db.get_user_info(input_username=input_username,
                                                input_hashed_password=hash_password(input_password))
            login_username = user_info_dict["name"]
            # ドキュメント ID をセッション管理して、ユーザ認証する
            session["document_id"] = user_info_dict["document_id"]
            session["new_user"] = False
            # session["user_id"] = user_info_dict["user_id"]
            # session["name"] = user_info_dict["name"]
            # session["password"] = user_info_dict["password"]
        else:
            # TODO: 存在しないとき、新規登録
            game_db.create_new_user(name=input_username,
                                    hashed_password=hash_password(input_password))
            # 登録後、読み込み
            user_info_dict = game_db.get_user_info(input_username=input_username,
                                                input_hashed_password=hash_password(input_password))
            login_username = user_info_dict["name"]
            # ドキュメント ID をセッション管理して、ユーザ認証する
            session["document_id"] = user_info_dict["document_id"]
            session["new_user"] = True
        new_user_message = "新規登録しました" if session["new_user"] else ""
        return render_template("game.html", user_name=login_username, new_user_message=new_user_message)

@app.route("/logout")
def logout():
    session.pop("document_id", None)
    session.pop("new_user", None)
    return redirect("/")

@app.route('/pipe')
def pipe():
    if request.environ.get('wsgi.websocket'):
        ws = request.environ['wsgi.websocket']
        while True:
            main(ws=ws)
        ws.close()
    return 200

def hash_password(password):
    text = password.encode("utf-8")
    result = hashlib.sha512(text).hexdigest()
    return result

def main(ws):
    class Player:
        def __init__(self, name, bankroll):
            self.name = name
            # self.bankroll = 1000
            self.bankroll = bankroll
            self.original_bet = 0
            self.bet_amount = []
            self.income = 0
            self.hand = []
            self.is_blackjack = False
            self.bet_insurance = False
            self.bet_surrender = False
            self.split = False
            self.is_win = []
            # TODO: bankroll を firestore からロードする

        def bet(self, original_bet):
            self.original_bet = original_bet
            self.bet_amount.append(self.original_bet)
            print("bet amount =", self.bet_amount)

        def key_input(self, hand_num, can_hit_flag=True, can_double_flag=True, can_surrender_flag=True):
            # キーボード入力を受け付ける関数．CLI デバッグ用．
            # キー入力に対してアクションを決定する
            print("=== ", self.name, "s turn ! ===")
            print(self.hand[hand_num])
            print("Hit = h key")
            print("Stand = s key")
            if can_double_flag:
                print("Double down = d key")
            if can_surrender_flag:
                print("Surrender = u key")
            # json送信
            active_button = create_active_button_dictionary(can_hit_flag=True,
                                                            can_stand_flag=True,
                                                            can_double_flag=True,
                                                            can_surrender_flag=True)
            send_json_data(ws=ws,
                        pop_message="アクションを選択してください",
                        active_button=active_button)
            # stand は常に可能
            key_word = ["stand"]
            if can_hit_flag:
                key_word.append("hit")
            if can_double_flag:
                key_word.append("double")
            if can_surrender_flag:
                key_word.append("surrender")
            key = receive_action_input(ws, key_word)
            if key == "stand":
                # stand
                pass
            elif key == "hit" and can_hit_flag:
                # hit
                self.hand[hand_num].append(deck.draw())
                # json送信
                active_button = create_active_button_dictionary(can_hit_flag=True, can_stand_flag=True)
                send_json_data(ws=ws, player_hand=self.hand, active_button=active_button)
                # burst 確認
                if 0 < calc_hand(self.hand[hand_num]) < 21:
                    # 一度ヒットした場合．次はヒットかスタンドのみ
                    d = {"can_hit_flag": True, "can_double_flag": False, "can_surrender_flag": False}
                    self.key_input(hand_num, **d)
                elif calc_hand(self.hand[hand_num]) == 21:
                    return
                elif calc_hand(self.hand[hand_num]) == 0:
                    print(p.name, "burst !")
            elif key == "double" and can_double_flag:
                # double
                print("double down !")
                self.bet_amount[hand_num] = self.bet_amount[hand_num] * 2
                print("bet amount =", self.bet_amount)
                # ダブルダウンした場合．次はヒットかスタンドのみ，それで終了．
                # json送信
                active_button = create_active_button_dictionary(can_hit_flag=True, can_stand_flag=True)
                send_json_data(ws=ws, pop_message="アクションを選択してください", active_button=active_button)
                print("Hit = h key")
                print("Stand = s key")
                # key = ord(readchar.readchar())
                key = receive_action_input(ws, ["hit", "stand"])
                if key == "hit":
                    self.hand[hand_num].append(deck.draw())
                    # json送信
                    send_json_data(ws=ws, player_hand=self.hand)
            elif key == "surrender" and can_surrender_flag:
                # surrender
                self.bet_surrender = True
        def insurance(self):
            # 呼ばれた時に insurance するかしないか選択する．
            # した場合， self.bet_insurance = True
            print("Insurance ? - y/n")
            # json送信
            active_button = create_active_button_dictionary(can_select_yes_flag=True, can_select_no_flag=True)
            send_json_data(ws=ws,
                        pop_message="インシュランスしますか？",
                        active_button=active_button)
            key = receive_action_input(ws=ws, key_word=["yes", "no"])
            if key == "yes":
                # y
                print("insurance accepted!")
                self.bet_insurance = True
            elif key == "no":
                # n
                print("insurance rejected!")
                self.bet_insurance = False

    class Dealer:
        def __init__(self):
            self.hand = []
            self.is_blackjack = False
        def action(self):
            while 0 < calc_hand(self.hand) < 17:
                # hit 
                self.hand.append(deck.draw())
                # json送信
                send_json_data(ws=ws,
                                player_hand=False,
                                dealer_hand=self.hand,
                )
            
    class Deck:
        def __init__(self,deck_num):
            self.deck_num = deck_num#何デックか
            self.num = [1,2,3,4,5,6,7,8,9,10,11,12,13]
            # self.num = ["A", "2" ,"3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K"]
            self.suit = [100,200,300,400] * deck_num
            # self.suit = ["H", "D", "C", "S"]
            self.deck = np.zeros(len(self.num) * len(self.suit), dtype = int)
            self.draw_count = 0#ドローカウント
            self.left_card_count = np.full(13,4) * self.deck_num
            self.card_count = 0#カードカウンティング用変数
            #print(self.left_card_count)
            c = 0#カウント用
            for s in range(len(self.suit)):
                for n in range(len(self.num)):
                    self.deck[c] = self.num[n] + self.suit[s]
                    c = c + 1
            self.shuffle()
            #print(self.deck)
        def shuffle(self):
            self.draw_count = 0#ドローカウントの初期化
            random.shuffle(self.deck)
            #print(self.deck)
        def draw(self):
            drawn_card = self.deck[self.draw_count]
            drawn_card_num = drawn_card % 100
            self.left_card_count[drawn_card_num - 1] -= 1
            self.draw_count += 1
            self.card_count += self.card_counting(drawn_card)
            return drawn_card
        def calc_prob(self,obj_num):
            return self.left_card_count[obj_num - 1] / np.sum(self.left_card_count) * 100
        def card_counting(self, card):
            num = card % 100
            if num in [10,11,12,13,1]:
                return -1
            elif num in [7,8,9]:
                return 0
            elif num in [2,3,4,5,6]:
                return +1

    def calc_hand(hand_array):
        score = 0
        ace_count = 0
        for card in hand_array:
            num = card % 100
            if num in [2,3,4,5,6,7,8,9]:
                score += num
            elif num in [10,11,12,13]:
                score += 10
            elif num in [1]:
                ace_count += 1
        # A の補正計算
        for _ in range(ace_count):
            if score + 11 > 21:
                score += 1
            else:
                score += 11
        if score > 21:
            score = 0
        return score
    
    def create_active_button_dictionary(can_hit_flag=False,
                                        can_stand_flag=False,
                                        can_double_flag=False,
                                        can_surrender_flag=False,
                                        can_select_yes_flag=False,
                                        can_select_no_flag=False,
                                        can_move_to_next_game=False):
        '''
        デフォルトの false は非表示を表す。
        表示したいボタンのフラグに true を立てて ディクショナリを作成する。
        '''
        active_button = {
            "hit": can_hit_flag,
            "stand": can_stand_flag,
            "double": can_double_flag,
            "surrender": can_surrender_flag,
            "yes": can_select_yes_flag,
            "no": can_select_no_flag,
            "to_next_game" : can_move_to_next_game
        }
        return active_button

    def send_json_data(
                    ws,
                    player_hand=False,#False ならフロントの player_hand は更新しない
                    player_handnum = None,
                    dealer_hand=False,#False ならフロントの dealer_hand は更新しない
                    is_split_hand=False,
                    pop_message="アクションを選択してください",
                    active_button={"hit":False,
                                "stand":False,
                                "double":False,
                                "surrender":False,
                                "yes": False,
                                "no": False,
                                "to_next_game": False},
                    player_bankroll=False,
                    result_message=[""]):
        '''
        ハンドにカードを追加し、追加したタイミングでブラウザに json を投げる関数
        カードを追加せずに json を投げる場合は add_card には False を代入する
        - json の内容
        ws = ソケットの変数
        player_hand = プレイヤーのハンド
        player_handnum = プレイヤーのどっちのハンドか示す。
        dealer_hand = ディーラーのハンド
        is_player_win = 0=未完了, 1=勝ち, 2=プッシュ, 3=負け, 4=サレンダー
        is_split_hand = スプリットしてるかどうか、True ならスプリットしてる状態
        pop_message = ブラウザに表示させるメッセージ
        active_button = 実行可能なアクションボタンを通知する．create_active_button_dictionary()で作成可
        player_bankroll = プレイヤーのバンクロール
        result_message = 結果表示
        '''
        # player hand を int にキャスト
        if player_hand == False:
            # Flase の場合、フロントの更新なし
            int_player_hand = False
        else:
            int_player_hand = []
            if is_split_hand:
                for hand_num in range(len(player_hand)):
                    hand_tmp = []
                    for c in player_hand[hand_num]:
                        hand_tmp.append(int(c))
                    int_player_hand.append(hand_tmp)
            else:
                for c in player_hand[0]:
                    int_player_hand.append(int(c))
        # dealer hand を int にキャスト
        if dealer_hand == False:
            int_dealer_hand = False
        else:
            int_dealer_hand = []
            for c in dealer_hand:
                int_dealer_hand.append(int(c))
        # json 投げる
        ws.send(json.dumps(
            {
                "player_hand": int_player_hand,
                "player_handnum": player_handnum,
                "dealer_hand": int_dealer_hand,
                "is_split_hand": is_split_hand,
                "pop_message": pop_message,
                "active_button": active_button,
                "player_bankroll": player_bankroll,
                "result_message": result_message
            }))

    def receive_action_input(ws, key_word):
        '''
        フロントから json が送信されてくるので、
        keyword に含まれているワードが帰ってくるまで待ち、
        json の "action" のキーを取り出す
        '''
        flag = True
        while flag:
            key = json.loads(ws.receive())
            if key["action"] in key_word:
                flag = False
        return key["action"]
    
    def receive_bet_input(ws):
        '''
        フロントから json が送信されてくるので、
        json の "bet_amount" のキーを取り出す
        '''
        # TODO: receive_action_input() と統合するか考える
        key = json.loads(ws.receive())["bet_amount"]
        print(key)
        if key:
            # bet 額に false が代入されていないとき
            return int(key)
        else:
            pass

    GAME_REPEAT = 2
    deck = Deck(3)

    print("------------------------ GAME START ------------------------")
    for _ in range(GAME_REPEAT):
        # リスト初期化
        players = []# プレイヤーインスタンスのリスト
        # 各インスタンス生成
        mizuki = Player(name="mizuki",
                        bankroll=game_db.get_bankroll_from_document_id(session["document_id"]))
        players.append(mizuki)
        # yokosawa = Player("yokosawa")
        # players.append(yokosawa)
        dealer = Dealer()
        # json送信
        for p in players:
            send_json_data(ws=ws,
                        player_bankroll=p.bankroll,
                        pop_message="",
                        active_button=create_active_button_dictionary())
        # - プレイヤーのベット金額を決定する ***
        for p in players:
            original_bet = receive_bet_input(ws=ws)
            p.bet(original_bet=original_bet)
            print(original_bet)
        # - プレイヤーにカードを配る ***
        for p in players:
            p.hand.append([deck.draw()])
        for p in players:
            p.hand[0].append(deck.draw())
        # ブラックジャックかチェック
        for p in players:
            if calc_hand(p.hand[0]) == 21:
                p.is_blackjack = True
            else:
                p.is_blackjack = False
        # - ディーラーにカードを配る
        dealer.hand.append(deck.draw())
        dealer.hand.append(deck.draw())
        # json送信 - hand
        for p in players:
            active_button = create_active_button_dictionary(can_hit_flag=True,
                                                            can_stand_flag=True,
                                                            can_double_flag=True,
                                                            can_surrender_flag=True)
            send_json_data(ws=ws,
                            player_hand=p.hand,
                            dealer_hand=[0, dealer.hand[1]],
                            active_button = active_button
            )
        # A の場合、インシュランス選択
        if dealer.hand[1] % 100 == 1:
            for p in players:
                p.insurance()
        # 勝敗決定処理
        if calc_hand(dealer.hand) == 21:
            # ディーラーがブラックジャックだった場合．
            dealer.is_blackjack = True
        else:
            # - ディーラーがブラックジャックでなかった場合．
            dealer.is_blackjack = False
            # - プレイヤーのアクション ***
            for p in players:
                # プレイヤーが natural 21 でないときのみアクション
                if not p.is_blackjack:
                    # スプリットできるとき
                    if p.hand[0][0] % 100 == p.hand[0][1] % 100:
                        print("split? - y/n")
                        # json送信 - message action
                        active_button = create_active_button_dictionary(can_select_yes_flag=True, can_select_no_flag=True)
                        send_json_data(ws=ws,
                                    pop_message="スプリットしますか？",
                                    active_button=active_button)
                        split_key = receive_action_input(ws=ws, key_word=["yes", "no"])
                        if split_key == "yes":
                            # yes 時の処理
                            p.split = True
                            p.hand.append([p.hand[0].pop(0)])
                            p.bet_amount.append(p.original_bet)
                        elif split_key == "no":
                            # no 時
                            pass
                    # どのハンド(スプリット時)に対するアクションか決めるのが hand_num
                    if p.split:
                        # スプリットしてる場合、action は一回まで。
                        # 二枚目は強制的(?)にヒット
                        for hand_num in range(len(p.hand)):
                            p.hand[hand_num].append(deck.draw())
                        print(p.hand)
                        # 三枚目は hit or stand のみ選択可能
                        # TODO: ここダブルできないの？
                        for hand_num in range(len(p.hand)):
                            # json送信 - hand action
                            active_button = create_active_button_dictionary(can_hit_flag=True, can_stand_flag=True)
                            send_json_data(ws=ws,
                                        player_hand=p.hand,
                                        player_handnum=hand_num,
                                        is_split_hand=p.split,
                                        active_button=active_button)
                            key = receive_action_input(ws, ["hit", "stand"])
                            if key == "hit":
                                p.hand[hand_num].append(deck.draw())
                            elif key == "stand":
                                pass
                            print(p.hand[hand_num])
                        # json送信
                        send_json_data(ws=ws,
                                        player_hand=p.hand,
                                        is_split_hand=p.split,
                        )
                    else:
                        for hand_num in range(len(p.hand)):
                            p.key_input(hand_num)# メソッド内で json 送信してる
            # - ディーラーのアクション
            dealer.action()
        # アクション終了後の手札表示処理
        print("dealer hand", dealer.hand)
        for p in players:
            print(p.name, p.hand)
        # 勝敗の決定
        result_message_list = {
            0: "",
            1: "結果: 勝ち",
            2: "結果: Push!",
            3: "結果: 負け",
            4: "結果: サレンダーしました"
        }
        for p in players:
            if p.bet_surrender:
                print(p.name, "surrendered.")
                is_player_win = 4
                p.is_win.append(result_message_list[is_player_win])
            else:
                if dealer.is_blackjack:# ディーラーが　BJ だった場合．
                    # この場合，split に入らないので，必ず bet_amount[0]
                    if p.is_blackjack:
                        # Push
                        print("Push!")
                        is_player_win = 2
                        p.is_win.append(result_message_list[is_player_win])
                    else:
                        # プレイヤーの負け
                        print("dealers blackjack!")
                        p.income -= p.bet_amount[0]
                        is_player_win = 3
                        p.is_win.append(result_message_list[is_player_win])
                    # insurance 処理
                    if p.bet_insurance:
                        # insurance が適応される場合
                        p.income += p.original_bet
                else:# ディーラーが　BJ でない場合．
                    if p.is_blackjack:
                        # プレイヤーのBJ！
                        # split には入らない．
                        print(p.name, "s blackjack!")
                        p.income += p.original_bet * 1.5
                        is_player_win = 1
                        p.is_win.append(result_message_list[is_player_win])
                    else:
                        # バーストしてないか確認
                        for hand_num in range(len(p.hand)):
                            if calc_hand(dealer.hand) == 0 or calc_hand(p.hand[hand_num]) == 0:
                                # どっちかがバーストしてるとき
                                if calc_hand(dealer.hand) != 0 and calc_hand(p.hand[hand_num]) == 0:
                                    # プレイヤーのみバーストのとき
                                    print(p.name, "lose!")
                                    p.income -= p.bet_amount[hand_num]
                                    is_player_win = 3
                                    p.is_win.append(result_message_list[is_player_win])
                                elif calc_hand(dealer.hand) == 0 and calc_hand(p.hand[hand_num]) != 0:
                                    # ディーラーのみバーストのとき
                                    print(p.name, "s win!")
                                    p.income += p.bet_amount[hand_num]
                                    is_player_win = 1
                                    p.is_win.append(result_message_list[is_player_win])
                                elif calc_hand(dealer.hand) == 0 and calc_hand(p.hand[hand_num]) == 0:
                                    # 両方バーストのとき
                                    print(p.name, "lose!")
                                    p.income -= p.bet_amount[hand_num]
                                    is_player_win = 3
                                    p.is_win.append(result_message_list[is_player_win])
                            else:
                                # スコア勝負
                                if calc_hand(dealer.hand) < calc_hand(p.hand[hand_num]):
                                    print(p.name, "s win! スコア勝負")
                                    p.income += p.bet_amount[hand_num]
                                    is_player_win = 1
                                    p.is_win.append(result_message_list[is_player_win])
                                elif calc_hand(dealer.hand) == calc_hand(p.hand[hand_num]):
                                    # 引き分け時
                                    print("push スコア勝負")
                                    p.income += 0
                                    is_player_win = 2
                                    p.is_win.append(result_message_list[is_player_win])
                                else:
                                    print(p.name, "lose! スコア勝負")
                                    p.income -= p.bet_amount[hand_num]
                                    is_player_win = 3
                                    p.is_win.append(result_message_list[is_player_win])
                    if p.bet_insurance:
                        # insurance 失敗
                        p.income -= p.original_bet
        # - 清算
        for p in players:
            if p.bet_surrender:
                # サレンダーしてた場合、bet 額半額没収
                print(p.name, "s income", -p.original_bet / 2)
                p.bankroll -= p.original_bet / 2
                print(p.name, "s bankroll", p.bankroll)
                p.income = 0
            else:
                print(p.name, "s income", p.income)
                p.bankroll += p.income
                print(p.name, "s bankroll", p.bankroll)
                p.income = 0
        # json送信 - 結果の表示
        # is_player_win と表示するメッセージのマッピング
        print(dealer.hand)
        # json送信
        for p in players:
            active_button = create_active_button_dictionary(can_move_to_next_game=True)
            send_json_data(ws=ws,
                            player_hand=p.hand,
                            dealer_hand=dealer.hand,
                            is_split_hand=p.split,
                            pop_message="",
                            player_bankroll=p.bankroll,
                            active_button=active_button,
                            result_message=p.is_win
            )
            # TODO: 結果を DB に保存
            game_db.update_bankroll_from_document_id(
                new_bankroll=p.bankroll,
                document_id=session["document_id"]
            )
        # 次のゲームを続行するかどうかの入力待ち
        receive_action_input(ws, ["to_next_game"])
    # デッキシャッフル
    deck.shuffle()   

if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(
        usage='Usage: python ' + __file__ + ' [--port <port>] [--help]'
    )
    arg_parser.add_argument('-p', '--port', type=int, default=int(os.environ.get('PORT', 8000)), help='port')
    arg_parser.add_argument('-d', '--debug', default=False, help='debug')
    arg_parser.add_argument('--host', default='0.0.0.0', help='host')
    options = arg_parser.parse_args()

    # app.run(debug=options.debug, host=options.host, port=options.port)

    app.debug = options.debug
    host = options.host
    port = ptions.port

    host_port = (host, port)
    server = WSGIServer(
        host_port,
        app,
        handler_class=WebSocketHandler
    )
    server.serve_forever()