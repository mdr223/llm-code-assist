import anthropic
import argparse
import chromadb
import os

OUTPUT_UNIT_TEST_DIR = "unit-test-outputs"
INPUT_UNIT_TEST_DIR = "unit-test-inputs"
MODEL = "claude-3-5-sonnet-20240620"
UNIT_TEST_GEN_SYSTEM_PROMPT = """
You are an intelligent agent tasked with generating and/or modifying unit tests for a code base in order to implement a user request.

The system is divided into two parts:
- the system software, which contains the actual source code files (written in {language})
- the system documentation, which describes the purpose and desired implementation of the source code

Your job is to generate unit tests for new code which will be written and tested against these tests.
You may do one or more of the following in order to implement the user's request:
- create new unit test(s) in one or more existing test files
- edit unit test(s) in one or more existing files
- delete unit test(s) from one or more existing files

Your objective is to produce a valid code patch which can be applied directly to the file(s) you specify.

RELEVANT SYSTEM DOCS
--------------------
{relevant_docs}

RELEVANT SOURCE CODE
--------------------
{relevant_code}

RELEVANT RUST SOURCE CODE
-------------------------
{relevant_rust_code}

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

    # TODO: improve -- hard-coding attention over RustDB tests
    update_collection("rustdb-testgen", "rustdb-testgen", allowed_extensions=[".rs"])

    # get handles to collections
    chroma_client = chromadb.PersistentClient(path="chromadb")
    docs_collection = chroma_client.get_collection(name=system_docs)
    code_collection = chroma_client.get_collection(name=dbname)
    
    # TODO
    rust_code_collection = chroma_client.get_collection(name="rustdb-testgen")

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

    # query the collection for relevant source code from rust
    results = rust_code_collection.query(query_texts=[user_request], n_results=num_code_files)
    relevant_rust_code_files = results['documents'][0]
    relevant_rust_code_ids = results['ids'][0]
    relevant_rust_code_str = ""
    for id, file in zip(relevant_rust_code_ids, relevant_rust_code_files):
        relevant_rust_code_str += f"{id}\n-----\n{file}\n\n"

    # format the recommendation prompt
    unit_test_gen_prompt = UNIT_TEST_GEN_SYSTEM_PROMPT.format(
        language=language,
        user_request=user_request,
        relevant_docs=relevant_docs_str,
        relevant_code=relevant_code_str,
        relevant_rust_code=relevant_rust_code_str,
    )
    print(unit_test_gen_prompt)

    # send the prompt to the model
    client = anthropic.Anthropic(api_key=os.environ.get("TIM_ANTHROPIC_API_KEY"))
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        messages=[
            {"role": "user", "content": [{"type": "text", "text": unit_test_gen_prompt}]}
        ]
    )
    print(response.content[0].text)

    # record input and output
    os.makedirs(INPUT_UNIT_TEST_DIR, exist_ok=True)
    next_input_num = len(os.listdir(INPUT_UNIT_TEST_DIR))
    with open(os.path.join(INPUT_UNIT_TEST_DIR, f"prompt-{next_input_num}.txt"), 'w') as f:
        f.write(unit_test_gen_prompt)

    os.makedirs(OUTPUT_UNIT_TEST_DIR, exist_ok=True)
    next_unit_test_gen_num = len(os.listdir(OUTPUT_UNIT_TEST_DIR))
    with open(os.path.join(OUTPUT_UNIT_TEST_DIR, f"unit-test-gen-{next_unit_test_gen_num}.txt"), 'w') as f:
        f.write(response.content[0].text)
