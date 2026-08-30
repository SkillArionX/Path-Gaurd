from llm_reader import intelligent_reading

text = "NO PARKING"

question = "What does this sign mean?"

answer = intelligent_reading(text, question)

print("OCR Text:", text)
print("Question:", question)
print("Qwen Answer:", answer)