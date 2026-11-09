"""Use the installed local image-comparer endpoint; save its unedited response."""
import argparse
import base64
import json
from pathlib import Path
import urllib.request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prompt', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--max-tokens', type=int, default=1000)
    parser.add_argument('images', nargs='+', type=Path)
    args = parser.parse_args()
    content = [{'type': 'text', 'text': args.prompt.read_text()}]
    for image in args.images:
        encoded = base64.b64encode(image.read_bytes()).decode()
        content.append({'type': 'image_url', 'image_url': {'url': 'data:image/png;base64,' + encoded}})
    payload = dict(model='qwen3.8-27b', messages=[
        {'role': 'system', 'content': 'You are image-comparer, an independent visual QA agent. Inspect the supplied pixels. Distinguish observations from hypotheses. Do not infer numerical geometry gate compliance from images. Return JSON only.'},
        {'role': 'user', 'content': content}], max_tokens=args.max_tokens, temperature=.1,
        chat_template_kwargs={'enable_thinking': False})
    request = urllib.request.Request('http://127.0.0.1:8308/v1/chat/completions',
                                     data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=900) as response:
        result = json.load(response)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(result['choices'][0]['message']['content'], flush=True)


if __name__ == '__main__':
    main()
