//WebSocket接続
var port = String(location.port)
var uri = "test-web-app-mizuki0842.herokuapp.com"
var url = "wss://" + uri + ":" + port + "/pipe"
var connection = new WebSocket(url);

// サーバからメッセージを受け取った時の処理
connection.onmessage = function (event) {
    console.log(event.data);
    json_data = JSON.parse(event.data);

    // プレイヤーの ハンドHTML書き換え
    player_hand_html = document.getElementById("player_hand");
    // player_hand が False の場合、 False の箇所は更新しない
    if (json_data.player_hand != false) {
        // 空に初期化する
        player_hand_html.textContent = '';
        // スプリットハンドのときと通常時とで表示方法を切り替える
        if (json_data.is_split_hand) {
            if (json_data.player_handnum == null) {
                for (let i = 0; i < json_data.player_hand.length; i++) {
                    hand = cardnumToSuit(json_data.player_hand[i]);
                    player_hand_html.insertAdjacentHTML("afterbegin", "<div>" + hand + json_data.result_message[i] + "</div>")
                }
            } else {
                for (let i = 0; i < json_data.player_hand.length; i++) {
                    if (i == json_data.player_handnum) {
                        cursor_pre_split = " ← アクションを選択してください";
                    } else {
                        cursor_pre_split = "";
                    }
                    hand = cardnumToSuit(json_data.player_hand[i]);
                    player_hand_html.insertAdjacentHTML("afterbegin", "<div>" + hand + cursor_pre_split + "</div>")
                }
            }
        } else {
            player_hand_html.innerHTML = cardnumToSuit(json_data.player_hand) + json_data.result_message[0];
        }
    }
    
    // ディーラーの ハンドHTML書き換え
    dealer_hand_html = document.getElementById("dealer_hand");
    // dealer_hand が False の場合、 False の箇所は更新しない
    if (json_data.dealer_hand != false) {
        dealer_hand_html.innerHTML = cardnumToSuit(json_data.dealer_hand);
    }

    // ポップメッセージの更新
    pop_message_html = document.getElementById("pop_message");
    pop_message_html.textContent = '';
    if (json_data.pop_message) {
        // pop_message に メッセージが代入されているとき
        pop_message_html.innerHTML = json_data.pop_message;
    }

    // ボタンのインアクティベート
    document.getElementById("hit").disabled = !json_data.active_button.hit
    document.getElementById("stand").disabled = !json_data.active_button.stand
    document.getElementById("double").disabled = !json_data.active_button.double
    document.getElementById("surrender").disabled = !json_data.active_button.surrender
    document.getElementById("yes").disabled = !json_data.active_button.yes
    document.getElementById("no").disabled = !json_data.active_button.no
    document.getElementById("to_next_game").disabled = !json_data.active_button.to_next_game

    // バンクロールの更新
    if (json_data.player_bankroll != false) {
        bankroll_pre_str = "所持金: "
        document.getElementById("bankroll").innerHTML = bankroll_pre_str + json_data.player_bankroll
    }
}

function exitGame() {
    // TODO: 押すとサーバー側でエラー出るのでその対処
    ret = confirm("ゲームを終了します．よろしいですか？");
    if (ret == true){
        connection.close();
        location.href = "/logout";
    }
}

function action(ele) {
    // 押したボタンの id を送信する関数
    id_value = ele.id;
    dic = {
        "action": id_value,
        "bet_amount": false
    }
    console.log(dic.action)
    if (id_value == "to_next_game") {
        // game_main_container を非表示にする
        document.getElementById("game_main_container").style.display = "none";
        // bet_form を表示する
        document.getElementById("bet_form_container").style.display = "block";
    }
    message = JSON.stringify(dic);
    connection.send(message);
}

function cardnumToSuit(hand) {
    // 仮想カード番号のリスト から マークのリストに変換する関数
    suit_list = ["♥", "♦", "♣", "♠"];
    str_hand = [];
    for (let i = 0; i < hand.length; i++) {
        if (hand[i] == 0) {
            str_hand.push("？？")
        } else {
            num = hand[i] % 100;
            suit = suit_list[(hand[i] - num) / 100 - 1];
            str_hand.push(suit + String(num));
        }
    }
    return str_hand;
}

function select_bet_amount(ele) {
    // 押された bet button の id を取得して、送信
    str_bet_amount = ele.id;
    console.log(str_bet_amount)
    // json送信
    dic = {
        "action": false,
        "bet_amount": str_bet_amount
    }
    connection.send(JSON.stringify(dic))
    // game_main_container を表示する
    document.getElementById("game_main_container").style.display = "block";
    // bet_form を非表示にする
    document.getElementById("bet_form_container").style.display = "none";
    // bet_amount に bet 額を表示する
    bet_amount_pre_str = "ベット額: "
    document.getElementById("bet_amount").innerHTML = bet_amount_pre_str + str_bet_amount;
}