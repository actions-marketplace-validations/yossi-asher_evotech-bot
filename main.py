import os
from typing import List

import openai
import requests

model = 'ft:gpt-3.5-turbo-0613:microsoft::7s8kAVg6'

def get_latest_version(pkg_name: str) -> str:
    url = f'https://pypi.org/pypi/{pkg_name}/json'
    response = requests.get(url)
    response.raise_for_status()
    return response.json()['info']['version']


def get_pkg_version_from_requirements_line(line: str) -> (str | None, str | None):
    line = line.strip()
    if line.startswith('#'):
        package, version = None, None
    elif '>=' in line:
        package, version = line.split('>=')
    elif '==' in line:
        package, version = line.split('==')
    else:  # No version specified
        package, version = line, None
    return package, version


def get_curr_pkg_version(package_name: str, requirements_path: str = 'requirements.txt') -> str | None:
    with open(requirements_path) as requirements_file:
        for line in requirements_file:
            package, version = get_pkg_version_from_requirements_line(line)
            if package == package_name:
                return version
    raise Exception(f"Package {package_name} not found in requirements.txt")


def create_prompt(file_txt: str) -> List[dict]:
    prompt = []
    prompt.append({"role": "user", "content": f'{file_txt}'})
    return prompt


def update_requirements(package_name: str, new_version: str, requirements_path: str = 'requirements.txt'):
    with open(requirements_path, 'r') as requirements_file:
        lines = requirements_file.readlines()
    for i, line in enumerate(lines):
        package, version = get_pkg_version_from_requirements_line(line)
        if package == package_name:
            lines[i] = f'{package_name}=={new_version}\n'
            break

    with open(requirements_path, 'w') as requirements_file:
        requirements_file.writelines(lines)


def handle_py_file(path: str, pkg_old_ver: str, pkg_new_ver: str, pkg_name: str):
    with open(path, "r+") as f:
        content = f.read()
        prompt = create_prompt(content)
        new_file_code = openai_call(prompt, pkg_old_ver, pkg_new_ver, pkg_name)
        f.seek(0)
        f.write(new_file_code)
        f.truncate()


def openai_call(prompt: list[dict], old_ver, new_ver, name) -> str:
    system_message = {"role": "system",
                      "content": f"I will convert your code from version {old_ver} to version {new_ver} of the package {name}. Only the code changes are required, and no additional text"}
    prompt.insert(0, system_message)
    response = openai.ChatCompletion.create(
        model=model,
        messages=prompt
    )
    return response['choices'][0]['message']['content']


def main(pkg_name, pkg_old_ver, pkg_new_ver):
    for root, dirs, files in os.walk("."):
        for file in files:
            if file.endswith(".py"):
                handle_py_file(os.path.join(root, file), pkg_old_ver, pkg_new_ver, pkg_name)

    update_requirements(pkg_name, pkg_new_ver)


if __name__ == "__main__":
    supported_pkgs = ['numpy']
    for pkg_name in supported_pkgs:
        pkg_new_ver = get_latest_version(pkg_name)
        try:
            pkg_old_ver = get_curr_pkg_version(pkg_name)
        except Exception as e:
            print(e)

        if pkg_new_ver == pkg_old_ver:
            print(f"Package {pkg_name} is already up to date")
            continue

        print(f"Converting {pkg_name} from {pkg_old_ver} to {pkg_new_ver}")

        main(pkg_name, pkg_old_ver, pkg_new_ver)
