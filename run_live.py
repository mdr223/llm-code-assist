#!/usr/bin/env python3

"""
This module contains functions for running a live inference session on a GitHub issue.
It clones the repository associated with the issue, builds a BM25 retrieval index, and
generates a prompt for the user to interact with the model. The output is saved to a
specified directory.
"""
import json
import subprocess
from pathlib import Path
from ghapi.all import GhApi
import os
import re
import time
import torch
from git import Repo
from pathlib import Path
from datetime import datetime
from tqdm.auto import tqdm
from harness.constants import TESTS_PASSED
from make_datasets.utils import ContextManager, string_to_bool, extract_diff, extract_minimal_patch
from make_datasets.create_instance import (
    PROMPT_FUNCTIONS,
    TOKENIZER_FUNCS,
    make_code_text,
    ingest_files,
)
from run_api import call_chat, call_anthropic
from sentence_transformers import SentenceTransformer
import logging
from argparse import ArgumentParser

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# DEFINITIONS
INSTANCE_RE = re.compile('(.*)__(.*)-(.*)', re.DOTALL)


def clone_repo(repo, root_dir, token):
    """
    Clones a GitHub repository to a specified directory.

    Args:
        repo (str): The GitHub repository to clone.
        root_dir (str): The root directory to clone the repository to.
        token (str): The GitHub personal access token to use for authentication.

    Returns:
        Path: The path to the cloned repository directory.
    """
    repo_dir = Path(root_dir, f"repo__{repo.replace('/', '__')}")

    if not repo_dir.exists():
        repo_url = f"https://{token}@github.com/{repo}.git"
        logger.info(f"Cloning {repo} {os.getpid()}")
        Repo.clone_from(repo_url, repo_dir)
    return repo_dir


def get_problem_statement(owner, repo, issue_num, ghapi, include_comments=False):
    issue = ghapi.issues.get(owner, repo, issue_num)
    issue_text = "\n".join([issue.title, issue.body])
    # Solved issues may include comments that give answers away too much
    if include_comments:
        all_comments = list(ghapi.issues.list_comments(owner, repo, issue_num))
        comments = [comment.body for comment in all_comments]
        comment_text = "Comment: " if comments else "" + "\nComment:".join(comments)
        issue_text += "\n" + comment_text
    return issue_text


def get_readme_files(repo_path):
    files = list(Path(repo_path).iterdir())
    files = list(filter(lambda x: x.is_file(), files))
    files = list(filter(lambda x: x.name.lower().startswith("readme"), files))
    if files:
        files = sorted(files, key=lambda x: len(x.name))
        files = [files[0]]
    return [Path(file).relative_to(repo_path).as_posix() for file in files]


def retrieve_top_k_files(issue_context: str, k: int):
    # load embedding model
    model = SentenceTransformer("all-MiniLM-L6-v2")

    # compute embedding for the issue context
    query_embedding = model.encode(issue_context)

    # compute embedding for each file in codebase
    all_filepaths, all_file_data = [], []
    for root, _, files in os.walk('.'):
        for file in files:
            if any([file.endswith(suffix) for suffix in ['.py', '.md', '.sql', '.txt']]): 
                filepath = os.path.join(root, file)
                all_filepaths.append(filepath)
                try:
                    with open(filepath, 'r') as f:
                        data = f.read()
                        all_file_data.append(data)
                except:
                    import pdb
                    pdb.set_trace()

    # compute file embeddings
    file_embeddings = model.encode(all_file_data)

    # compute similarity between query and file embeddings
    similarities = model.similarity(query_embedding, file_embeddings)

    # get indices of top-k similar files
    top_k_indices = set(torch.topk(similarities.flatten(), k=k).indices.tolist())

    # filter for top files' data and return
    top_k_files = [
        {"docid": fp, "file_contents": file_data}
        for idx, (fp, file_data) in enumerate(zip(all_filepaths, all_file_data))
        if idx in top_k_indices
    ]

    return top_k_files

def make_instance(
    owner,
    repo,
    query,
    commit,
    root_dir,
    token,
    instance_id,
):
    """
    Creates an instance for a given query and repository.

    Args:
        owner (str): The owner of the repository.
        repo (str): The name of the repository.
        query (str): The query to search for.
        commit (str): The commit hash to use.
        root_dir (str): The root directory to clone the repository to.
        token (str): The GitHub token to use for authentication.
        instance_id (int): The ID of the instance.

    Returns:
        dict: The instance.
    """
    instance = {"instance_id": instance_id, "problem_statement": query}
    logger.info(f"Cloning repo {owner}/{repo}")
    repo_dir = clone_repo(f"{owner}/{repo}", root_dir, token)
    if commit is None:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=repo_dir
        ).decode("utf-8").strip()

    return instance, repo_dir, commit

def retriever_agent(
    instance,
    query,
    repo_dir,
    commit,
    tokenizer,
    tokenizer_func,
    prompt_style,
    max_context_len,
    include_readmes,
):
    with ContextManager(repo_dir, commit) as cm:
        if include_readmes:
            readmes = get_readme_files(cm.repo_path)
        else:
            readmes = list()
        instance["readmes"] = ingest_files(readmes)

        hits = retrieve_top_k_files(issue_context=query, k=3)

        instance["file_contents"] = dict()
        base_text_inputs = PROMPT_FUNCTIONS[prompt_style](instance)
        base_text_input_length = len(tokenizer_func(base_text_inputs, tokenizer))
        instance["file_contents"] = {x["docid"]: x["file_contents"] for x in hits}
        cur_input_len = base_text_input_length
        include_files = list()
        for filename in [x["docid"] for x in hits]:
            content = make_code_text({filename: instance["file_contents"][filename]})
            tokens = tokenizer_func(content, tokenizer)
            if cur_input_len + len(tokens) < max_context_len:
                include_files.append(filename)
                cur_input_len += len(tokens)
        logger.info(
            f"Including {len(include_files)} files in context with {cur_input_len} tokens:\n"
            + "\n\t".join(sorted(include_files))
        )
        instance["file_contents"] = {
            filename: instance["file_contents"][filename] for filename in include_files
        }
        instance["text_inputs"] = PROMPT_FUNCTIONS[prompt_style](instance)
        return instance

def codegen_agent(model_name, inputs):
    logger.info(f"Calling model {model_name}")
    start = time.time()
    if model_name.startswith("gpt"):
        import openai
        openai.api_key = os.environ.get("OPENAI_API_KEY", None)
        response, _ = call_chat(
            model_name, inputs, use_azure=False, temperature=0, top_p=1
        )
        completion = response.choices[0]["message"]["content"]
        logger.info(f'Generated {response.usage.completion_tokens} tokens in {(time.time() - start):.2f} seconds')
    else:
        from anthropic import Anthropic
        api_key = os.environ.get("ANTHROPIC_API_KEY", None)
        anthropic = Anthropic(api_key=api_key)
        response = call_anthropic(
            inputs, anthropic, model_name, temperature=0, top_p=1
        )
        completion = response.completion
    
    return completion

def parse_issue_url(issue_url):
    issue_pat = re.compile(r"github\.com\/(.+?)\/(.+?)\/issues\/(\d+)")
    match = issue_pat.search(issue_url)
    if not match:
        raise ValueError(
            f"issue_url ({issue_url}) does not seem to be a valid issue url."
            + "\nPlease use url like https://github.com/owner/repo/issues/12345"
        )
    owner, repo, issue_num = match.groups()
    return owner, repo, issue_num


def main(
    model_name,
    prompt_style,
    instance_id,
    base_commit,
    max_context_length,
    output_dir,
    root_dir,
    include_readmes,
):
    if base_commit is not None and len(instance_id) != len(base_commit):
        raise ValueError(
            f"Must provide either no base commits or one base commit per issue url"
        )
    if base_commit is None:
        base_commit = [None] * len(instance_id)

    # for now, only process a single instance_id / base_commit
    instance_id = instance_id[0]
    base_commit = base_commit[0]

    gh_token = os.environ.get("GITHUB_TOKEN", None)
    if gh_token is not None:
        logger.warning(f'Using GitHub token: {"*" * 8}{gh_token[-4:]}')
    gh = GhApi(token=gh_token)
    tokenizer, tokenizer_func = TOKENIZER_FUNCS["cl100k"]

    # TODO: convert to compound ai system
    # owner, repo, issue_num = parse_issue_url(issue)
    match = INSTANCE_RE.match(instance_id)
    owner, repo, issue_num = match.group(1), match.group(2), match.group(3)
    problem_statement = get_problem_statement(owner, repo, int(issue_num), gh)
    instance_id = f"{owner}__{repo}-{issue_num}"
    logger.info(f"Creating instance {instance_id}")
    instance, repo_dir, commit = make_instance(
        owner,
        repo,
        problem_statement,
        base_commit,
        root_dir,
        gh_token,
        instance_id,
    )

    # call retriever agent
    instance = retriever_agent(
        instance,
        problem_statement,
        repo_dir,
        commit,
        tokenizer,
        tokenizer_func,
        prompt_style,
        max_context_length,
        include_readmes,
    )

    # call codegen agent
    inputs = instance["text_inputs"]
    completion = codegen_agent(model_name, inputs)

    # extract answer
    model_patch = extract_diff(completion)
    minimal_patch = extract_minimal_patch(model_patch)
    output = {
        "instance_id": instance_id,
        "response": completion,
        "problem_statement": problem_statement,
        "text_inputs": inputs,
        "model_patch": model_patch,
        "minimal_patch": minimal_patch,
        "model_name_or_path": model_name,
    }

    # write answer to file
    os.makedirs(output_dir, exist_ok=True)
    output_file = Path(
        output_dir,
        f'{model_name}__{prompt_style}__{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.jsonl',
    )
    with open(output_file, "+a") as f:
        print(json.dumps(output), file=f, flush=True)
    logger.info(f"Wrote output to {output_file}")

    # invoke evaluation
    _ = subprocess.check_output(
        ["python", "harness/run_evaluation.py", "--predictions_path", str(output_file), "--log_dir", "eval-logs", "--swe_bench_tasks", "swe-bench-tasks.jsonl", "--testbed", "testbed"]
    ).decode("utf-8").strip()

    # check output for string indicating success
    success = False
    with open(f'eval-logs/{model_name}/{instance_id}.{model_name}.eval.log', 'r') as f:
        output = f.read()
        for line in output[-10:]:
            if TESTS_PASSED in line:
                success = True
                break

    print(f"SUCCESS: {success}")

if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--model_name", type=str)
    parser.add_argument(
        "--prompt_style", type=str, choices=PROMPT_FUNCTIONS.keys(), default="style-3"
    )
    parser.add_argument("--instance-id", type=str, nargs="+")
    parser.add_argument("--base_commit", type=str, nargs="+")
    parser.add_argument("--max_context_length", type=int, default=16_000)
    parser.add_argument("--output_dir", type=str, default="./live_outputs")
    parser.add_argument("--root_dir", type=str, default="./run_live_data")
    parser.add_argument("--include_readmes", type=string_to_bool, default=False)
    args = parser.parse_args()
    main(**vars(args))
