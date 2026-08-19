from langchain_text_splitters import RecursiveCharacterTextSplitter
import chromadb
import json
from pypdf import PdfReader
from audio_add import speech_to_text
from thread import stream_tts
from strean_llm import stream_llm

#Loading system prompt as text

with open("system_prompt.txt") as f:
    system_prompt = f.read()

#Loading PDF and coverting it into raw text    

path = "/home/alphazerox/Documents/Existentialism_is_Humanism.pdf"

reader = PdfReader(path)

full_text = ""

for page in reader.pages:
    full_text += page.extract_text()

#Defining Text Splitter

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=150,
    length_function=len,
    separators=["\n\n", "\n", ". ", " "]
)

#Applying Text Splitteron text from PDF

text_split = text_splitter.split_text(full_text)

chunks = []

for i, chunk in enumerate(text_split):

    chunks.append({
        "text" : chunk,
        "text_id" : i + 1
    })

#Initiating Chromadb, embedding    

client = chromadb.Client()

collection = client.get_or_create_collection(name="phil_text")

documents = [item["text"] for item in chunks]

ids = [f"chunk_{item['text_id']}" for item in chunks]

#Using batching for easier and faster embeddings

batch_size = 50

for i in range(0, len(chunks), batch_size):
    
    batch_docs = documents[i : i + batch_size]
    batch_ids = ids[i : i + batch_size]
    
    
    collection.upsert(
        documents=batch_docs,
        ids=batch_ids
    )

#conversations, for recording conversations history

conversations = []

def save_history(conversations):

    with open("conversations.json", "w") as f:
        json.dump(conversations, f, indent=2)

#defining con_rag which returns final prompt to be sent to LLM      

def con_rag(question : str):

#Asking query to be mathced with retrieved passages, default results = 3

    result = collection.query(
    query_texts=[question],
    n_results=3,
    include=["documents", "distances"]
)

#Defining Criteria to only add relevant texts, you can change as you want

    relevant_chunks = []

    for doc, dist in zip(result["documents"][0], result["distances"][0]):
        if dist < 1.0:
            relevant_chunks.append(doc)

    if relevant_chunks:
        context_block = "\n\n".join(
            f"Context_{i+1}: {chunk}" for i, chunk in enumerate(relevant_chunks)
        )
    else:
        context_block = "No relevant passages were found for this question. You MUST treat this as out-of-scope — do not answer with unflagged confidence even if you have general knowledge on the topic."   

#Defining Final prompt, contains context, conversation history, and question asked.

    prompt = f"""
    
    Answer the question using the context below.

    context : {context_block}

    Use the contexts only if there's direct connection between them and question asked and don't refer to the contexts in answers.

    Conversations_history : {conversations}

    Question : {question}

"""

#Appending user question.

    conversations.append({
            "role" : "user",
            "content" : question
        })


    return prompt

#Available providers, you can change as you go.

providers = {
     1 : "Mistral",
     2 : "Gemini"
}        

def choose_provider():

    while True:

        print("\nSelect provider:")
        print("1. Mistral")
        print("2. Gemini")

        try:
            provider = int(input("Provider: "))
        except ValueError:
            print("Invalid input. Enter 1, 2, or 3.")
            continue

        if provider in [1, 2]:
            return provider

        print("Invalid input. Choose one of the provided numbers.")


def choose_mode():

    while True:

        print("\nSelect the mode:")
        print("1. Text")
        print("2. Audio")

        try:
            mode = int(input("Mode: "))
        except ValueError:
            print("Invalid input. Enter 1 or 2.")
            continue

        if mode in [1, 2]:
            return mode

        print("Invalid input. Choose 1 or 2.")

         
provider = choose_provider()
mode = choose_mode()

print(f"\nProvider: {providers[provider]}")

if mode == 1:
    print("Mode: Text")
else:
    print("Mode: Audio")


while True:  

    print(f"\nAsk anything to {providers[provider]}")

    if mode == 1:
        question = input("Enter question here: ")
        if question.lower() in ["exit", "quit"]:
                save_history(conversations)
                print("Conversation ended.")
                break   
        else:
             prompt = con_rag(question)
             response = stream_llm(provider, system_prompt, prompt)

             all_res = ""

             for content in response:
                all_res += content
                print(content, end="", flush=True)


        conversations.append({
            "assistant" : all_res
        })

        print()

        print("Ask anything else: ")   
        
        
    elif mode == 2:
        
        question = speech_to_text()

        normalized = question.lower().strip().rstrip(".!?")

        if normalized in ["exit", "quit", "goodbye"]:
                save_history(conversations)
                print("Conversation ended.")
                break   

        else:
             all_res = ""
             prompt = con_rag(question)
             all_res = stream_tts(provider, system_prompt, prompt)

             conversations.append({
                 "assistant" : all_res
             })

             print("Ask anything else: ")

        







