import anthropic
import argparse
import chromadb
import openai
import os
import re


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
    parser = argparse.ArgumentParser(description="Compile a build file from natural language to code")
    parser.add_argument(
        "--build-file", default=None, help="path to the build file",
    )
    parser.add_argument(
        "--source-code", default=None, help="path to the code files",
    )
    parser.add_argument(
        "--num-code-files", default=3, help="number of relevant source code files to fetch"
    )
    parser.add_argument(
        "--language", default="Rust", help="language for the source code of the project",
    )
    args = parser.parse_args()

    # the user has to provide a build file and source directory
    if args.build_file is None:
        print("Please provide a build file")
        exit(1)

    if args.source_code is None:
        print("Please provide a path to the source code")
        exit(1)

    # parse args to set local variables
    build_file = args.build_file
    source_code = args.source_code
    language = args.language
    num_code_files = int(args.num_code_files)

    # update vector stores
    extensions = [".rs"] if language.lower() == "rust" else [".go"]
    update_collection(source_code, source_code, allowed_extensions=extensions)

    # get handles to collections
    chroma_client = chromadb.PersistentClient(path="chromadb")
    code_collection = chroma_client.get_collection(name=source_code)

    # read the build file
    with open(build_file, 'r') as f:
        build_file = f.read()

    # iterate over steps in the build file
    steps = build_file.split("STEP \d+\.\d+", flags=re.DOTALL)

    # query the collection for relevant source code
    results = code_collection.query(query_texts=[user_request], n_results=num_code_files)
    relevant_code_files = results['documents'][0]
    relevant_code_ids = results['ids'][0]
    relevant_code_str = ""
    for id, file in zip(relevant_code_ids, relevant_code_files):
        relevant_code_str += f"{id}\n-----\n{file}\n\n"

    # format the recommendation prompt
    codegen_prompt = CODEGEN_SYSTEM_PROMPT.format(
        language=language,
        user_request=user_request,
        relevant_docs=relevant_docs_str,
        relevant_code=relevant_code_str,
    )
    print(codegen_prompt)

    # send the prompt to the model
    client = anthropic.Anthropic(api_key=os.environ.get("TIM_ANTHROPIC_API_KEY"))
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        messages=[
            {"role": "user", "content": [{"type": "text", "text": codegen_prompt}]}
        ]
    )
    print(response.content[0].text)

    # record input and output
    os.makedirs(INPUT_CODE_DIR, exist_ok=True)
    next_input_num = len(os.listdir(INPUT_CODE_DIR))
    with open(os.path.join(INPUT_CODE_DIR, f"prompt-{next_input_num}.txt"), 'w') as f:
        f.write(codegen_prompt)

    os.makedirs(OUTPUT_CODE_DIR, exist_ok=True)
    next_codegen_num = len(os.listdir(OUTPUT_CODE_DIR))
    with open(os.path.join(OUTPUT_CODE_DIR, f"codegen-{next_codegen_num}.txt"), 'w') as f:
        f.write(response.content[0].text)
