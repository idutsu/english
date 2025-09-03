from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

MODEL_PATH = "/models/Llama-3-ELYZA-JP-8B"

print("🔄 モデルロード中...")
tok = AutoTokenizer.from_pretrained(MODEL_PATH)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_PATH,
    device_map="auto",
    torch_dtype=torch.float16
)

messages = [
    {"role": "system", "content": "あなたは英語例文を出すアシスタントです。"},
    {"role": "user", "content": "フレーズ：have to （〜しなければならない） 数：3"}
]
prompt = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)

inputs = tok(prompt, return_tensors="pt").to("cuda")

with torch.no_grad():
    outputs = model.generate(
        **inputs,
        max_new_tokens=100,
        do_sample=True,
        temperature=0.8,
        top_p=0.95,
        pad_token_id=tok.eos_token_id
    )

print("✅ 出力結果:")
print(tok.decode(outputs[0], skip_special_tokens=True))

