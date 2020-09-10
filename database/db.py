import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

class DB():
    def __init__(self, json_path):
        cred = credentials.Certificate(json_path)
        app = firebase_admin.initialize_app(cred) 
        self.db = firestore.client()

    def create_new_user(self, name, hashed_password, bankroll=1000):
        '''
        DB に存在しないことが確認された段階で実行される
        引数の 
        '''
        new_user = User(name=name,
                        hashed_password=hashed_password,
                        bankroll=bankroll,
                        registered_at=firestore.SERVER_TIMESTAMP)
        self.db.collection("user").add(new_user.to_dict())

    def get_user_info(self, input_username, input_hashed_password):
        docs = self.db.collection('user').where(u"name", u'==', input_username).where(u"hashed_password", u"==", input_hashed_password).stream()
        for doc in docs:
            d = doc.to_dict()
            user_info = {
                "document_id": doc.id,
                "name": d["name"]
            }
        return user_info

    def check_user_existance(self, input_username, input_hashed_password):
        # ユーザーIDを取得できなかったら存在しないと判断する
        uid = []
        docs = self.db.collection('user').where(u"name", u'==', input_username).where(u"hashed_password", u"==", input_hashed_password).stream()
        for doc in docs:
            uid.append(doc.id)
        if uid:
            # なんか入ってるとき
            return True
        else:
            # 入ってないとき
            return False

    def get_bankroll_from_document_id(self, document_id):
        return self.db.collection(u"user").document(document_id).get().to_dict()["bankroll"]

    def update_bankroll_from_document_id(self, new_bankroll, document_id):
        new_data = {
            "bankroll": new_bankroll
        }
        self.db.collection("user").document(document_id).update(new_data)
    
class User(object):
    def __init__(self, name, hashed_password, bankroll, registered_at):
        # self.user_id = user_id
        self.name = name
        self.hashed_password = hashed_password
        self.bankroll = bankroll
        self.registered_at = registered_at

    @staticmethod
    def from_dict(source):
        # [START_EXCLUDE]
        user = User(name=source[u"name"],
                    hashed_password=source["hashed_password"],
                    bankroll=source[u"bankroll"],
                    registered_at=source[u"registered_at"])

        # 任意で。あるならデフォルト引数を指定する
        # if u"capital" in source:
        #     city.capital = source[u"capital"]

        return user
        # [END_EXCLUDE]

    def to_dict(self):
        # [START_EXCLUDE]
        dest = {
            u"name": self.name,
            u"hashed_password": self.hashed_password,
            u"bankroll": self.bankroll,
            u"registered_at": self.registered_at
        }

        # 任意で。デフォルト引数を指定する
        # if self.capital:
        #     dest[u"capital"] = self.capital

        return dest


# if __name__ == "__main__":
#     a = DB()
#     a.get_user_info("mizuki", "test")
#     print(a.check_user_existance("mizuki", "test"))

    # cred = credentials.Certificate("blackjack-app-1ab6b-firebase-adminsdk-6iwas-253abd9bd1.json")
    # app = firebase_admin.initialize_app(cred) 
    # db = firestore.client()

    # docs = db.collection(u"user").where(u"name", u"==", u"mizuki").stream()
    # for doc in docs:
    #     print(u"{} => {}".format(doc.id, doc.to_dict()))
    #     mizukinoID = doc.id


# docs = db.collection(u"user").where(u"name", u"==", u"mizuki").stream()
# for doc in docs:
#     print(u"{} => {}".format(doc.id, doc.to_dict()))
#     mizukinoID = doc.id

# # 取得した コレクションのプリント
# for doc in docs:
#     print(u"{} => {}".format(doc.id, doc.to_dict()))
# # 変更したい箇所
# data = {
#     u"field": u"変更したバリュー2",
# }

# # .set() でデータの更新
# db.collection(u"collection1").document(u"Hq6v5xzR97mqkHXzh5LZ").set(data)
# ref = db.collection(u"collection1")
# docs = ref.stream()

# for doc in docs:
#     print(u"{} => {}".format(doc.id, doc.to_dict()))
#     # doc.id でドキュメント id を取得できる
#     print(doc.id)

# # ユーザーネームからドキュメントIDを取得
# docs = db.collection(u"game_user").where(u"name", u"==", u"mizuki").stream()
# for doc in docs:
#     print(u"{} => {}".format(doc.id, doc.to_dict()))
#     mizukinoID = doc.id

# # ドキュメントの削除 name: "hoge" というユーザを作成しておく
# docs = db.collection(u"game_user").where(u"name", u"==", u"hoge").stream()
# # name はユニークだという設定、hoge が登録されてない状態で実行すると当然だが　for に入らない
# for doc in docs:
#     print(doc.id)
#     db.collection(u"game_user").document(doc.id).delete()

# # モデルを使ったドキュメントの作成 (複数回実行すると複数回保存されてしまうので注意！)
# # 存在するかどうかのチェックが必要。
# import model
# user = model.User(name="perochan", bankroll=7000, password="peronopasuwa-do", registered_at=firestore.SERVER_TIMESTAMP)
# db.collection(u"game_user").add(user.to_dict())

# # ドキュメントの検索 (username == perochan になるユーザのドキュメントIDを検索するコード)
# docs = db.collection(u"game_user").where(u"name", u"==", u"perochan").stream()
# for doc in docs:
#     print("ぺろちゃんのIDは、", doc.id, "です。")
