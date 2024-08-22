from openai import OpenAI
import argparse
import chromadb
import os
import subprocess

OUTPUT_REC_DIR = "recommendation-outputs"
INPUT_REC_DIR = "recommendation-inputs"
MODEL = "gpt-4o"
RECOMMENDER_SYSTEM_PROMPT = """
You are an intelligent agent tasked with recommending system-level changes to a code base in order to implement a user request.

The system is divided into two parts:
- the system software, which contains the actual source code files (written in {language})
- the system documentation, which describes the purpose and desired implementation of the source code

Your job is to recommend *high-level* decisions related to:
- the creation, deletion, or refactoring of (one or more) system software modules
- the creation, deletion, or editing of (one or more) system software files
- the creation, deletion, or editing of (one or more) system documentation pages

You may suggest ideas for how to implement code changes, but DO NOT generate code. Your objective is to produce plans for updating the system.

SOURCE CODE LAYOUT
------------------
{source_code_layout}

SYSTEM DOCS LAYOUT
------------------
{system_docs_layout}

RELEVANT SYSTEM DOCS
--------------------
{relevant_docs}

USER REQUEST
------------
{user_request}

YOUR RECOMMENDATIONS
--------------------
1. 
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

    # get tree layouts for rustdb and system-docs
    source_out = subprocess.run(f"tree {dbname} --gitfile ignore-files.txt --noreport".split(" "), capture_output=True)
    source_code_layout = source_out.stdout.decode("utf-8")
    docs_out = subprocess.run(f"tree {system_docs} --noreport".split(" "), capture_output=True)
    system_docs_layout = docs_out.stdout.decode("utf-8")

    # update vector store
    update_collection(system_docs, system_docs)

    # get handles to collections
    chroma_client = chromadb.PersistentClient(path="chromadb")
    docs_collection = chroma_client.get_collection(name=system_docs)

    # query the collection for relevant docs
    results = docs_collection.query(query_texts=[user_request], n_results=num_docs)
    relevant_docs = results['documents'][0]
    relevant_ids = results['ids'][0]
    relevant_docs_str = ""
    for id, doc in zip(relevant_ids, relevant_docs):
        relevant_docs_str += f"{id}\n-----\n{doc}\n\n"

    # format the recommendation prompt
    recommendation_prompt = RECOMMENDER_SYSTEM_PROMPT.format(
        language=language,
        user_request=user_request,
        source_code_layout=source_code_layout,
        system_docs_layout=system_docs_layout,
        relevant_docs=relevant_docs_str,
    )
    print(recommendation_prompt)

    # send the prompt to the model
    client = OpenAI(api_key=os.environ.get("TIM_OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
                # {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": recommendation_prompt}
            ]
    )
    print(response.choices[0].message.content)

    # record input and output
    os.makedirs(INPUT_REC_DIR, exist_ok=True)
    next_input_num = len(os.listdir(INPUT_REC_DIR))
    with open(os.path.join(INPUT_REC_DIR, f"prompt-{next_input_num}.txt"), 'w') as f:
        f.write(recommendation_prompt)

    os.makedirs(OUTPUT_REC_DIR, exist_ok=True)
    next_rec_num = len(os.listdir(OUTPUT_REC_DIR))
    with open(os.path.join(OUTPUT_REC_DIR, f"recommendation-{next_rec_num}.txt"), 'w') as f:
        f.write(response.choices[0].message.content)
