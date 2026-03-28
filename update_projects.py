import os
import requests
import re

USERNAME = "Mohit-cmd-jpg"
TOKEN = os.getenv("GITHUB_TOKEN")

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# 1. Try to fetch explicit pinned items via GraphQL
query = """
{
  user(login: "%s") {
    pinnedItems(first: 4, types: REPOSITORY) {
      nodes {
        ... on Repository {
          name
          description
          url
          defaultBranchRef {
            name
          }
        }
      }
    }
  }
}
""" % USERNAME

response = requests.post("https://api.github.com/graphql", json={"query": query}, headers=headers)
data = response.json()
repos = data.get("data", {}).get("user", {}).get("pinnedItems", {}).get("nodes", [])

# 2. Fallback if no pinned repos exist on profile, get the most recently pushed repos
if not repos:
    print("No pinned repos found or API rate limited. Fetching top 4 recently pushed repos instead.")
    rest_url = f"https://api.github.com/users/{USERNAME}/repos?sort=pushed&per_page=10"
    response = requests.get(rest_url, headers=headers)
    rest_repos = response.json()
    
    repos = []
    # filter out forks inside the python loop
    if isinstance(rest_repos, list):
        for r in rest_repos:
            if not r.get("fork"):
                repos.append({
                    "name": r["name"],
                    "description": r["description"],
                    "url": r["html_url"],
                    "defaultBranchRef": {"name": r["default_branch"]}
                })
        repos = repos[:4]
    else:
        print("API Limit reached or error:", rest_repos)
        exit(1)

if not repos:
    print("No repositories found to process.")
    exit(0)

# 3. Generate Markdown content
html_content = '<table align="center" width="100%">\n'

# Process arrays into pairs of 2 for table cells
for i in range(0, len(repos), 2):
    html_content += '  <tr>\n'
    for j in range(2):
        if i + j < len(repos):
            repo = repos[i + j]
            name = repo['name']
            desc = repo['description'] or ""
            url = repo['url']
            branch = repo.get('defaultBranchRef', {}).get('name', 'main') if repo.get('defaultBranchRef') else 'main'
            
            # Check if custom frontend image exists in repo root
            img_url = ""
            for img in ["frontpage.png", "dashboard.png", "frontpage.jpg", "dashboard.jpg", "frontpage.webp"]:
                check_url = f"https://raw.githubusercontent.com/{USERNAME}/{name}/{branch}/{img}"
                img_resp = requests.head(check_url, headers=headers)
                if img_resp.status_code == 200:
                    img_url = f"https://github.com/{USERNAME}/{name}/raw/{branch}/{img}"
                    break
            
            # If no image is specifically uploaded by you in the repo root, fallback to github stats or opengraph image
            if not img_url:
                img_url = f"https://opengraph.githubassets.com/1/{USERNAME}/{name}"

            html_content += f'''    <td width="50%" valign="top">
      <a href="{url}">
        <img src="{img_url}" width="100%" alt="{name}" style="border-radius: 8px; margin-bottom: 5px;"/>
      </a>
      <h3 style="margin: 0;"><a href="{url}">{name}</a></h3>
      <p style="margin-top: 5px;"><i>{desc}</i></p>
    </td>\n'''
        else:
            html_content += '    <td width="50%"></td>\n'
    html_content += '  </tr>\n'

html_content += '</table>'

# 4. Read the current README.md
with open("README.md", "r", encoding="utf-8") as file:
    readme = file.read()

# 5. Inject generated content between markers
marker_start = "<!-- PROJECTS_START -->"
marker_end = "<!-- PROJECTS_END -->"

pattern = re.compile(rf"({marker_start}).*?({marker_end})", flags=re.DOTALL)

if not pattern.search(readme):
    print("Could not find replacement markers in README.md")
    exit(1)

new_readme = pattern.sub(rf"\1\n{html_content}\n\2", readme)

# 6. Save the modified README.md
with open("README.md", "w", encoding="utf-8") as file:
    file.write(new_readme)

print("Successfully updated README.md with dynamic projects!")
