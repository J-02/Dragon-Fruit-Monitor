import json
import adafruit_hashlib as hashlib
import os
from setup import setup
import microcontroller
import gc

excluded_files = ['settings.toml', 'secrets.py']
excluded_dirs = ['__pycache__', '.fseventsd', '.idea', '.vscode', 'System Volume Information']

def gitupdate():
    # Update changed files from github
    owner = 'jonhenk'
    repo = 'Dragon-Fruit-Monitor'
    requests = setup(IO = False)


    def get_github_files(owner, repo):
        github_py_files = {}
        github_files = []
        url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/main?recursive=1"
        response = requests.get(url)
        data = json.loads(response.text)
        
        for item in data['tree']:
            if item['type'] == 'blob':
                if item['path'].endswith('.py') and '/' not in item['path']:
                    github_py_files[item['path']] = item['sha']
                else:
                    github_files.append(item['path'])
                
        return github_py_files, github_files

    def get_local_files(directory="."):
        local_files = []
        local_py_files = {}
        
        for filename in os.listdir(directory):
            # Manually join the directory and filename
            file_path = directory + "/" + filename if directory != "." else filename
            gc.collect()
            try:
                # Try to open the file to see if it's actually a file
                with open(file_path, 'rb') as f:
                
                    if directory == "." and filename.endswith('.py'):
                        content = f.read()
                        m = hashlib.sha1()
                        m.update(content)
                        sha = m.hexdigest()
                        local_py_files[file_path] = sha
                    else:
                        local_files.append(file_path)
                    
            except OSError:
                # This will catch the error if 'file_path' is a directory
                # Recursively get files from this directory
                local_files.extend(get_local_files(file_path)[0])
            except MemoryError:
                print(f"MemoryError occurred while processing {file_path}")
                
        return local_py_files, local_files


    def compare(github_py_files, github_files, local_py_files, local_files):  
        local_files = [f for f in local_files if not any(f.startswith(dir + '/') for dir in excluded_dirs)]
        github_files = [f for f in github_files if not any(f.startswith(dir + '/') for dir in excluded_dirs)]

        common_py_files = set(local_py_files.keys()) & set(github_py_files.keys())
        different_py_files = {file: (github_py_files[file], local_py_files[file]) 
                            for file in common_py_files if github_py_files[file] != local_py_files[file]}

        # Check if all the same files exist everywhere
        missing_on_github = set(local_files) - set(github_files) - set(excluded_files)
        missing_locally = set(github_files) - set(local_files)
        
        # Output results
        if different_py_files:
            print(f".py files with different hashes: {different_py_files}")

        if missing_on_github:
            print(f"Files present locally but missing on GitHub: {missing_on_github}")

        if missing_locally:
            print(f"Files present on GitHub but missing locally: {missing_locally}")

        if not different_py_files and not missing_on_github and not missing_locally:
            print("All files match.")

        
        # Compare .py files at the root for hash matching
    github_py_files, github_files = get_github_files(owner, repo)
    local_py_files, local_files = get_local_files()
    compare(github_py_files, github_files, local_py_files, local_files)  

    print(oo)
