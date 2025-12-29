import ollama as llama
import re
import json
from pathlib import Path

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def llm_semantic_comparison(buffer_a, buffer_b):
    # TODO: could be improved with input from the cosine similarity comparison as well -- works good enough for now though
    # will plan to do this for next semester
    def remove_think_section(text):
        # Uses regex to remove <think> section and its contents
        return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)

    def comparison_prompt(buffer_a, buffer_b, pass_text):
        try:
            prompt_path = PROMPTS_DIR / pass_text
            file = open(prompt_path, "r")
            system_prompt_text = file.read()
        except Exception:
            raise Exception(f"trouble opening system prompt file: {pass_text}")

        # NOTE: important to have the system prompt be the last thing the LLM reads
        system_prompt = f"""Given Input:\nText A: "{buffer_a}"\n\n---------------------------\nText B: "{buffer_b}"\n\n{system_prompt_text}"""
        return system_prompt

    first_pass_prompt = comparison_prompt(buffer_a, buffer_b, "prompts/first_pass.txt")
    second_pass_prompt = comparison_prompt(
        buffer_a, buffer_b, "prompts/second_pass.txt"
    )
    prompts = [first_pass_prompt, second_pass_prompt]
    responses = [None, None]

    for response_index, prompt in enumerate(prompts):
        server_response = llama.generate(
            model="deepseek-r1:latest", prompt=prompt, options={"temperature": 0.0}
        )
        print(server_response["response"])
        prompt_response = remove_think_section(server_response["response"])
        prompt_response = (
            prompt_response.replace("```json", "").replace("```", "").strip()
        )
        responses[response_index] = json.loads(prompt_response)

    # combine json into one response
    combined_json = {**responses[0], **responses[1]}

    try:
        print(f"COMBINED IS: {combined_json}")
        return combined_json
    except Exception:
        print("-" * 200)
        print(f"COULD NOT PARSE JSON STRING:\n{prompt_response}")
        print("-" * 200)
        return {}


# text_a = "Bob went to the mall to buy ice cream. He ate ice cream there. The mall had a lot of traffic."
# text_b = "Bob went to the mall. He ate ice cream there. The mall had a lot of traffic."
# output = llm_semantic_comparison(text_a, text_b)
# print(f'OUTPUT: {output}')

# missing = output['missing_info']
# extra = output['extra_info']
# print(f'Info in A that is NOT in B (A - B): {missing}')
# print(f'Info in B that is NOT in A (B - A): {extra}')
