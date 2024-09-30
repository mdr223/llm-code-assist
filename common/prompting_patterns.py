from .language_model import LANGUAGE_MODEL
from .util import web_search, fetch_page_content
from collections import OrderedDict
import json
import requests
import logging
import typing as t

LOGGER = logging.getLogger(__name__)

WEB_SEARCH_FILTER = """
I want to filter the search results to only include the top most relevant links.

Please provide the indices of the top most relevant links up to the requested number.
If there are no good links, provide an empty list.

Format the output as follows:
<reason>
```md
# Reasoning for your response.
```
</reason>

<list>
```json
[
    {
        "index": ...,
        "good_url": "Original/Transformed URL of the search result."
    }
]
```
</list>

Be sure to respect the tags (reason, list) and the JSON format.
"""


class PromptingPatterns:
    def __init__(self):
        pass


    def list_to_completion(
            self,
            system_msg: str, common_context: str, list_instructions: str, complete_instructions: str,
            list_id: str, item_key: str, delete_key: str,
            num_iterations: int, expected_iterations: int,
            list_tag: str="list"
        ):
        """
        Repeatedly ask the LLM to create and complete a list of items until it is sure that the list is complete.
        """
        current_list_dict = OrderedDict()
        for i in range(num_iterations):
            rule_name = f"{list_id}_{i}"
            instructions = list_instructions if i == 0 else complete_instructions
            if i >= expected_iterations:
                additional_note = "The list is almost certainly complete. I just need to be really sure. Return an empty if all is ok."
            else:
                additional_note = ""
            if i > 0:
                previous_output = json.dumps(list(current_list_dict.values()), indent=2)
                previous_output = f"\n---\nHere is the current list:\n{previous_output}\n---\n"
            else:
                previous_output = ""
            prompt = f"""{common_context}\n{previous_output}\nYour Task: {instructions}\n{additional_note}""".strip()
            if i == 2:
                with open("diff1", "w") as f:
                    f.write(prompt)
                    f.write(f"\n\ni={i}, expected_iterations={expected_iterations}, num_iterations={num_iterations}, {i > expected_iterations}")
            response = LANGUAGE_MODEL.invoke(prompt, cache_key=rule_name, system_msg=system_msg)
            # print(response)
            _, codeblocks, _ = LANGUAGE_MODEL.parse_standard_response(response, code_tag=list_tag)
            assert "list" in codeblocks, "Expected a list of completions."
            new_list = json.loads(codeblocks["list"])
            if len(new_list) == 0:
                break
            has_new_items = False
            for new_item in new_list:
                print(new_item)
                new_item_key = new_item[item_key].lower()
                # Check deletes.
                if delete_key is not None and new_item.get(delete_key, False) and new_item_key in current_list_dict:
                    has_new_items = True
                    del current_list_dict[new_item_key]
                # Check adds.
                if new_item_key not in current_list_dict:
                    has_new_items = True
                    current_list_dict[new_item_key] = new_item
            if not has_new_items:
                break
        return list(current_list_dict.values())


    def prompt_and_confirm(
        self,
        system_msg: str, common_context: str, initial_instructions: str, confirm_instructions: str,
        cache_key: str,
        num_iterations: int, expected_iterations: int,
        response_tag: str,
    ):
        """
        Repeatedly ask the LLM to create and confirm a list of items until it is sure that the list is complete.
        """
        prev_response = None
        confirmed = False
        for i in range(num_iterations):
            rule_name = f"{cache_key}_{i}"
            instructions = initial_instructions if i == 0 else confirm_instructions
            if i >= expected_iterations:
                additional_note = "The previous response is almost certainly complete. I just need to be really sure."
            else:
                additional_note = ""
            if i > 0:
                previous_output = f"\n---\nHere is the previous response:\n{prev_response}\n---\n"
            else:
                previous_output = ""
            prompt = f"""{common_context}\n{previous_output}Your Task: {instructions}\n{additional_note}""".strip()
            response = LANGUAGE_MODEL.invoke(prompt, cache_key=rule_name, system_msg=system_msg)
            _, codeblocks, _ = LANGUAGE_MODEL.parse_standard_response(response, code_tag=response_tag)
            if response_tag not in codeblocks:
                is_empty = True
            else:
                is_empty = len(codeblocks[response_tag].strip()) == 0
            if is_empty:
                confirmed = True
                break
            prev_response = response
        return prev_response, confirmed


    def search_web_context(
            self,
            system_msg: str, search_context: str, search_id: str,
            query: str, desired: str,
            num_search_results=1, max_content_length=30000
        ):
        """Generic function to search for web context and ask the LLM for refine it."""
        results = web_search(query, num_results=10, cache_key=f"search_{search_id}")
        results_context = []
        for i, result in enumerate(results):
            if "postgresqltutorial" in result["url"]:
                # For some reason, cannot fetch content from this site.
                continue
            results_context.append(f"""
---
Result index {i}: {result["url"]}
Title: {result["title"]}
Description: {result["description"]}
---
""")
        results_context = "\n".join(results_context)
        prompt = f"""
The search results:
{results_context}
---
{search_context}
---
The search query: {query}
The desired information: {desired}
I want the top {num_search_results} search results.
Your task: {WEB_SEARCH_FILTER}
        """.strip()
        response = LANGUAGE_MODEL.invoke(prompt, cache_key=search_id, system_msg=system_msg)
        _, codeblocks, _ = LANGUAGE_MODEL.parse_standard_response(response, code_tag="list")
        assert "list" in codeblocks, "Expected a list of indices."
        best_results = json.loads(codeblocks["list"])
        best_results_content = []
        curr_len = 0
        for i, result in enumerate(best_results):
            url = result["good_url"] if "good_url" in result else results[result["index"]]["url"]
            print(f"Fetching content for {url}")
            try:
                content = fetch_page_content(url)
                curr_len += len(content)                    
                best_results_content.append(f"\n___\nSearch result: {url}\n{content}\n___\n")
                if curr_len >= max_content_length:
                    break
            except requests.exceptions.HTTPError as e:
                LOGGER.error(f"Failed to fetch content for {url}")
                raise e
        best_results_content = "\n".join(best_results_content)
        return best_results_content
    

    def prompt_and_validate(self, system_msg: str, prompt: str, validation_fn, cache_key: str, num_attempts=2, with_error=False):
        """
        Prompt the LLM with a question and validate the response.
        """
        for attempt in range(num_attempts):
            attempt_key = f"{cache_key}_{attempt}"
            response = LANGUAGE_MODEL.invoke(prompt, cache_key=attempt_key, system_msg=system_msg)
            try:
                result = validation_fn(response)
                return result
            except ValueError as e:
                e_str = f"{e}"
            if not with_error:
                continue
            attempt_key = f"{cache_key}_{attempt}_retry"
            prompt = f"{prompt}\n\n\nYour previous failed as follows, do not repeat it: {e_str}"
            response = LANGUAGE_MODEL.invoke(prompt, cache_key=attempt_key, system_msg=system_msg)
            try:
                result = validation_fn(response)
                return result
            except ValueError as e:
                last_error = e

        raise ValueError(f"Failed to validate the response for {cache_key} after {num_attempts} attempts. Last error:\n{last_error}")

PROMPTING_PATTERNS = PromptingPatterns()