# Talking Books — CLI RAG Application

A command-line Retrieval-Augmented Generation (RAG) application that lets you have a
grounded, in-character conversation with a PDF — as if you were speaking directly with
the author. Ask questions, push back, and the system defends its answers using the
actual retrieved text, not general knowledge dressed up as the source.

Supports both **text** and **voice** interaction, streamed LLM responses, and multiple
LLM providers through a common interface.

> Inspired by Socrates' critique of writing in Plato's *Phaedrus*: a written text cannot
> answer back. This project is an attempt to give it a voice.

---

## Overview

This project explores the core engineering behind a real RAG application, built by hand
rather than through a high-level framework, in order to actually understand each layer:

**PDF → Chunking → Vector Database → Retrieval → LLM → Streaming Response → Text / Audio**

Current capabilities:

- PDF-based retrieval grounded in the source text
- Retrieval-threshold filtering, so the system only answers from the document when the
  retrieved passages are genuinely relevant — otherwise it clearly flags that it's
  answering from general knowledge instead
- An "author persona" system prompt that stays in character, defends arguments when
  challenged, and adapts tone without abandoning its grounding rules
- Multiple LLM providers (Mistral, Google Gemini) behind a single common interface
- Streaming LLM responses
- Text mode and voice mode, selected per session
- Sentence-level text-to-speech with a producer/consumer audio pipeline, so playback
  doesn't wait for the full response to finish generating
- Conversation memory across turns

This is intentionally a CLI-first, modular backend, built before moving on to a
separate web-based version of the project.

---

## Architecture

```text
                         ┌─────────────────┐
                         │       PDF       │
                         └────────┬────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │  Text Extraction│
                         │     (PyPDF)     │
                         └────────┬────────┘
                                  │
                                  ▼
                       ┌─────────────────────┐
                       │   Text Chunking     │
                       │ RecursiveCharacter  │
                       │      Splitter       │
                       └──────────┬──────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │    ChromaDB     │
                         │  Vector Store   │
                         └────────┬────────┘
                                  │
                          User Question
                                  │
                                  ▼
                       ┌─────────────────────┐
                       │  Similarity Search   │
                       │      ChromaDB        │
                       │  + Distance Filter    │
                       └──────────┬──────────┘
                                  │
                                  ▼
                       ┌─────────────────────┐
                       │     RAG Prompt       │
                       │                      │
                       │  Context + Question  │
                       │   + Conversation     │
                       └──────────┬──────────┘
                                  │
                                  ▼
                 ┌────────────────────────────────┐
                 │          LLM Provider           │
                 │        (common interface)       │
                 │     ┌────────┐   ┌────────┐     │
                 │     │Mistral │   │ Gemini │     │
                 │     └────────┘   └────────┘     │
                 └───────────────┬────────────────┘
                                 │
                                 ▼
                          Streamed Response
                                 │
                    ┌────────────┴────────────┐
                    │                         │
                    ▼                         ▼
              ┌───────────┐           ┌──────────────┐
              │ Text Mode │           │  Voice Mode  │
              └─────┬─────┘           └──────┬───────┘
                    │                        │
                    ▼                        ▼
               Terminal                 Sentence
                 Output                 Detection
                                             │
                                             ▼
                                            TTS
                                             │
                                             ▼
                                      Audio Queue
                                        (Producer)
                                             │
                                             ▼
                                        Playback
                                        (Consumer)
```

---

## Features

### RAG Pipeline

- Extracts text from PDF documents
- Splits documents into overlapping chunks to preserve cross-page arguments
- Stores chunks in ChromaDB
- Performs similarity-based retrieval
- Filters retrieved chunks by distance threshold — if nothing relevant is found, the
  system says so explicitly instead of forcing a connection
- Injects only genuinely relevant passages into the LLM prompt

### Grounded, In-Character Responses

- Speaks as the intellectual voice of the document's author, in first person
- Defends the text's arguments when challenged, without folding under pressure alone
- Distinguishes clearly between claims grounded in the retrieved passages and general
  knowledge used to fill a gap — the latter is always flagged, never presented as if
  it were sourced from the document
- Adapts tone on request (politeness, simplicity) without treating that as a concession
  on the argument itself
- Handles greetings, farewells, meta-questions, and hostile input gracefully while
  staying in character

### Multiple LLM Providers

Supported via a common streaming interface, so the rest of the application never has to
know which provider is active:

- **Mistral**
- **Google Gemini**

Provider is selected at the start of each session.

### Streaming Responses

LLM responses are streamed token by token rather than waiting for the full response,
so the application can begin processing — and, in voice mode, begin speaking — before
generation finishes.

### Text Mode

The streamed response is printed directly to the terminal as it arrives.

### Voice Mode

1. Record a spoken question from the microphone
2. Transcribe it locally with Whisper
3. Retrieve relevant passages and generate a grounded response
4. Split the streamed response into sentences as they complete
5. Generate speech for each sentence and queue it
6. Play queued audio continuously via a producer/consumer pipeline, so audio generation
   for later sentences happens while earlier ones are still playing

---

## Tech Stack

| Component         | Technology                        |
|--------------------|-----------------------------------|
| Language           | Python                            |
| RAG                | Custom pipeline                   |
| Vector Database    | ChromaDB                          |
| PDF Processing     | PyPDF                             |
| Text Splitting     | LangChain Text Splitters          |
| LLM Providers      | Mistral, Google Gemini            |
| Speech-to-Text     | Local Whisper (faster-whisper)    |
| Text-to-Speech     | edge-tts                          |
| Audio Playback     | sounddevice, pydub                |
| Concurrency        | Python `threading`, `queue.Queue` |
| Configuration      | python-dotenv                     |

---

## Project Structure

```text
CLI-Based-RAG-Application/
│
├── main.py              # App entry point: ingestion, retrieval, conversation loop
├── stream_llm.py         # Common streaming interface across LLM providers
├── thread.py             # Producer/consumer audio pipeline
├── audio_add.py          # Speech-to-text and text-to-speech functions
├── system_prompt.txt     # Author-persona system prompt
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

**`main.py`** — PDF loading, text extraction, chunking, ChromaDB setup, retrieval,
prompt construction, provider selection, mode selection, and the main conversation loop.

**`stream_llm.py`** — Exposes a single function, `stream_llm(provider, system_prompt, prompt)`,
that returns a plain stream of text regardless of which provider is selected. The rest
of the application never needs to know provider-specific request or response formats.

**`thread.py`** — The voice pipeline: sentence detection from the streamed response,
TTS generation on a producer thread, a shared audio queue, playback on a consumer
thread, and cleanup of temporary audio files.

**`audio_add.py`** — Recording, Whisper transcription, and TTS generation helpers.

**`system_prompt.txt`** — The author-persona instructions, including grounding rules,
tone handling, and out-of-scope behavior.

---

## How the RAG Pipeline Works

```text
User:
"What does existentialism say about freedom?"
```

1. The question is embedded and sent to ChromaDB.
2. ChromaDB returns the most similar chunks, along with their distance scores.
3. Chunks above the distance threshold are discarded as not relevant.
4. Remaining chunks are inserted into the prompt:

```text
Context:
<retrieved, relevant passages only>

Conversation history:
<previous turns>

Question:
"What does existentialism say about freedom?"
```

5. The prompt is sent to the selected provider and streamed back.
6. If no chunks passed the relevance filter, the model is explicitly told no relevant
   passages were found, so it answers — if at all — clearly flagged as outside the
   source document.

---

## Audio Pipeline

Voice mode uses a producer/consumer architecture so TTS generation and playback happen
concurrently instead of sequentially.

**Producer** — reads the streamed LLM output, buffers it until a full sentence is
detected, generates speech for that sentence, and pushes the resulting audio onto a
queue.

**Consumer** — continuously pulls audio off the queue and plays it back-to-back,
deleting each temporary file once played.

This means the producer can keep generating audio for upcoming sentences while the
consumer is still playing an earlier one, instead of the whole pipeline waiting for
each step to fully finish before the next begins.

---

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/2022n02511-stack/CLI-Based-RAG-Application.git
cd CLI-Based-RAG-Application
```

### 2. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure API keys

Copy `.env.example` to `.env` and fill in your own keys:

```text
MISTRAL_API_KEY=your_mistral_api_key
GEMINI_API_KEY=your_gemini_api_key
```

`.env` is excluded from version control via `.gitignore` — never commit real API keys.
You only need a key for the provider(s) you actually plan to use.

---

## Running the Application

```bash
python main.py
```

You'll be asked to choose a provider:

```text
Select provider:
1. Mistral
2. Gemini
Provider:
```

Then a mode:

```text
Select the mode:
1. Text
2. Audio
Mode:
```

Then start asking questions about the configured document. To end the session, type
`exit` or `quit`.

### Example — Text Mode

```text
Provider: 1 (Mistral)
Mode: 1 (Text)

Ask anything:
> What does existentialism mean?

At its core, existentialism holds that existence precedes essence — we are not
born with a fixed nature, but define ourselves through our choices...
```

### Example — Voice Mode

```text
Provider: 2 (Gemini)
Mode: 2 (Audio)

Recording...
Recording done. Transcribing...

You said: "Explain existentialism"

[Generating response]
[Producer started — generating audio]
[Consumer started — playback beginning]
```

---

## Current Limitations

- PDF path is currently configured in code rather than passed as an argument
- Only one document is loaded per session
- Provider and mode are chosen once, at the start of a session
- No web interface yet — CLI only
- No authentication
- No persistent, multi-session vector database configuration
- Speech-to-text is not streamed in real time (recording is a fixed/blocking step)
- Audio pacing operates at the sentence level, not the word level

---

## Future Improvements

**Frontend** — a separate web-based version of this project is in progress, adding PDF
upload, a chat interface, streamed responses and voice in the browser, an evidence
panel showing retrieved source passages, and provider selection in the UI.

**RAG** — multiple document support, document management, reranking, metadata-based
filtering, and a persistent vector store.

**Voice** — streaming speech-to-text, lower-latency TTS, word-level audio pacing, and
voice activity detection instead of fixed-duration recording.

**LLM providers** — the existing provider abstraction makes it straightforward to add
further providers (e.g. OpenAI, Anthropic) later without changing the rest of the
application.

---

## Development Phases

1. **RAG foundation** — PDF ingestion, chunking, vector search, context retrieval, LLM generation
2. **Streaming** — LLM streaming, sentence detection, streaming text output
3. **Voice** — speech-to-text, text-to-speech, producer/consumer audio queue
4. **Multi-provider architecture** — common provider interface, SDK-based streaming
5. **Web application** *(separate project, in progress)* — frontend, PDF upload, chat interface, evidence panel, deployment

---

## What I Learned

This project was built to understand the actual engineering behind a RAG application,
rather than relying entirely on a high-level framework to hide the details. Areas
explored in depth:

- Document preprocessing and chunking strategy, including how naive chunking fragments
  long-form arguments across page boundaries
- Vector similarity search and retrieval-threshold tuning
- Prompt engineering for a persona that stays grounded, holds its position under
  challenge, and clearly flags claims that aren't sourced from the retrieved text
- LLM response streaming and provider abstraction across different SDKs
- Producer/consumer concurrency for real-time audio generation and playback
- Iterative debugging of LLM behavior through direct adversarial testing rather than
  assuming a prompt works because it reads well

---

## License

This project is intended for educational and portfolio purposes.
