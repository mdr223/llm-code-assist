from openai import OpenAI
import argparse
import chromadb
import os

OUTPUT_DEBUG_DIR = "debug-outputs"
INPUT_DEBUG_DIR = "debug-inputs"
MODEL = "gpt-4o"
CODE_DEBUGGER_SYSTEM_PROMPT = """
You are an intelligent agent tasked with debugging code and compilation errors for a code base.

The system is divided into two parts:
- the system software, which contains the actual source code files (written in {language})
- the system documentation, which describes the purpose and desired implementation of the source code

Your job is to debug code and/or compilation errors and suggest fixes to the code base which do one or more of the following:
- create new code in one or more existing files
- edit code in one or more existing files
- delete code from one or more existing files

Your objective is to produce a valid code patch which can be applied directly to the file(s) you specify.

RELEVANT SYSTEM DOCS
--------------------
{relevant_docs}

RELEVANT SOURCE CODE
--------------------
{relevant_code}

USER REQUEST
------------
{user_request}

YOUR CODE PATCH(ES)
-------------------

"""

def update_collection(name, source_path, allowed_extensions=None):
    chroma_client = chromadb.PersistentClient(path="chromadb")
    try:
        collection = chroma_client.get_collection(name=name)
    except:
        collection = chroma_client.create_collection(name=name)

    texts, ids = [], []
    for path, _, filenames in os.walk(source_path):
        for filename in filenames:
            if allowed_extensions and not any([filename.endswith(ext) for ext in allowed_extensions]):
                continue

            try:
                filepath = os.path.join(path, filename)
                with open(filepath, 'r') as f:
                    file_data = f.read()
                    texts.append(file_data)
                    ids.append(filepath)
            except:
                import pdb; pdb.set_trace()
    
    collection.upsert(documents=texts, ids=ids)


if __name__ == "__main__":
    # parse arguments
    parser = argparse.ArgumentParser(description="Recommend system-level changes")
    parser.add_argument(
        "--prompt", default=None, help="path to a text prompt w/the input for the recommender agent"
    )
    parser.add_argument(
        "--num-docs", default=3, help="number of relevant system documents to fetch"
    )
    parser.add_argument(
        "--num-code-files", default=3, help="number of relevant source code files to fetch"
    )
    parser.add_argument(
        "--name", default="rustdb", help="name for the project",
    )
    parser.add_argument(
        "--language", default="Rust", help="language for the source code of the project",
    )
    args = parser.parse_args()

    # the user has to provide a prompt
    if args.prompt is None:
        print("Please provide a prompt")
        exit(1)

    # read the prompt into a user request
    with open(args.prompt, 'r') as f:
        user_request = f.read()

    # parse args to set local variables
    dbname = args.name
    system_docs = f"system-docs-{dbname}"
    language = args.language
    num_docs = int(args.num_docs)
    num_code_files = int(args.num_code_files)

    # update vector stores
    extensions = [".rs"] if language.lower() == "rust" else [".go"]
    update_collection(system_docs, system_docs)
    update_collection(dbname, dbname, allowed_extensions=extensions)

    # get handles to collections
    chroma_client = chromadb.PersistentClient(path="chromadb")
    docs_collection = chroma_client.get_collection(name=system_docs)
    code_collection = chroma_client.get_collection(name=dbname)

    # query the collection for relevant docs
    results = docs_collection.query(query_texts=[user_request], n_results=num_docs)
    relevant_docs = results['documents'][0]
    relevant_doc_ids = results['ids'][0]
    relevant_docs_str = ""
    for id, doc in zip(relevant_doc_ids, relevant_docs):
        relevant_docs_str += f"{id}\n-----\n{doc}\n\n"

    # query the collection for relevant source code
    results = code_collection.query(query_texts=[user_request], n_results=num_code_files)
    relevant_code_files = results['documents'][0]
    relevant_code_ids = results['ids'][0]
    relevant_code_str = ""
    for id, file in zip(relevant_code_ids, relevant_code_files):
        relevant_code_str += f"{id}\n-----\n{file}\n\n"

    # format the recommendation prompt
    code_debug_prompt = CODE_DEBUGGER_SYSTEM_PROMPT.format(
        language=language,
        user_request=user_request,
        relevant_docs=relevant_docs_str,
        relevant_code=relevant_code_str,
    )
    print(code_debug_prompt)

    # send the prompt to the model
    client = OpenAI(api_key=os.environ.get("TIM_OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
                # {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": code_debug_prompt}
            ]
    )
    print(response.choices[0].message.content)

    # record input and output
    os.makedirs(INPUT_DEBUG_DIR, exist_ok=True)
    next_input_num = len(os.listdir(INPUT_DEBUG_DIR))
    with open(os.path.join(INPUT_DEBUG_DIR, f"prompt-{next_input_num}.txt"), 'w') as f:
        f.write(code_debug_prompt)

    os.makedirs(OUTPUT_DEBUG_DIR, exist_ok=True)
    next_code_debug_num = len(os.listdir(OUTPUT_DEBUG_DIR))
    with open(os.path.join(OUTPUT_DEBUG_DIR, f"code-debug-{next_code_debug_num}.txt"), 'w') as f:
        f.write(response.choices[0].message.content)
