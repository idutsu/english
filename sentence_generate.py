from transformers import AutoModelForCausalLM, AutoTokenizer
import torch, requests, json, re, time

API_BASE_URL = "https://idutsu.com"

def validate_output(text: str):
    try:
        data = json.loads(text)
        if not isinstance(data, list) or len(data) == 0:
            print("空の配列または配列ではありません")
            return {"data": text, "error": "空の配列または配列ではありません"}
        for i, item in enumerate(data, start=1):
            if not isinstance(item, dict):
                return {"data": text, "error": f"{i} 番目の要素は辞書型ではありません: {item}"}
            if "en" not in item or "ja" not in item:
                return {"data": text, "error": f"{i} 番目の要素に 'en' または 'ja' がありません: {item}"}
            if re.search(r"[ぁ-んァ-ン一-龥々]", item["en"]):
                return {"data": text, "error": f"{i} 番目の要素の 'en' に日本語が含まれています: {item['en']}"}
            if re.search(r"[a-zA-Z]", item["ja"]):
                return {"data": text, "error": f"{i} 番目の要素の 'ja' にアルファベットが含まれています: {item['ja']}"}
            if re.search(r"[{}\[\]<>]", item["ja"]):
                return {"data": text, "error": f"{i} 番目の要素の 'ja' に不正な記号が含まれています: {item['ja']}"}
            if re.search(r"[{}\[\]<>]", item["en"]):
                return {"data": text, "error": f"{i} 番目の要素の 'en' に不正な記号が含まれています: {item['en']}"}
        return {"data": data, "error": None}
    except json.JSONDecodeError as e:
        return {"data": text, "error": f"JSONDecodeError: {e.msg} at pos {e.pos}"}

# モデル読み込み
MODEL_PATH = "/models/Llama-3-ELYZA-JP-8B"
print("モデル（Llama-3-ELYZA-JP-8B）を読み込んでいます...")
tok = AutoTokenizer.from_pretrained(MODEL_PATH)
if tok.pad_token_id is None and tok.eos_token_id is not None:
    tok.pad_token = tok.eos_token
model = AutoModelForCausalLM.from_pretrained(
    MODEL_PATH,
    device_map="auto",
    torch_dtype=torch.float16
).eval()

sys = (
    "あなたは英語学習のための英語例文ジェネレーターです。"
    "プロンプトで指定されたフレーズを使って英語例文を生成してください。"
    "プロンプトで指定された個数だけ英語例文を生成してください。"
    "英語例文の主語は、指定がなければ必ず「I（私）」にしてください。"
    "出力は必ず有効なJSON配列 ([]) にしてください。"
    'JSON配列内の各要素は必ず{"en": "...", "ja": "..."}の辞書型にしてください。'
    '出力例：[{"en": "I go to school.", "ja": "私は学校に行きます。"},{"en": "I play soccer.", "ja": "私はサッカーをします。"},{"en": "I eat breakfast.", "ja": "私は朝食を食べます。"}]'
    '出力はJSON配列として有効になるよう必ず"["で始まり"]"で終わるようにしてください。'
    "和訳は必ず指定された文言をそのまま使ってください。"
    "出力する英語例文は短くシンプルにしてください。"
    "動詞は一文に付き一回にしてください。"
    "文の途中で接続詞や句読点を使わないでください。"
    "前置きやメタ発言は禁止です。回答のみ出力してください。"
)

# DBからフレーズを取得
r = requests.get(f"{API_BASE_URL}/fetch/phrases", timeout=60)
r.raise_for_status()
phrases = r.json()["rows"]

done = 0

for phrase in phrases:
    en = phrase["en"]
    ja = phrase["ja"]
    phrase_id = phrase["id"]

    user_prompt = f"フレーズ：{en}（{ja}）。 個数：3。"
    messages = [
        {"role": "system", "content": sys},
        {"role": "user", "content": user_prompt}
    ]

    prompt_str = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tok(prompt_str, return_tensors="pt").to("cuda")

    count = 3
    print(f"「{en}（{ja}）」で英語例文を{count}文生成します。")

    with torch.no_grad():
        output_ids = model.generate(
            **inputs,
            max_new_tokens=512,
            do_sample=True,
            temperature=0.8,
            top_p=0.95,
            pad_token_id=tok.pad_token_id or tok.eos_token_id
        )

    input_len = inputs["input_ids"].shape[1]
    generated_ids = output_ids[0][input_len:]
    text = tok.decode(generated_ids, skip_special_tokens=True)

    result = validate_output(text)

    if result["error"] is None:
        # 成功ログ
        print(f"📝 正しいJSONの出力に成功しました")
        out = {"text": text, "phrase": phrase_id, "score": "good"}
        try:
            resp = requests.post(f"{API_BASE_URL}/insert/outputs", json=out, timeout=30)
            resp.raise_for_status()
            print(f"📝 正しいJSON出力の保存に成功しました (phrase_id={phrase_id}):", resp.json())
        except requests.RequestException as e:
            print(f"⚠️ 正しいJSON出力の保存に失敗しました (phrase_id={phrase_id}):", e)
        # 例文をDB（sents）に保存
        payload = [{"en": ex["en"], "ja": ex["ja"], "phrase": phrase_id} for ex in result["data"]]
        try:
            resp = requests.post(f"{API_BASE_URL}/insert/sents", json=payload, timeout=30)
            resp.raise_for_status()
            print(f"✅ 例文の保存に成功しました (phrase_id={phrase_id}):", resp.json())
            conmplete += 1
        except requests.RequestException as e:
            print(f"⚠️ 例文の保存に失敗しました (phrase_id={phrase_id}):", e)
    else:
        # 失敗ログ
        print(f"📝 正しいJSONの出力に失敗しました: result['error']")
        out = {"text": text, "phrase": phrase_id, "score": "bad", "comment": result["error"]}
        try:
            resp = requests.post(f"{API_BASE_URL}/insert/outputs", json=out, timeout=30)
            resp.raise_for_status()
            print(f"📝 誤ったJSON出力の保存に成功しました (phrase_id={phrase_id}):", resp.json())
        except requests.RequestException as e:
            print(f"⚠️ 誤ったJSON出力の保存に失敗しました (phrase_id={phrase_id}):", e)

    # 連投しすぎないように（任意）
    time.sleep(0.3)


print(f"例文生成数:{done} 件")