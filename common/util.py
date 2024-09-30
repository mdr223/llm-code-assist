import requests
import logging
from bs4 import BeautifulSoup
from .cache import CACHE
from .colors import bcolors
import json
import ast
import typing as t
import googlesearch

LOGGER = logging.getLogger(__name__)

def fetch_page_content(url, length_limit=30000, body_only=True, cache_key=None):
    """
    Fetch the content of a webpage.
    """
    # Check the cache
    if cache_key is not None:
        cached = CACHE.get_prompt(cache_key, url)
        if cached is not None:
            LOGGER.info(f"{bcolors.OKBLUE}{bcolors.BOLD}Cache hit for {url}{bcolors.ENDC}")
            return cached
    # Fetch the page
    LOGGER.info(f"{bcolors.OKGREEN}{bcolors.BOLD}Fetching {url}{bcolors.ENDC}")
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")
    # Strip styles and scripts
    for tag in soup(["style", "script"]):
        tag.decompose()
    if body_only:
        content = soup.body
    else:
        content = soup
    content = content.get_text()
    if length_limit is not None:
        content = content[:length_limit]
    # Cache the result
    if cache_key is not None:
        CACHE.set_prompt(cache_key, url, content)
    return content

def gather_contents(urls: t.List[str], base_cache_key=None):
    contents = []
    for i, link in enumerate(urls):
        cache_key = f"{base_cache_key}_link{i}" if base_cache_key is not None else None
        content = fetch_page_content(link, cache_key=cache_key)
        contents.append((link, content))
    contents = [
            f"""
---
Link {i}: {link}
Content from the link {i}:
{content}
---
            """.strip() for i, (link, content) in enumerate(contents)
    ]
    contents = "\n".join(contents)
    return contents


def web_search(query: str, num_results=10, cache_key=None):
    """
    Perform a web search.
    """
    if cache_key is not None:
        cached = CACHE.get_prompt(cache_key, query)
        if cached is not None:
            LOGGER.info(f"{bcolors.OKBLUE}{bcolors.BOLD}Cache hit for {query}{bcolors.ENDC}")
            return json.loads(cached)
    LOGGER.info(f"{bcolors.OKGREEN}{bcolors.BOLD}Searching for {query}{bcolors.ENDC}")
    search_results = googlesearch.search(query, num_results=num_results, advanced=True, lang="en")
    results = []
    for result in search_results:
        print(result)
        results.append({
            "url": result.url,
            "title": result.title,
            "description": result.description
        })
    if cache_key is not None:
        CACHE.set_prompt(cache_key, query, json.dumps(results))
    return results


def parse_json_string(s: str, try_hard=False):
    """
    Parse a JSON response.
    """
    def safe_parse(s):
        try:
            return json.loads(s), True
        except json.JSONDecodeError as e:
            return e, False
    res, ok = safe_parse(s)
    if ok:
        return res
    if not try_hard:
        raise res
    # TODO: Try more tricks.
    new_s = s.replace("NULL", "\"NULL\"")
    res, ok = safe_parse(new_s)
    if ok:
        return res
    raise res



def run_code(code: str, code_vars: t.Dict[str, t.Any], fn_name: str):
    """
    Get the function definition from a code snippet.
    """
    tree = ast.parse(code)
    found = False
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            if node.name == fn_name:
                found = True
                break
    if not found:
        return None
    print(code)
    code_vars["typing"] = t
    code_vars["t"] = t
    exec(code, {}, code_vars)
    print(list(code_vars.keys()))
    final_result = code_vars["final_result"]
    return final_result
