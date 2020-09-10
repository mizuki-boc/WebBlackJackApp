function inputChecker() {
    if (document.form1.username.value == "") {
        // 名前フォームが空の場合
        alert("名前を入力してください")
        return false
    } else {
        return true
    }
}